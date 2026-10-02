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
        if path.name == "pool.json":
            continue
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
            return path
    except OSError as error:
        raise RuntimeError(f"cannot use the seat pool of account {spec['name']} under {accounts_dir()} "
                           f"(set PATHFINDER_ACCOUNTS to a writable directory): {error}") from error


def release(reservation: Path | None) -> None:
    if reservation is not None:
        Path(reservation).unlink(missing_ok=True)


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
            try:
                count += _alive(json.loads(path.read_text()).get("pid"))
            except (OSError, ValueError):
                continue
        return count
    except OSError:
        return None
