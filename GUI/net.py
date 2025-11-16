# net.py
import socket
from typing import Any, Dict

from backend.protocol import (
    send_message,
    read_message,
    new_req_id,
)

from backend.config import SERVER_HOST, SERVER_PORT


class AubusClient:
    """
    Simple client wrapper to talk to the AUBus backend using the same
    JSON-line protocol as all the test scripts.

    The GUI uses this class instead of dealing with raw sockets.
    """

    def __init__(self) -> None:
        self.sock: socket.socket | None = None

    # ----------------------------
    # Connection Management
    # ----------------------------

    def connect(self) -> None:
        """
        Open TCP connection to the backend.
        Safe to call multiple times: it reconnects if needed.
        """
        self.close()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((SERVER_HOST, SERVER_PORT))

    def close(self) -> None:
        """
        Close socket safely if it's open.
        """
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    # ----------------------------
    # Low-level send/receive
    # ----------------------------

    def send(self, type_: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a message to the server and wait for a response.

        Returns the server's JSON dict.
        Raises RuntimeError if not connected.
        """
        if not self.sock:
            raise RuntimeError("Client not connected")

        msg = {
            "type": type_,
            "req_id": new_req_id(),
            "payload": payload,
        }

        send_message(self.sock, msg)
        resp = read_message(self.sock)

        if resp is None:
            raise RuntimeError("Connection closed by server")

        return resp

    # ----------------------------
    # High-level API Methods
    # ----------------------------

    # ---- HEALTH ----
    def health(self) -> bool:
        resp = self.send("health", {})
        return resp["type"] == "health_ok"

    # ---- AUTH ----
    def login(self, username: str, password: str) -> Dict[str, Any]:
        return self.send("login", {"username": username, "password": password})

    def register(self, **fields) -> Dict[str, Any]:
        # fields: name, email, username, password, area, is_driver
        return self.send("register", fields)

    # ---- PROFILE ----
    def update_profile(self, area: str, is_driver: bool) -> Dict[str, Any]:
        return self.send("update_profile", {
            "area": area,
            "is_driver": is_driver
        })

    # ---- SCHEDULE ----
    def add_schedule(self, weekday: int, depart_time: str, direction: str) -> Dict[str, Any]:
        return self.send("add_schedule", {
            "weekday": weekday,
            "depart_time": depart_time,
            "direction": direction,
        })

    def list_schedules(self) -> Dict[str, Any]:
        return self.send("list_schedules", {})

    def delete_schedule(self, schedule_id: int) -> Dict[str, Any]:
        return self.send("delete_schedule", {"schedule_id": schedule_id})

    # ---- RIDE REQUESTS ----

    def post_ride_request(self, area: str, weekday: int, target_time: str, direction: str) -> Dict[str, Any]:
        return self.send("post_ride_request", {
            "area": area,
            "weekday": weekday,
            "target_time": target_time,
            "direction": direction,
        })

    # ---- DRIVER ACTIONS ----

    def driver_accept(self, request_id: int) -> Dict[str, Any]:
        return self.send("driver_accept", {"request_id": request_id})

    def driver_decline(self, request_id: int) -> Dict[str, Any]:
        return self.send("driver_decline", {"request_id": request_id})

        # ---- RIDE REQUESTS ----

    def list_my_requests(self):
        return self.send("list_my_requests", {})

    def list_driver_requests(self):
        return self.send("list_driver_requests", {})

    # ---- RATINGS ----

    def rate_user(self, ratee_id: int, stars: int, comment: str) -> Dict[str, Any]:
        return self.send("rate_user", {
            "ratee_id": ratee_id,
            "stars": stars,
            "comment": comment,
        })

    def list_ratings(self) -> Dict[str, Any]:
        return self.send("list_ratings", {})

    # ---- RELAY (CHAT) ----
    def relay_send(self, channel_id: str, text: str) -> Dict[str, Any]:
        return self.send("relay_send", {
            "channel_id": channel_id,
            "text": text,
        })

    def relay_poll(self, channel_id: str, last_seq: int) -> Dict[str, Any]:
        return self.send("relay_poll", {
            "channel_id": channel_id,
            "last_seq": last_seq,
        })
