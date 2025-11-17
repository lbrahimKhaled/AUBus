from dataclasses import dataclass
import socket
from typing import Optional

@dataclass
class User:
    def __init__(
        self,
        id: int = 0,
        name: str = "",
        email: str = "",
        username: str = "",
        pass_hash: str = "",
        area: str = "",
        is_driver: bool = True,
        rating_avg: float = 0.0,
        rating_count: int = 0,
        created_at: str = "",
        ip: str = "",
        port: int = 0,
    ):
        # DB fields
        self.id = id
        self.name = name
        self.email = email
        self.username = username
        self.pass_hash = pass_hash
        self.area = area
        self.is_driver = is_driver
        self.rating_avg = rating_avg
        self.rating_count = rating_count
        self.created_at = created_at

        # Network fields
        self.ip = ip
        self.port = port

        # Runtime-only fields
        self.online = False

    @classmethod
    def default(cls):
        """Default empty user (explicit alternative constructor)."""
        return cls()

    def set_connection(self, conn: socket.socket):
        """Attach a live socket connection to this user."""
        self.conn = conn
        self.online = True

    def to_dict(self) -> dict:
        """Safe JSON representation for sending to clients."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "username": self.username,
            "area": self.area,
            "is_driver": self.is_driver,
            "rating_avg": self.rating_avg,
            "rating_count": self.rating_count,
            "created_at": self.created_at,
            "ip": self.ip,
            "port": self.port,
            "online": self.online,
        }
    

@dataclass
class Schedule:
    id: int
    user_id: int
    weekday: int            # 0=Monday ... 6=Sunday
    depart_time: str        # "HH:MM" (24h format, e.g. "07:30")
    direction: str          # "toAUB" or "fromAUB"


@dataclass
class RideRequest:
    id: int
    rider_id: int
    area: str
    direction: str
    target_time: str        # "YYYY-MM-DDTHH:MM"
    status: str             # "open", "accepted", "declined", "expired"
    driver_id: Optional[int]
    created_at: str         # ISO timestamp string


@dataclass
class Rating:
    id: int
    rater_id: int
    ratee_id: int
    stars: int              # 1..5
    comment: str
    created_at: str