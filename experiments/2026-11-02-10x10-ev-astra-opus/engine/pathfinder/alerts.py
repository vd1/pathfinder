"""Local failure alerts independent of model access; delivery is best effort."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time

from . import health


def _desktop(title, message):
    if sys.platform != "darwin":
        return "unsupported"
    script = ('on run argv\n'
              'display notification (item 2 of argv) with title (item 1 of argv)\n'
              'end run')
    subprocess.run(["osascript", "-e", script, title, message],
                   capture_output=True, text=True, timeout=5, check=True)
    return "submitted"  # macOS notification settings still control visibility.


def _fingerprint(evidence) -> str | None:
    """What the evidence says now: a file's content, or a directory's file names and modification times.
    Two alerts of one kind are the same state only when this matches."""
    path = os.fspath(evidence)
    digest = hashlib.sha256()
    try:
        if os.path.isdir(path):
            for top, dirs, files in os.walk(path):
                dirs.sort()
                for name in sorted(files):
                    full = os.path.join(top, name)
                    digest.update(f"{os.path.relpath(full, path)}:{os.stat(full).st_mtime_ns}\n".encode())
        else:
            with open(path, "rb") as stream:
                digest.update(stream.read())
    except FileNotFoundError:
        return "missing"
    except OSError:
        return None                                   # unreadable: never treated as a repeat
    return digest.hexdigest()


def emit(campaign, kind, evidence):
    """Never mask the underlying failure, including when notification itself fails. An alert identical to
    the last one within alert_repeat_seconds (default 3600) is counted, not sent again: repeated
    notifications of one state train the operator to ignore them. Identical means the same kind and the same
    evidence content; repeats are still logged in alerts.jsonl, marked as such."""
    message = f"{campaign.root.name}: {kind}. Inspect the local campaign health and supervision records."
    window = float((campaign.raw or {}).get("alert_repeat_seconds", 3600))
    try:
        last = json.loads(campaign.path("alert.json").read_text())
    except (OSError, ValueError):
        last = None
    fingerprint = _fingerprint(evidence)
    if (last and last.get("kind") == kind and last.get("evidence") == str(evidence) and fingerprint is not None
            and last.get("fingerprint") == fingerprint and time.time() - last.get("at", 0) < window):
        last["repeats"] = last.get("repeats", 0) + 1
        last["last_repeat_at"] = time.time()
        try:
            health.write(campaign.path("alert.json"), last)
            with campaign.path("alerts.jsonl").open("a") as stream:
                stream.write(json.dumps({"at": last["last_repeat_at"], "kind": kind, "evidence": str(evidence),
                                         "fingerprint": fingerprint, "repeat": True}) + "\n")
        except OSError:
            pass
        print(f"Pathfinder still needs attention ({last['repeats']} repeat(s)): {message}", file=sys.stderr, flush=True)
        return
    record = {"at": time.time(), "kind": kind, "evidence": str(evidence), "fingerprint": fingerprint,
              "desktop": "disabled", "repeats": 0}
    print(f"\aPathfinder needs attention: {message}", file=sys.stderr, flush=True)
    try:
        # Persist before attempting desktop delivery; no model or network is needed.
        health.write(campaign.path("alert.json"), record)
        if campaign.raw.get("notifications", {}).get("desktop", True):
            try:
                record["desktop"] = _desktop("Pathfinder needs attention", message)
            except (OSError, subprocess.SubprocessError):
                record["desktop"] = "failed"
        health.write(campaign.path("alert.json"), record)
        with campaign.path("alerts.jsonl").open("a") as stream:
            stream.write(json.dumps(record) + "\n")
    except OSError as error:
        print(f"Cannot persist Pathfinder alert: {type(error).__name__}", file=sys.stderr, flush=True)
