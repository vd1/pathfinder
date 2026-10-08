"""One research thread: peers on a shared ledger, consolidate, verify, up to `rounds` rounds.

Since the phase 9 sweep this module keeps the single-engine thread (peers, stage calls, run_thread) and
re-exports everything else under its old names: what every thread shares is in thread.py, the material a
composable review reads in review_evidence.py, and composable research (direct EVA, EVA over bundles) in
composable_research.py."""
from __future__ import annotations
import hashlib, json, os, re, shutil, sys, tempfile, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit
from dataclasses import asdict
from . import context, contracts, corpus, failures, transport
from .context import Section
from .ledger import Ledger
from .scan import prompts_dir
from .admission import Refused
from .thread import (PEERS, TERMINAL, Stopped, _now, _atomic_write, status, OVERSIZE_FAILURE, _set, _pair, HELPER_DIR, install_helper, prepare, thread_sections, _stage_attempts, judge_sections, _consolidate_prompt, READING, evidence_by_reference, evidence_pointer, unfence, is_latex_document, _tex_escape, paper_meta, status_line, write_meta, _inputs, ROLE_BRIEFS, _prompt, role_brief, _check, _scan_row)
from .review_evidence import (EvidenceUnavailable, EvidenceError, _external_citations, _declared_outputs, EVIDENCE_PATH, EVIDENCE_MAX_BYTES, _evidence_references, _assessment_evidence, _bundle_evidence, _review_material)
from .composable_research import (_request_file, retain_response, _direct_requests, _review_contract, _apply_research_review, next_requests, export_outcome, _verdict_under_direct_eva, _repair_review, _finish_repairs, _run_composable)


def _outline(path) -> str:
    """A paper's headings by line, for a peer that reads it by reference: it jumps to the lines it needs."""
    text = path.read_text(errors="replace")
    found = context.outline(text)
    return f"\n\nOutline of inputs/{path.name} ({len(text.splitlines())} lines):\n{found}\n" if found else ""


def _peers(campaign, pair_id, stop):
    """@planks("When Pathfinder executes scan, peer, consolidation, and verification model requests")
    @planks("When Pathfinder executes one stage attempt")
    @planks("When Pathfinder executes one peer stage attempt")
    @planks("When Pathfinder verifies execution routing")
    """
    d, L = campaign.thread_dir(pair_id), Ledger(campaign.thread_dir(pair_id) / "ledger.jsonl")
    A = campaign.allowances; inp = _inputs(d); row = _scan_row(campaign, pair_id)
    helper = install_helper(d)
    used = {}; lock = threading.Lock()                    # each peer's own seconds; the round's clock is the largest

    peers = list(campaign.peers)
    outlines = "".join(_outline(d / "inputs" / inp[side]) for side in "QP")


    def one(actor):
        others = [a for a in peers if a != actor]
        for call_no in range(A["peer_calls"]):
            with lock:
                left = A["peer_seconds"] - max(used.values(), default=0.0)
            if left <= 0 or L.ready(peers):
                return
            while L.ready([actor]) and not all(done[o] for o in others):   # my word stands; wait for my partners
                time.sleep(15)
                if L.ready(peers):
                    return
            if L.ready(peers):
                return
            _check(stop)
            # two independent switches, both off by default: the agent reads what it needs through tools
            in_papers, in_ledger = bool(campaign.raw.get("inline_papers")), bool(campaign.raw.get("inline_ledger"))
            last = L.count() if in_ledger else 0                  # where the agent's own reading of the ledger starts
            material = (("Q and P are above" if in_papers else f"Read inputs/{inp['Q']} and inputs/{inp['P']}")
                        + (f"; the ledger as it stood when this call began is above too, ending at entry {last}."
                           if in_ledger else ", then the ledger with the read command below.")
                        + (f" The files are inputs/{inp['Q']}, inputs/{inp['P']} and ledger.jsonl if you need to quote by line." if in_papers or in_ledger else ""))
            p = _prompt(campaign, "peer", ACTOR=actor, PEERS=" and ".join(others), Q_INPUT=f"inputs/{inp['Q']}", P_INPUT=f"inputs/{inp['P']}",
                        MATERIAL=material, LEDGER=f"{helper} --actor {actor}", LAST_SEQ=last, SECONDS=int(min(left, 1200)),
                        CALLS_LEFT=A["peer_calls"] - call_no - 1, FEASIBILITY=row.get("feasibility", "?"),
                        GAIN=row.get("gain", "?"), CONNEXION=row.get("connexion") or "none recorded.",
                        RATIONALE=row.get("rationale") or "none recorded.")
            if not in_papers:
                p += outlines
            if call_no or L.count():
                p += "\n\nThis call continues an existing thread. Start by reading the ledger, then carry on from where it stands.\n"
            if in_papers or in_ledger:
                p = context.build(campaign, "peer", thread_sections(d, inp, in_papers, in_ledger)
                                  + [Section("", text="## your task\n\n" + p, keep=True)], tools=True, cwd=d, unit=pair_id)
            r = transport.execute(campaign, transport.ModelRequest(
                identity=f"{pair_id}:peer:{actor}:{call_no}", prompt=p, model=campaign.peer_model(actor), tools=True,
                search=campaign.peer_search, cwd=d, timeout=int(min(left, 1200)) + 30, thread=pair_id,
                stage="peer", actor=actor,
            ))
            with lock:
                used[actor] = used.get(actor, 0.0) + r["seconds"]
            if r["transport_failed"]:
                raise transport.TransportFailed(pair_id, failure=r.get("failure"))

    done = {a: False for a in peers}

    def guarded(actor):
        try:
            one(actor)
        finally:
            done[actor] = True

    with ThreadPoolExecutor(len(peers)) as ex:
        for f in [ex.submit(guarded, a) for a in peers]:
            f.result()


