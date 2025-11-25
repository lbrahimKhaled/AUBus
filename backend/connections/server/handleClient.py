import socket
import sqlite3
import threading
import json
import time

# DB dependencies
from backend.DB.db import add_driver_request, find_candidate_drivers, getRequests, delete_driver_requests_for_user, add_rating, get_user_by_username
from backend.DB.db import authenticate_user, create_user, add_schedule, update_is_driver_by_username, add_emergency_report, update_user_location
from backend.DB.models.models import User
from backend.connections.client.client import start_driver_listener

online_users: dict[str, User] = {}


def handleClient(person: User):
    try:
        # logging in / registering
        person = handleClientCredentials(person)
        online_users[person.username] = person
        print(online_users)
        # while true for multiple requests i.e. we will be always listening for upcoming requests
        while True:
            print("waiting for request...")
            message = person.conn.recv(1024).decode('utf-8')
            print("received msg: ", message)
            # acknowledging the reception of the message
            person.conn.send("1".encode('utf-8'))
            if message.startswith("request"):
                # Expected format: request|drivers|<area> or request|passengers
                target = "drivers"
                area_filter = None
                min_rating = None
                depart_time = None
                direction = None
                weekday = None

                if "|" in message:
                    parts = message.split("|")
                    if len(parts) > 1 and parts[1]:
                        target = parts[1]
                    if len(parts) > 2:
                        area_filter = parts[2].strip() or None
                    # parse optional filters such as min_rating=4 or depart_time=08:30
                    for part in parts[3:]:
                        if not part:
                            continue
                        key = None
                        value = part
                        if "=" in part:
                            key, value = part.split("=", 1)
                        key = (key or "").strip().lower()
                        value = value.strip()
                        if key in ("min_rating", "rating", "rating_threshold"):
                            try:
                                min_rating = float(value)
                            except ValueError:
                                pass
                        elif key in ("depart_time", "time", "pickup_time"):
                            depart_time = value
                        elif key in ("direction", "dir"):
                            direction = value
                        elif key == "weekday":
                            try:
                                weekday = int(value)
                            except:
                                weekday = None
                        elif min_rating is None:
                            # allow raw numeric rating in legacy positional format
                            try:
                                min_rating = float(part)
                            except ValueError:
                                pass
                elif "=" in message:
                    # backward compatibility: request=<area>
                    _, area_raw = message.split("=", 1)
                    area_filter = area_raw.strip() or None

                if target == "passengers" and person.is_driver:
                    driverRequest(person)
                else:
                    drivers: list[User] = propagateRequest(
                        person,
                        area_filter=area_filter,
                        min_rating=min_rating,
                        depart_time=depart_time,
                        direction=direction,
                        weekday=weekday,
                    )

                    sendDriversToPassenger(person, drivers)

            elif message == "change":  # weather requests (TO DO LATER)
                person.is_driver = not person.is_driver
                online_users[person.username] = person
                try:
                    update_is_driver_by_username(
                        person.username, person.is_driver)
                except Exception as e:
                    print("Error updating is_driver in DB:", e)
                print("is he? ", person.is_driver)

            elif message == "schedule":  # schedule addition
                data = person.conn.recv(4096)
                payload = json.loads(data.decode("utf-8"))
                weekday = payload.get("weekday")
                depart_time = payload.get("depart_time")
                direction = payload.get("direction")
                # now we will add this schedule to the DB
                try:
                    add_schedule(person.id, weekday, depart_time, direction)
                    person.conn.send("1".encode("utf-8"))
                except Exception as e:
                    print("Error adding schedule:", e)
                    person.conn.send("0".encode("utf-8"))

            # Passenger initiates chat
            elif message.startswith("chat_request|"):
                try:
                    driver_username = message.split("|")[1]
                    if driver_username in online_users:
                        driver_user = online_users[driver_username]
                        notify = f"chat_req_from|{person.username}"
                        driver_user.conn.send(notify.encode("utf-8"))
                    else:
                        person.conn.send("0".encode("utf-8"))
                except Exception as e:
                    print("Error in chat_request:", e)
                    person.conn.send("0".encode("utf-8"))

            # Driver approves chat
            elif message.startswith("chat_ok"):
                target = message.split("*")[1]
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

            elif message == "emergency":
                # payload contains client-side context for the emergency
                data = person.conn.recv(8192)
                success = False
                try:
                    payload = json.loads(data.decode("utf-8"))
                    partner_info = payload.get("chat_partner") or {}
                    partner_username = partner_info.get("username", "")
                    partner_user = get_user_by_username(
                        partner_username) if partner_username else None
                    partner_id = partner_user.id if partner_user else None
                    partner_role = (
                        "driver" if partner_user and partner_user.is_driver else partner_info.get(
                            "role", "")
                    )
                    add_emergency_report(
                        reporter_id=person.id,
                        reporter_username=person.username,
                        reporter_role="driver" if person.is_driver else "passenger",
                        partner_id=partner_id,
                        partner_username=partner_username,
                        partner_role=partner_role,
                        raw_context=json.dumps(payload),
                    )
                    success = True
                except Exception as e:
                    print("Error handling emergency report:", e)
                person.conn.send(("1" if success else "0").encode("utf-8"))
            elif message == "update_location":
                data = person.conn.recv(4096)
                success = False
                try:
                    payload = json.loads(data.decode("utf-8"))
                    latitude = payload.get("latitude")
                    longitude = payload.get("longitude")
                    city = payload.get("city")
                    country = payload.get("country")
                    area = payload.get("area")
                    # Update area to city if provided so matching uses latest city
                    update_user_location(
                        person.id,
                        area=area or city or person.area,
                        latitude=latitude,
                        longitude=longitude,
                        city=city,
                        country=country,
                    )
                    # Refresh in-memory user info
                    person.latitude = latitude
                    person.longitude = longitude
                    person.city = city
                    person.country = country
                    person.area = area or city or person.area
                    online_users[person.username] = person
                    success = True
                except Exception as e:
                    print("Error updating location:", e)
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
    # Best-effort ACK (non-blocking-ish) to avoid timeouts if client doesn't reply
    prev_timeout = driver.conn.gettimeout()
    driver.conn.settimeout(0.5)
    try:
        ack = driver.conn.recv(1024)
        if ack.decode('utf-8') != "1":
            print("Warning: unexpected ACK from driver when sending passengers")
    except Exception:
        # Do not block or fail if driver doesn't ACK
        pass
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
    print("Sending drivers data:", driversData)
    driverJSON = json.dumps(driversData)
    passenger.conn.sendall(driverJSON.encode('utf-8'))
    prev_timeout = passenger.conn.gettimeout()
    passenger.conn.settimeout(0.5)
    try:
        ack = passenger.conn.recv(1024)
        if ack.decode('utf-8') != "1":
            print("Warning: unexpected ACK from passenger when sending drivers")
    except Exception:
        # Avoid blocking caller if passenger does not ACK
        pass
    finally:
        passenger.conn.settimeout(prev_timeout)


