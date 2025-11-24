import socket
import json
import threading
from typing import Callable, Optional

from backend.DB.models.models import User
from typing import Callable, Optional

# peer to peer code
def connectToDriver(ip: str)->socket.socket:
    currentSocket : socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    currentSocket.connect((ip, 9980))
    return currentSocket

def start_driver_listener(on_connect: Optional[Callable[[socket.socket], None]] = None):
    """
    Opens a listening socket for P2P communication.
    The OS chooses a free port automatically.
    """
    global DRIVER_LISTEN_SOCKET
    if DRIVER_LISTEN_SOCKET is not None:
        return DRIVER_LISTEN_SOCKET

    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_socket.bind(("0.0.0.0", 9980))  # 0 → auto-assign free port
    listen_socket.listen()
    DRIVER_LISTEN_SOCKET = listen_socket

    # Run in a thread so we can accept multiple connections
    threading.Thread(target=listen_loop, args=(listen_socket, on_connect), daemon=True).start()
    return listen_socket


def stop_driver_listener():
    """
    Close the driver listening socket if it is running.
    """
    global DRIVER_LISTEN_SOCKET
    if DRIVER_LISTEN_SOCKET is not None:
        try:
            DRIVER_LISTEN_SOCKET.close()
        except:
            pass
        DRIVER_LISTEN_SOCKET = None


def listen_loop(listen_socket: socket.socket, on_connect: Optional[Callable[[socket.socket], None]] = None):
    """Accepts incoming P2P connections from passengers."""

    while True:
        try:
            connection, client_address = listen_socket.accept()
        except OSError:
            # socket was likely closed
            break
        clientP : User = User()
        clientP.set_connection(connection)
        clientP.ip = client_address[0]
        clientP.port = client_address[1]
        if on_connect:
            # Chat UI will own this socket; don't spawn a competing reader
            on_connect(connection)
        else:
            # Fallback: just log incoming data
            threading.Thread(target=handle_peer, args=(connection,), daemon=True).start()

def sendMsg(connection: socket.socket, msg: str)->None:
    connection.send(msg.encode('utf-8'))
    if connection.recv(1024).decode('utf-8') != "1":
        raise RuntimeError("Something went wrong when sending the message to the passenger")


def handle_peer(peer_conn):
    """Handles the communication with one passenger."""
    while True:
        data = peer_conn.recv(1024)
        if not data:
            break
        print("Received from passenger:", data.decode("utf-8"))

    peer_conn.close()

## driver related code

def sendMessageToDriver(driverSocket: socket.socket, msg: str)->None:
    driverSocket.send(msg.encode('utf-8'))
    if driverSocket.recv(1024).decode('utf-8') != "1":
        raise RuntimeError("Something went wrong when sending the message to the driver")

def driverReceiveMessage(driverSocket: socket.socket)->str:
    data = driverSocket.recv(1024).decode('utf-8')
    driverSocket.send("1".encode('utf-8'))
    return data


# server related code
def connectToServer(ipServer: str)->socket.socket:
    client : socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((ipServer, 9999))
    return client

def changeMsg(client: socket.socket)->None:
    client.send("change".encode('utf-8'))
    msg = client.recv(1024).decode('utf-8') != "1"

def send_schedule_to_server(client: socket.socket,
                            weekday: int,
                            depart_time: str,
                            direction: str) -> bool:
    """
    Sends a schedule to the server as JSON.
    The server uses the authenticated user's id from the connection.
    """
    client.send("schedule".encode("utf-8"))
    if client.recv(1024).decode("utf-8").strip() != "1":
        raise RuntimeError("Something went wrong when signaling schedule addition to the server")

    payload = {
        "action": "add_schedule",
        "weekday": weekday,           # 0..6
        "depart_time": depart_time,   # "HH:MM"
        "direction": direction,       # "toAUB" / "fromAUB"
    }

    data = json.dumps(payload).encode("utf-8")
    client.send(data)

    # Wait for ack
    response = client.recv(1024).decode("utf-8").strip()
    return response == "1"


def update_location_on_server(
    client: socket.socket,
    latitude: float | None,
    longitude: float | None,
    city: str | None,
    country: str | None,
    area: str | None,
) -> bool:
    """
    Send latest geolocation to the server.
    """
    client.send("update_location".encode("utf-8"))
    try:
        ack = client.recv(1).decode("utf-8", errors="ignore")
        if ack != "1":
            print("Warning: unexpected ACK when starting location update")
    except Exception as e:
        print("Warning: failed to read ACK when starting location update:", e)

    payload = {
        "latitude": latitude,
        "longitude": longitude,
        "city": city,
        "country": country,
        "area": area,
    }
    client.send(json.dumps(payload).encode("utf-8"))
    try:
        ack = client.recv(1).decode("utf-8", errors="ignore")
        return ack == "1"
    except Exception as e:
        print("Warning: failed to read final ACK after location update:", e)
        return False


