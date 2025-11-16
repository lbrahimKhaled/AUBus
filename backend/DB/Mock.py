from backend.DB.models.models import Person, Person, Person
import socket
def handleDB(username: str, passwrd : str):
    return True


## for the Person inbox we need to have an incoming time and there's a threshold time and based on that we will send the thingy or not
def savePerson(x: str,y: int, connection: socket.socket):
    """
    this function must save the record to the DB
    """
    p = Person(
        name="Ali",
        ip=x,
        port=y,
        location="Ballout qegwva2qbv wrda",
        departure="",
        is_driver=False,        # or True if driver
    )
    p.set_connection(connection)
    return p

def getAllDrivers(location : str):
    return [
    Person("Ali",  "192.168.1.2", 5050, "Ballout", "08:00",True, 4.5),
    Person("Sara", "192.168.1.3", 5051, "Hamra", "07:30", True, 4.8),
    Person("Omar", "192.168.1.4", 5052, "Jounieh", "09:00", True, 4.2),
    Person("Nour", "192.168.1.5", 5053, "Achrafieh", "08:45", True, 5.0),
]

def getAllPassengers(location: str):
    return [
        Person("Karim", "192.168.1.10", 6000, "Hamra", "", False),
        Person("Maya",   "192.168.1.11", 6001, "Verdun", "", False),
        Person("Hadi",   "192.168.1.12", 6002, "Ballout", "", False),
        Person("Jana",   "192.168.1.13", 6003, "Achrafieh", "", False),
    ]


def saveRequest(d : Person, msg: str):
    return