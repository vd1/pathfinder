"""A fixed schedule of (arm, pair) entries across child campaigns, one pair at a time.

    schedule.json, in the parent directory:
    {"arms": {"repeat": "repeat", "reinjection": "reinjection"},
     "stages": ["research", "edit", "paper"],
     "schedule": [{"arm": "repeat", "pair": "Q1P1"}, {"arm": "reinjection", "pair": "Q1P1"}, ...]}

Each arm is a campaign whose campaign.json sets "parent" to the path of the parent directory, so the
parent's stop marker stops its calls. The coordinator owns the parent (runner.lock there), writes a
heartbeat to runner.json, and runs each entry with runner.run_pair, which resumes where the pair stands.
Semantics, as the repeat and reinjection pilot established them:

- resume: a completed entry, accepted paper included, is skipped; the schedule's order is kept;
- a budget stop in one arm censors that arm and the others continue;
- a stop on the parent, or an operator stop in an arm, halts everything;
- a research, edit or paper failure stops before the next entry;
- progress.json after every entry, outcomes.json at the end, status complete, censored, stopped or failed.

An optional "batch" block bounds the run: {"deadline": "<ISO UTC>", "max_units": n, "max_consecutive_failures": k}.
The deadline and the unit limit stop admitting entries (status deadline or unit limit) and never interrupt the
entry in flight; with k set, a failed entry is recorded in failed_entries and the next one runs, and k failed
entries in a row fail the coordination. Without the block the first failure fails it, as before."""
from __future__ import annotations
import json, os, threading, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from . import config, edit, health, paper, research, runner


class CoordinatorStopped(RuntimeError):
    pass


def _read(path: Path):
    return json.loads(path.read_text()) if path.exists() else {}


def _parent(root: Path):
    return SimpleNamespace(root=root, raw={}, path=lambda name: root / name)


def load(schedule_path: Path) -> tuple[SimpleNamespace, dict, dict]:
    """(parent, arms as campaigns, schedule), after checking every arm names the parent as its parent."""
    schedule_path = Path(schedule_path).resolve()
    root = schedule_path.parent
    schedule = json.loads(schedule_path.read_text())
    arms = {}
    for name, rel in schedule["arms"].items():
        c = config.load(root / rel)
        declared = (c.raw or {}).get("parent")
        if not declared or (Path(c.root) / declared).resolve() != root:
            raise ValueError(f"arm {name}: campaign.json must set parent to {os.path.relpath(root, c.root)}")
        arms[name] = c
    seen = set()
    for entry in schedule["schedule"]:
        if entry["arm"] not in arms:
            raise ValueError(f"schedule names unknown arm {entry['arm']}")
        key = (entry["arm"], entry["pair"])
        if key in seen:
            raise ValueError(f"schedule repeats {key}")
        seen.add(key)
        shortlist = {p["pair_id"] for p in json.loads(arms[entry["arm"]].path("shortlist.json").read_text())["pairs"]}
        if entry["pair"] not in shortlist:              # checked before any dispatch, not when the entry is reached
            raise ValueError(f"{entry['pair']} is not on the shortlist of arm {entry['arm']}")
    stages = tuple(schedule.get("stages") or ("research", "edit", "paper"))
    if stages not in runner.STAGE_SETS:
        raise ValueError(f"stages must be one of {sorted(runner.STAGE_SETS)}")
    return _parent(root), arms, {**schedule, "stages": stages}


def _budget_stop(campaign) -> bool:
    return "budget:" in str(_read(campaign.path("stop.json")).get("reason"))


def outcomes(arms, schedule) -> dict:
    return {a: {e["pair"]: {"research": research.status(c, e["pair"]), "editor": edit.status(c, e["pair"]),
                            "paper": paper.status(c, e["pair"])}
                for e in schedule["schedule"] if e["arm"] == a}
            for a, c in arms.items()}


class ScheduleChanged(RuntimeError):
    """The schedule differs from the previous coordination's and the change was not accepted."""


def normalized(parent, arms, schedule) -> dict:
    return {"arms": {name: os.path.relpath(c.root, parent.root) for name, c in sorted(arms.items())},
            "stages": list(schedule["stages"]),
            "schedule": [{"arm": e["arm"], "pair": e["pair"]} for e in schedule["schedule"]]}


def start_coordination(parent, arms, schedule, accept_change=None) -> dict:
    """Bind this coordination to its normalized schedule: coordination.json and coordinations.jsonl in the
    parent. A schedule that differs from the previous coordination's is refused unless accepted."""
    import hashlib
    norm = normalized(parent, arms, schedule)
    digest = hashlib.sha256(json.dumps(norm, sort_keys=True).encode()).hexdigest()
    previous = _read(parent.path("coordination.json")) or None
    rec = {"coordination_id": uuid.uuid4().hex, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "schedule_sha256": digest, "schedule": norm}
    if previous:
        rec["previous_coordination_id"] = previous.get("coordination_id")
        if previous.get("schedule_sha256") != digest:
            if not accept_change:
                raise ScheduleChanged("the schedule changed since the previous coordination (see coordination.json);"
                                      " rerun with --accept-change REASON to start a linked coordination")
            rec["accepted_change"] = {"components": ["schedule"], "reason": accept_change}
    health.write(parent.path("coordination.json"), rec)
    with parent.path("coordinations.jsonl").open("a") as stream:
        stream.write(json.dumps(rec) + "\n")
    return rec


