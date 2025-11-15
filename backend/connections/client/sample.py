from .client import connectToServer, sendCredentials, requestDrivers, receiveDrivers

def testConnecting():
    ip = input("Enter server IP address: ")
    client = connectToServer(ip)
    print("Connected to server at", ip)

def testSendCredentials():
    ip = input("Enter server IP address: ")
    username = input("Enter username: ")
    pswrd = input("Enter password: ")
    client = connectToServer(ip)
    sendCredentials(client, username, pswrd)
    print("Credentials sent.")

def testRequestDrivers():
    ip = input("Enter server IP address: ")
    username = input("Enter username: ")
    pswrd = input("Enter password: ")
    client = connectToServer(ip)
    sendCredentials(client, username, pswrd)
    requestDrivers(client)
    drivers = receiveDrivers(client)
    print("Received drivers:", drivers)

#you can put here the client functionality that you want to test
testRequestDrivers()