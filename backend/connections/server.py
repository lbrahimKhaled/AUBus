import socket
import threading
from util import bindServerSocket
from handleClient import handleClient
from backend.DB.models.models import Passenger
from backend.DB.Mock import savePerson
def welcomeServerPort():
    '''
    this is the welcoming port of the server it will receive the request and redirect is to other ports 
    '''
    server = bindServerSocket(9999)

    server.listen()

    #so here the welcoming port will have 9999 as its port nb and the IP address of the laptop we will be running the code from

    while True: # we will continiously accept any incoming requests
        connection, client_address = server.accept()
        # next we will dedicate a certain thread for handling this client 
        clientP : Passenger = savePerson(client_address[0], client_address[1])
        client_thread = threading.Thread(target = handleClient, args= (clientP, 0))
        client_thread.start()