def _stage_request(campaign, pair_id, stage, prompt, tools, seconds, attempt=0):
    return transport.ModelRequest(
        identity=f"{pair_id}:{stage}:{attempt}", prompt=prompt, model=campaign.model, tools=tools,
        search=False, cwd=campaign.thread_dir(pair_id), timeout=seconds, thread=pair_id, stage=stage,
        actor=campaign.peers[0] if stage == "consolidate" else "verifier", reads=stage == "verify",
        schema=contracts.SCHEMAS["verify"] if stage == "verify" else None)


def _stage_call(campaign, pair_id, stage, prompt, tools, seconds, done=lambda: False):
    """@planks("When Pathfinder consolidates pair \"Q1P1\"")
    @planks("When Pathfinder executes scan, peer, consolidation, and verification model requests")
    @planks("When Pathfinder executes one stage attempt")
    @planks("When Pathfinder verifies execution routing")

    @planks("When its consolidation response is empty or failed")
    @planks("When its first consolidation response is empty and its next response contains an account")
    @planks("When every fresh repair response reports a provider failure")

    Run consolidate or verify for up to "stage_attempts" attempts (default 2). A reply that failed in
    transport raises TransportFailed (the thread stops, resumable). A reply carrying an error is not an
    answer: consolidation tries again, and a verifier reply with an error raises TransportFailed rather
    than being read as a verdict. An empty consolidation reply is retried.
    """
    for attempt in range(_stage_attempts(campaign)):
        r = transport.execute(campaign, _stage_request(campaign, pair_id, stage, prompt, tools, seconds, attempt))
        if r["transport_failed"]:
            raise transport.TransportFailed(pair_id, failure=r.get("failure"))
        if r.get("error"):
            if stage == "consolidate":
                continue
            raise transport.TransportFailed(pair_id, failure=r.get("failure"))
        if done() or r["text"].strip():
            return r
    return r


