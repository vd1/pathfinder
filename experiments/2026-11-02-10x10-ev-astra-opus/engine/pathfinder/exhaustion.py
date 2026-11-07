"""A provider subscription exhausted: one campaign's call meets the usage limit, every campaign pauses its calls
to that provider (codex or claude) until the reset time the provider gave, then goes on by itself.

The pause is a file per provider under $PATHFINDER_ACCOUNTS/_providers/ (shared by every campaign of this
user, whatever its account name, since the subscription is the provider's): {backend, at, reason, until,
until_source, campaign}. Admission holds a call to a paused provider until `until`, rechecking stop markers as
it waits; an expired pause is no pause. When the message names no reset time the pause lasts DEFAULT_HOLD and
the next call tries again. `pathfinder pauses` lists the pauses; `--clear BACKEND` removes one."""
from __future__ import annotations
import json, os, re, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_HOLD = 3600                       # seconds, when the provider names no reset time
_ISO = re.compile(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?\s*(Z|[+-]\d{2}:?\d{2})?")
_IN = re.compile(r"\bin\s+(\d+)\s*(minute|min|hour|hr|h|day)s?\b", re.I)


def _dir() -> Path:
    from . import seats
    return seats.accounts_dir() / "_providers"


def _stamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def reset_time(text: str) -> tuple[str, str]:
    """(until as UTC ISO, "provider" or "default") from a usage-limit message."""
    now = datetime.now(timezone.utc)
    found = _ISO.search(text or "")
    if found:
        date, hh, mm, ss, zone = found.groups()
        moment = datetime.fromisoformat(f"{date}T{hh}:{mm}:{ss or '00'}")
        if zone in (None, "Z"):
            moment = moment.replace(tzinfo=timezone.utc)
        else:
            sign = 1 if zone[0] == "+" else -1
            hours, minutes = int(zone[1:3]), int(zone[-2:])
            moment = moment.replace(tzinfo=timezone(sign * timedelta(hours=hours, minutes=minutes)))
        return _stamp(moment), "provider"
    found = _IN.search(text or "")
    if found:
        n, unit = int(found.group(1)), found.group(2).lower()
        delta = {"minute": 60, "min": 60, "hour": 3600, "hr": 3600, "h": 3600, "day": 86400}[unit] * n
        return _stamp(now + timedelta(seconds=delta)), "provider"
    return _stamp(now + timedelta(seconds=DEFAULT_HOLD)), "default"


def record(backend: str, error: str, campaign=None) -> dict:
    until, source = reset_time(error)
    entry = {"backend": backend, "at": _stamp(datetime.now(timezone.utc)), "reason": (error or "").strip()[:300],
             "until": until, "until_source": source, "campaign": str(campaign) if campaign is not None else None}
    d = _dir(); d.mkdir(parents=True, exist_ok=True)
    tmp = d / f".{backend}.{os.getpid()}.json"
    tmp.write_text(json.dumps(entry, indent=1)); os.replace(tmp, d / f"{backend}.json")
    return entry


def active(backend: str) -> dict | None:
    """The provider's pause while it lasts, with the seconds remaining; None when there is none or it expired."""
    try:
        entry = json.loads((_dir() / f"{backend}.json").read_text())
        until = datetime.fromisoformat(entry["until"].replace("Z", "+00:00"))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
    remaining = (until - datetime.now(timezone.utc)).total_seconds()
    return {**entry, "remaining_seconds": round(remaining, 1)} if remaining > 0 else None


def all_active() -> list[dict]:
    d = _dir()
    return [p for p in (active(f.stem) for f in sorted(d.glob("*.json"))) if p] if d.is_dir() else []


def clear(backend: str) -> bool:
    try:
        (_dir() / f"{backend}.json").unlink(); return True
    except FileNotFoundError:
        return False


def describe(pause: dict) -> str:
    return (f"{pause['backend']} subscription exhausted until {pause['until']}"
            f"{' (no reset time given; retried then)' if pause.get('until_source') == 'default' else ''}"
            f", recorded {pause['at']}" + (f" by {pause['campaign']}" if pause.get("campaign") else ""))
