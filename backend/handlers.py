# handlers.py
from typing import Any, Dict

from protocol import make_response, make_error
from relay import relay_post_message, relay_get_messages_since
from db import (
    create_user,
    get_user_by_username,
    authenticate_user,
    update_user_profile,
    add_schedule,
    list_schedules_for_user,
    delete_schedule,
    create_ride_request,
    update_ride_request_status,
    get_ride_request_by_id,
    add_rating,
    list_ratings_for_user,
    list_requests_by_rider,
    list_requests_for_driver,
)

from matching import find_candidates_for_request


# Type aliases for readability
Message = Dict[str, Any]
Context = Dict[str, Any]


def handle_request(msg: Message, context: Context) -> Message:
    """
    Main dispatcher for all message types.
    """
    msg_type = msg.get("type")
    if not msg_type:
        return make_error(msg, "MISSING_TYPE")

    if msg_type == "ping":
        return handle_ping(msg, context)

    elif msg_type == "register":
        return handle_register(msg, context)

    elif msg_type == "login":
        return handle_login(msg, context)

    elif msg_type == "update_profile":
        return handle_update_profile(msg, context)

    elif msg_type == "add_schedule":
        return handle_add_schedule(msg, context)

    elif msg_type == "list_schedules":
        return handle_list_schedules(msg, context)

    elif msg_type == "delete_schedule":
        return handle_delete_schedule(msg, context)

    elif msg_type == "post_ride_request":
        return handle_post_ride_request(msg, context)

    elif msg_type == "driver_accept":
        return handle_driver_accept(msg, context)

    elif msg_type == "driver_decline":
        return handle_driver_decline(msg, context)

    elif msg_type == "rate_user":
        return handle_rate_user(msg, context)

    elif msg_type == "list_ratings":
        return handle_list_ratings(msg, context)

    elif msg_type == "relay_send":
        return handle_relay_send(msg, context)

    elif msg_type == "relay_poll":
        return handle_relay_poll(msg, context)

    elif msg_type == "health":
        return handle_health(msg, context)

    elif msg_type == "list_my_requests":
        return handle_list_my_requests(msg, context)

    elif msg_type == "list_driver_requests":
        return handle_list_driver_requests(msg, context)

    # Unknown type
    return make_error(msg, f"UNKNOWN_TYPE_{msg_type}")


# ---------------------------------------------------------
# PING (already implemented)
# ---------------------------------------------------------

def handle_ping(msg: Message, context: Context) -> Message:
    payload = msg.get("payload", {}) or {}
    response_payload = {"message": "pong"}
    response_payload.update(payload)
    return make_response(msg, "ok", response_payload)


# ---------------------------------------------------------
# REGISTER
# ---------------------------------------------------------

def handle_register(msg: Message, context: Context) -> Message:
    payload = msg.get("payload", {})
    required = ["name", "email", "username", "password", "area", "is_driver"]

    # Validate input
    for key in required:
        if key not in payload:
            return make_error(msg, f"MISSING_FIELD_{key.upper()}")

    name = payload["name"]
    email = payload["email"]
    username = payload["username"]
    password = payload["password"]
    area = payload["area"]
    is_driver = bool(payload["is_driver"])

    # Check username availability
    if get_user_by_username(username) is not None:
        return make_error(msg, "USERNAME_TAKEN")

    # Create the user
    try:
        user = create_user(
            name=name,
            email=email,
            username=username,
            plain_password=password,
            area=area,
            is_driver=is_driver,
        )
    except Exception as e:
        # DB uniqueness constraint? Other error?
        return make_error(msg, "REGISTER_FAILED")

    return make_response(msg, "ok", {"user_id": user.id})


# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------

def handle_login(msg: Message, context: Context) -> Message:
    payload = msg.get("payload", {})
    if "username" not in payload or "password" not in payload:
        return make_error(msg, "MISSING_CREDENTIALS")

    username = payload["username"]
    password = payload["password"]

    user = authenticate_user(username, password)
    if user is None:
        return make_error(msg, "INVALID_CREDENTIALS")

    # Store the logged-in user_id in the context
    context["user_id"] = user.id

    return make_response(msg, "ok", {
        "user_id": user.id,
        "name": user.name,
        "area": user.area,
        "is_driver": user.is_driver,
        "rating_avg": user.rating_avg,
        "rating_count": user.rating_count,
    })


