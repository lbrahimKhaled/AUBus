# matching.py
from datetime import datetime, timedelta
from typing import List, Dict, Any

from config import MATCH_TIME_WINDOW_MIN
from db import find_candidate_drivers


def find_candidates_for_request(
    area: str,
    target_time_iso: str,
    direction: str,
    window_minutes: int = MATCH_TIME_WINDOW_MIN,
) -> List[Dict[str, Any]]:
    """
    Given a ride request description, compute the matching time window and
    use the DB helper to find candidate drivers.

    target_time_iso: 'YYYY-MM-DDTHH:MM'
    direction: 'toAUB' or 'fromAUB'
    """
    # Parse the ISO timestamp
    target_dt = datetime.fromisoformat(
        target_time_iso)  # raises ValueError if invalid

    weekday = target_dt.weekday()  # Monday=0 .. Sunday=6

    start_dt = target_dt - timedelta(minutes=window_minutes)
    end_dt = target_dt + timedelta(minutes=window_minutes)

    # We only care about time-of-day for schedule matching
    start_time_str = start_dt.strftime("%H:%M")
    end_time_str = end_dt.strftime("%H:%M")

    # NOTE: This simple approach doesn't specially handle crossing midnight.
    # For typical AUB commuting times, that's fine.

    return find_candidate_drivers(area, weekday, start_time_str, end_time_str, direction)
