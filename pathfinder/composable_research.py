"""Composable research (direct EVA, and EVA over bundles): retained requests and responses, reviews read
under their contracts, and the transitions they make. Split from research.py in the phase 9 sweep;
research re-exports every name."""
from __future__ import annotations
import hashlib, json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from . import contracts, failures, transport
from .context import Section
from .ledger import Ledger
from .admission import Refused
from .thread import (TERMINAL, Stopped, _now, status, OVERSIZE_FAILURE, _set, install_helper, prepare, _stage_attempts, _consolidate_prompt, evidence_by_reference, write_meta, _inputs, _prompt, role_brief, _check, _scan_row)
from .review_evidence import EvidenceUnavailable, _bundle_evidence, _review_material


def _request_file(campaign, pair_id, identity):
    """@planks("the retained response is applied without another model dispatch")"""
    return campaign.thread_dir(pair_id) / "research-requests" / (hashlib.sha256(identity.encode()).hexdigest() + ".json")


def retain_response(campaign, pair_id, request, result):
    """@planks("Pathfinder resumes the investigation")
    @planks("the retained Vera response has no valid request list")
    @planks("the evidence changes before that response is applied")

    Store provider output before applying any ledger or research transition.
    """
    path = _request_file(campaign, pair_id, request.identity)
    saved = json.loads(path.read_text())
    saved["result"] = result
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(saved))
    temporary.replace(path)


def _direct_requests(response, existing):
    """@planks("Vera returns no new requests and omits disposition of the active request")
    @planks("a later Vera review defers that request with a missing-input reason")
    @planks("Vera returns PAUSE instead of a request review")
    @planks("the retained Vera response has no valid request list")
    """
    if not isinstance(response, dict) or response.get("decision") not in (None, "REVISE", "ITERATE"):
        raise ValueError("direct EVA requires a request review without a scientific verdict")
    if not isinstance(response.get("requests"), list) or not isinstance(response.get("dispositions"), list):
        raise ValueError("review requires requests and dispositions lists")
    updated = {key: dict(value) for key, value in existing.items()}
    handled = set()
    for item in response["dispositions"]:
        if not isinstance(item, dict) or item.get("id") not in existing or item["id"] in handled:
            raise ValueError("disposition must identify an existing request exactly once")
        if item.get("status") not in ("resolved", "deferred") or not isinstance(item.get("reason"), str) or not item["reason"].strip():
            raise ValueError("disposition requires resolved/deferred status and a reason")
        handled.add(item["id"])
        updated[item["id"]].update(status=item["status"], disposition=item)
    outstanding = {key for key, value in existing.items() if value["status"] == "active"}
    if outstanding - handled:
        raise ValueError("missing disposition for active requests: " + ", ".join(sorted(outstanding - handled)))
    for item in response["requests"]:
        if (not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"].strip()
                or item["id"] in updated or item.get("action") not in ("REVISE", "ITERATE")
                or not isinstance(item.get("text"), str) or not item["text"].strip()):
            raise ValueError("new request requires a distinct id, REVISE/ITERATE action and concrete text")
        updated[item["id"]] = {**item, "status": "active"}
    return updated


def _review_contract(campaign, s):
    """(contract name, check) for a composable review: a request review under direct EVA, else a verdict."""
    if campaign.raw.get("research_scheme", "eva") == "direct_eva":
        return "request_review", (lambda value: _direct_requests(value, s.get("requests", {})))
    return "verify", None


