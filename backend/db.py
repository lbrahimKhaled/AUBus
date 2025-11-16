# db.py
import sqlite3
from datetime import datetime, timedelta
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
            direction TEXT DEFAULT 'toAUB',
            weekday INTEGER NOT NULL,            -- 0..6 (Monday=0)
            target_time TEXT NOT NULL,           -- "HH:MM"
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

# ---------------------------------------------------------
# Authentication helper: validate a login attempt
# ---------------------------------------------------------


def authenticate_user(username: str, plain_password: str) -> Optional[User]:
    """
    Return the User if the username exists AND the password matches.
    Otherwise return None.
    """
    user = get_user_by_username(username)
    if user is None:
        return None

    if verify_password(plain_password, user.pass_hash):
        return user

    return None


# ---------------------------------------------------------
# Update profile (area + is_driver)
# ---------------------------------------------------------

def update_user_profile(user_id: int, area: str, is_driver: bool) -> Optional[User]:
    """
    Update the area and driver flag of the user.
    Returns the updated user, or None if user_id doesn't exist.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE users
        SET area = ?, is_driver = ?
        WHERE id = ?
        """,
        (area, int(is_driver), user_id),
    )
    conn.commit()

    conn.close()

    # Return the updated user
    return get_user_by_id(user_id)


# ---------------------------------------------------------
# Schedule CRUD
# ---------------------------------------------------------

def add_schedule(user_id: int, weekday: int, depart_time: str, direction: str):
    """
    Add a schedule entry for the given user.
    direction: "toAUB" or "fromAUB"
    depart_time: "HH:MM"
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO schedules (user_id, weekday, depart_time, direction)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, weekday, depart_time, direction),
    )

    conn.commit()
    conn.close()


def list_schedules_for_user(user_id: int):
    """
    Return a list of schedule rows for the user.
    Returns a list of dicts prepared for JSON output.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, weekday, depart_time, direction
        FROM schedules
        WHERE user_id = ?
        ORDER BY weekday ASC, depart_time ASC
        """,
        (user_id,),
    )

    rows = cur.fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append({
            "id": r["id"],
            "weekday": r["weekday"],
            "depart_time": r["depart_time"],
            "direction": r["direction"],
        })
    return result


def delete_schedule(user_id: int, schedule_id: int) -> bool:
    """
    Delete a schedule row if it belongs to the user.
    Returns True if deleted, False otherwise.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        DELETE FROM schedules
        WHERE id = ? AND user_id = ?
        """,
        (schedule_id, user_id),
    )

    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()

    return deleted


# ---------------------------------------------------------
# Ride requests
# ---------------------------------------------------------

def create_ride_request(
    rider_id: int,
    area: str,
    weekday: int,
    target_time: str,
    direction: str,
    status: str = "open",
):
    """
    Insert a ride request into the DB.

    weekday: 0..6 (Monday=0)
    target_time: 'HH:MM'
    direction: 'toAUB' or 'fromAUB'
    """
    conn = get_connection()
    cur = conn.cursor()

    created_at = datetime.utcnow().isoformat(timespec="seconds")

    cur.execute(
        """
        INSERT INTO ride_requests (
            rider_id,
            area,
            weekday,
            target_time,
            direction,
            status,
            driver_id,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, NULL, ?)
        """,
        (rider_id, area, weekday, target_time, direction, status, created_at),
    )

    req_id = cur.lastrowid
    conn.commit()
    conn.close()

    return req_id


def update_ride_request_status(
    request_id: int,
    status: str,
    driver_id: int | None = None,
) -> None:
    """
    Update the status (and optionally driver_id) of a ride request.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE ride_requests
        SET status = ?, driver_id = ?
        WHERE id = ?
        """,
        (status, driver_id, request_id),
    )

    conn.commit()
    conn.close()


# ---------------------------------------------------------
# Matching query: find candidate drivers in a time window
# ---------------------------------------------------------


def normalize_time(time_str: str) -> str:
    """
    Ensure time_str is in HH:MM (24h) format.
    """
    from datetime import datetime
    dt = datetime.strptime(time_str, "%H:%M")
    return dt.strftime("%H:%M")


def find_candidate_drivers(
    area: str,
    weekday: int,
    start_time: str,
    end_time: str,
    direction: str,
):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Normalize HH:MM formats
    start_time = normalize_time(start_time)
    end_time = normalize_time(end_time)

    cur.execute(
        """
        SELECT
            s.id AS schedule_id,
            s.user_id AS driver_id,
            s.weekday,
            s.depart_time,
            s.direction,
            u.username AS driver_name,
            u.area,
            u.rating_avg,
            u.rating_count
        FROM schedules AS s
        JOIN users AS u ON u.id = s.user_id
        WHERE
            u.area = ?
            AND s.weekday = ?
            AND s.direction = ?
            AND s.depart_time BETWEEN ? AND ?
        ORDER BY u.rating_avg DESC, u.rating_count DESC
        """,
        (area, weekday, direction, start_time, end_time),
    )

    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ---------------------------------------------------------
# Fetch single ride request
# ---------------------------------------------------------


def get_ride_request_by_id(request_id: int):
    """
    Return a dict representing the ride request, or None if not found.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM ride_requests
        WHERE id = ?
        """,
        (request_id,),
    )

    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "id": row["id"],
        "rider_id": row["rider_id"],
        "area": row["area"],
        "target_time": row["target_time"],
        "status": row["status"],
        "driver_id": row["driver_id"],
        "created_at": row["created_at"],
    }


# ---------------------------------------------------------
# Ratings
# ---------------------------------------------------------

def add_rating(
    rater_id: int,
    ratee_id: int,
    stars: int,
    comment: str,
):
    """
    Insert a rating and update the ratee's rating_avg and rating_count.

    stars: 1..5
    """
    conn = get_connection()
    cur = conn.cursor()

    created_at = datetime.utcnow().isoformat(timespec="seconds")

    # 1) Insert into ratings table
    cur.execute(
        """
        INSERT INTO ratings (rater_id, ratee_id, stars, comment, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (rater_id, ratee_id, stars, comment, created_at),
    )

    # 2) Fetch current stats for the ratee
    cur.execute(
        """
        SELECT rating_avg, rating_count
        FROM users
        WHERE id = ?
        """,
        (ratee_id,),
    )
    row = cur.fetchone()

    if row is None:
        # Ratee user doesn't exist; rollback rating
        conn.rollback()
        conn.close()
        raise ValueError("Ratee user not found")

    old_avg = row["rating_avg"]
    old_count = row["rating_count"]

    # 3) Compute new average
    new_count = old_count + 1
    new_avg = (old_avg * old_count + stars) / \
        new_count if old_count > 0 else float(stars)

    # 4) Update user row
    cur.execute(
        """
        UPDATE users
        SET rating_avg = ?, rating_count = ?
        WHERE id = ?
        """,
        (new_avg, new_count, ratee_id),
    )

    conn.commit()
    conn.close()

    return new_avg, new_count


