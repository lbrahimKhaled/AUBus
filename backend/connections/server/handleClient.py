import socket
import sqlite3
import threading
import json
import time

#DB dependencies
from backend.DB.db import add_driver_request, find_candidate_drivers, getRequests, delete_driver_requests_for_user, add_rating, get_user_by_username
from backend.DB.db import authenticate_user, create_user, add_schedule, update_is_driver_by_username
from backend.DB.models.models import User
from backend.connections.client.client import start_driver_listener

online_users: dict[str, User] = {}

def handleClient(person : User):
    try:
        #logging in / registering
        person = handleClientCredentials(person)
        online_users[person.username] = person
        print(online_users)
        #while true for multiple requests i.e. we will be always listening for upcoming requests
        while True:
            print("waiting for request...")
            message = person.conn.recv(1024).decode('utf-8')
            print("received msg: ", message)
            person.conn.send("1".encode('utf-8')) #acknowledging the reception of the message
            if message == "request=1" and person.is_driver:#drive requests
                # Driver wants list of riders that requested them
                driverRequest(person)

            elif message == "request=1" and not person.is_driver: # passenger requesting drivers
                drivers : list[User] = propagateRequest(person)
                sendDriversToPassenger(person, drivers)

            elif message == "change": # weather requests (TO DO LATER)
                person.is_driver = not person.is_driver
                online_users[person.username] = person
                try:
                    update_is_driver_by_username(person.username, person.is_driver)
                except Exception as e:
                    print("Error updating is_driver in DB:", e)
                print("is he? ", person.is_driver)

            elif message == "schedule": # schedule addition
                data = person.conn.recv(4096)
                payload = json.loads(data.decode("utf-8"))
                weekday = payload.get("weekday")
                depart_time = payload.get("depart_time")
                direction = payload.get("direction")
                # now we will add this schedule to the DB
                person.conn.send("1".encode("utf-8"))
                print("Adding schedule:", weekday, depart_time, direction)
                add_schedule(person.id, weekday, depart_time, direction)

            elif message.startswith("chat_ok"):
                target = message.split("*")[1]
                # Find passenger, send back approval + driver IP/port
                if target in online_users:
                    online_users[target].conn.send(person.ip.encode("utf-8"))

            elif message == "rate":
                # acknowledge receipt of rating intent
                person.conn.send("1".encode("utf-8"))
                data = person.conn.recv(4096)
                payload = json.loads(data.decode("utf-8"))
                target_username = payload.get("target_username")
                stars = int(payload.get("stars", 0))
                comment = payload.get("comment", "")
                success = False
                if target_username and 1 <= stars <= 5:
                    ratee = get_user_by_username(target_username)
                    if ratee:
                        try:
                            add_rating(person.id, ratee.id, stars, comment)
                            success = True
                        except Exception as e:
                            print("Error adding rating:", e)
                person.conn.send(("1" if success else "0").encode("utf-8"))
    finally:
        # cleanup DB and in-memory tracking
        try:
            delete_driver_requests_for_user(person.id)
        except Exception as e:
            print("Error cleaning driver_requests for user", person.id, e)
        online_users.pop(person.username, None)
        # clean socket
        try:
            person.conn.close()
        except:
            pass




def sendPassengerstoDriver(driver: User, passList: list[User]):
    # Serialize only safe fields (no sockets)
    passengersData = [p.to_dict() for p in passList]
    passengerJSON = json.dumps(passengersData)
    driver.conn.sendall(passengerJSON.encode('utf-8'))
    # Avoid hanging forever waiting for ACK from client
    prev_timeout = driver.conn.gettimeout()
    driver.conn.settimeout(2.0)
    try:
        ack = driver.conn.recv(1024)
        if ack.decode('utf-8') != "1":
            print("Warning: unexpected ACK from driver when sending passengers")
    except socket.timeout:
        print("Warning: timed out waiting for driver ACK (passenger list)")
    finally:
        driver.conn.settimeout(prev_timeout)
    # Clear requests once delivered so past ones don't linger
    try:
        delete_driver_requests_for_user(driver.id)
    except Exception as e:
        print("Error cleaning requests after sending to driver:", e)


def sendDriversToPassenger(passenger: User, drivers: list[User]):
    # Serialize only safe fields (no sockets)
    driversData = [d.to_dict() for d in drivers]
    driverJSON = json.dumps(driversData)
    passenger.conn.sendall(driverJSON.encode('utf-8'))
    prev_timeout = passenger.conn.gettimeout()
    passenger.conn.settimeout(2.0)
    try:
        ack = passenger.conn.recv(1024)
        if ack.decode('utf-8') != "1":
            print("Warning: unexpected ACK from passenger when sending drivers")
    except socket.timeout:
        print("Warning: timed out waiting for passenger ACK (drivers list)")
    finally:
        passenger.conn.settimeout(prev_timeout)


def driverRequest(person: User):
    passengers : list[User] = getRequests(person.id)
    sendPassengerstoDriver(person, passengers)


def propagateRequest(person: User)->list[User]:
    # Drop old requests for this rider so we only keep the fresh ones
    try:
        delete_driver_requests_for_user(person.id)
    except Exception as e:
        print("Error cleaning old requests for rider:", e)

    availableDrivers : list[User] = find_candidate_drivers(person)
    actualDrivers: list[User] = []
    print(online_users)
    for driver in availableDrivers:
        add_driver_request(person.id, driver.id)
        if online_users.get(driver.username) is not None:
            actualDrivers.append(online_users[driver.username])

    return actualDrivers



def handleClientCredentials(person: User)-> User:
  # Receive raw bytes from client
    data = person.conn.recv(4096)
    print("Received data for credentials:", data)
    try:
        payload = json.loads(data.decode("utf-8"))
    except json.JSONDecodeError:
        # Bad JSON → fail hard
        person.conn.sendall("0".encode("utf-8"))
        return person
    
    user : User = person
    login = payload.get("login")  # expect 1 for login, 0 for signup

    if login == 1:
        # LOGIN FLOW
        username = payload.get("username")
        pswrd = payload.get("password")

        temp = authenticate_user(username, pswrd)
        user = temp if temp is not None else person
        if temp is not None:
            success = True
            person.conn.sendall("1".encode("utf-8"))
        else:
            person.conn.sendall("0".encode("utf-8"))
            success = False
        user.is_driver = bool(payload.get("is_driver"))

    else:
        # SIGNUP / REGISTER FLOW
        username  = payload.get("username")
        pswrd     = payload.get("password")
        name      = payload.get("name")
        email     = payload.get("email")
        area      = payload.get("area")
        is_driver = bool(payload.get("is_driver"))  # expect true/false in JSON
        print("registering user:", username, email, name, area, is_driver)
        try:
            # create_user should return a User or raise on failure
            user = create_user(name, email, username, pswrd, area, is_driver)
            print("Created user:", user)
            success = user is not None
        except Exception as e:
            print("Error creating user:", e)
            # any other error → treat as failure for now
            success = False

        if success:
            person.conn.sendall("1".encode("utf-8"))
        else:
            person.conn.sendall("0".encode("utf-8"))
    if not success:
        return handleClientCredentials(person)  # retry on failure
    user.conn = person.conn
    user.ip = person.ip
    user.port = person.port
    return user
    
    
