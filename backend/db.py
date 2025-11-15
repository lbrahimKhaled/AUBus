# db.py
import sqlite3
from datetime import datetime
from typing import Optional

import bcrypt  # make sure to: pip install bcrypt

from config import DB_PATH
from models import User


# ---------- Connection helpers ----------

def get_connection() -> sqlite3.Connection:
    """
    Open a new SQLite connection.

    We set row_factory to sqlite3.Row so we can access columns by name,
    like row["username"].
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------- Schema / migrations ----------

def init_db() -> None:
    """
    Create all tables if they don't already exist.

    You can safely call this every time the server starts.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL UNIQUE,
            pass_hash TEXT NOT NULL,
            area TEXT NOT NULL,
            is_driver INTEGER NOT NULL DEFAULT 0,
            rating_avg REAL NOT NULL DEFAULT 0.0,
            rating_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            weekday INTEGER NOT NULL,            -- 0..6
            depart_time TEXT NOT NULL,           -- "HH:MM"
            direction TEXT NOT NULL,             -- "toAUB" / "fromAUB"
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS ride_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rider_id INTEGER NOT NULL,
            area TEXT NOT NULL,
            target_time TEXT NOT NULL,           -- "YYYY-MM-DDTHH:MM"
            status TEXT NOT NULL,                -- "open", "accepted", ...
            driver_id INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (rider_id) REFERENCES users(id),
            FOREIGN KEY (driver_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rater_id INTEGER NOT NULL,
            ratee_id INTEGER NOT NULL,
            stars INTEGER NOT NULL,              -- 1..5
            comment TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (rater_id) REFERENCES users(id),
            FOREIGN KEY (ratee_id) REFERENCES users(id)
        );
        """
    )

    conn.commit()
    conn.close()


# ---------- Password helpers ----------

def hash_password(plain_password: str) -> str:
    """
    Hash a password using bcrypt and return the hash as a UTF-8 string.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check if a plain password matches the stored bcrypt hash.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ---------- User CRUD ----------

def create_user(
    name: str,
    email: str,
    username: str,
    plain_password: str,
    area: str,
    is_driver: bool,
) -> User:
    """
    Insert a new user into the DB and return a User dataclass.

    Raises sqlite3.IntegrityError if email/username are not unique.
    """
    conn = get_connection()
    cur = conn.cursor()

    pass_hash = hash_password(plain_password)
    created_at = datetime.utcnow().isoformat(timespec="seconds")

    cur.execute(
        """
        INSERT INTO users (name, email, username, pass_hash, area, is_driver,
                           rating_avg, rating_count, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 0.0, 0, ?)
        """,
        (name, email, username, pass_hash, area, int(is_driver), created_at),
    )

    user_id = cur.lastrowid
    conn.commit()

    conn.close()

    return User(
        id=user_id,
        name=name,
        email=email,
        username=username,
        pass_hash=pass_hash,
        area=area,
        is_driver=is_driver,
        rating_avg=0.0,
        rating_count=0,
        created_at=created_at,
    )


def _row_to_user(row: sqlite3.Row) -> User:
    """
    Internal helper to convert a sqlite3.Row into a User dataclass.
    """
    return User(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        username=row["username"],
        pass_hash=row["pass_hash"],
        area=row["area"],
        is_driver=bool(row["is_driver"]),
        rating_avg=row["rating_avg"],
        rating_count=row["rating_count"],
        created_at=row["created_at"],
    )


def get_user_by_username(username: str) -> Optional[User]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()

    conn.close()

    if row is None:
        return None
    return _row_to_user(row)


def get_user_by_id(user_id: int) -> Optional[User]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()

    conn.close()

    if row is None:
        return None
    return _row_to_user(row)
