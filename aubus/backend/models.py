# models.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    id: int
    name: str
    email: str
    username: str
    pass_hash: str          # hashed password (we'll store bcrypt hashes)
    area: str               # e.g. "Hamra", "Tayouneh"
    is_driver: bool
    rating_avg: float
    rating_count: int
    created_at: str         # ISO timestamp string ("2025-11-15T15:30:00")


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
