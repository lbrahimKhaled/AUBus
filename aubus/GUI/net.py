# gui/net.py
import socket
from typing import Any, Dict, Optional

from backend.protocol import (
    send_message,
    read_message,
    new_req_id,
)
from backend.config import SERVER_HOST, SERVER_PORT


class AubusClientError(Exception):
    def __init__(self, code: str, response: Optional[Dict[str, Any]] = None):
        super().__init__(code)
        self.code = code
        self.response = response or {}


class AubusClient:
    """
    Simple client wrapper to talk to the AUBus backend using the same
    JSON-line protocol as the server.

    One AubusClient instance holds a single TCP connection and preserves
    login context (user_id) via the server-side session.
    """

    def __init__(self, host: str = SERVER_HOST, port: int = SERVER_PORT) -> None:
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self._connect()

    # ---------------- Core plumbing ----------------

    def _connect(self) -> None:
        if self.sock is not None:
            return
        self.sock = socket.create_connection((self.host, self.port))

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None

    def _ensure_socket(self) -> socket.socket:
        if self.sock is None:
            self._connect()
        assert self.sock is not None
        return self.sock

    def send_raw(self, msg_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a message and return the raw decoded response dict.
        """
        sock = self._ensure_socket()
        request = {
            "type": msg_type,
            "req_id": new_req_id(),
            "payload": payload,
        }
        send_message(sock, request)
        response = read_message(sock)
        if response is None:
            raise AubusClientError("CONNECTION_CLOSED")
        return response

    def send(self, msg_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a message and either return payload on success or raise
        AubusClientError on error.
        """
        resp = self.send_raw(msg_type, payload)
        resp_type = resp.get("type", "")
        if resp_type.endswith("_error"):
            code = resp.get("payload", {}).get("error", "UNKNOWN_ERROR")
            raise AubusClientError(code, resp)
        return resp.get("payload", {})

    # ---------------- High-level API ----------------

    # Health / ping

    def health(self) -> Dict[str, Any]:
        return self.send("health", {})

    def ping(self, extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return self.send("ping", extra or {})

    # Auth

    def register(
        self,
        name: str,
        email: str,
        username: str,
        password: str,
        area: str,
        is_driver: bool,
    ) -> Dict[str, Any]:
        return self.send(
            "register",
            {
                "name": name,
                "email": email,
                "username": username,
                "password": password,
                "area": area,
                "is_driver": is_driver,
            },
        )

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Returns payload:
          {
            "user_id": int,
            "name": str,
            "area": str,
            "is_driver": bool,
            "rating_avg": float,
            "rating_count": int
          }
        """
        return self.send(
            "login",
            {
                "username": username,
                "password": password,
            },
        )

    def update_profile(self, area: str, is_driver: bool) -> Dict[str, Any]:
        return self.send(
            "update_profile",
            {
                "area": area,
                "is_driver": is_driver,
            },
        )

    # Schedules

    def add_schedule(self, weekday: int, depart_time: str, direction: str) -> Dict[str, Any]:
        """
        weekday: 0..6 (Monday = 0)
        depart_time: "HH:MM"
        direction: "toAUB" / "fromAUB"
        """
        return self.send(
            "add_schedule",
            {
                "weekday": weekday,
                "depart_time": depart_time,
                "direction": direction,
            },
        )

    def list_schedules(self) -> Dict[str, Any]:
        # payload: { "schedules": [ {id, weekday, depart_time, direction}, ... ] }
        return self.send("list_schedules", {})

    def delete_schedule(self, schedule_id: int) -> Dict[str, Any]:
        return self.send("delete_schedule", {"schedule_id": schedule_id})

    # Ride requests

    def post_ride_request(
        self,
        area: str,
        weekday: int,
        target_time: str,
        direction: str,
    ) -> Dict[str, Any]:
        """
        target_time is "HH:MM" as expected by matching.
        Returns payload:
          {
            "ride_request_id": int,
            "candidates": [...]
          }
        """
        return self.send(
            "post_ride_request",
            {
                "area": area,
                "weekday": weekday,
                "target_time": target_time,
                "direction": direction,
            },
        )

    def list_my_requests(self) -> Dict[str, Any]:
        # payload: { "requests": [...] }
        return self.send("list_my_requests", {})

    def list_driver_requests(self) -> Dict[str, Any]:
        # payload: { "requests": [...] }
        return self.send("list_driver_requests", {})

    def driver_accept(self, request_id: int) -> Dict[str, Any]:
        return self.send("driver_accept", {"request_id": request_id})

    def driver_decline(self, request_id: int) -> Dict[str, Any]:
        return self.send("driver_decline", {"request_id": request_id})

    # Ratings

    def rate_user(self, ratee_id: int, stars: int, comment: str) -> Dict[str, Any]:
        return self.send(
            "rate_user",
            {
                "ratee_id": ratee_id,
                "stars": stars,
                "comment": comment,
            },
        )

    def list_ratings(self) -> Dict[str, Any]:
        # payload: { "ratings": [...] }
        return self.send("list_ratings", {})

    # Relay (chat)

    def relay_send(self, channel_id: str, text: str) -> Dict[str, Any]:
        return self.send(
            "relay_send",
            {
                "channel_id": channel_id,
                "text": text,
            },
        )

    def relay_poll(self, channel_id: str, last_seq: int) -> Dict[str, Any]:
        return self.send(
            "relay_poll",
            {
                "channel_id": channel_id,
                "last_seq": last_seq,
            },
        )