def _apply_research_review(campaign, pair_id, saved, s):
    """@planks("the review is appended to the ledger with its reviewed evidence identity")
    @planks("the full review is appended to the ledger exactly once")
    @planks("Pathfinder records an operational review error rather than a handoff")
    @planks("Pathfinder blocks the stale response before a research transition")
    @planks("the branch is ready for handoff because no further requests remain")
    @planks("the branch is ready for handoff because its allowance is exhausted")
    @planks("Emmy repairs the account before scientific verification")
    @planks("the existing PAUSE scientific ending is preserved")
    @planks("the existing PAUSE-ON-ITERATE ending retains the unanswered request")
    """
    d = campaign.thread_dir(pair_id)
    identity = saved["request"]["identity"]
    _, evidence_id = _review_material(campaign, pair_id, identity, with_id=True)
    if evidence_id != saved["evidence_id"]:
        _set(campaign, pair_id, status="BLOCKED", reason="stale review: research evidence changed")
        return
    direct = campaign.raw.get("research_scheme", "eva") == "direct_eva"
    verdict = _verdict_under_direct_eva(campaign, saved["result"].get("text"))
    if verdict:
        _set(campaign, pair_id, status="BLOCKED", reason=f"review: {verdict}")
        return
    try:                                        # the retained reply was read and repaired under its contract when it came
        name, check = _review_contract(campaign, s)
        value = contracts.parse(name, saved["result"]["text"], check)
        if direct:
            requests = _direct_requests(value, s.get("requests", {}))
    except contracts.ContractViolation as violation:
        failure = failures.Failure("contract", *failures.SCOPES["contract"]).record()
        _set(campaign, pair_id, status="BLOCKED", reason=f"contract: review: {violation}", failure=failure)
        return
    ledger = Ledger(d / "ledger.jsonl")
    feedback = {"review_id": identity, "evidence_id": saved["evidence_id"], "response": value}
    encoded = json.dumps(feedback)
    if not any(row["kind"] == "review" and row["text"] == encoded for row in ledger.read()):
        ledger.add("verifier", "review", encoded)
    update = dict(pending=[], reviews=s.get("reviews", 0) + 1, latest_review=feedback,
                  reviewed_head=saved["ledger_head"], reason=value.get("reason"), status="running")
    if direct:
        update["requests"] = requests
        if not any(item["status"] == "active" for item in requests.values()):
            update.update(stage="done", status="HANDOFF", handoff_reason="no_further_requests")
        elif s["round"] >= campaign.rounds:
            update.update(stage="done", status="HANDOFF", handoff_reason="research_allowance_exhausted")
        else:
            update.update(stage="peers", round=s["round"] + 1, peer_call=0, peer_seconds=0)
    else:
        verdicts = d / f"{pair_id}.verdict.json"
        history = json.loads(verdicts.read_text()) if verdicts.exists() else []
        if not any(item.get("review_id") == identity for item in history):
            history.append({"review_id": identity, "round": s["round"], "at": _now(),
                            "note_sha256": hashlib.sha256((d / f"{pair_id}.tex").read_bytes()).hexdigest(), **value})
            verdicts.write_text(json.dumps(history, indent=1))
        decision = value["decision"]
        if decision == "REVISE" and s.get("repairs", 0) < campaign.raw.get("repairs", 1):
            update.update(stage="consolidate", repairs=s.get("repairs", 0) + 1, repair=value)
        elif decision == "ITERATE" and s["round"] < campaign.rounds:
            update.update(stage="peers", round=s["round"] + 1, peer_call=0, peer_seconds=0)
        else:
            update.update(stage="done", status={"ITERATE": "PAUSE-ON-ITERATE", "REVISE": "PAUSE-ON-REVISE"}.get(decision, decision))
    _set(campaign, pair_id, **update)
    if not direct:
        write_meta(campaign, pair_id, d)


