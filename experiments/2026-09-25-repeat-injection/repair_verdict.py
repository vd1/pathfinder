"""Recover an existing terminal verifier reply; no new judgment or model call."""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import re
import time

import launch

ROOT = Path(__file__).resolve().parent


def decode(raw):
    """Escape only illegal JSON string escapes; leave valid escape pairs intact."""
    out, inside, i, changed = [], False, 0, 0
    while i < len(raw):
        ch = raw[i]
        if ch == '"':
            inside = not inside
        if inside and ch == "\\":
            if i + 1 == len(raw):
                raise ValueError("Trailing backslash")
            nxt = raw[i + 1]
            if nxt in '"\\/bfnrtu':
                out.extend((ch, nxt))
                i += 2
                continue
            out.append("\\")
            changed += 1
        out.append(ch)
        i += 1
    corrected = "".join(out)
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    value = json.loads(corrected, object_pairs_hook=unique)
    if not changed or set(value) != {"decision", "reason", "action"}:
        raise ValueError("Not the supported escape-only schema repair")
    if value["decision"] not in {"PAUSE", "DRAFT"} or value["action"] is not None:
        raise ValueError("Only existing terminal PAUSE/DRAFT replies with null action are authorized")
    if not isinstance(value["reason"], str) or not value["reason"].strip():
        raise ValueError("Missing reason")
    return corrected, value, changed


def repair(arm, pair):
    if arm not in launch.ARMS or not re.fullmatch(r"Q[1-9]\d*P[1-9]\d*", pair):
        raise ValueError("Invalid arm/pair")
    launch.preflight()
    config, health, runner = launch.setup_runtime()
    from pathfinder import research
    parent = config.load(ROOT)
    campaign = config.load(ROOT / arm)
    with ExitStack() as stack:
        for c in [parent] + [config.load(ROOT / a) for a in launch.ARMS]:
            stack.enter_context(health.owner(c))
            snap = health.snapshot(c)
            if snap["stop"] or (snap["runner"] and snap["runner"].get("pid_alive")):
                raise RuntimeError("Stop marker or live recorded owner: inspect before repair")
        if pair not in {p["pair_id"] for p in launch.read(campaign.path("shortlist.json"))["pairs"]}:
            raise ValueError("Pair is not shortlisted")
        d = campaign.thread_dir(pair)
        stack.enter_context(runner.Lock(d))
        state = research.status(campaign, pair)
        if state["status"] != "BLOCKED" or state["stage"] != "verify" or not state.get("reason", "").startswith("verify: unreadable decision"):
            raise ValueError("Not a blocked verifier parse failure")
        raw_path = d / "verify-unreadable.txt"
        raw = raw_path.read_text()
        corrected, verdict, count = decode(raw)
        receipts = [r for r in launch.rows(campaign.path("receipts.jsonl"))
                    if r.get("thread") == pair and r.get("stage") == "verify"]
        receipt = receipts[-1]
        if receipt.get("outcome") != "completed" or receipt.get("error"):
            raise ValueError("Last verifier call was not a completed reply")
        messages = []
        for event in receipt["raw_events"]:
            event = json.loads(event)
            item = event.get("item", {})
            if event.get("type") == "item.completed" and item.get("type") == "agent_message":
                messages.append(item.get("text", ""))
        if not messages or messages[-1].strip() != raw.strip():
            raise ValueError("Saved raw reply does not match the completed verifier receipt")
        history_path = d / f"{pair}.verdict.json"
        history = launch.read(history_path) if history_path.exists() else []
        if any(v.get("round") == state["round"] for v in history):
            raise ValueError("This round already has a verdict; manual reconciliation required")
        note = d / f"{pair}.tex"
        custody = ROOT / "supervision/repairs" / f"{arm}-{pair}-{time.time_ns()}"
        custody.mkdir(parents=True)
        launch.save(custody / "before.json", {"status": state, "verdicts": history,
                    "note_sha256": launch.digest(note), "raw_sha256": launch.digest(raw_path)})
        (custody / "raw.txt").write_bytes(raw_path.read_bytes())
        (custody / "corrected.json").write_text(corrected)
        incident = {"at": time.time(), "arm": arm, "pair": pair, "stage": "verify",
                    "action": "escape-only saved terminal verdict repair", "decision": verdict["decision"],
                    "escape_count": count, "custody": str(custody), "status": "attempting"}
        ledger = ROOT / "supervision/incidents.jsonl"
        with ledger.open("a") as stream:
            stream.write(json.dumps(incident) + "\n")
        history.append({"round": state["round"], "at": receipt["at"],
                        "note_sha256": launch.digest(note), **verdict})
        launch.save(history_path, history)
        research._set(campaign, pair, stage="done", status=verdict["decision"], reason=verdict["reason"])
        assert launch.digest(raw_path) == launch.read(custody / "before.json")["raw_sha256"]
        assert launch.digest(note) == launch.read(custody / "before.json")["note_sha256"]
        incident.update(status="repaired", follow_up="Resume full pipeline; verify readable editing advances")
        with ledger.open("a") as stream:
            stream.write(json.dumps(incident) + "\n")
        print(json.dumps(incident))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("arm", choices=launch.ARMS)
    parser.add_argument("pair")
    args = parser.parse_args()
    repair(args.arm, args.pair)