def send_rating(client: socket.socket, target_username: str, stars: int, comment: str = "") -> bool:
    """
    Send a rating for target_username.
    """
    client.send("rate".encode("utf-8"))
    try:
        ack = client.recv(1).decode("utf-8", errors="ignore")
        if ack != "1":
            print("Warning: unexpected ACK when starting rating")
    except Exception as e:
        print("Warning: failed to read ACK when starting rating:", e)

    payload = {
        "target_username": target_username,
        "stars": stars,
        "comment": comment or "",
    }
    client.send(json.dumps(payload).encode("utf-8"))
    try:
        ack = client.recv(1).decode("utf-8", errors="ignore")
        return ack == "1"
    except Exception as e:
        print("Warning: failed to read rating ACK:", e)
        return False


# Single global for listener socket
DRIVER_LISTEN_SOCKET: socket.socket | None = None

def sendCredentials(client: socket.socket, payload: dict) -> bool:
    """
    Sends the given JSON payload to the server.
    payload MUST be a Python dict already containing
    whatever fields you want (login, username, password, etc.).

    Returns True if server replies with "1", else False.
    """

    try:
        # Convert dict → JSON bytes
        data = json.dumps(payload).encode("utf-8")

        # Send to server
        client.sendall(data)

        # Read server reply ("1" or "0")
        response = client.recv(1024).decode("utf-8").strip()
        return response == "1"

    except Exception as e:
        print("Error sending JSON:", e)
        return False


# requesting driver/passenger
def requestOther(
    client: socket.socket,
    area_filter: str | None = None,
    target: str = "drivers",
    min_rating: float | None = None,
    depart_time: str | None = None,
) -> None:
    """
    area_filter:
        None → use server default (user area)
        "all" → request all drivers
        "<AreaName>" → request drivers in that area
    target:
        "drivers"    → passenger requesting available drivers
        "passengers" → driver requesting rider list
    min_rating:
        None → no rating filter
        N    → only drivers with rating >= N
    depart_time:
        None → ignore time preference
        "HH:MM" → request drivers near that time
    """
    area_value = (area_filter or "").strip()
    parts = ["request", target, area_value]
    if min_rating is not None:
        parts.append(f"min_rating={min_rating}")
    if depart_time:
        parts.append(f"depart_time={depart_time}")
    msg = "|".join(parts)
    client.send(msg.encode("utf-8"))
    try:
        ack = client.recv(1)  # read only the ack byte to avoid mixing with payload
        if ack.decode("utf-8", errors="ignore") != "1":
            print("Warning: unexpected ACK when requesting others")
    except Exception as e:
        print("Warning: failed to read ACK when requesting others:", e)
    


def receiveOther(client: socket.socket)->list[dict]:
    data_bytes = client.recv(4096)
    if not data_bytes:
        return []
    try:
        driversData = json.loads(data_bytes.decode('utf-8'))
    except json.JSONDecodeError:
        return []
    return driversData if isinstance(driversData, list) else []

import json
import socket

def waitForChatApproval(client: socket.socket)->socket.socket | None:
    """
    Passenger waits for driver approval (IP + port) from server.
    And returns a connection to the driver
    """
    try:
        data = client.recv(1024).decode("utf-8")
        if not data:
            return None
        connection = connectToDriver(data)
        return connection

    except Exception as e:
        print("Error waiting for chat approval:", e)
        return None

def sendChatOK(client: socket.socket, passenger_username: str):
    """
    Driver approves chat with a passenger.
    """
    msg = "chat_ok*" + passenger_username
    client.send(msg.encode("utf-8"))


def send_emergency(client: socket.socket, payload: dict) -> bool:
    """
    Send an emergency packet to the server with all available context.
    """
    try:
        client.send("emergency".encode("utf-8"))
        ack = client.recv(1024).decode("utf-8").strip()
        if ack != "1":
            return False
        client.send(json.dumps(payload).encode("utf-8"))
        final_ack = client.recv(1024).decode("utf-8").strip()
        return final_ack == "1"
    except Exception as e:
        print("Error sending emergency:", e)
        return False