def next_requests(campaign, pair_id):
    """@planks("Pathfinder prepares its first Vera review")
    @planks("its peer research round finishes")
    @planks("Vera requests REVISE of a ledger argument from existing evidence")
    @planks("Vera requests ITERATE with a concrete research gap")
    @planks("Pathfinder prepares peer research and synthesis and scientific verification")
    @planks("Pathfinder prepares the peer research instructions")
    @planks("Pathfinder prepares the research evidence for that investigation")
    @planks("Pathfinder resumes the investigation")
    @planks("the next research and review cycle is prepared")
    @planks("Pathfinder advances the branch")
    @planks("its calls have identities distinct from the earlier review cycle")
    @planks("the branch hands off the latest research with an explicit unreviewed-head marker")
    @planks("the instructions require investigating disagreements and new connections")
    @planks("the instructions distinguish inherited evidence from new derivations and conjectures")
    @planks("Vera requests REVISE of the returned account using existing evidence")
    @planks("the review is blocked before a provider call with the missing path identified")

    Apply retained outputs, then prepare the next real provider requests.
    """
    _stage_attempts(campaign)
    d = prepare(campaign, pair_id)
    ledger = Ledger(d / "ledger.jsonl")
    direct = campaign.raw.get("research_scheme", "eva") == "direct_eva"
    try:
        while True:
            s = status(campaign, pair_id)
            if s["status"] in TERMINAL | {"HANDOFF", "BLOCKED"}:
                return []
            pending = [json.loads(_request_file(campaign, pair_id, identity).read_text()) for identity in s.get("pending", [])]
            if pending:
                waiting = [item for item in pending if "result" not in item]
                if waiting:
                    return [transport.ModelRequest(**{**item["request"], "cwd": d}) for item in waiting]
                failed = next((item for item in pending if item["result"].get("transport_failed") or item["result"].get("error")), None)
                if failed and ((failed["result"].get("failure") or {}).get("scope") == "campaign"):
                    # the call hit a campaign-wide wall (quota, auth, launch); after the operator resumes, issue it again
                    for item in pending:
                        if (item["result"].get("failure") or {}).get("scope") == "campaign":
                            path = _request_file(campaign, pair_id, item["request"]["identity"])
                            saved = json.loads(path.read_text()); saved.pop("result", None)
                            temporary = path.with_suffix(".tmp"); temporary.write_text(json.dumps(saved)); temporary.replace(path)
                    continue
                if failed:
                    error = failed["result"].get("error") or "transport failed"
                    reason = (f"contract: review: {error.removeprefix('contract: ')}"
                              if (failed["result"].get("failure") or {}).get("class") == "contract" else f"{s['stage']}: {error}")
                    _set(campaign, pair_id, status="BLOCKED", reason=reason, failure=failed["result"].get("failure"))
                    return []
                if s["stage"] == "peers":
                    calls = s.get("peer_call", 0) + 1
                    seconds = s.get("peer_seconds", 0) + sum(item["result"]["seconds"] for item in pending)
                    more = calls < campaign.allowances["peer_calls"] and seconds < campaign.allowances["peer_seconds"] and not ledger.ready(list(campaign.peers))
                    _set(campaign, pair_id, pending=[], peer_call=calls, peer_seconds=seconds,
                         stage="peers" if more else "ledger_review" if direct else "consolidate")
                elif s["stage"] == "consolidate":
                    result = pending[0]["result"]["text"]
                    if not result.strip():
                        _set(campaign, pair_id, status="BLOCKED", reason="consolidate: no note")
                        return []
                    note = d / f"{pair_id}.tex"
                    if note.exists() and note.read_text() != result:
                        versions = d / "account-versions"
                        versions.mkdir(exist_ok=True)
                        (versions / (hashlib.sha256(note.read_bytes()).hexdigest() + ".tex")).write_bytes(note.read_bytes())
                    note.write_text(result)
                    _set(campaign, pair_id, stage="verify", pending=[], repair=None)
                else:
                    _apply_research_review(campaign, pair_id, pending[0], s)
                continue
            stage = s["stage"]
            if stage == "ledger_review" and s.get("reviews", 0) >= campaign.raw.get("ledger_reviews", campaign.rounds + 1):
                _set(campaign, pair_id, status="HANDOFF", stage="done", handoff_reason="review_allowance_exhausted")
                return []
            material, evidence_id = _review_material(campaign, pair_id, with_id=True)
            actors = campaign.peers if stage == "peers" else (campaign.peers[0],) if stage == "consolidate" else ("verifier",)
            batch = []
            for actor in actors:
                if stage == "peers":
                    seconds = min(campaign.allowances["peer_seconds"] - s.get("peer_seconds", 0), 1200)
                    row = _scan_row(campaign, pair_id)
                    prompt = material + "\n\n" + _prompt(campaign, "peer", ACTOR=actor,
                        PEERS=" and ".join(a for a in campaign.peers if a != actor),
                        Q_INPUT=f"inputs/{_inputs(d)['Q']}", P_INPUT=f"inputs/{_inputs(d)['P']}",
                        MATERIAL="Both papers (or their file references), the attributed ledger and the evidence index are above.",
                        LEDGER=f"{install_helper(d)} --actor {actor}",
                        LAST_SEQ=ledger.count(), SECONDS=int(seconds),
                        CALLS_LEFT=campaign.allowances["peer_calls"] - s.get("peer_call", 0) - 1,
                        FEASIBILITY=row.get("feasibility", "?"), GAIN=row.get("gain", "?"),
                        CONNEXION=row.get("connexion") or "none recorded.", RATIONALE=row.get("rationale") or "none recorded.")
                    if s.get("requests"):
                        prompt += "\nReview requests and dispositions:\n" + json.dumps(s["requests"])
                elif stage == "consolidate":
                    seconds = campaign.allowances["consolidate_seconds"]
                    repair = s.get("repair")
                    prior = ("Repair the existing account from existing evidence. Preserve accepted results. " + json.dumps(repair)
                             if repair else "Preserve prior results that still stand and append this round's work.")
                    bundles = _bundle_evidence(campaign, d, by_reference=evidence_by_reference(campaign))
                    prompt = _consolidate_prompt(campaign, d, _inputs(d), pair_id, "", f"{pair_id}.tex", prior,
                                                 extra=[Section("", text=bundles)] if bundles.strip() else [])
                    write_meta(campaign, pair_id, d)
                else:
                    seconds = campaign.allowances["verify_seconds"]
                    if direct:
                        prompt = material + "\n\n" + role_brief(campaign) + ('\n\nReview this research ledger directly. Return JSON with requests and dispositions lists. '
                            'Each new request needs a distinct id, action REVISE or ITERATE, and concrete text. '
                            'REVISE corrects an argument using existing evidence; ITERATE investigates a research gap. '
                            'Every active prior request needs a disposition with its id, status resolved or deferred, and reason. '
                            'For work that remains actionable, resolve the superseded request and issue a new request. '
                            'An empty requests list means no further actionable requests. Never issue a scientific verdict. '
                            'Prior requests and dispositions:\n' + json.dumps(s.get("requests", {})))
                    else:
                        prompt = material + "\n\n" + _prompt(campaign, "verify", Q_INPUT=f"inputs/{_inputs(d)['Q']}",
                                                            P_INPUT=f"inputs/{_inputs(d)['P']}", NOTE=f"{pair_id}.tex")
                identity = f"{pair_id}:{stage}:{actor}:round-{s['round']}:review-{s.get('reviews', 0)}:repair-{s.get('repairs', 0)}:call-{s.get('peer_call', 0)}"
                request = transport.ModelRequest(identity=identity, prompt=prompt, model=campaign.model,
                    tools=True, search=campaign.peer_search if stage == "peers" else False,
                    cwd=d, timeout=int(seconds) + (30 if stage == "peers" else 0), thread=pair_id,
                    stage="peer" if stage == "peers" else stage, actor=actor, reads=stage == "verify",
                    schema=contracts.SCHEMAS[_review_contract(campaign, s)[0]] if stage in ("verify", "ledger_review") else None)
                path = _request_file(campaign, pair_id, identity)
                path.parent.mkdir(exist_ok=True)
                path.write_text(json.dumps({"request": {**asdict(request), "cwd": str(d)},
                    "evidence_id": evidence_id, "ledger_head": ledger.latest_substantive()}))
                batch.append(request)
            _set(campaign, pair_id, pending=[request.identity for request in batch], status="running")
            return batch
    except EvidenceUnavailable as error:
        _set(campaign, pair_id, status="BLOCKED", reason=str(error))
        return []
    except transport.PromptTooLarge as error:           # the review material does not fit the verify budget
        _set(campaign, pair_id, status="BLOCKED", reason=f"{status(campaign, pair_id).get('stage')}: {error}", failure=OVERSIZE_FAILURE)
        return []


