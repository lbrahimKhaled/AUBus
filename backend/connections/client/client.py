import socket
import json
#providing certain functionalities for the GUI to use when connecting and everything
def connectToServer(ipServer: str)->socket.socket:
    client : socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((ipServer, 9999))
    return client

def sendCredentials(client: socket.socket, username: str, pswrd: str)->None:
    msg = username + "*" + pswrd
    client.send(msg.encode("utf-8"))
    msg2 = client.recv(1024).decode('utf-8')
    if msg2 != "1":
        raise RuntimeError("Something went wrong when signing you in")

def requestDrivers(client: socket.socket)->None:
    msg = "request=1"
    client.send(msg.encode('utf-8'))
    if client.recv(1024).decode('utf-8') != "1":
        raise RuntimeError("Something went wrong when signing you in")


def receiveDrivers(client: socket.socket)->list[dict]:
    data = client.recv(4096).decode('utf-8')
    client.send("1".encode('utf-8'))
    driversData = json.loads(data)
    return driversData