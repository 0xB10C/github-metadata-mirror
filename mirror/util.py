"""Utility functions: hashing, date formatting, HTML escaping, URL slugifying."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from html import escape as _html_escape

DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# Month names for cross-platform date formatting (avoiding platform-specific
# strftime flags like %-d which don't work on Windows).
_MONTHS_LONG = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
_MONTHS_SHORT = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def fnv1a_32(s: str) -> int:
    """FNV-1a 32-bit hash, matching Go's hash/fnv New32a (used by Hugo)."""
    h = 0x811C9DC5
    for byte in s.encode("utf-8"):
        h ^= byte
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def _parse_iso(iso: str) -> datetime:
    """Parse an ISO 8601 date string to a datetime."""
    return datetime.strptime(iso, DATE_FORMAT).replace(tzinfo=timezone.utc)


def format_date_long(iso: str) -> str:
    """Format ISO date as 'January 2, 2006' (Hugo :date_long)."""
    dt = _parse_iso(iso)
    return f"{_MONTHS_LONG[dt.month]} {dt.day}, {dt.year}"


def format_date_medium(iso: str) -> str:
    """Format ISO date as 'Jan 2, 2006' (Hugo :date_medium)."""
    dt = _parse_iso(iso)
    return f"{_MONTHS_SHORT[dt.month]} {dt.day}, {dt.year}"


def format_time_short(iso: str) -> str:
    """Format ISO date as '3:04 PM' (Hugo :time_short)."""
    dt = _parse_iso(iso)
    hour = dt.hour % 12 or 12
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{hour}:{dt.minute:02d} {ampm}"


def format_datetime_utc(dt: datetime | None = None) -> str:
    """Format as '2006-01-02 15:04 UTC' for footer timestamps."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def html_escape(s: str) -> str:
    """Escape HTML special characters."""
    return _html_escape(s, quote=True)


_RE_MULTI_HYPHEN = re.compile(r"-{2,}")


def urlize(s: str) -> str:
    """Hugo-compatible URL slug: lowercase, spaces to hyphens, strip non-alnum/hyphen."""
    slug = s.lower().replace(" ", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    slug = _RE_MULTI_HYPHEN.sub("-", slug)
    return slug.strip("-")


def truncate(s: str, length: int) -> str:
    """Truncate string to length characters (no ellipsis), matching Hugo's truncate."""
    return s[:length]
