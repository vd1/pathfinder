"""The research loop: seats, rolling admission, budget guard, stop as a drain, health flag."""
from __future__ import annotations
import json, os, signal, time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from pathlib import Path
from . import research, transport


PROBE_INTERVAL = 60


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
    pairs = [p["pair_id"] for p in json.loads(campaign.path("shortlist.json").read_text())["pairs"]]
    return [p for p in pairs if research.status(campaign, p).get("status") not in research.TERMINAL
            and not Lock.holder(campaign.thread_dir(p))]


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


def _loop(campaign, ex, interval, futures):
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
