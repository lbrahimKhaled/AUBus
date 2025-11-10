import socket
from backend.DB.Mock import handleDB
from backend.DB.models.models import Driver
from backend.DB.models.models import Passenger, Driver

def handleClient(person : Passenger):
    #logging in / registering
    handleClientCredentials(person.conn, (person.ip, person.port))

    #handling requests
    handleClientRequests(person.conn, (person.ip, person.port))


def handleClientRequests(person: Passenger)->None:
    message = person.conn.recv(1024).decode('utf-8')
    if(message == "request=1"):
        driver : Driver = propagateRequest(person.location) # this will return the first driver that accepted our request
        msg : str = str(driver.ip) + "*" + str(driver.port)  #then the client will split this and get the IP and port number fromt msg
        
        person.conn.send(msg.encode('utf-8'))

def propagateRequest(location: str)->Driver:
    availableDrivers : list[Driver] = getAllDrivers(location)
    
    #we can play here with asyncio and concurrency but meh
    caller = bindServerSocket()
    
    for driver in availableDrivers:
        #establish a connection with the driver and ask for his permission:

        ######### we will create a connection with each driver and ask them they will reply by 1 or 0




def handleClientCredentials(connection, clientAddress)->None:
    #considering that the GUI will give me 2 credentials consecutively 
    username: str = connection.recv(1024).decode('utf-8')
    pswrd:str = connection.recv(1024).decode('utf-8')
    #where checkDB will
    handleDB(username, pswrd)

