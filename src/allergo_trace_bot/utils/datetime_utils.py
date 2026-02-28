"""Universal datetime utilities for UTC handling.

This module provides a standardized approach for datetime handling:
1. ALL timestamps in the database are stored in UTC
2. User timezone is used only for display and input
3. All datetime comparisons happen in UTC

Best Practices:
- Always use get_utc_now() instead of datetime.now()
- Store datetimes in UTC in the database
- Convert to user timezone only when displaying
- Convert from user timezone to UTC when saving user input
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo


def get_utc_now() -> datetime:
    """Get current time in UTC as timezone-aware datetime.

    Returns:
        datetime: Current UTC time with tzinfo=UTC
    """
    return datetime.now(UTC)


def to_user_timezone(dt: datetime, timezone: str) -> datetime:
    """Convert UTC datetime to user's local timezone.

    Args:
        dt: UTC datetime (timezone-aware or naive, treated as UTC)
        timezone: IANA timezone string (e.g., "Europe/Berlin")

    Returns:
        datetime: Datetime converted to user's timezone
    """
    # If datetime is naive, assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    # Convert to user timezone
    user_tz = ZoneInfo(timezone)
    return dt.astimezone(user_tz)


def utc_from_local(dt: datetime, timezone: str) -> datetime:
    """Convert user's local datetime to UTC.

    Args:
        dt: Local datetime (timezone-aware or naive)
        timezone: IANA timezone string (e.g., "Europe/Berlin")

    Returns:
        datetime: Datetime converted to UTC
    """
    # If datetime is naive, localize it to user's timezone
    if dt.tzinfo is None:
        user_tz = ZoneInfo(timezone)
        dt = dt.replace(tzinfo=user_tz)

    # Convert to UTC
    return dt.astimezone(UTC)


def format_user_time(dt: datetime, timezone: str, format_str: str = "%H:%M") -> str:
    """Format UTC datetime for display in user's timezone.

    Args:
        dt: UTC datetime
        timezone: IANA timezone string
        format_str: strftime format string (default: "%H:%M")

    Returns:
        str: Formatted time string in user's timezone
    """
    user_time = to_user_timezone(dt, timezone)
    return user_time.strftime(format_str)


def get_current_user_time(timezone: str = "UTC") -> datetime:
    """Get current time in user's timezone.

    This is a convenience function for displaying current time.
    DO NOT use this for database storage - always store UTC!

    Args:
        timezone: IANA timezone string (default: "UTC")

    Returns:
        datetime: Current time in user's timezone
    """
    utc_now = get_utc_now()
    return to_user_timezone(utc_now, timezone)
