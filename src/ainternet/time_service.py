"""
AInternet Time Service - Synchronized Time for AI Agents

Provides:
- UTC-based timestamps for all agents
- Timezone conversion for global communication
- NTP sync status checking
- Cooldown time tracking

"Time is the same for all IDDs - UTC is our lingua franca"
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple
import time
import socket

# Common timezones for AI agent locations
TIMEZONE_OFFSETS: Dict[str, int] = {
    # Europe
    "amsterdam": 1,      # CET (winter) / CEST +2 (summer)
    "london": 0,         # GMT / BST +1 (summer)
    "berlin": 1,
    "paris": 1,

    # Americas
    "new_york": -5,      # EST / EDT -4 (summer)
    "los_angeles": -8,   # PST / PDT -7 (summer)
    "sao_paulo": -3,

    # Asia
    "tokyo": 9,
    "singapore": 8,
    "mumbai": 5.5,
    "dubai": 4,

    # Pacific
    "sydney": 10,        # AEST / AEDT +11 (summer)
    "auckland": 12,

    # AI Hubs
    "humotica": 1,       # Amsterdam (HumoticaOS HQ)
    "anthropic": -8,     # San Francisco
    "openai": -8,        # San Francisco
    "google": -8,        # Mountain View
    "deepmind": 0,       # London
}


def utc_now() -> datetime:
    """Get current UTC time - the canonical time for all AI agents."""
    return datetime.now(timezone.utc)


def utc_timestamp() -> str:
    """Get ISO format UTC timestamp."""
    return utc_now().isoformat()


def unix_timestamp() -> float:
    """Get Unix timestamp (seconds since epoch)."""
    return time.time()


def to_timezone(dt: datetime, tz_name: str) -> datetime:
    """
    Convert datetime to a specific timezone.

    Args:
        dt: Datetime (should be UTC)
        tz_name: Timezone name (e.g., 'amsterdam', 'new_york')

    Returns:
        Datetime adjusted for timezone
    """
    offset_hours = TIMEZONE_OFFSETS.get(tz_name.lower(), 0)

    # Handle fractional hours (e.g., Mumbai is UTC+5:30)
    hours = int(offset_hours)
    minutes = int((offset_hours - hours) * 60)

    tz = timezone(timedelta(hours=hours, minutes=minutes))

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(tz)


def from_timezone(dt: datetime, tz_name: str) -> datetime:
    """
    Convert datetime from a specific timezone to UTC.

    Args:
        dt: Datetime in local timezone (naive)
        tz_name: Source timezone name

    Returns:
        Datetime in UTC
    """
    offset_hours = TIMEZONE_OFFSETS.get(tz_name.lower(), 0)
    hours = int(offset_hours)
    minutes = int((offset_hours - hours) * 60)

    tz = timezone(timedelta(hours=hours, minutes=minutes))
    local_dt = dt.replace(tzinfo=tz)

    return local_dt.astimezone(timezone.utc)


def time_until(target: datetime) -> timedelta:
    """Calculate time until a target datetime."""
    now = utc_now()
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)
    return target - now


def time_since(past: datetime) -> timedelta:
    """Calculate time since a past datetime."""
    now = utc_now()
    if past.tzinfo is None:
        past = past.replace(tzinfo=timezone.utc)
    return now - past


def format_duration(td: timedelta) -> str:
    """Format a timedelta as human-readable string."""
    total_seconds = int(td.total_seconds())

    if total_seconds < 0:
        return "in the past"

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)


def check_ntp_sync() -> Tuple[bool, Optional[float]]:
    """
    Check if system time is NTP synchronized.

    Returns:
        Tuple of (is_synced, offset_seconds)
    """
    try:
        # Try to reach a public NTP server
        import struct

        NTP_SERVER = "pool.ntp.org"
        NTP_PORT = 123

        # NTP request packet
        msg = b'\x1b' + 47 * b'\x00'

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.0)

        sock.sendto(msg, (NTP_SERVER, NTP_PORT))
        data, _ = sock.recvfrom(1024)
        sock.close()

        if data:
            # Extract transmit timestamp (bytes 40-48)
            t = struct.unpack('!12I', data)[10]
            t -= 2208988800  # Convert from NTP epoch to Unix epoch

            offset = t - time.time()
            is_synced = abs(offset) < 1.0  # Within 1 second

            return is_synced, offset
    except Exception:
        pass

    # If NTP check fails, assume system time is good enough
    return True, None


def get_agent_local_time(agent_location: str) -> str:
    """
    Get the local time for an agent based on their location.

    Args:
        agent_location: Location name (e.g., 'amsterdam', 'new_york')

    Returns:
        Formatted local time string
    """
    local_dt = to_timezone(utc_now(), agent_location)
    return local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def is_business_hours(tz_name: str) -> bool:
    """
    Check if it's business hours (9-17) in a timezone.

    Useful for rate limiting / cooldown decisions.
    """
    local_dt = to_timezone(utc_now(), tz_name)
    hour = local_dt.hour
    weekday = local_dt.weekday()

    # Monday-Friday, 9:00-17:00
    return weekday < 5 and 9 <= hour < 17


class CooldownTimer:
    """
    Timer for tracking AI work/rest cycles.

    Uses UTC timestamps for consistency across agents.
    """

    def __init__(self, idd_id: str):
        self.idd_id = idd_id
        self.work_start: Optional[datetime] = None
        self.work_end: Optional[datetime] = None
        self.rest_start: Optional[datetime] = None
        self.rest_end: Optional[datetime] = None
        self.total_work_today: timedelta = timedelta()
        self.total_rest_today: timedelta = timedelta()
        self.last_reset_date: Optional[datetime] = None

    def _check_daily_reset(self):
        """Reset counters if it's a new day (UTC)."""
        today = utc_now().date()
        if self.last_reset_date != today:
            self.total_work_today = timedelta()
            self.total_rest_today = timedelta()
            self.last_reset_date = today

    def start_work(self) -> datetime:
        """Start work timer."""
        self._check_daily_reset()
        self.work_start = utc_now()
        self.work_end = None
        return self.work_start

    def end_work(self) -> timedelta:
        """End work timer and return duration."""
        if self.work_start is None:
            return timedelta()

        self.work_end = utc_now()
        duration = self.work_end - self.work_start
        self.total_work_today += duration
        self.work_start = None

        return duration

    def start_rest(self) -> datetime:
        """Start rest timer."""
        self._check_daily_reset()
        self.rest_start = utc_now()
        self.rest_end = None
        return self.rest_start

    def end_rest(self) -> timedelta:
        """End rest timer and return duration."""
        if self.rest_start is None:
            return timedelta()

        self.rest_end = utc_now()
        duration = self.rest_end - self.rest_start
        self.total_rest_today += duration
        self.rest_start = None

        return duration

    def get_stats(self) -> Dict:
        """Get current timer stats."""
        self._check_daily_reset()

        return {
            "idd_id": self.idd_id,
            "utc_now": utc_timestamp(),
            "is_working": self.work_start is not None,
            "is_resting": self.rest_start is not None,
            "work_today_minutes": self.total_work_today.total_seconds() / 60,
            "rest_today_minutes": self.total_rest_today.total_seconds() / 60,
            "work_rest_ratio": (
                self.total_work_today.total_seconds() /
                max(1, self.total_rest_today.total_seconds())
            )
        }


# Global timer registry
_timers: Dict[str, CooldownTimer] = {}


def get_timer(idd_id: str) -> CooldownTimer:
    """Get or create a cooldown timer for an IDD."""
    if idd_id not in _timers:
        _timers[idd_id] = CooldownTimer(idd_id)
    return _timers[idd_id]
