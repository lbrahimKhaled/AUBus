import socket

class Driver:
    def __init__(self, ip: str, port: int, location: str):
        self.ip = ip
        self.port = port
        self.location = location

    def __repr__(self):
        return f"Driver(ip='{self.ip}', port={self.port}, location='{self.location}')"


class Passenger:
    def __init__(self, conn: socket.socket, ip: str, port: int, location: str):
        self.conn = conn            # socket.socket object (client connection)
        self.ip = ip
        self.port = port
        self.location = location
        # Create a Driver object inside Passenger
        self.driver = Driver(ip, port, "ballout qegwva2qbv wrda")

    def __repr__(self):
        return (
            f"Passenger(ip='{self.ip}', port={self.port}, location='{self.location}', "
            f"driver={self.driver})"
        )