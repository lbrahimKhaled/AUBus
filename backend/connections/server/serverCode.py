import socket
import threading
from .util import bindServerSocket
from .handleClient import handleClient
from ...DB.models.models import User
from ...DB.db import init_db
def welcomeServerPort():
    '''
    this is the welcoming port of the server it will receive the request and redirect is to other ports 
    '''
    init_db()
    server = bindServerSocket(9999)

    server.listen()
    print("Server is listening on port 9999 and ip:", socket.gethostbyname(socket.gethostname()))
    #so here the welcoming port will have 9999 as its port nb and the IP address of the laptop we will be running the code from

    while True: # we will continiously accept any incoming requests
        connection, client_address = server.accept()
        # next we will dedicate a certain thread for handling this client 
        clientP : User = User()
        clientP.set_connection(connection)
        clientP.ip = client_address[0]
        clientP.port = client_address[1]
        client_thread = threading.Thread(target = handleClient, args= (clientP,))
        client_thread.start()

if __name__ == "__main__":
    welcomeServerPort()




