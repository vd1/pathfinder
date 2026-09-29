"""The research loop: seats, rolling admission, budget guard, stop as a drain, health flag."""
from __future__ import annotations
import copy, hashlib, json, os, signal, time, uuid
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from pathlib import Path
from . import research, transport
from . import alerts, corpus, health
from .admission import Refused


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_manifest(campaign) -> dict:
    """@planks("When a comparison run is created")
    @planks("When the campaign is inspected or repeated")
    """
    digests = {side: _digest(campaign.path(f"{side}.jsonl")) for side in ("Q", "P")}
    manifest = {"snapshots": {side: f"{side}.jsonl" for side in ("Q", "P")}, "snapshot_digests": digests}
    campaign.path("manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def pair_identity(campaign, pair_id: str) -> str:
    """@planks("When both runs enumerate their cross-corpus pairs")"""
    i, j = (int(n) for n in pair_id[1:].split("P"))
    q = corpus.read(campaign.path("Q.jsonl"))[i - 1]["id"]
    p = corpus.read(campaign.path("P.jsonl"))[j - 1]["id"]
    return hashlib.sha256(f"{q}\0{p}".encode()).hexdigest()


def result_provenance(campaign, pair_id: str) -> dict:
    """@planks("Given a run produces a result for one cross-corpus pair")"""
    i, j = (int(n) for n in pair_id[1:].split("P"))
    return {
        "record_ids": [corpus.read(campaign.path("Q.jsonl"))[i - 1]["id"], corpus.read(campaign.path("P.jsonl"))[j - 1]["id"]],
        "snapshot_digests": [_digest(campaign.path(f"{side}.jsonl")) for side in ("Q", "P")],
    }


def validate_manifest(manifest: dict) -> dict:
    """@planks("When the operator defines a run manifest")
    @planks("When the operator defines a run")
    @planks("Then role \"{role}\" records its own model, backend, execution class, prompt arrangement, tool policy, and budget")
    """
    required = {"model", "backend", "execution_class", "prompt", "tool_policy", "budget"}
    roles = ["scan", "research", "consolidate", "verify"]            # every run has these
    roles += [r for r in ("edit",) if r in manifest["assignments"]]   # a run that edits assigns the editor too
    for role in roles:
        if role not in manifest["assignments"] or required - manifest["assignments"][role].keys():
            raise ValueError(f"incomplete assignment for {role}")
    return manifest


def comparison_arm(baseline: dict, role: str, *, model: str | None = None, backend: str | None = None) -> dict:
    """@planks("When the operator creates a comparison arm for role \"verify\"")"""
    arm = copy.deepcopy(baseline)
    if model is not None:
        arm["assignments"][role]["model"] = model
    if backend is not None:
        arm["assignments"][role]["backend"] = backend
    return arm


def compare_manifests(baseline: dict, arm: dict) -> dict:
    """@planks("When the runs are compared")"""
    changed = [role for role in baseline["assignments"] if baseline["assignments"][role] != arm["assignments"][role]]
    return {"role": changed[0], "outcomes": [], "cost": [], "latency": []}


def reproduction_record(campaign, manifest: dict) -> dict:
    """@planks("When the comparison run starts")"""
    encoded = json.dumps(manifest, sort_keys=True).encode()
    prompts = campaign.path("prompts")
    return {
        "manifest_digest": hashlib.sha256(encoded).hexdigest(),
        "snapshot_digests": {side: _digest(campaign.path(f"{side}.jsonl")) for side in ("Q", "P")},
        "prompt_digests": {path.name: _digest(path) for path in prompts.glob("*") if path.is_file()} if prompts.exists() else {},
    }


def execution_route(assignment: dict) -> str:
    """@planks("When the comparison run schedules role \"scan\"")
    @planks("When the comparison run schedules role \"research\"")
    @planks("When the comparison run schedules role \"consolidate\"")
    @planks("When Pathfinder schedules the same frozen stage through each provider")
    """
    return "provider" if assignment.get("execution_class") == "provider" else assignment["backend"]


def prepare_provider_stage(role: str, inputs: dict, *, input_limit: int, output_limit: int) -> dict:
    """@planks("When Pathfinder prepares role \"consolidate\" for provider execution")
    @planks("When Pathfinder prepares role \"consolidate\" for one frozen paper pair")
    @planks("Then the provider request exposes no workspace or search tools")
    """
    frozen = copy.deepcopy(inputs)
    request = {
        "role": role,
        "inputs": frozen,
        "input_digests": {
            name: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
            for name, value in frozen.items()
        },
        "input_tokens": sum(len(str(value).split()) for value in frozen.values()),
        "output_token_limit": output_limit,
        "tools": [],
        "status": "ready",
    }
    if request["input_tokens"] > input_limit:
        request["status"] = "blocked"
    return request


def execute_provider_stage(request: dict, provider_call):
    """@planks("When Pathfinder executes role \"verify\" through its assigned provider")"""
    return provider_call(request)


def prepare_provider_batch(role: str, jobs: list[dict], *, input_limit: int, output_limit: int) -> list[dict]:
    """@planks("When Pathfinder prepares their provider stage jobs")"""
    prepared = []
    for job in jobs:
        request = prepare_provider_stage(role, job["inputs"], input_limit=input_limit, output_limit=output_limit)
        request["result_id"] = hashlib.sha256(f'{role}\0{job["pair_id"]}'.encode()).hexdigest()
        prepared.append(request)
    return prepared


def execution_receipt(role, backend, model, execution_class, prompt_digest, provider_job_id, raw_response, outcome, latency, token_usage, cost):
    """@planks("When the execution finishes")
    @planks("When the same assignment is repeated")
    """
    return dict(role=role, backend=backend, model=model, execution_class=execution_class, prompt_digest=prompt_digest,
                provider_job_id=provider_job_id, raw_response=raw_response, outcome=outcome, latency=latency,
                token_usage=token_usage, cost=cost)


def run_assigned_comparison(campaign, assignments: dict) -> dict:
    """@planks("When Pathfinder runs the assigned comparison workflow")
    @planks("Then the provider call has a \"{timeout}\" second timeout")
    @planks("Then the provider receipt retains budget \"{budget}\" for role \"{role}\"")
    @planks("When Pathfinder executes role \"{role}\" for one frozen paper pair")
    """
    receipts = []
    outcome = None
    for role, assignment in assignments.items():
        campaign.backend = assignment["backend"]
        campaign.raw = {**campaign.raw, "codex": {"name": "elm", "env_key": "ELM_API_KEY"}}
        prompt = f"Role: {role}. Review frozen pair Q1P1 and return a concise outcome."
        reply = transport.call(
            prompt, campaign=campaign, model=assignment["model"], tools=False, search=False,
            cwd=campaign.path(f"comparison-{role}"), timeout=120, thread="Q1P1", stage=role, actor=role,
        )
        receipt = execution_receipt(
            role, assignment["backend"], assignment["model"], assignment["execution_class"],
            hashlib.sha256(prompt.encode()).hexdigest(), reply["session"], reply["text"], reply["text"],
            reply["seconds"], {"input": reply["input_tokens"], "output": reply["output_tokens"]}, reply["cost"],
        )
        receipt["budget"] = assignment["budget"]
        receipts.append(receipt)
        if role == "verify":
            outcome = reply["text"]
    return {"receipts": receipts, "pairs": {"Q1P1": {"verification_outcome": outcome}}}


def validate_assignment(assignment: dict) -> bool:
    """@planks("When the run manifest is validated")"""
    return assignment.get("provider") == "elm" and assignment.get("backend") in {"opencode", "pi"}


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Lock:
    """One lock file per thread directory holding the owner's pid."""

    def __init__(self, d: Path):
        self.d = Path(d); self.p = self.d / "lock"

    @staticmethod
    def holder(d: Path) -> int | None:
        p = Path(d) / "lock"
        if not p.exists():
            return None
        try:
            pid = int(p.read_text().strip()); os.kill(pid, 0); return pid
        except (ValueError, ProcessLookupError, PermissionError):
            return None

    def __enter__(self):
        if Lock.holder(self.d):
            raise RuntimeError(f"{self.d.name} is held by pid {Lock.holder(self.d)}")
        self.d.mkdir(parents=True, exist_ok=True); self.p.write_text(str(os.getpid())); return self

    def __exit__(self, *a):
        self.p.unlink(missing_ok=True)


def stopped(campaign) -> bool:
    """A stop marker on the campaign, or on the parent it runs under (campaign.raw["parent"]): the same
    predicate admission uses, so a refused call and the scheduler always agree that the run is stopping."""
    from .admission import _stop_marker
    return _stop_marker(campaign) is not None


def request_stop(campaign, reason: str):
    campaign.path("stop.json").write_text(json.dumps({"reason": reason, "at": _now()}))


def unhealthy(campaign) -> bool:
    return campaign.path("health.json").exists()


def guard_ok(campaign, inflight: int) -> bool:
    projected = transport.spend(campaign) + inflight * campaign.call_estimate_usd
    if projected > campaign.budget_usd:
        if not stopped(campaign):
            request_stop(campaign, f"budget: {projected:.2f} projected against cap {campaign.budget_usd:.2f}")
        return False
    return True


def pending(campaign) -> list[str]:
    """@planks("Pathfinder admits pending investigations")
    @planks("the operator runs the research command")
    @planks("it records the branch handoff without invoking account editing")
    """
    pairs = [p["pair_id"] for p in json.loads(campaign.path("shortlist.json").read_text())["pairs"]]
    selection = getattr(campaign, "selection", None)
    if selection is not None:                    # a bounded run: unlisted pairs, BLOCKED ones included, are not considered
        pairs = [p for p in pairs if p in selection]
    from . import edit
    return [p for p in pairs if not Lock.holder(campaign.thread_dir(p))
            and research.status(campaign, p).get("status") not in {"BLOCKED", "HANDOFF"}
            and (research.status(campaign, p).get("status") not in research.TERMINAL
                 or edit.status(campaign, p).get("status") != "done")]


def _work(campaign, pair_id):
    """@planks("When the campaign processes pair \"{pair_id}\" to completion")"""
    with Lock(campaign.thread_dir(pair_id)):
        stop = lambda: stopped(campaign) or unhealthy(campaign)
        result = research.status(campaign, pair_id).get("status")
        stage = research.status(campaign, pair_id).get("stage")
        try:
            if result not in research.TERMINAL:
                result = research.run_thread(campaign, pair_id, stop=stop)
            if result in research.TERMINAL and not stop():
                from . import edit
                stage = "edit"
                if edit.status(campaign, pair_id).get("status") != "done":
                    edited = edit.run(campaign, pair_id, stop=stop)
                    if edited != "done" and not stop():
                        raise RuntimeError(f"editor {edited}: {edit.status(campaign, pair_id).get('reason')}")
        except Exception as error:
            error.stage = stage if stage == "edit" else research.status(campaign, pair_id).get("stage")
            raise
        return result


def _validate_selection(campaign, pairs) -> list[str]:
    pairs = list(pairs)
    shortlist = {p["pair_id"] for p in json.loads(campaign.path("shortlist.json").read_text())["pairs"]}
    if len(set(pairs)) != len(pairs):
        raise ValueError(f"duplicate pairs in selection: {pairs}")
    missing = [p for p in pairs if p not in shortlist]
    if missing:
        raise ValueError(f"not on the shortlist: {', '.join(missing)}")
    held = [p for p in pairs if Lock.holder(campaign.thread_dir(p))]
    if held:
        raise RuntimeError(f"held by another runner: {', '.join(held)}")
    return pairs


def run(campaign, interval: float = 5.0, pairs=None, accept_change: str | None = None):
    """Run under exclusive ownership; an explicit invocation starts a new run.
    pairs: a bounded run over exactly these shortlisted pairs, through research and edit. Unlisted pairs are
    ignored, BLOCKED ones included; when no listed pair has research or edit work left, the run returns at
    once with status nothing-to-run. A listed BLOCKED pair is reported and does not stop the others."""
    if pairs is not None:
        campaign.selection = _validate_selection(campaign, pairs)
    try:
        return _owned_run(campaign, interval, accept_change)
    finally:
        if pairs is not None:
            del campaign.selection


def _owned_run(campaign, interval, accept_change=None):
    with health.owner(campaign, nested=True):
        if stopped(campaign):
            print("stop marker exists; clear it explicitly before restarting")
            return 1
        selection = getattr(campaign, "selection", None)
        if selection is not None and not pending(campaign) and not _blocked(campaign):
            print("nothing to run: every selected pair has finished research and edit")
            return 0
        from . import provenance
        try:
            with provenance.run_context(campaign, accept_change):
                return _recorded_run(campaign, interval)
        except provenance.ChangeRefused as refused:
            print(f"refusing to resume: {refused}")
            return 1


def _recorded_run(campaign, interval):
    old = health.read(campaign.path("health.json"))
    metadata = {"run_id": campaign.run_id, "pid": os.getpid(), "status": "running",
                "started_at": time.time(), "heartbeat_at": time.time(),
                "last_progress": None, "previous_failure": old}
    campaign.path("health.json").unlink(missing_ok=True)
    health.write(campaign.path("runner.json"), metadata)
    try:
        result = _run(campaign, interval, metadata)
        metadata["status"] = "failed" if unhealthy(campaign) else "stopped" if stopped(campaign) else "blocked" if result else "finished"
        if getattr(campaign, "selection", None) is not None:
            metadata["selection"] = list(campaign.selection)
        return result
    except BaseException as error:
        metadata.update(status="failed", error=repr(error))
        alerts.emit(campaign, "runner failed", campaign.path("runner.json"))
        raise
    finally:
        metadata.update(heartbeat_at=time.time(), finished_at=time.time())
        health.write(campaign.path("runner.json"), metadata)


def _run(campaign, interval, metadata):
    """@planks("When the operator runs the research command")"""
    futures = {}
    interrupted = {"n": 0}

    def on_int(*_):
        interrupted["n"] += 1
        if interrupted["n"] == 1:
            request_stop(campaign, "interrupt"); print("stop requested: draining calls in flight; Ctrl-C again to abort")
        else:
            os._exit(130)

    previous = signal.signal(signal.SIGINT, on_int)
    try:
        with ThreadPoolExecutor(campaign.seats) as ex:
            _loop(campaign, ex, interval, futures, metadata)
    finally:
        signal.signal(signal.SIGINT, previous)
    blocked = _blocked(campaign)
    if blocked:
        print(f"blocked investigations require reconcile: {', '.join(blocked)}")
        alerts.emit(campaign, "research blocked", campaign.path("threads"))
    return 1 if unhealthy(campaign) or blocked else 0


def _blocked(campaign) -> list[str]:
    """BLOCKED pairs in scope: the whole shortlist, or only the selection of a bounded run."""
    selection = getattr(campaign, "selection", None)
    return [p["pair_id"] for p in json.loads(campaign.path("shortlist.json").read_text())["pairs"]
            if (selection is None or p["pair_id"] in selection)
            and research.status(campaign, p["pair_id"]).get("status") == "BLOCKED"]


def _loop(campaign, ex, interval, futures, metadata):
    """@planks("When the operator requests a stop")"""
    while True:
        metadata.update(heartbeat_at=time.time(), active_pairs=list(futures.values()),
                        status="draining" if stopped(campaign) or unhealthy(campaign) else "running")
        health.write(campaign.path("runner.json"), metadata)
        queue = [] if (stopped(campaign) or unhealthy(campaign)) else pending(campaign)
        for pair_id in queue:
            if len(futures) >= campaign.seats:
                break
            if pair_id in futures.values():
                continue
            if not guard_ok(campaign, inflight=len(futures) + 1):
                break
            futures[ex.submit(_work, campaign, pair_id)] = pair_id
            print(f"{_now()} admitted {pair_id} ({len(futures)}/{campaign.seats} seats)")
        if not futures:
            if stopped(campaign) or unhealthy(campaign) or not pending(campaign):
                done = "selected pairs finished research and edit" if getattr(campaign, "selection", None) is not None else "all threads terminal"
                print("failure: inspect `pathfinder health`" if unhealthy(campaign) else "stopped" if stopped(campaign) else done); return
            time.sleep(interval); continue
        done, _ = wait(list(futures), timeout=interval, return_when=FIRST_COMPLETED)
        for f in done:
            pair_id = futures.pop(f)
            try:
                result = f.result()
                print(f"{_now()} {pair_id}: {result}")
                from . import edit
                if result in research.TERMINAL and edit.status(campaign, pair_id).get("status") == "done":
                    metadata["last_progress"] = {"pair": pair_id, "result": result, "at": _now()}
            except Refused as e:
                print(f"{_now()} {pair_id}: refused ({e}); stopping")
                if not stopped(campaign):
                    request_stop(campaign, f"refused: {e}")
            except Exception as e:
                print(f"{_now()} {pair_id}: error {e!r}")
                failure = {"run_id": campaign.run_id, "at": _now(), "pair": pair_id,
                           "stage": getattr(e, "stage", None), "reason": repr(e),
                           "receipts": "receipts.jsonl"}
                with campaign.path("failures.jsonl").open("a") as stream:
                    stream.write(json.dumps(failure) + "\n")
                if not unhealthy(campaign):
                    health.write(campaign.path("health.json"), failure)
                    alerts.emit(campaign, "runner stage failed", campaign.path("health.json"))


PAPER_DONE = {"ACCEPTED", "PAUSE-ON-AMEND"}
STAGE_SETS = {("research", "edit"), ("research", "edit", "paper")}


def pair_complete(campaign, pair_id, stages=("research", "edit", "paper")) -> bool:
    """Complete over the requested stages: research terminal and edit done; with paper, also either research
    is not DRAFT or the paper is ACCEPTED or PAUSE-ON-AMEND."""
    from . import edit, paper
    if research.status(campaign, pair_id).get("status") not in research.TERMINAL:
        return False
    if edit.status(campaign, pair_id).get("status") != "done":
        return False
    if "paper" in stages and research.status(campaign, pair_id).get("status") == "DRAFT":
        return paper.status(campaign, pair_id).get("status") in PAPER_DONE
    return True


def run_pair(campaign, pair_id: str, stages=("research", "edit", "paper"), interval: float = 5.0,
             accept_change: str | None = None, links: dict | None = None) -> dict:
    """One shortlisted pair through the requested stages, resuming where it stands: research and edit as a
    bounded run, then, for a DRAFT, the paper under campaign ownership and the thread lock. Returns each
    stage's status and the research run's exit code."""
    from . import edit, paper
    stages = tuple(stages)
    if stages not in STAGE_SETS:
        raise ValueError(f"stages must be one of {sorted(STAGE_SETS)}, got {stages}")
    _validate_selection(campaign, [pair_id])       # always, before any completion shortcut or paper resume
    from . import provenance
    with provenance.run_context(campaign, accept_change, links):   # one run for research, edit and paper; may refuse
        return _run_pair(campaign, pair_id, stages, interval)


def _run_pair(campaign, pair_id, stages, interval) -> dict:
    from . import edit, paper
    code = 0
    if not pair_complete(campaign, pair_id, ("research", "edit")):
        code = run(campaign, interval=interval, pairs=[pair_id])
    out = {"code": code, "research": research.status(campaign, pair_id).get("status"),
           "edit": edit.status(campaign, pair_id).get("status"), "paper": paper.status(campaign, pair_id).get("status")}
    def paper_due():
        return (research.status(campaign, pair_id).get("status") == "DRAFT"
                and edit.status(campaign, pair_id).get("status") == "done"
                and paper.status(campaign, pair_id).get("status") not in PAPER_DONE
                and not stopped(campaign) and not unhealthy(campaign))
    if "paper" in stages and code == 0 and paper_due():
        with health.owner(campaign, nested=True), Lock(campaign.thread_dir(pair_id)):
            if paper_due():                          # re-read under ownership: state may have moved meanwhile
                out["paper"] = paper.run(campaign, pair_id, stop=lambda: stopped(campaign) or unhealthy(campaign))
            else:
                out["paper"] = paper.status(campaign, pair_id).get("status")
    out["complete"] = pair_complete(campaign, pair_id, stages)
    return out
