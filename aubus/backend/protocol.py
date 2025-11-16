# protocol.py
import json
import uuid
from typing import Any, Dict, Optional


# ---------------------------------------------------------
# Utility: generate a unique request ID (uuid4)
# ---------------------------------------------------------

def new_req_id() -> str:
    """
    Generate a random unique request ID using UUID4.
    The GUI client will use this when sending messages.
    """
    return str(uuid.uuid4())


# ---------------------------------------------------------
# Encoding messages (server → client, client → server)
# ---------------------------------------------------------

def send_message(sock, msg: Dict[str, Any]) -> None:
    """
    Send a Python dict as a JSON line: b"...\\n"
    """
    data = json.dumps(msg).encode("utf-8") + b"\n"
    sock.sendall(data)


# ---------------------------------------------------------
# Reading messages (server ← client)
# ---------------------------------------------------------

def read_message(sock) -> Optional[Dict[str, Any]]:
    """
    Read one JSON line from the socket.
    Returns None if the connection is closed.

    Assumes the client always sends '\n' at the end.
    """
    buffer = b""
    while True:
        chunk = sock.recv(1)
        if not chunk:
            return None  # client disconnected
        if chunk == b"\n":
            break
        buffer += chunk

    try:
        return json.loads(buffer.decode("utf-8"))
    except json.JSONDecodeError:
        return None  # malformed JSON


# ---------------------------------------------------------
# Response helper
# ---------------------------------------------------------

def make_response(request: Dict[str, Any], suffix: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a response message with:
    - the same req_id as the request
    - type = request.type + "_" + suffix
    """
    return {
        "type": f"{request['type']}_{suffix}",
        "req_id": request["req_id"],
        "payload": payload
    }


# ---------------------------------------------------------
# Error response helper
# ---------------------------------------------------------

def make_error(request: Dict[str, Any], error_code: str) -> Dict[str, Any]:
    """
    Create a standardized error response.
    """
    return {
        "type": f"{request['type']}_error",
        "req_id": request.get("req_id"),
        "payload": {"error": error_code},
    }
