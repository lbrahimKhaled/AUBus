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
    def __init__(
        self,
        name: str,
        ip: str,
        port: int,
        area: str,
        departure: str,
        rating: float = 0.0,
    ):
        super().__init__(name, ip, port, area)

        # These are the ONLY fields you care about on the client:
        self.name = name          # already in Person, but explicit doesn’t hurt
        self.departure = departure  # e.g. "08:00"
        self.rating = rating      # e.g. 4.5

        # Internal / non-serializable stuff
        self._connection: socket.socket | None = None
        self.online: bool = False

    def set_connection(self, conn: socket.socket):
        self._connection = conn
        self.online = True