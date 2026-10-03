"""Seats shared across processes by account (H7).

Campaigns that run on one subscription name it, and share its seats whatever process runs them:

    "account": {"name": "codex-main", "seats": 6}

Each pool is a directory under $PATHFINDER_ACCOUNTS (default ~/.pathfinder/accounts). An admitted call holds
one reservation file there, {pid, root, stage, actor, thread, at}, from admission until the call ends, and keeps it
open under an exclusive lock. Taking a seat happens under an exclusive lock on the pool: reservations no call holds
any more are removed (a call killed outright leaves its file behind; its lock dies with it, whatever process later
reuses its pid), the live ones are counted, and a file is created only if fewer than `seats` remain. Within one process, admission still counts per campaign root as before."""
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


_held: dict = {}                    # reservation path -> the open file whose lock says the call is alive


def _holder_alive(path: Path) -> bool:
    """A reservation is alive while its call holds an exclusive lock on it. A pid alone can be reused by an
    unrelated process after a crash; a lock dies with the process that held it."""
    try:
        with open(path, "rb") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return True
            fcntl.flock(handle, fcntl.LOCK_UN)
            return False
    except OSError:
        return False


def _live(pool: Path) -> list[Path]:
    """Live reservations, after removing those no call holds any longer."""
    out = []
    for path in sorted(pool.glob("*.json")):
        if path.name == "pool.json":
            continue
        if _holder_alive(path):
            out.append(path)
        else:
            path.unlink(missing_ok=True)
    return out


def take(campaign, *, stage, actor, thread) -> Path | None:
    """A reservation file if a seat is free, else None; None at once for a campaign without an account.
    The first campaign to use an account records its seat count in pool.json; a campaign that names the same
    account with another count is refused, since two counts on one subscription would oversubscribe it."""
    spec = account(campaign)
    if spec is None:
        return None
    try:
        pool = _pool(spec)
        with _locked(pool):
            recorded = pool / "pool.json"
            if recorded.exists():
                seats = json.loads(recorded.read_text()).get("seats")
                if seats != spec["seats"]:
                    raise ValueError(f"account {spec['name']} has {seats} seats in {recorded}; this campaign says "
                                     f"{spec['seats']}: one account, one seat count")
            else:
                recorded.write_text(json.dumps({"name": spec["name"], "seats": spec["seats"]}))
            if len(_live(pool)) >= spec["seats"]:
                return None
            path = pool / f"{os.getpid()}-{uuid.uuid4().hex}.json"
            path.write_text(json.dumps({"pid": os.getpid(), "root": str(campaign.root), "stage": stage, "actor": actor,
                                        "thread": thread, "at": time.time()}))
            handle = open(path, "rb")                  # held, and locked, until the call ends
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _held[str(path)] = handle
            return path
    except OSError as error:
        raise RuntimeError(f"cannot use the seat pool of account {spec['name']} under {accounts_dir()} "
                           f"(set PATHFINDER_ACCOUNTS to a writable directory): {error}") from error


def release(reservation: Path | None) -> None:
    if reservation is not None:
        Path(reservation).unlink(missing_ok=True)
        handle = _held.pop(str(reservation), None)
        if handle is not None:
            handle.close()


def in_use(campaign) -> int | None:
    """Live reservations of the campaign's account, read only: nothing is created or removed; None when the
    pool cannot be read."""
    spec = account(campaign)
    if spec is None:
        return 0
    pool = accounts_dir() / spec["name"]
    try:
        if not pool.is_dir():
            return 0
        count = 0
        for path in pool.glob("*.json"):
            if path.name == "pool.json":
                continue
            count += _holder_alive(path)
        return count
    except OSError:
        return None
