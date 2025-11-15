# config.py

# Path to the SQLite database file.
# This will be created automatically on first run.
DB_PATH = "aubus.sqlite3"

# Server host and port (we'll use these later in server.py)
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000

# Matching time window in minutes (+/- around requested time)
MATCH_TIME_WINDOW_MIN = 45
