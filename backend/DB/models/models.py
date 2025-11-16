import socket

class Person:
    def __init__(
        self,
        name: str,
        ip: str,
        port: int,
        location: str,               # area / location (works for both)
        departure: str,  # driver-only, e.g. "08:00"
        is_driver: bool = False,     # True = driver, False = passenger
        rating: float = 0.0,              # rating for driver or passenger
    ):
        self.name = name
        self.ip = ip
        self.port = port
        self.location = location      # for drivers this is their area
        self.is_driver = is_driver
        self.departure = departure
        self.rating = rating
        self.online = False

    def set_connection(self, conn: socket.socket):
        self.conn = conn
        self.online = True

    def to_dict(self) -> dict:
        """Safe JSON-serializable representation to send to clients."""
        return {
            "name": self.name,
            "ip": self.ip,
            "port": self.port,
            "location": self.location,
            "is_driver": self.is_driver,
            "departure": self.departure,
            "rating": self.rating,
        }