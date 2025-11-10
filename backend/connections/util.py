import socket

def bindServerSocket(portNb: int)->socket.socket:
    server : socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((socket.gethostbyname(socket.gethostname()), portNb))
    return server
