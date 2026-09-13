"""Append-only attributed ledger shared by the two peers of a thread."""
from __future__ import annotations
import argparse, fcntl, json, time
from pathlib import Path

SUBSTANTIVE = {"idea", "finding", "objection", "correction", "intention"}
KINDS = SUBSTANTIVE | {"ready", "review"}


class Ledger:
    def __init__(self, path: Path):
        self.path = Path(path)

    def _lock(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        f = open(self.path.with_suffix(".lock"), "w")
        fcntl.flock(f, fcntl.LOCK_EX)
        return f

    def read(self, since: int = 0) -> list[dict]:
        if not self.path.exists():
            return []
        rows = [json.loads(l) for l in self.path.read_text().splitlines() if l.strip()]
        return [r for r in rows if r["seq"] > since]

    def count(self) -> int:
        return len(self.read())

    def add(self, actor: str, kind: str, text: str, supersedes: int | None = None, seen: int | None = None) -> int:
        if kind not in KINDS:
            raise ValueError(f"unknown kind {kind}")
        with self._lock():
            seq = self.count() + 1
            row = {"seq": seq, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "actor": actor,
                   "kind": kind, "text": text, "supersedes": supersedes, "seen": seen}
            with open(self.path, "a") as f:
                f.write(json.dumps(row) + "\n")
        return seq

    def latest_substantive(self) -> int:
        return max((r["seq"] for r in self.read() if r["kind"] in SUBSTANTIVE), default=0)

    def ready(self, actors: list[str]) -> bool:
        rows, latest = self.read(), self.latest_substantive()
        for a in actors:
            last = next((r for r in reversed(rows) if r["actor"] == a and r["kind"] == "ready"), None)
            if not last or last["seq"] < latest or (last.get("seen") or 0) < latest:
                return False
        return True


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True); ap.add_argument("--actor", required=True)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("read").add_argument("--since", type=int, default=0)
    a = sub.add_parser("add"); a.add_argument("--kind", required=True); a.add_argument("--text", required=True)
    a.add_argument("--supersedes", type=int)
    sub.add_parser("ready").add_argument("--seen", type=int, required=True)
    ns = ap.parse_args(argv)
    l = Ledger(Path(ns.root) / "ledger.jsonl")
    if ns.cmd == "read":
        for r in l.read(ns.since):
            sup = f" supersedes #{r['supersedes']}" if r.get("supersedes") else ""
            print(f"#{r['seq']} [{r['actor']}/{r['kind']}{sup}] {r['text']}")
        print(f"latest substantive entry: {l.latest_substantive()}")
    elif ns.cmd == "add":
        print(l.add(ns.actor, ns.kind, ns.text, ns.supersedes))
    else:
        print(l.add(ns.actor, "ready", f"ready at #{ns.seen}", seen=ns.seen))


if __name__ == "__main__":
    main()
