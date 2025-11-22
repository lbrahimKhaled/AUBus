# db.py
import sqlite3
from datetime import datetime, timedelta
from typing import Optional
import threading

import bcrypt  # make sure to: pip install bcrypt

DB_PATH = "aubus.sqlite3"
from .models.models import User
DB_LOCK = threading.Lock()

# ---------- Connection helpers ----------

def get_connection() -> sqlite3.Connection:
    """
    Open a new SQLite connection.

    We set row_factory to sqlite3.Row so we can access columns by name,
    like row["username"].
    """
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ---------- Schema / migrations ----------

def init_db() -> None:
    """
    Create all tables if they don't already exist.

    You can safely call this every time the server starts.
    """
    with DB_LOCK:
        conn = get_connection()
        cur = conn.cursor()

        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                pass_hash TEXT NOT NULL,
                area TEXT NOT NULL,
                is_driver INTEGER NOT NULL DEFAULT 0,
                rating_avg REAL NOT NULL DEFAULT 0.0,
                rating_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                city TEXT,
                country TEXT
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

            CREATE TABLE IF NOT EXISTS driver_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rider_id INTEGER NOT NULL,
                driver_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (rider_id) REFERENCES users(id),
                FOREIGN KEY (driver_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS emergencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id INTEGER,
                reporter_username TEXT,
                reporter_role TEXT,
                partner_id INTEGER,
                partner_username TEXT,
                partner_role TEXT,
                raw_context TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reporter_id) REFERENCES users(id),
                FOREIGN KEY (partner_id) REFERENCES users(id)
            );
            """
        )

        # Ensure location columns exist for older DBs
        cur.execute("PRAGMA table_info(users);")
        existing_cols = {row[1] for row in cur.fetchall()}
        for col_sql, col_name in [
            ("ALTER TABLE users ADD COLUMN latitude REAL;", "latitude"),
            ("ALTER TABLE users ADD COLUMN longitude REAL;", "longitude"),
            ("ALTER TABLE users ADD COLUMN city TEXT;", "city"),
            ("ALTER TABLE users ADD COLUMN country TEXT;", "country"),
        ]:
            if col_name not in existing_cols:
                try:
                    cur.execute(col_sql)
                except sqlite3.OperationalError:
                    # Column might have been added concurrently; ignore
                    pass

        conn.commit()
        conn.close()

def add_driver_request(rider_id: int, driver_id: int) -> None:
    """
    Store that rider_id has sent a request to driver_id.
    """
    with DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO driver_requests (rider_id, driver_id)
            VALUES (?, ?)
            """,
            (rider_id, driver_id),
        )

        conn.commit()
        conn.close()

def getRequests(driver_id: int) -> list[User]:
    """
    Returns a list of User objects representing all riders
    who have sent a request to the given driver.
    Most recent requests first.
    """

    with DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(
            """
            SELECT u.*
            FROM driver_requests dr
            JOIN users u ON u.id = dr.rider_id
            WHERE dr.driver_id = ?
            ORDER BY dr.created_at DESC
            """,
            (driver_id,),
        )

        rows = cur.fetchall()
        conn.close()

        return [_row_to_user(row) for row in rows]


def delete_driver_requests_for_user(user_id: int) -> None:
    """
    Remove all driver_requests rows where the given user
    is either the rider or the driver. Used on disconnect cleanup.
    """
    with DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM driver_requests
            WHERE rider_id = ? OR driver_id = ?
            """,
            (user_id, user_id),
        )
        conn.commit()
        conn.close()


def add_emergency_report(
    reporter_id: Optional[int],
    reporter_username: str,
    reporter_role: str,
    partner_id: Optional[int],
    partner_username: str,
    partner_role: str,
    raw_context: str,
) -> None:
    """Persist an emergency report with as much context as available."""
    with DB_LOCK:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO emergencies (
                reporter_id, reporter_username, reporter_role,
                partner_id, partner_username, partner_role,
                raw_context, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reporter_id,
                reporter_username,
                reporter_role,
                partner_id,
                partner_username,
                partner_role,
                raw_context,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
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
    with DB_LOCK:
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
            id=user_id if user_id is not None else -1,
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
        latitude=row["latitude"] if "latitude" in row.keys() else None,
        longitude=row["longitude"] if "longitude" in row.keys() else None,
        city=row["city"] if "city" in row.keys() else "",
        country=row["country"] if "country" in row.keys() else "",
    )


def get_user_by_username(username: str) -> Optional[User]:
    with DB_LOCK:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cur.fetchone()

        conn.close()

        if row is None:
            return None
        return _row_to_user(row)
    
def update_is_driver_by_username(username: str, new_value: bool) -> None:
    with DB_LOCK:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE users SET is_driver = ? WHERE username = ?",
                (1 if new_value else 0, username),
            )
            conn.commit()
        finally:
            conn.close()

def update_user_location(
    user_id: int,
    area: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    city: str | None = None,
    country: str | None = None,
) -> None:
    """
    Update persisted location fields for a user.
    """
    with DB_LOCK:
        conn = get_connection()
        cur = conn.cursor()

        fields = []
        values = []
        if area is not None:
            fields.append("area = ?")
            values.append(area)
        if latitude is not None:
            fields.append("latitude = ?")
            values.append(latitude)
        if longitude is not None:
            fields.append("longitude = ?")
            values.append(longitude)
        if city is not None:
            fields.append("city = ?")
            values.append(city)
        if country is not None:
            fields.append("country = ?")
            values.append(country)

        if not fields:
            conn.close()
            return

        values.append(user_id)
        sql = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"
        cur.execute(sql, values)
        conn.commit()
        conn.close()

def get_user_by_id(user_id: int) -> Optional[User]:
    with DB_LOCK:
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
    with DB_LOCK:
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
    with DB_LOCK:
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
    with DB_LOCK:
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
    with DB_LOCK:
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
    with DB_LOCK:
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


def find_candidate_drivers(user: User, area_filter: str | None = None) -> list[User]:
    """
    Return a list of User objects representing all drivers
    filtered by area.
    area_filter:
        None/"" -> use user's area
        "all"   -> all drivers
        other   -> specific area
    """
    with DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        area_value = (area_filter or "").strip()
        if area_value.lower() == "all":
            cur.execute(
                """
                SELECT *
                FROM users
                WHERE is_driver = 1
                ORDER BY rating_avg DESC, rating_count DESC
                """
            )
        else:
            target_area = area_value or user.area
            cur.execute(
                """
                SELECT *
                FROM users
                WHERE is_driver = 1
                AND area = ?
                ORDER BY rating_avg DESC, rating_count DESC
                """,
                (target_area,),
            )

        rows = cur.fetchall()
        conn.close()

        # Convert rows → User objects
        result = []
        for row in rows:
            result.append(
                User(
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
            )

        return result


# ---------------------------------------------------------
# Fetch single ride request
# ---------------------------------------------------------


def get_ride_request_by_id(request_id: int):
    """
    Return a dict representing the ride request, or None if not found.
    """
    with DB_LOCK:
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
    with DB_LOCK:
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
    with DB_LOCK:
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
    with DB_LOCK:
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
    
    with DB_LOCK:
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
