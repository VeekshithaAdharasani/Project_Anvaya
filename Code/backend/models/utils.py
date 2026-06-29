from datetime import datetime, timezone
from typing import Any


def parse_datetime(val: Any) -> datetime:
    """Parses a value into a timezone-aware UTC datetime.

    If the value is a string, it is parsed from ISO format.
    If the value is None, it returns the current UTC time.
    If it is a naive datetime, it is localized to UTC.
    """
    if isinstance(val, str):
        return datetime.fromisoformat(val)
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)
    return datetime.now(timezone.utc)