def list_ratings_for_user(user_id: int):
    """
    Return a list of ratings received by the given user.
    Each rating is a dict ready for JSON.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT r.id, r.stars, r.comment, r.created_at,
               u.name AS rater_name, u.id AS rater_id
        FROM ratings r
        JOIN users u ON r.rater_id = u.id
        WHERE r.ratee_id = ?
        ORDER BY r.created_at DESC
        """,
        (user_id,),
    )

    rows = cur.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append({
            "id": row["id"],
            "stars": row["stars"],
            "comment": row["comment"],
            "created_at": row["created_at"],
            "rater_id": row["rater_id"],
            "rater_name": row["rater_name"],
        })
    return result


def list_requests_by_rider(rider_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            r.id,
            r.target_time,
            r.direction,
            r.status,
            r.area,
            r.driver_id,
            u.username AS driver_name
        FROM ride_requests AS r
        LEFT JOIN users AS u ON u.id = r.driver_id
        WHERE r.rider_id = ?
        ORDER BY r.created_at DESC
    """, (rider_id,))
    rows = cur.fetchall()
    conn.close()
    # if you set row_factory = sqlite3.Row, this works:
    return [dict(row) for row in rows]


def list_requests_for_driver(driver_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            r.id,
            r.target_time,
            r.direction,
            r.status,
            r.area,
            r.rider_id,
            u.username AS rider_name
        FROM ride_requests AS r
        JOIN users AS u ON u.id = r.rider_id
        WHERE r.driver_id = ? OR (r.driver_id IS NULL AND r.status = 'open')
        ORDER BY r.created_at DESC
    """, (driver_id,))

    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]
