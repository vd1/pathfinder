"""Explicit, evidence-preserving repair of malformed saved terminal verdicts."""
from __future__ import annotations

import hashlib
import json
import re
import time
import uuid

from . import corpus, health, research, runner, transport


def decode_verdict(raw):
    """Fix illegal JSON string escapes only; never infer a missing judgment."""
    out, inside, i, changes = [], False, 0, 0
    while i < len(raw):
        char = raw[i]
        if char == '"':
            inside = not inside
        if inside and char == "\\":
            if i + 1 == len(raw):
                raise ValueError("Trailing backslash")
            if raw[i + 1] in '"\\/bfnrtu':
                out.extend(raw[i:i + 2]); i += 2; continue
            out.append("\\"); changes += 1
        out.append(char); i += 1
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("Duplicate JSON key")
            value[key] = item
        return value
    corrected = "".join(out)
    value = json.loads(corrected, object_pairs_hook=unique)
    if not isinstance(value, dict) or set(value) != {"decision", "reason", "action"} or not changes:
        raise ValueError("Not a supported escape-only verdict repair")
    if value["decision"] not in ("PAUSE", "DRAFT") or value["action"] is not None:
        raise ValueError("Only saved terminal PAUSE/DRAFT judgments with null action can be repaired")
    if not isinstance(value["reason"], str) or not value["reason"].strip():
        raise ValueError("Missing reason")
    return corrected, value, changes


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repair_verdict(campaign, pair_id):
    """Run only with explicit repair authority, after checking process descendants."""
    if not corpus.PAIR.fullmatch(pair_id or ""):
        raise ValueError("Invalid pair identity")
    with health.owner(campaign):
        if runner.stopped(campaign):
            raise RuntimeError("Stop marker exists; repair must not override it")
        owner = health.read(campaign.path("runner.json"))
        if owner and health.alive(owner.get("pid")):
            raise RuntimeError("Recorded runner PID is alive; inspect before repair")
        selected = health.read(campaign.path("shortlist.json")) or {}
        if pair_id not in {p["pair_id"] for p in selected.get("pairs", [])}:
            raise ValueError("Pair is not shortlisted")
        d = campaign.thread_dir(pair_id)
        with runner.Lock(d):
            state = research.status(campaign, pair_id)
            if state.get("status") != "BLOCKED" or state.get("stage") != "verify" or not state.get("reason", "").startswith("verify: unreadable decision"):
                raise ValueError("Not a blocked verifier parse failure")
            raw_path = d / "verify-unreadable.txt"
            raw = raw_path.read_text()
            corrected, value, count = decode_verdict(raw)
            receipts = [r for r in transport.receipts(campaign)
                        if r.get("thread") == pair_id and r.get("stage") == "verify"]
            if not receipts or receipts[-1].get("outcome") != "completed" or receipts[-1].get("error"):
                raise ValueError("No completed verifier receipt")
            receipt = receipts[-1]
            parsed = transport._parse(campaign, receipt.get("model", campaign.model), receipt.get("raw_events", []))
            if parsed[0].strip() != raw.strip():
                raise ValueError("Saved response does not match the verifier receipt")
            note = d / f"{pair_id}.tex"
            verdict_path = d / f"{pair_id}.verdict.json"
            history = health.read(verdict_path) or []
            if any(v.get("round") == state["round"] for v in history):
                raise ValueError("Round already has a verdict; interrupted repairs require reconciliation")
            custody = campaign.path("supervision/repairs") / f"{pair_id}-{uuid.uuid4().hex}"
            custody.mkdir(parents=True)
            before = {"state": state, "history": history, "note_sha256": _sha(note),
                      "raw_sha256": _sha(raw_path), "receipt_at": receipt.get("at")}
            health.write(custody / "before.json", before)
            (custody / "raw.txt").write_bytes(raw_path.read_bytes())
            (custody / "corrected.json").write_text(corrected)
            incident = {"at": time.time(), "pair": pair_id, "stage": "verify", "round": state["round"],
                        "action": "escape-only saved verdict repair", "decision": value["decision"],
                        "changes": count, "custody": str(custody), "status": "attempting"}
            ledger = campaign.path("supervision/incidents.jsonl")
            with ledger.open("a") as stream:
                stream.write(json.dumps(incident) + "\n")
            history.append({"round": state["round"], "at": receipt["at"],
                            "note_sha256": before["note_sha256"], **value})
            health.write(verdict_path, history)
            health.write(d / "status.json", {**state, "status": value["decision"], "stage": "done",
                                             "reason": value["reason"], "updated": research._now()})
            assert _sha(note) == before["note_sha256"] and _sha(raw_path) == before["raw_sha256"]
            incident.update(status="repaired", follow_up="Resume the authorized pipeline and verify advancement")
            with ledger.open("a") as stream:
                stream.write(json.dumps(incident) + "\n")
            return incident
