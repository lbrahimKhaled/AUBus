import socket
import threading
import json

from backend.connections.server.util import requestDrive
#DB dependencies
from backend.DB.Mock import getAllDrivers ### TO DO
from backend.DB.Mock import handleDB
from backend.DB.models.models import Passenger, Driver, Person
from backend.connections.server.util import bindServerSocket

def handleClient(person : Passenger):
    #logging in / registering
    handleClientCredentials(person)
    #while true for multiple requests i.e. we will be always listening for upcoming requests
    while True:
        driverList : list[Driver] = handleClientRequests(person)
    #now we will dump the list of drivers to the GUI and it will deal with it we'll send the client the json file of drivers
        
        driversData = [driver.__dict__ for driver in driverList]
        driverJSON = json.dumps(driversData)
        person.conn.sendall(driverJSON.encode('utf-8'))

def handleClientRequests(person: Passenger)->list[Driver]:
    print("waiting for request...")

    message = person.conn.recv(1024).decode('utf-8')
    if message : person.conn.send("1".encode('utf-8')) #acknowledging the reception of the message
    
    driver : list[Driver] = []
    if(message == "request=1"):
        driver = propagateRequest(person) # this will return the first driver that accepted our request
    return driver


def propagateRequest(person: Passenger)->list[Driver]:
    availableDrivers : list[Driver] = getAllDrivers(person.location)

    actualDrivers : list[Driver] = []

    # #we can play here with asyncio and concurrency but meh     
    for driver in availableDrivers:
        #establish a connection with the driver and ask for his permission:
        thread = threading.Thread(target = requestDrive, args = (person, driver, actualDrivers))
        thread.start()
    
    return actualDrivers




def handleClientCredentials(person: Person):
    #considering that the GUI will give me 2 credentials consecutively 
    data = person.conn.recv(1024)

    credentials = data.decode('utf-8').split("*")
    username = credentials[0]
    pswrd = credentials[1]
    person.conn.send("1".encode('utf-8'))
    #where checkDB will
    # handleDB(username, pswrd)
    ##More to do's based on DB's implementation

