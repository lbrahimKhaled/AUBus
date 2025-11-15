from backend.DB.models.models import Person, Passenger, Driver
import socket
def handleDB(username: str, passwrd : str):
    return None


## for the Driver inbox we need to have an incoming time and there's a threshold time and based on that we will send the thingy or not
def savePerson(x: str,y: int, connection: socket.socket):
    p: Passenger = Passenger(    name="Ali",
    ip="192.168.1.10",
    port=6060,
    location="Ballout qegwva2qbv wrda",)
    p.set_connection(connection)
    return p

def getAllDrivers(location : str):
    return [
    Driver("Ali", "192.168.1.2", 5050, "Ballout"),
    Driver("Sara", "192.168.1.3", 5051, "Hamra"),
    Driver("Omar", "192.168.1.4", 5052, "Jounieh"),
    Driver("Nour", "192.168.1.5", 5053, "Achrafieh"),
]


def saveRequest(d : Driver, msg: str):
    return