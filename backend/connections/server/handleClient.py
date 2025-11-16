import socket
import threading
import json
import time

from backend.connections.server.util import requestDrive
#DB dependencies
from backend.DB.Mock import getAllDrivers, getAllPassengers ### TO DO
from backend.DB.Mock import handleDB
from backend.DB.models.models import Person
from backend.connections.server.util import bindServerSocket

def handleClient(person : Person):
    #logging in / registering
    handleClientCredentials(person)
    #while true for multiple requests i.e. we will be always listening for upcoming requests
    while True:
        print("waiting for request...")
        message = person.conn.recv(1024).decode('utf-8')
        print("received msg: ", message)
        person.conn.send("1".encode('utf-8')) #acknowledging the reception of the message
        if message == "request=1" and person.is_driver:#drive requests
            driverRequest(person)

        elif message == "request=1" and not person.is_driver: #signaling that he is a driver:
            # we need to constantly send him the requests from the DB
            passengers : list[Person] = getAllPassengers(person.location)
            sendPassengerstoDriver(person, passengers)

        elif message == "change": # weather requests (TO DO LATER)
            person.is_driver = not person.is_driver

        print("is he?", person.is_driver)



def sendPassengerstoDriver(driver: Person, passList: list[Person]):
    passengersData = [p.__dict__ for p in passList]
    passengerJSON = json.dumps(passengersData)
    driver.conn.sendall(passengerJSON.encode('utf-8'))
    if driver.conn.recv(1024).decode('utf-8') != "1":
        raise RuntimeError("Something went wrong when sending passengers data to the driver")
    print("Ack received from driver")


def driverRequest(person: Person):
    drivers : list[Person] = propagateRequest(person)
        #now we will dump the list of drivers to the GUI and it will deal with it we'll send the client the json file of drivers
    
    driversData = [driver.__dict__ for driver in drivers]
    driverJSON = json.dumps(driversData)
    person.conn.sendall(driverJSON.encode('utf-8'))
    if person.conn.recv(1024).decode('utf-8') != "1":
        raise RuntimeError("Something went wrong when sending drivers data to the client")
    print("Ack received")


def propagateRequest(person: Person)->list[Person]:
    availableDrivers : list[Person] = getAllDrivers(person.location)

    actualDrivers : list[Person] = []

    #we can play here with asyncio and concurrency but meh     
    # for driver in availableDrivers:
    #     #establish a connection with the driver and ask for his permission:
    #     thread = threading.Thread(target = requestDrive, args = (person, driver, actualDrivers))
    #     thread.start()
    
    return availableDrivers




def handleClientCredentials(person: Person):
    #considering that the GUI will give me 2 credentials consecutively 
    data = person.conn.recv(1024)

    credentials = data.decode('utf-8').split("*")
    username = credentials[0]
    pswrd = credentials[1]
    if(handleDB(username, pswrd)):
        person.conn.send("1".encode('utf-8'))
    else:
        person.conn.send("0".encode('utf-8'))
    #where checkDB will
    ##More to do's based on DB's implementation

