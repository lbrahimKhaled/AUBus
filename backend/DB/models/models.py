import socket

class Person:
    def __init__(self, name: str, ip: str, port: int, location: str):
        self.name = name
        self.ip = ip
        self.port = port
        self.location = location
        
    def set_connection(self, conn: socket.socket):
        self.conn = conn

class Passenger(Person):
    def __init__(self, name: str, ip: str, port: int, location: str):
        super().__init__(name, ip, port, location)
        self.connection: socket.socket | None = None
        self.online: bool = False

    def set_connection(self, conn: socket.socket):
        self.conn = conn
        self.online = True


class Driver(Person):
    def __init__(self, name: str, ip: str, port: int, location: str):
        super().__init__(name, ip, port, location)
        self.connection: socket.socket | None = None
        self.online: bool = False

    def set_connection(self, conn: socket.socket):
        self.conn= conn
        self.online = True