# ---------------------------------------------------------
# UPDATE PROFILE
# ---------------------------------------------------------

def handle_update_profile(msg: Message, context: Context) -> Message:
    # Must be logged in
    user_id = context.get("user_id")
    if not user_id:
        return make_error(msg, "NOT_LOGGED_IN")

    payload = msg.get("payload", {})
    if "area" not in payload or "is_driver" not in payload:
        return make_error(msg, "MISSING_FIELDS")

    area = payload["area"]
    is_driver = bool(payload["is_driver"])

    updated_user = update_user_profile(user_id, area, is_driver)
    if updated_user is None:
        return make_error(msg, "USER_NOT_FOUND")

    return make_response(msg, "ok", {
        "area": updated_user.area,
        "is_driver": updated_user.is_driver,
    })


# ---------------------------------------------------------
# ADD SCHEDULE
# ---------------------------------------------------------

def handle_add_schedule(msg: Message, context: Context) -> Message:
    user_id = context.get("user_id")
    if not user_id:
        return make_error(msg, "NOT_LOGGED_IN")

    payload = msg.get("payload", {})
    needed = ["weekday", "depart_time", "direction"]

    for key in needed:
        if key not in payload:
            return make_error(msg, f"MISSING_FIELD_{key.upper()}")

    weekday = payload["weekday"]
    depart_time = payload["depart_time"]
    direction = payload["direction"]

    # Validate weekday
    if not isinstance(weekday, int) or weekday < 0 or weekday > 6:
        return make_error(msg, "INVALID_WEEKDAY")

    if direction not in ("toAUB", "fromAUB"):
        return make_error(msg, "INVALID_DIRECTION")

    try:
        add_schedule(user_id, weekday, depart_time, direction)
    except Exception:
        return make_error(msg, "ADD_SCHEDULE_FAILED")

    return make_response(msg, "ok", {"status": "added"})


# ---------------------------------------------------------
# LIST SCHEDULES
# ---------------------------------------------------------

def handle_list_schedules(msg: Message, context: Context) -> Message:
    user_id = context.get("user_id")
    if not user_id:
        return make_error(msg, "NOT_LOGGED_IN")

    schedules = list_schedules_for_user(user_id)
    return make_response(msg, "ok", {"schedules": schedules})


# ---------------------------------------------------------
# DELETE SCHEDULE
# ---------------------------------------------------------

def handle_delete_schedule(msg: Message, context: Context) -> Message:
    user_id = context.get("user_id")
    if not user_id:
        return make_error(msg, "NOT_LOGGED_IN")

    payload = msg.get("payload", {})
    if "schedule_id" not in payload:
        return make_error(msg, "MISSING_FIELD_SCHEDULE_ID")

    schedule_id = payload["schedule_id"]

    success = delete_schedule(user_id, schedule_id)
    if not success:
        return make_error(msg, "DELETE_FAILED_OR_NOT_OWNER")

    return make_response(msg, "ok", {"deleted": schedule_id})


# ---------------------------------------------------------
# POST RIDE REQUEST + MATCHING
# ---------------------------------------------------------

def handle_post_ride_request(msg: Message, context: Context) -> Message:
    user_id = context.get("user_id")
    if not user_id:
        return make_error(msg, "NOT_LOGGED_IN")

    payload = msg.get("payload", {})
    needed = ["area", "weekday", "target_time", "direction"]

    for key in needed:
        if key not in payload:
            return make_error(msg, f"MISSING_FIELD_{key.upper()}")

    area = payload["area"]
    weekday = int(payload["weekday"])
    target_time = payload["target_time"]  # 'HH:MM'
    direction = payload["direction"]

    if direction not in ("toAUB", "fromAUB"):
        return make_error(msg, "INVALID_DIRECTION")

    if not (0 <= weekday <= 6):
        return make_error(msg, "INVALID_WEEKDAY")

    from datetime import datetime
    try:
        datetime.strptime(target_time, "%H:%M")
    except ValueError:
        return make_error(msg, "INVALID_TARGET_TIME")

    # 1) Create the ride request in DB (status 'open')
    try:
        request_id = create_ride_request(
            rider_id=user_id,
            area=area,
            weekday=weekday,
            target_time=target_time,
            direction=direction,
            status="open",
        )
    except Exception:
        return make_error(msg, "CREATE_RIDE_REQUEST_FAILED")

    # 2) Find candidate drivers using the matching module
    try:
        candidates = find_candidates_for_request(
            area, weekday, target_time, direction
        )
    except Exception:
        return make_error(msg, "MATCHING_FAILED")

    # Right now we just return the list of candidates to the rider.
    # Later, when we add live notifications, we'll also "broadcast" to drivers.
    return make_response(msg, "ok", {
        "ride_request_id": request_id,
        "candidates": candidates,
    })


