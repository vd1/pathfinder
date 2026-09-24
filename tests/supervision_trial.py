"""Isolated supervision drill, with a deliberately failing editor test double.

No model calls, source-paper edits, or scientific results are produced.
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pathfinder import config, edit, health, research, runner


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["prepare", "crash", "resume"])
    ap.add_argument("root", type=Path)
    ns = ap.parse_args()
    root = ns.root.resolve()
    if ns.action == "prepare":
        root.mkdir(parents=True, exist_ok=True)
        if any(root.iterdir()):
            raise SystemExit("prepare requires an empty test directory")
        health.write(root / "supervision-trial.json", {"fixture": "pathfinder-supervision-drill-v1"})
        health.write(root / "campaign.json", {"backend": "claude", "model": "unused-test-model",
                     "allowances": {}, "budget_usd": 9, "seats": 1})
        health.write(root / "shortlist.json", {"pairs": [{"pair_id": "Q1P1"}]})
        health.write(root / "threads/Q1P1/status.json",
                     {"pair_id": "Q1P1", "status": "PAUSE", "stage": "done", "round": 1,
                      "reason": "Synthetic terminal research fixture, not a scientific result."})
        health.write(root / "threads/Q1P1/edited/edit.json", {"status": "stopped"})
        print(root)
        return 0
    if health.read(root / "supervision-trial.json") != {"fixture": "pathfinder-supervision-drill-v1"}:
        raise SystemExit("refusing a directory without the supervision drill marker")
    campaign = config.load(root)

    def editor(campaign, pair_id, stop):
        if stop():
            return "stopped"
        if ns.action == "crash":
            edit._set(campaign, pair_id, status="editing")
            print("fixture editor entered; injecting runner exit 23", flush=True)
            os._exit(23)
        # A deterministic editor double tests the recovery path without model spend.
        health.write(root / "resumed-stage.json", {"pair": pair_id, "stage": "edit",
                     "research_status": research.status(campaign, pair_id)["status"],
                     "fixture_only": True})
        edit._set(campaign, pair_id, status="done")
        return "done"

    edit.run = editor
    return runner.run(campaign, interval=.05)


if __name__ == "__main__":
    sys.exit(main())
