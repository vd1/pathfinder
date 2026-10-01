"""The campaign's event stream: one JSON line per thing that happened, appended to events.jsonl.

Events add what status files cannot hold: when each call started and ended, every status transition
with its previous value, stops and runs with their execution identifier. The status files stay the
authority for where a unit stands; events are its history. A write never breaks the stage that emits
it. A reader is told when the last line is incomplete, so a monitor can say "unknown" instead of
inferring progress from a cut record."""
from __future__ import annotations
import json, sys, threading, time

KINDS = frozenset({"run_started", "run_finished", "call_started", "call_finished", "status_changed", "stop_requested"})
_lock = threading.Lock()


def emit(campaign, kind: str, **fields) -> None:
    if kind not in KINDS:
        raise ValueError(f"unknown event kind {kind!r}; expected one of {', '.join(sorted(KINDS))}")
    row = {"v": 1, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "run_id": getattr(campaign, "run_id", None), "kind": kind, **fields}
    line = json.dumps(row, default=str) + "\n"
    try:
        with _lock, open(campaign.path("events.jsonl"), "a") as stream:
            stream.write(line)
    except OSError as error:
        print(f"pathfinder: event not recorded ({kind}): {error}", file=sys.stderr)


def read(campaign) -> tuple[list[dict], bool]:
    path = campaign.path("events.jsonl")
    if not path.is_file():
        return [], False
    rows, truncated = [], False
    text = path.read_text(errors="replace")
    lines = text.split("\n")
    for number, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            truncated = True                       # a cut or corrupt line: progress cannot be read past it
    if text and not text.endswith("\n"):
        truncated = True
    return rows, truncated


def transition(campaign, unit: str, axis: str, before: dict, after: dict) -> None:
    """A status_changed event when a status file's "status" value changed."""
    if before.get("status") != after.get("status"):
        emit(campaign, "status_changed", unit=unit, axis=axis, **{"from": before.get("status")},
             to=after.get("status"), reason=after.get("reason"))