# ---------------------------------------------------------
# DRIVER ACCEPT
# ---------------------------------------------------------


def handle_driver_accept(msg: Message, context: Context) -> Message:
    user_id = context.get("user_id")

    if not user_id:
        return make_error(msg, "NOT_LOGGED_IN")

    # Ensure this user is a driver
    # We reuse get_user_by_username or get_user_by_id?
    from db import get_user_by_id
    driver_user = get_user_by_id(user_id)
    if not driver_user or not driver_user.is_driver:
        return make_error(msg, "NOT_A_DRIVER")

    payload = msg.get("payload", {})
    if "request_id" not in payload:
        return make_error(msg, "MISSING_FIELD_REQUEST_ID")

    request_id = payload["request_id"]

    # Fetch the ride request
    ride = get_ride_request_by_id(request_id)
    if ride is None:
        return make_error(msg, "REQUEST_NOT_FOUND")

    # Check if it's still open
    if ride["status"] != "open":
        return make_error(msg, "REQUEST_NOT_OPEN")

    # Optional check: driver must be in same area
    if ride["area"] != driver_user.area:
        return make_error(msg, "AREA_MISMATCH")

    # Accept the request
    try:
        update_ride_request_status(request_id, "accepted", driver_id=user_id)
    except Exception:
        return make_error(msg, "ACCEPT_FAILED")

    # Return info for the driver or for rider later
    return make_response(msg, "ok", {
        "request_id": request_id,
        "status": "accepted",
        "driver_id": user_id,
        "driver_name": driver_user.name,
    })

# ---------------------------------------------------------
# DRIVER DECLINE
# ---------------------------------------------------------


def handle_driver_decline(msg: Message, context: Context) -> Message:
    user_id = context.get("user_id")

    if not user_id:
        return make_error(msg, "NOT_LOGGED_IN")

    from db import get_user_by_id
    driver_user = get_user_by_id(user_id)
    if not driver_user or not driver_user.is_driver:
        return make_error(msg, "NOT_A_DRIVER")

    payload = msg.get("payload", {})
    if "request_id" not in payload:
        return make_error(msg, "MISSING_FIELD_REQUEST_ID")

    request_id = payload["request_id"]
    ride = get_ride_request_by_id(request_id)
    if ride is None:
        return make_error(msg, "REQUEST_NOT_FOUND")

    # Declining does NOT change status.
    # It simply acknowledges that THIS driver refuses.
    # Later GUI will decide how to show this.
    return make_response(msg, "ok", {
        "status": "declined",
        "request_id": request_id,
    })

# ---------------------------------------------------------
# RATE USER
# ---------------------------------------------------------


def handle_rate_user(msg: Message, context: Context) -> Message:
    user_id = context.get("user_id")
    if not user_id:
        return make_error(msg, "NOT_LOGGED_IN")

    payload = msg.get("payload", {})
    needed = ["ratee_id", "stars", "comment"]

    for key in needed:
        if key not in payload:
            return make_error(msg, f"MISSING_FIELD_{key.upper()}")

    ratee_id = payload["ratee_id"]
    stars = payload["stars"]
    comment = payload["comment"]

    # Basic validations
    if not isinstance(stars, int) or stars < 1 or stars > 5:
        return make_error(msg, "INVALID_STARS")

    if ratee_id == user_id:
        return make_error(msg, "CANNOT_RATE_SELF")

    try:
        new_avg, new_count = add_rating(
            rater_id=user_id,
            ratee_id=ratee_id,
            stars=stars,
            comment=comment,
        )
    except ValueError:
        return make_error(msg, "RATEE_NOT_FOUND")
    except Exception:
        return make_error(msg, "RATING_FAILED")

    return make_response(msg, "ok", {
        "ratee_id": ratee_id,
        "rating_avg": new_avg,
        "rating_count": new_count,
    })


