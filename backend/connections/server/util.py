import socket
from backend.DB.models.models import Person, Passenger, Driver
from backend.DB.Mock import saveRequest
def bindServerSocket(portNb: int)->socket.socket:
    server : socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((socket.gethostbyname(socket.gethostname()), portNb))
    return server

def requestDrive(p: Passenger , d :Driver, L : list[Driver])->bool:
    """
    this function will save the messages to the DB for offline Drivers and will contact Directly online drivers
    will return true if the function is correctly executed and false otherwise (since this is good practice)
    """
    ### TO DO : we need to have some good implementation of the msg
    if(d.online):
        #we will directly send since it is persistent TCP connection 
        msg = "request from " + p.ip
        d.conn.send(msg.encode('utf-8'))
        msg = d.conn.recv(1024).decode('utf-8')
        if(msg == "1"):
            L.append(d)
        return True
    
    else:
        #we need to send it to the DB
        saveRequest(d, "request from" + p.ip)
        return True