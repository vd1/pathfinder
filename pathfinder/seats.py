"""Seats shared across processes by account (H7).

Campaigns that run on one subscription name it, and share its seats whatever process runs them:

    "account": {"name": "codex-main", "seats": 6}

Each pool is a directory under $PATHFINDER_ACCOUNTS (default ~/.pathfinder/accounts). An admitted call holds
one reservation file there, {pid, root, stage, actor, thread, at}, from admission until the call ends. Taking a
seat happens under an exclusive lock on the pool: reservations whose process is gone are removed (a call
killed outright leaves its file behind), the live ones are counted, and a file is created only if fewer than
`seats` remain. Within one process, admission still counts per campaign root as before."""
from __future__ import annotations
import fcntl, json, os, time, uuid
from contextlib import contextmanager
from pathlib import Path


def accounts_dir() -> Path:
    return Path(os.environ.get("PATHFINDER_ACCOUNTS") or Path.home() / ".pathfinder" / "accounts")


def account(campaign) -> dict | None:
    spec = (campaign.raw or {}).get("account")
    if not spec:
        return None
    if not isinstance(spec, dict) or not spec.get("name") or not isinstance(spec.get("seats"), int) or spec["seats"] < 1:
        raise ValueError(f"account must be {{\"name\": ..., \"seats\": n >= 1}}, got {spec!r}")
    return spec


def _pool(spec) -> Path:
    path = accounts_dir() / spec["name"]
    path.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def _locked(pool: Path):
    with open(pool / "pool.lock", "a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _alive(pid) -> bool:
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:                         # another user's process: alive
        return True
    except (TypeError, ValueError):
        return False
    return True


def _live(pool: Path) -> list[Path]:
    """Live reservations, after removing those whose process is gone or whose file cannot be read."""
    out = []
    for path in sorted(pool.glob("*.json")):
        try:
            pid = json.loads(path.read_text()).get("pid")
        except (OSError, ValueError):
            pid = None
        if _alive(pid):
            out.append(path)
        else:
            path.unlink(missing_ok=True)
    return out


def take(campaign, *, stage, actor, thread) -> Path | None:
    """A reservation file if a seat is free, else None; None at once for a campaign without an account."""
    spec = account(campaign)
    if spec is None:
        return None
    pool = _pool(spec)
    with _locked(pool):
        if len(_live(pool)) >= spec["seats"]:
            return None
        path = pool / f"{os.getpid()}-{uuid.uuid4().hex}.json"
        path.write_text(json.dumps({"pid": os.getpid(), "root": str(campaign.root), "stage": stage, "actor": actor,
                                    "thread": thread, "at": time.time()}))
        return path


def release(reservation: Path | None) -> None:
    if reservation is not None:
        Path(reservation).unlink(missing_ok=True)


def in_use(campaign) -> int:
    spec = account(campaign)
    if spec is None:
        return 0
    pool = _pool(spec)
    with _locked(pool):
        return len(_live(pool))
