import socket
import json
#providing certain functionalities for the GUI to use when connecting and everything
def connectToDriver(driver: dict)->socket.socket:
    currentSocket : socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    currentSocket.connect((driver['ip'], driver['port']))
    return currentSocket

def sendMessageToDriver(driverSocket: socket.socket, msg: str)->None:
    driverSocket.send(msg.encode('utf-8'))
    if driverSocket.recv(1024).decode('utf-8') != "1":
        raise RuntimeError("Something went wrong when sending the message to the driver")

def driverReceiveMessage(driverSocket: socket.socket)->str:
    data = driverSocket.recv(1024).decode('utf-8')
    driverSocket.send("1".encode('utf-8'))
    return data

def connectToServer(ipServer: str)->socket.socket:
    client : socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((ipServer, 9999))
    return client

def sendCredentials(client: socket.socket, username: str, pswrd: str)->bool:
    msg = username + "*" + pswrd
    client.send(msg.encode("utf-8"))
    msg2 = client.recv(1024).decode('utf-8')
    if msg2 == "0":
        return False
    return True

def requestOther(client: socket.socket)->None:
    msg = "request=1"
    client.send(msg.encode('utf-8'))
    if client.recv(1024).decode('utf-8') != "1":
        raise RuntimeError("Something went wrong when signing you in")


def receiveOther(client: socket.socket)->list[dict]:
    data = client.recv(4096).decode('utf-8')
    client.send("1".encode('utf-8'))
    driversData = json.loads(data)
    return driversData

def changeMsg(client: socket.socket)->None:
    client.send("change".encode('utf-8'))
    msg = client.recv(1024).decode('utf-8') != "1"