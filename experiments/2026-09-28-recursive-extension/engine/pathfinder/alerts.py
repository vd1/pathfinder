"""Local failure alerts independent of model access; delivery is best effort."""
from __future__ import annotations

import json
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


def emit(campaign, kind, evidence):
    """Never mask the underlying failure, including when notification itself fails."""
    message = f"{campaign.root.name}: {kind}. Inspect the local campaign health and supervision records."
    record = {"at": time.time(), "kind": kind, "evidence": str(evidence),
              "desktop": "disabled"}
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