def driverRequest(person: User):
    passengers: list[User] = getRequests(person.id)
    sendPassengerstoDriver(person, passengers)


def propagateRequest(
    person,
    area_filter=None,
    min_rating=None,
    depart_time=None,
    direction=None,
    weekday=None
):

    # Drop old requests for this rider so we only keep the fresh ones
    try:
        delete_driver_requests_for_user(person.id)
    except Exception as e:
        print("Error cleaning old requests for rider:", e)

    availableDrivers = find_candidate_drivers(
        person,
        area_filter,
        min_rating=min_rating,
        depart_time=depart_time,
        direction=direction,
        weekday=weekday,
    )

    actualDrivers: list[User] = []
    print(online_users)
    for driver in availableDrivers:
        add_driver_request(person.id, driver.id)
        online_driver = online_users.get(driver.username)
        if online_driver is not None and getattr(online_driver, "is_driver", False):
            actualDrivers.append(online_driver)

    return actualDrivers


def handleClientCredentials(person: User) -> User:
  # Receive raw bytes from client
    data = person.conn.recv(4096)
    print("Received data for credentials:", data)
    try:
        payload = json.loads(data.decode("utf-8"))
    except json.JSONDecodeError:
        # Bad JSON → fail hard
        person.conn.sendall("0".encode("utf-8"))
        return person

    user: User = person
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
        username = payload.get("username")
        pswrd = payload.get("password")
        name = payload.get("name")
        email = payload.get("email")
        area = payload.get("area")
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