def run_thread(campaign, pair_id: str, stop=lambda: False) -> str:
    """@planks("When the standard research entry point opens the investigation")
    @planks("When the findings are consolidated into a research account")
    @planks("When the peer stage finishes")
    @planks("When the verifier returns \"DRAFT\"")
    @planks("When the verifier returns \"ITERATE\" with an unanswered question")
    @planks("When the verifier returns \"ITERATE\"")
    @planks("When the verifier returns \"REVISE\" with a correction")
    @planks("When the verifier returns \"REVISE\"")
    @planks("When the campaign continues")
    @planks("When the provider returns a research account for pair \"Q1P1\"")
    @planks("When both consolidation attempts produce no stored research account")
    @planks("When the provider returns a complete research account on its consolidation retry")
    @planks("When the research workflow receives a nonempty repair account after \"REVISE\"")
    @planks("When the research workflow receives a nonempty next-round account after \"ITERATE\"")
    @planks("When the interrupted research workflow resumes")
    @planks("When every fresh repair response is empty")
    @planks("When every fresh repair response reports a provider failure")
    @planks("When the research workflow starts")
    @planks("Then the previous account remains available as an immutable version")
    """
    _stage_attempts(campaign)                   # an invalid setting fails before any call
    if campaign.raw.get("research_scheme") == "composable":
        from . import composable
        return composable.run(campaign, pair_id, stop)
    if campaign.raw.get("research_scheme") or campaign.raw.get("research_bundles"):
        return _run_composable(campaign, pair_id, stop)
    d = prepare(campaign, pair_id); L = Ledger(d / "ledger.jsonl"); A = campaign.allowances
    note, verdicts = d / f"{pair_id}.tex", d / f"{pair_id}.verdict.json"
    inp = _inputs(d)
    try:
        while True:
            s = status(campaign, pair_id)
            if s["status"] in TERMINAL:
                return s["status"]
            _set(campaign, pair_id, status="running")
            if s["stage"] == "peers":
                _check(stop); _peers(campaign, pair_id, stop)
                if L.latest_substantive() == 0:
                    _set(campaign, pair_id, stage="done", status="PAUSE", reason="empty ledger"); return "PAUSE"
                _set(campaign, pair_id, stage="consolidate")
            elif s["stage"] == "consolidate":
                _check(stop)
                why = "" if L.ready(list(campaign.peers)) else " because the allowance ran out before every peer declared ready"
                repair = s.get("repair")
                if repair:
                    prior = (f" This is a repair of the existing {note.name}, not new research. An independent verifier found"
                             f" these defects: {repair.get('reason')} Corrections: {repair.get('action')} Correct them, keep every"
                             " result the verifier accepted, and do not open new directions.")
                elif note.exists():
                    prior = (f" A previous round wrote {note.name} and the verifier returned ITERATE on it; keep every result"
                             " of that note that still stands and append this round's work to it, rather than rewriting from"
                             " scratch. The verifier's review is the latest review entry in the ledger.")
                else:
                    prior = ""
                write_meta(campaign, pair_id, d)                     # the note's title block: pair, papers, date, state
                # every accepted consolidation reply is kept per round and repair, so a restart applies it
                # without paying for it again; the returned text always becomes the account
                response = d / "consolidation" / f"round-{s['round']}-repair-{s.get('repairs', 0)}.json"
                if response.exists():
                    try:
                        text = json.loads(response.read_text())["text"]
                        if not isinstance(text, str) or not is_latex_document(text):
                            raise ValueError("retained text is not a LaTeX document")
                    except (OSError, ValueError, KeyError, TypeError) as error:
                        _set(campaign, pair_id, status="BLOCKED", reason=f"consolidate: invalid retained response: {error}")
                        return "BLOCKED"
                else:
                    before = note.read_bytes() if note.exists() else None
                    r = _stage_call(campaign, pair_id, "consolidate",
                                    _consolidate_prompt(campaign, d, inp, pair_id, why, note.name, prior),
                                    True, A["consolidate_seconds"])
                    text = unfence(r["text"] or "")
                    if not is_latex_document(text) and note.exists() and note.read_bytes() != before:
                        text = note.read_text(errors="replace")      # it wrote the account to the file instead
                    if r.get("error") or not text.strip():   # never re-verify the older account as if repaired
                        _set(campaign, pair_id, status="BLOCKED", reason=f"consolidate: {r.get('error') or 'no note'}"); return "BLOCKED"
                    if not is_latex_document(text):                # e.g. a quota message returned as the reply
                        (d / "consolidate-unreadable.txt").write_text(r["text"])     # keep the paid reply for inspection
                        _set(campaign, pair_id, status="BLOCKED", reason="consolidate: reply is not a LaTeX document"); return "BLOCKED"
                    response.parent.mkdir(exist_ok=True)
                    _atomic_write(response, json.dumps({"text": text, "session": r.get("session"), "at": _now(),
                                                       "run_id": getattr(campaign, "run_id", None)}).encode())
                if note.exists():                                    # archive the account being replaced
                    previous = note.read_bytes()
                    version = d / "account-versions" / f"{hashlib.sha256(previous).hexdigest()}.tex"
                    version.parent.mkdir(exist_ok=True)
                    if not version.exists():
                        _atomic_write(version, previous)
                _atomic_write(note, text.encode())
                _set(campaign, pair_id, stage="verify", repair=None)
            elif s["stage"] == "verify":
                _check(stop)
                # static material first, the instruction last: the head is shared with every other judge call
                task = "## your task\n\n" + _prompt(campaign, "verify", Q_INPUT=f"inputs/{inp['Q']}", P_INPUT=f"inputs/{inp['P']}", NOTE=note.name)
                task += "\n\n" + evidence_pointer(campaign) + " Do not modify any file.\n"
                p = context.build(campaign, "verify", judge_sections(d, inp, note.name) + [Section("", text=task, keep=True)],
                                  tools=True, cwd=d, unit=pair_id)
                # a paid reply to this very prompt, kept before its repair turn, is reused after a stop
                pending, prompt_sha = d / "verify-pending.json", hashlib.sha256(p.encode()).hexdigest()
                kept = json.loads(pending.read_text()) if pending.exists() else {}
                if kept.get("prompt_sha256") == prompt_sha:
                    r = kept["result"]
                else:
                    r = _stage_call(campaign, pair_id, "verify", p, True, A["verify_seconds"], done=lambda: True)
                    _atomic_write(pending, json.dumps({"prompt_sha256": prompt_sha, "result": {
                        k: r.get(k) for k in ("text", "session", "seconds", "transport_failed", "error", "failure")}}).encode())
                first = r.get("text") or ""                  # read once under the verdict contract, repaired at most once
                v, r = contracts.ensure(campaign, _stage_request(campaign, pair_id, "verify", p, True, A["verify_seconds"]), r, "verify")
                if v is None and r.get("transport_failed"):   # the repair turn failed in transport: the kept reply waits
                    raise transport.TransportFailed(pair_id, failure=r.get("failure"))
                pending.unlink(missing_ok=True)
                if v is None:                             # an operational failure, not a verdict
                    (d / "verify-unreadable.txt").write_text(first + "\n\n--- repair reply ---\n\n" + (r.get("text") or ""))
                    _set(campaign, pair_id, status="BLOCKED", reason=f"contract: verify: {r['error'].removeprefix('contract: ')}",
                         failure=r["failure"]); return "BLOCKED"
                dec = v["decision"]
                hist = json.loads(verdicts.read_text()) if verdicts.exists() else []
                hist.append({"round": s["round"], "at": _now(), "note_sha256": hashlib.sha256(note.read_bytes()).hexdigest(), **v})
                verdicts.write_text(json.dumps(hist, indent=1))
                write_meta(campaign, pair_id, d)                     # the state on the note follows the verdicts
                repairs = s.get("repairs", 0)
                if dec == "REVISE" and repairs < campaign.raw.get("repairs", 1):
                    L.add("verifier", "review", f"REVISE: {v.get('reason')} Corrections: {v.get('action')}")
                    _set(campaign, pair_id, stage="consolidate", repairs=repairs + 1, repair=v, reason=v.get("reason"))
                elif dec == "ITERATE" and s["round"] < campaign.rounds:
                    L.add("verifier", "review", f"ITERATE: {v.get('reason')} Action: {v.get('action')}")
                    _set(campaign, pair_id, stage="peers", round=s["round"] + 1, reason=v.get("reason"))
                else:
                    final = {"ITERATE": "PAUSE-ON-ITERATE", "REVISE": "PAUSE-ON-REVISE"}.get(dec, dec)
                    _set(campaign, pair_id, stage="done", status=final, reason=v.get("reason")); write_meta(campaign, pair_id, d); return final
    except (Stopped, Refused):
        _set(campaign, pair_id, status="stopped"); return "stopped"
    except transport.PromptTooLarge as error:
        _set(campaign, pair_id, status="BLOCKED", reason=f"{status(campaign, pair_id).get('stage')}: {error}",
             failure=OVERSIZE_FAILURE)
        return "BLOCKED"
    except transport.TransportFailed as error:
        _set(campaign, pair_id, status="stopped", reason=transport.stopped_reason(error.failure), failure=error.failure); raise