def export_outcome(campaign, pair_id):
    """@planks("its composable research outcome is exported")
    @planks("the handoff preserves deferred objections without a scientific verdict")
    @planks("the handoff preserves the unanswered request without a scientific verdict")
    @planks("the public scientific verdict is ACCEPT")
    @planks("the original verifier decision remains DRAFT in provenance")
    @planks("the branch hands off the latest research with an explicit unreviewed-head marker")
    @planks("no scientific verdict is inferred")
    """
    s = status(campaign, pair_id)
    ledger = Ledger(campaign.thread_dir(pair_id) / "ledger.jsonl")
    head = ledger.latest_substantive()
    direct = campaign.raw.get("research_scheme", "eva") == "direct_eva"
    return {**s, "scientific_verdict": None if direct else {"DRAFT": "ACCEPT"}.get(s["status"], s["status"] if s["status"] in TERMINAL else None),
            "ledger_head": head, "unreviewed_head": head > s.get("reviewed_head", -1),
            "provenance": [row for row in ledger.read() if row["kind"] == "review"]}


def _verdict_under_direct_eva(campaign, text) -> str | None:
    """Under direct EVA a scientific verdict is not a malformed request review: it is never repaired into one."""
    if campaign.raw.get("research_scheme") != "direct_eva":
        return None
    try:
        value = contracts.extract_json(text or "")
    except ValueError:
        return None
    if isinstance(value, dict) and isinstance(value.get("decision"), str) and value["decision"].upper() in ("DRAFT", "PAUSE"):
        return "direct EVA requires a request review without a scientific verdict"
    return None


