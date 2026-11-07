"""Reopen a finished thread with a bounded grant (nobel, 14 October 2026).

`pathfinder reopen PAIR --grant repair|round --reason TEXT [--note TEXT]` gives a classic or EVA thread (including the joint thread
of a composable campaign) one more step after it ended:

    PAUSE-ON-REVISE   repair   consolidate with the verifier's last corrections, then novelty, then verify
    PAUSE-ON-ITERATE  round    one more peer round from the verifier's last action, then on to verify
    PAUSE             round    the same, with the operator's note (required) added to the ledger
    DRAFT             extend   one more peer round aimed at the operator's target (the note, required), then on
                               to verify; the edit, actionability answer and paper move to reopened/<n>/ first

The verdict that follows ends the thread whatever it decides (REVISE as PAUSE-ON-REVISE, ITERATE as
PAUSE-ON-ITERATE): one grant is one verdict, and nothing reopens without the command. Each reopen is appended
to threads/<pair>/<pair>.reopen.json with its time, grant, reason, note, the ending it left and the engine of
that moment (each run's own record names the engine its calls used). Verdicts, ledger and novelty reports are
appended to, never rewritten; the earlier edit and actionability answer move to reopened/<n>/, so the new
outcome is edited afresh. A pair missing from shortlist.json is listed again, marked reopened, so the runner
reaches it.

An extension (nobel, 15 October 2026) is how a DRAFT changes on purpose: its edit and paper are archived, and the
thread keeps them as prior_result. A new DRAFT is edited and may get a new paper; any other ending leaves the
earlier DRAFT and its paper as the thread's result, which status, state and playbook show."""
from __future__ import annotations
import hashlib, json, shutil
from . import paper, provenance, research
from .ledger import Ledger

GRANTS = {"PAUSE-ON-REVISE": "repair", "PAUSE-ON-ITERATE": "round", "PAUSE": "round", "DRAFT": "extend"}
NEEDS_NOTE = ("PAUSE", "DRAFT")                  # a round with nothing new to go on needs the operator's input
PAPER_RUNNING = ("writing", "reviewing")
SCHEMES = (None, "eva", "composable")            # None: the classic scheme (research_scheme absent)


def records(campaign, pair_id) -> list:
    p = campaign.thread_dir(pair_id) / f"{pair_id}.reopen.json"
    return json.loads(p.read_text()) if p.exists() else []


