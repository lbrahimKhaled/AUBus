# from backend.DB.models.models import User, User, User
# import socket
# def handleDB(username: str, passwrd : str):
#     return True


# ## for the User inbox we need to have an incoming time and there's a threshold time and based on that we will send the thingy or not
# def savePerson(x: str,y: int, connection: socket.socket):
#     """
#     this function must save the record to the DB
#     """
#     p = User(
#         name="Ali",
#         ip=x,
#         port=y,
#         location="Ballout qegwva2qbv wrda",
#         departure="",
#         is_driver=False,        # or True if driver
#     )
#     p.set_connection(connection)
#     return p

# def getAllDrivers(location : str):
#     return [
#     User("Ali",  "192.168.1.2", 5050, "Ballout", "08:00",True, 4.5),
#     User("Sara", "192.168.1.3", 5051, "Hamra", "07:30", True, 4.8),
#     User("Omar", "192.168.1.4", 5052, "Jounieh", "09:00", True, 4.2),
#     User("Nour", "192.168.1.5", 5053, "Achrafieh", "08:45", True, 5.0),
# ]

# def getAllPassengers(d: User)-> list[User]:
#     return [
#         User("Karim", "192.168.1.10", 6000, "Hamra", "", False),
#         User("Maya",   "192.168.1.11", 6001, "Verdun", "", False),
#         User("Hadi",   "192.168.1.12", 6002, "Ballout", "", False),
#         User("Jana",   "192.168.1.13", 6003, "Achrafieh", "", False),
#     ]

# def getRequests(d: User)->list[User]:
#     """
#     this function will return the list of people that have requested a ride to driver d
#     """
#     return [
#         User("Karim", "192.168.1.10", 6000, "Hamra", "", False),
#         User("Maya",   "192.168.1.11", 6001, "Verdun", "", False),
#         User("Hadi",   "192.168.1.12", 6002, "Ballout", "", False),
#         User("Jana",   "192.168.1.13", 6003, "Achrafieh", "", False),
#     ]


# def saveRequest(d : User, p: User):
#     """
#     this function will save the request of the passenger p to the driver d in his table
#     """
#     listRequests: list[User] = getAllPassengers(d)
#     listRequests.append(p)

    