# ---------------------------------------------------------
# LIST RATINGS (for the logged-in user)
# ---------------------------------------------------------

def handle_list_ratings(msg: Message, context: Context) -> Message:
    user_id = context.get("user_id")
    if not user_id:
        return make_error(msg, "NOT_LOGGED_IN")

    ratings = list_ratings_for_user(user_id)
    return make_response(msg, "ok", {"ratings": ratings})


# ---------------------------------------------------------
# RELAY SEND (fallback chat)
# ---------------------------------------------------------

def handle_relay_send(msg: Message, context: Context) -> Message:
    """
    Send a chat message into a relay channel.

    Expected payload:
      {
        "channel_id": "some-string",   # often ride_request_id as string
        "text": "Hello there!"
      }
    """
    user_id = context.get("user_id")
    if not user_id:
        return make_error(msg, "NOT_LOGGED_IN")

    payload = msg.get("payload", {})
    if "channel_id" not in payload or "text" not in payload:
        return make_error(msg, "MISSING_FIELDS")

    channel_id = str(payload["channel_id"])
    text = str(payload["text"])

    if not text.strip():
        return make_error(msg, "EMPTY_MESSAGE")

    try:
        stored = relay_post_message(channel_id, user_id, text)
    except Exception:
        return make_error(msg, "RELAY_SEND_FAILED")

    # Echo back what we stored
    return make_response(msg, "ok", {
        "channel_id": channel_id,
        "message": stored,
    })


# ---------------------------------------------------------
# RELAY POLL (fetch chat messages)
# ---------------------------------------------------------

def handle_relay_poll(msg: Message, context: Context) -> Message:
    """
    Fetch chat messages from a relay channel since a given seq.

    Expected payload:
      {
        "channel_id": "some-string",
        "last_seq": 0   # client has seen up to this seq; get > last_seq
      }
    """
    user_id = context.get("user_id")
    if not user_id:
        return make_error(msg, "NOT_LOGGED_IN")

    payload = msg.get("payload", {})
    if "channel_id" not in payload or "last_seq" not in payload:
        return make_error(msg, "MISSING_FIELDS")

    channel_id = str(payload["channel_id"])
    try:
        last_seq = int(payload["last_seq"])
    except (ValueError, TypeError):
        return make_error(msg, "INVALID_LAST_SEQ")

    try:
        messages = relay_get_messages_since(channel_id, last_seq)
    except Exception:
        return make_error(msg, "RELAY_POLL_FAILED")

    return make_response(msg, "ok", {
        "channel_id": channel_id,
        "messages": messages,
    })

# ---------------------------------------------------------
# Health Handler
# ---------------------------------------------------------


def handle_health(msg, context):
    return make_response(msg, "ok", {"status": "ok"})


def handle_list_my_requests(msg: Message, context: Context) -> Message:
    user_id = context.get("user_id")
    if not user_id:
        return make_error(msg, "NOT_LOGGED_IN")

    try:
        requests = list_requests_by_rider(user_id)
        return make_response(msg, "ok", {"requests": requests})
    except Exception as e:
        print("ERROR in handle_list_my_requests:", e)
        return make_error(msg, "INTERNAL_SERVER_ERROR")


def handle_list_driver_requests(msg: Message, context: Context) -> Message:
    user_id = context.get("user_id")
    if not user_id:
        return make_error(msg, "NOT_LOGGED_IN")

    try:
        requests = list_requests_for_driver(user_id)
        return make_response(msg, "ok", {"requests": requests})
    except Exception as e:
        print("ERROR in handle_list_driver_requests:", e)
        return make_error(msg, "INTERNAL_SERVER_ERROR")