def reopen(campaign, pair_id: str, grant: str, reason: str, note: str | None = None) -> dict:
    """Record the grant and set the thread to run it; the runner (or `research --pairs PAIR`) runs it."""
    from .runner import Lock
    if (campaign.raw or {}).get("research_scheme") not in SCHEMES:
        raise ValueError("reopen needs the classic scheme (research_scheme absent), eva or composable: it grants a "
                         "verifier-decided step")
    if grant not in ("repair", "round", "extend"):
        raise ValueError(f"grant must be repair, round or extend, got {grant!r}")
    if not (isinstance(reason, str) and reason.strip()):
        raise ValueError("a reopen needs a reason (--reason TEXT)")
    d = campaign.thread_dir(pair_id)
    if not (d / "status.json").exists():
        raise ValueError(f"{pair_id} has no research thread to reopen")
    with Lock(d):
        s = research.status(campaign, pair_id)
        ending = s.get("status")
        if ending not in GRANTS:
            raise ValueError(f"{pair_id} is {ending}, not finished: only PAUSE-ON-REVISE, PAUSE-ON-ITERATE, PAUSE and DRAFT reopen")
        if GRANTS[ending] != grant:
            raise ValueError(f"{pair_id} ended {ending}, which reopens with --grant {GRANTS[ending]}, not {grant}"
                             + (": an extension archives its edit and paper" if ending == "DRAFT" else ""))
        if ending in NEEDS_NOTE and not (note or "").strip():
            raise ValueError(f"{pair_id} ended {ending}: say what the operator supplies"
                             + (" (the target of the extension)" if ending == "DRAFT" else "") + " with --note TEXT")
        if s.get("pending"):
            raise ValueError(f"{pair_id} has calls pending: {', '.join(s['pending'])}")
        written = paper.status(campaign, pair_id)
        if grant != "extend" and written.get("status") != "none":
            raise ValueError(f"{pair_id} has a paper: reopening would leave it describing other research")
        if written.get("status") in PAPER_RUNNING:
            raise ValueError(f"{pair_id}'s paper is {written['status']}: let the paper stage finish or stop first")
        classic = not campaign.raw.get("research_scheme") and not campaign.raw.get("research_bundles")
        review = _last_verdict(d, pair_id) if classic else (s.get("latest_review") or {}).get("response")
        if grant == "repair" and (not review or review.get("decision") != "REVISE" or not review.get("reason")):
            raise ValueError("repair requires the retained REVISE verdict and corrections")
        if classic and review and review.get("note_sha256"):
            if hashlib.sha256((d / f"{pair_id}.tex").read_bytes()).hexdigest() != review["note_sha256"]:
                raise ValueError("current note differs from the last judged note")
        n = len(records(campaign, pair_id)) + 1
        archive, moved = d / "reopened" / str(n), []
        names = ("edited", "actionability.json") + (("paper",) if grant == "extend" else ())
        prior = None
        if grant == "extend":
            prior = {"n": n, "status": ending, "edit": f"reopened/{n}/edited" if (d / "edited").exists() else None,
                     "paper": f"reopened/{n}/paper" if (d / "paper").exists() else None,
                     "paper_status": written.get("status") if written.get("status") != "none" else None}
        for name in names:
            if (d / name).exists():
                archive.mkdir(parents=True, exist_ok=True)
                shutil.move(str(d / name), str(archive / name)); moved.append(f"reopened/{n}/{name}")
        seq = Ledger(d / "ledger.jsonl").add("operator", "operator", note.strip()) if (note or "").strip() else None
        engine = provenance.engine()
        entry = {"n": n, "at": research._now(), "grant": grant, "reason": reason.strip(), "note": (note or "").strip() or None,
                 "ledger_seq": seq, "from": {k: s.get(k) for k in ("status", "stage", "round", "repairs", "reason")},
                 "engine": {k: engine.get(k) for k in ("kind", "commit", "ref", "runtime_sha256")}, "archived": moved,
                 **({"prior_result": prior} if prior else {})}
        (d / f"{pair_id}.reopen.json").write_text(json.dumps(records(campaign, pair_id) + [entry], indent=1))
        ready_after = Ledger(d / "ledger.jsonl").count()   # a peer's ready from before the reopen does not answer it
        update = {"status": "running", "reason": None, "failure": None,
                  "grant": {"n": n, "grant": grant, "ledger_seq": seq, "ready_after": ready_after, "review": review}}
        if prior:
            update["prior_result"] = prior
        if grant == "repair":
            update.update(stage="consolidate", repairs=s.get("repairs", 0) + 1,
                          repair=review)
        else:
            update.update(stage="peers", round=s.get("round", 1) + 1, peer_call=0, peer_seconds=0,
                          peer_seconds_exhausted=False)
        research._set(campaign, pair_id, **update)
        _list(campaign, pair_id)
    return entry


def _last_verdict(d, pair_id) -> dict | None:
    """The classic scheme keeps no latest_review: its repair is briefed with the last recorded verdict."""
    path = d / f"{pair_id}.verdict.json"
    history = json.loads(path.read_text()) if path.is_file() else []
    last = history[-1] if history else None
    return last


def _list(campaign, pair_id):
    path = campaign.path("shortlist.json")
    doc = json.loads(path.read_text()) if path.exists() else {"pairs": []}
    if pair_id not in {p["pair_id"] for p in doc.get("pairs", [])}:
        doc.setdefault("pairs", []).append({"pair_id": pair_id, "reopened": True})
        path.write_text(json.dumps(doc, indent=1))


def active(campaign, pair_id) -> dict | None:
    """The grant a reopened thread is running, or None."""
    return research.status(campaign, pair_id).get("grant") or None