def run(schedule_path: Path, interval: float = 5.0, heartbeat: float = 5.0, accept_change: str | None = None) -> dict:
    """accept_change covers a changed schedule and changed child run records in this coordination."""
    parent, arms, schedule = load(schedule_path)
    batch = schedule.get("batch") or {}
    deadline = None
    if batch.get("deadline"):
        moment = datetime.fromisoformat(batch["deadline"].replace("Z", "+00:00"))
        deadline = (moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)).timestamp()   # naive means UTC
    tolerance = batch.get("max_consecutive_failures")
    state = {"pid": os.getpid(), "run_id": uuid.uuid4().hex, "status": "running", "started_at": time.time(),
             "heartbeat_at": time.time(), "last_progress": None, "censored_arms": [],
             "units_started": 0, "failed_entries": [], "consecutive_failures": 0}
    ended = None                                  # deadline or unit limit
    stop_beating = threading.Event()

    def beat():
        while not stop_beating.is_set():
            health.write(parent.path("runner.json"), dict(state, heartbeat_at=time.time()))
            stop_beating.wait(heartbeat)

    with health.owner(parent):
        coordination = start_coordination(parent, arms, schedule, accept_change)
        state["coordination_id"] = coordination["coordination_id"]
        link = {"coordination_id": coordination["coordination_id"], "parent": str(parent.root)}
        thread = threading.Thread(target=beat, daemon=True); thread.start()
        try:
            for entry in schedule["schedule"]:
                c, pair = arms[entry["arm"]], entry["pair"]
                finished = bool(batch) and runner.pair_complete(c, pair, schedule["stages"])   # resumed: not a new unit
                if not finished and deadline is not None and time.time() >= deadline:
                    ended = "deadline"; break
                if not finished and batch.get("max_units") is not None and state["units_started"] >= batch["max_units"]:
                    ended = "unit limit"; break
                if runner.stopped(parent):
                    raise CoordinatorStopped("parent stop marker exists")
                if runner.stopped(c):
                    if _budget_stop(c):
                        if entry["arm"] not in state["censored_arms"]:
                            state["censored_arms"].append(entry["arm"])
                        continue
                    raise CoordinatorStopped(f"operator stop in arm {entry['arm']}")
                state.update(entry=entry, stage="pair")
                state["units_started"] += 0 if finished else 1
                out = runner.run_pair(c, pair, stages=schedule["stages"], interval=interval,
                                      accept_change=accept_change, links={"coordination": link})
                if runner.stopped(c) and not runner.stopped(parent) and _budget_stop(c):
                    if entry["arm"] not in state["censored_arms"]:
                        state["censored_arms"].append(entry["arm"])
                    continue
                if runner.stopped(parent):
                    raise CoordinatorStopped("parent stop marker exists")
                if runner.stopped(c):
                    raise CoordinatorStopped(f"operator stop in arm {entry['arm']}")
                problem = None
                if out["code"]:
                    problem = f"research or edit failed: {entry}: {out}"
                elif not out["complete"]:
                    stage = "paper" if out["edit"] == "done" and out["research"] in research.TERMINAL else "research or edit"
                    problem = f"{stage} incomplete: {entry}: {out}"
                if problem:
                    state["consecutive_failures"] += 1
                    if not tolerance or state["consecutive_failures"] >= tolerance:
                        raise RuntimeError(problem)
                    # tolerated: the arm's health flag belongs to this entry, so it is recorded here and cleared,
                    # or the arm's later entries (a paper-only resume) would silently refuse to start
                    flag = _read(c.path("health.json")) or None
                    c.path("health.json").unlink(missing_ok=True)
                    state["failed_entries"].append({"entry": entry, "error": problem, "at": time.time(), "health": flag})
                    health.write(parent.path("progress.json"), state)
                    continue
                state["consecutive_failures"] = 0
                state.update(last_progress=dict(entry, at=time.time()), stage="between-pairs")
                health.write(parent.path("progress.json"), state)
            state["status"] = ended or ("censored" if state["censored_arms"] else "complete")
        except CoordinatorStopped as stop:
            state.update(status="stopped", reason=str(stop))
        except BaseException as error:
            state.update(status="failed", error=repr(error))
            raise
        finally:
            stop_beating.set(); thread.join()
            state.update(heartbeat_at=time.time(), finished_at=time.time())
            health.write(parent.path("runner.json"), state)
            health.write(parent.path("progress.json"), state)
            health.write(parent.path("outcomes.json"), outcomes(arms, schedule))
    return state


def snapshot(schedule_path: Path) -> dict:
    """The parent's runner and progress records with every arm's health snapshot under arms."""
    parent, arms, schedule = load(schedule_path)
    return {"parent": str(parent.root), "runner": _read(parent.path("runner.json")),
            "progress": _read(parent.path("progress.json")), "stop": _read(parent.path("stop.json")) or None,
            "arms": {name: health.snapshot(c) for name, c in arms.items()},
            "schedule_length": len(schedule["schedule"])}
