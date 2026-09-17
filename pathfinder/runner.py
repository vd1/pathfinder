"""The research loop: seats, rolling admission, budget guard, stop as a drain, health flag."""
from __future__ import annotations
import copy, hashlib, json, os, signal, time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from pathlib import Path
from . import research, transport
from . import corpus


PROBE_INTERVAL = 60


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
    """
    required = {"model", "backend", "execution_class", "prompt", "tool_policy", "budget"}
    for role in ("scan", "research", "consolidate", "verify"):
        if required - manifest["assignments"][role].keys():
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
    """
    return "openai-compatible" if assignment["backend"] == "elm" else assignment["backend"]


def execution_receipt(role, backend, model, execution_class, prompt_digest, provider_job_id, raw_response, outcome, latency, token_usage, cost):
    """@planks("When the execution finishes")
    @planks("When the same assignment is repeated")
    """
    return dict(role=role, backend=backend, model=model, execution_class=execution_class, prompt_digest=prompt_digest,
                provider_job_id=provider_job_id, raw_response=raw_response, outcome=outcome, latency=latency,
                token_usage=token_usage, cost=cost)


def run_assigned_comparison(campaign, assignments: dict) -> dict:
    """@planks("When Pathfinder runs the assigned comparison workflow")
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
    return campaign.path("stop.json").exists()


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
    """@planks("When Pathfinder admits pending investigations")
    @planks("When the operator runs the research command")
    """
    pairs = [p["pair_id"] for p in json.loads(campaign.path("shortlist.json").read_text())["pairs"]]
    return [p for p in pairs if research.status(campaign, p).get("status") not in research.TERMINAL | {"BLOCKED"}
            and not Lock.holder(campaign.thread_dir(p))]          # BLOCKED waits for reconcile, never re-admission


def _work(campaign, pair_id):
    with Lock(campaign.thread_dir(pair_id)):
        result = research.run_thread(campaign, pair_id, stop=lambda: stopped(campaign))
        if result in research.TERMINAL and not stopped(campaign):
            from . import edit                      # the readable account, written once the verdict is final
            try:
                edit.run(campaign, pair_id, stop=lambda: stopped(campaign))
            except transport.TransportFailed:
                print(f"{_now()} {pair_id}: editor transport failure; run `pathfinder edit {pair_id}` later")
        return result


def _probe(campaign) -> bool:
    r = transport.call("Reply with the single word ok.", campaign=campaign, model=campaign.model, tools=False, search=False,
                       cwd=campaign.path("scan-work"), timeout=120, thread="probe", stage="probe", actor="probe")
    return not r["transport_failed"]


def run(campaign, interval: float = 5.0):
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
            _loop(campaign, ex, interval, futures)
    finally:
        signal.signal(signal.SIGINT, previous)
    blocked = [p["pair_id"] for p in json.loads(campaign.path("shortlist.json").read_text())["pairs"]
               if research.status(campaign, p["pair_id"]).get("status") == "BLOCKED"]
    if blocked:
        print(f"blocked investigations require reconcile: {', '.join(blocked)}")


def _loop(campaign, ex, interval, futures):
    """@planks("When the operator requests a stop")"""
    failures = 0
    while True:
        if unhealthy(campaign) and not futures:
            if _probe(campaign):
                campaign.path("health.json").unlink(); failures = 0; print("health restored")
            else:
                time.sleep(PROBE_INTERVAL); continue
        queue = [] if (stopped(campaign) or unhealthy(campaign)) else pending(campaign)
        for pair_id in queue:
            if len(futures) >= campaign.seats or pair_id in futures.values():
                break
            if not guard_ok(campaign, inflight=len(futures) + 1):
                break
            futures[ex.submit(_work, campaign, pair_id)] = pair_id
            print(f"{_now()} admitted {pair_id} ({len(futures)}/{campaign.seats} seats)")
        if not futures:
            if stopped(campaign) or not pending(campaign):
                print("stopped" if stopped(campaign) else "all threads terminal"); return
            time.sleep(interval); continue
        done, _ = wait(list(futures), timeout=interval, return_when=FIRST_COMPLETED)
        for f in done:
            pair_id = futures.pop(f)
            try:
                print(f"{_now()} {pair_id}: {f.result()}"); failures = 0
            except transport.TransportFailed:
                failures += 1; print(f"{_now()} {pair_id}: transport failure ({failures})")
                if failures >= 2 and not unhealthy(campaign):
                    campaign.path("health.json").write_text(json.dumps({"at": _now(), "reason": "two consecutive transport failures"}))
                    print("health flag set: admissions paused until a probe call succeeds")
            except Exception as e:
                print(f"{_now()} {pair_id}: error {e!r}")
