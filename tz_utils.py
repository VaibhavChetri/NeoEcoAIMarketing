"""
Neo Eco Cleaning — Timezone Utilities
========================================
Ensures all timestamps are in IST (Asia/Kolkata, UTC+5:30)
regardless of the server's system timezone (e.g. Render runs UTC).
"""

from datetime import datetime, timezone, timedelta

# IST = UTC + 5:30
IST = timezone(timedelta(hours=5, minutes=30))


def now_ist() -> datetime:
    """Return the current datetime in IST (Asia/Kolkata, UTC+5:30)."""
    return datetime.now(IST)
