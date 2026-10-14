"""Reopen a finished thread with a bounded grant (nobel, 14 October 2026).

`pathfinder reopen PAIR --grant repair|round --reason TEXT [--note TEXT]` gives an EVA thread (the joint thread
of a composable campaign) one more step after it ended:

    PAUSE-ON-REVISE   repair   consolidate with the verifier's last corrections, then novelty, then verify
    PAUSE-ON-ITERATE  round    one more peer round from the verifier's last action, then on to verify
    PAUSE             round    the same, with the operator's note (required) added to the ledger
    DRAFT             none     refused: the paper and its edit would no longer match the research

The verdict that follows ends the thread whatever it decides (REVISE as PAUSE-ON-REVISE, ITERATE as
PAUSE-ON-ITERATE): one grant is one verdict, and nothing reopens without the command. Each reopen is appended
to threads/<pair>/<pair>.reopen.json with its time, grant, reason, note, the ending it left and the engine of
that moment (each run's own record names the engine its calls used). Verdicts, ledger and novelty reports are
appended to, never rewritten; the earlier edit and actionability answer move to reopened/<n>/, so the new
outcome is edited afresh. A pair missing from shortlist.json is listed again, marked reopened, so the runner
reaches it."""
from __future__ import annotations
import json, shutil
from . import paper, provenance, research
from .ledger import Ledger

GRANTS = {"PAUSE-ON-REVISE": "repair", "PAUSE-ON-ITERATE": "round", "PAUSE": "round"}
SCHEMES = ("eva", "composable")


def records(campaign, pair_id) -> list:
    p = campaign.thread_dir(pair_id) / f"{pair_id}.reopen.json"
    return json.loads(p.read_text()) if p.exists() else []


def reopen(campaign, pair_id: str, grant: str, reason: str, note: str | None = None) -> dict:
    """Record the grant and set the thread to run it; the runner (or `research --pairs PAIR`) runs it."""
    from .runner import Lock
    if (campaign.raw or {}).get("research_scheme") not in SCHEMES:
        raise ValueError(f"reopen needs research_scheme {' or '.join(SCHEMES)}: it grants a verifier-decided step")
    if grant not in ("repair", "round"):
        raise ValueError(f"grant must be repair or round, got {grant!r}")
    if not (isinstance(reason, str) and reason.strip()):
        raise ValueError("a reopen needs a reason (--reason TEXT)")
    d = campaign.thread_dir(pair_id)
    if not (d / "status.json").exists():
        raise ValueError(f"{pair_id} has no research thread to reopen")
    with Lock(d):
        s = research.status(campaign, pair_id)
        ending = s.get("status")
        if ending == "DRAFT":
            raise ValueError(f"{pair_id} is DRAFT: reopening it would leave its edit and paper describing other research")
        if ending not in GRANTS:
            raise ValueError(f"{pair_id} is {ending}, not finished: only PAUSE-ON-REVISE, PAUSE-ON-ITERATE and PAUSE reopen")
        if GRANTS[ending] != grant:
            raise ValueError(f"{pair_id} ended {ending}, which reopens with --grant {GRANTS[ending]}, not {grant}")
        if ending == "PAUSE" and not (note or "").strip():
            raise ValueError(f"{pair_id} ended PAUSE: say what the operator supplies with --note TEXT")
        if s.get("pending"):
            raise ValueError(f"{pair_id} has calls pending: {', '.join(s['pending'])}")
        if paper.status(campaign, pair_id).get("status") != "none":
            raise ValueError(f"{pair_id} has a paper: reopening would leave it describing other research")
        n = len(records(campaign, pair_id)) + 1
        archive, moved = d / "reopened" / str(n), []
        for name in ("edited", "actionability.json"):
            if (d / name).exists():
                archive.mkdir(parents=True, exist_ok=True)
                shutil.move(str(d / name), str(archive / name)); moved.append(f"reopened/{n}/{name}")
        seq = Ledger(d / "ledger.jsonl").add("operator", "operator", note.strip()) if (note or "").strip() else None
        engine = provenance.engine()
        entry = {"n": n, "at": research._now(), "grant": grant, "reason": reason.strip(), "note": (note or "").strip() or None,
                 "ledger_seq": seq, "from": {k: s.get(k) for k in ("status", "stage", "round", "repairs", "reason")},
                 "engine": {k: engine.get(k) for k in ("kind", "commit", "ref", "runtime_sha256")}, "archived": moved}
        (d / f"{pair_id}.reopen.json").write_text(json.dumps(records(campaign, pair_id) + [entry], indent=1))
        update = {"status": "running", "reason": None, "failure": None, "grant": {"n": n, "grant": grant}}
        if grant == "repair":
            update.update(stage="consolidate", repairs=s.get("repairs", 0) + 1,
                          repair=(s.get("latest_review") or {}).get("response"))
        else:
            update.update(stage="peers", round=s.get("round", 1) + 1, peer_call=0, peer_seconds=0,
                          peer_seconds_exhausted=False)
        research._set(campaign, pair_id, **update)
        _list(campaign, pair_id)
    return entry


def _list(campaign, pair_id):
    path = campaign.path("shortlist.json")
    doc = json.loads(path.read_text()) if path.exists() else {"pairs": []}
    if pair_id not in {p["pair_id"] for p in doc.get("pairs", [])}:
        doc.setdefault("pairs", []).append({"pair_id": pair_id, "reopened": True})
        path.write_text(json.dumps(doc, indent=1))


def active(campaign, pair_id) -> dict | None:
    """The grant a reopened thread is running, or None."""
    return research.status(campaign, pair_id).get("grant") or None
