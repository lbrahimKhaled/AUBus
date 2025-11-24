"""
Simple manual test harness for the client-side protocol.
Run this script and pick actions from the menu to exercise the client APIs.
"""

import json
from typing import Optional

from .client import (
    connectToServer,
    sendCredentials,
    requestOther,
    receiveOther,
    changeMsg,
    send_schedule_to_server,
    update_location_on_server,
    send_rating,
    sendChatOK,
    waitForChatApproval,
    send_emergency,
)


def prompt(msg: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{msg}{suffix}: ").strip()
    return val or (default or "")


def connect_and_auth():
    ip = prompt("Enter server IP address", "127.0.0.1")
    client = connectToServer(ip)
    print("Connected to server at", ip)

    mode = prompt("Login (l) or Register (r)?", "l").lower()
    if mode.startswith("r"):
        payload = {
            "login": 0,
            "username": prompt("Choose username"),
            "password": prompt("Choose password"),
            "name": prompt("Full name"),
            "email": prompt("Email"),
            "area": prompt("Area", "Beirut"),
            "is_driver": prompt("Register as driver? (y/n)", "n").lower().startswith("y"),
        }
    else:
        payload = {
            "login": 1,
            "username": prompt("Username"),
            "password": prompt("Password"),
            "is_driver": prompt("Login as driver? (y/n)", "n").lower().startswith("y"),
        }
    success = sendCredentials(client, payload)
    print("Auth success" if success else "Auth failed")
    return client


def test_request_drivers(client):
    area = prompt("Area filter (empty = your area, 'all' = everyone)", "")
    min_rating = prompt("Min rating (blank to ignore)", "")
    depart_time = prompt("Preferred depart time HH:MM (blank to ignore)", "")
    requestOther(
        client,
        area_filter=area or None,
        target="drivers",
        min_rating=float(min_rating) if min_rating else None,
        depart_time=depart_time or None,
    )
    drivers = receiveOther(client)
    print("Received drivers:", json.dumps(drivers, indent=2))


def test_request_passengers(client):
    requestOther(client, target="passengers")
    passengers = receiveOther(client)
    print("Received passengers:", json.dumps(passengers, indent=2))


def test_change_mode(client):
    changeMsg(client)
    print("Toggled driver/passenger mode.")


def test_schedule(client):
    weekday = int(prompt("Weekday (0=Mon..6=Sun)", "0"))
    time_str = prompt("Depart time HH:MM", "08:00")
    direction = prompt("Direction (toAUB/fromAUB)", "toAUB")
    ok = send_schedule_to_server(client, weekday, time_str, direction)
    print("Schedule saved" if ok else "Schedule failed")


def test_location(client):
    lat = float(prompt("Latitude", "33.8938"))
    lon = float(prompt("Longitude", "35.5018"))
    city = prompt("City", "Beirut")
    country = prompt("Country", "LB")
    area = prompt("Area", city)
    ok = update_location_on_server(client, lat, lon, city, country, area)
    print("Location updated" if ok else "Location update failed")


def test_rating(client):
    target = prompt("Username to rate")
    stars = int(prompt("Stars 1-5", "5"))
    comment = prompt("Comment", "")
    ok = send_rating(client, target, stars, comment)
    print("Rating saved" if ok else "Rating failed")


def test_emergency(client):
    payload = {
        "demo": True,
        "chat_partner": {"username": prompt("Partner username", "")},
        "note": prompt("Note", "Test emergency"),
    }
    ok = send_emergency(client, payload)
    print("Emergency sent" if ok else "Emergency failed")


def test_chat_ok(client):
    passenger_username = prompt("Passenger username to approve")
    sendChatOK(client, passenger_username)
    print("chat_ok sent")
    conn = waitForChatApproval(client)
    print("P2P connection:", "connected" if conn else "not established")
    if conn:
        conn.close()


def main():
    client = connect_and_auth()
    actions = {
        "drivers": test_request_drivers,
        "passengers": test_request_passengers,
        "toggle": test_change_mode,
        "schedule": test_schedule,
        "location": test_location,
        "rating": test_rating,
        "emergency": test_emergency,
        "chatok": test_chat_ok,
    }
    while True:
        print("\nAvailable actions:", ", ".join(actions.keys()), "or 'quit'")
        choice = input("Pick action: ").strip().lower()
        if choice in ("quit", "exit"):
            break
        func = actions.get(choice)
        if not func:
            print("Unknown action")
            continue
        try:
            func(client)
        except Exception as e:
            print(f"Error running {choice}:", e)

    try:
        client.close()
    except Exception:
        pass


if __name__ == "__main__":
    main()