def _repair_review(campaign, pair_id, request, result):
    """Retain a review reply, then read it under its contract with at most one repair turn, then retain the outcome.
    The raw reply is kept first with contract_pending, so a stop during the repair turn loses nothing paid for."""
    if _verdict_under_direct_eva(campaign, result.get("text")):
        retain_response(campaign, pair_id, request, result); return      # applied, and blocked, as a verdict
    retain_response(campaign, pair_id, request, {**result, "contract_pending": True})
    name, check = _review_contract(campaign, status(campaign, pair_id))
    _, outcome = contracts.ensure(campaign, request, result, name, check)
    retain_response(campaign, pair_id, request, outcome)


def _finish_repairs(campaign, pair_id):
    """Complete any repair turn a stop interrupted, from the retained reply, before anything else is decided."""
    d = campaign.thread_dir(pair_id)
    for identity in status(campaign, pair_id).get("pending", []):
        path = _request_file(campaign, pair_id, identity)
        saved = json.loads(path.read_text()) if path.exists() else {}
        result = saved.get("result") or {}
        if result.get("contract_pending"):
            request = transport.ModelRequest(**{**saved["request"], "cwd": d})
            _repair_review(campaign, pair_id, request, {k: v for k, v in result.items() if k != "contract_pending"})


def _run_composable(campaign, pair_id, stop):
    """@planks("the standard research entry point opens the investigation")"""
    prepare(campaign, pair_id)
    try:
        while True:
            _check(stop)
            _finish_repairs(campaign, pair_id)
            requests = next_requests(campaign, pair_id)
            if not requests:
                return status(campaign, pair_id)["status"]
            def execute(request):
                """@planks("the standard research entry point opens the investigation")"""
                _check(stop)
                try:
                    result = transport.execute(campaign, request)
                except transport.PromptTooLarge as error:   # retained as a failed result: the pair blocks, the run goes on
                    retain_response(campaign, pair_id, request, {"text": "", "seconds": 0.0, "transport_failed": True,
                                                                 "error": str(error), "outcome": "refused",
                                                                 "failure": OVERSIZE_FAILURE})
                    return
                if request.stage in ("verify", "ledger_review") and not result.get("transport_failed"):
                    _repair_review(campaign, pair_id, request, result)     # kept first, so a stop never loses a paid reply
                    return
                retain_response(campaign, pair_id, request, result)
                if result.get("transport_failed"):
                    raise transport.TransportFailed(pair_id, failure=result.get("failure"))
            with ThreadPoolExecutor(len(requests)) as pool:
                for future in [pool.submit(execute, request) for request in requests]:
                    future.result()
    except (Stopped, Refused):                     # a refused call used no attempt: the same request is issued on resume
        _set(campaign, pair_id, status="stopped")
        return "stopped"
    except transport.TransportFailed as error:
        _set(campaign, pair_id, status="stopped", reason=transport.stopped_reason(error.failure), failure=error.failure)
        raise
