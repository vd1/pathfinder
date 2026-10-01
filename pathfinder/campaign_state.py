"""The campaign state document: what the operator's page and the apex agent read.

Derived, never authoritative: status files say where each unit stands, receipts what was spent, events
when things happened. Research, editorial and assessment states stay separate, so "DRAFT" research with
a blocked edit reads as both. A cut event stream makes progress "unknown" rather than inferred."""
from __future__ import annotations
import calendar, json, os, time
from collections import Counter
from pathlib import Path
from . import edit, events, paper, research, transport

ACTIVE_SECONDS = 600                       # an event this recent means the campaign is active
DOCUMENTS = (("research note", "{u}.tex", "{u}.pdf"), ("readable note", "edited/note.tex", "edited/note.pdf"),
             ("paper", "paper/paper.tex", "paper/paper.pdf"))


def _json(path: Path):
    try:
        return json.loads(path.read_text()) if path.is_file() else None
    except (ValueError, OSError):
        return None


def _scores(campaign) -> dict:
    out = {}
    path = campaign.path("scan.jsonl")
    for line in (path.read_text().splitlines() if path.is_file() else []):
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("feasibility") is not None and row.get("gain") is not None:
            out[row["pair_id"]] = row["feasibility"] * row["gain"]
    return out


def _documents(campaign, unit: str) -> list[dict]:
    d, out = campaign.thread_dir(unit), []
    for kind, source, pdf in DOCUMENTS:
        src, out_pdf = d / source.format(u=unit), d / pdf.format(u=unit)
        if not src.is_file() and not out_pdf.is_file():
            continue
        rel = lambda p: str(p.relative_to(campaign.root)) if p.is_file() else None
        stale = bool(src.is_file() and out_pdf.is_file() and out_pdf.stat().st_mtime < src.stat().st_mtime)
        out.append({"kind": kind, "pdf": rel(out_pdf), "source": rel(src), "stale": stale})
    return out


IN_PROGRESS = {"running", "editing", "writing", "reviewing"}


def _block_key(doc: dict) -> tuple[str, str]:
    """(class, cause): the class only from a structured failure the stage recorded, never from prose."""
    reason = doc.get("reason") or ""
    cause = reason.split(":")[0].strip() if ":" in reason else (reason or "unknown")
    return (doc.get("failure") or {}).get("class") or "undiagnosed", cause


def _controller(research_s: dict, edit_s: dict, paper_s: dict, active: set, seated: set, runner_alive: bool, unit: str) -> str:
    if unit in active or (runner_alive and unit in seated):
        return "running"
    states = (research_s.get("status"), edit_s.get("status"), paper_s.get("status"))
    if "BLOCKED" in states or "blocked" in states:
        return "blocked"
    if "stopped" in states:
        return "stopped"
    if any(s in IN_PROGRESS for s in states):
        return "orphaned"                         # recorded as in progress, but no live runner or call holds it
    if research_s.get("status") in research.TERMINAL and edit_s.get("status") == "done":
        return "done"
    if research_s.get("status") in research.TERMINAL:
        return "queued"
    return "new" if research_s.get("status", "new") == "new" else "waiting"


def _runner(campaign) -> dict:
    from . import health
    meta = _json(campaign.path("runner.json")) or {}
    if not meta:
        return {"status": None, "pid_alive": None, "heartbeat_age_seconds": None, "active_pairs": []}
    beat = meta.get("heartbeat_at")
    return {"status": meta.get("status"), "pid_alive": health.alive(meta.get("pid")),
            "heartbeat_age_seconds": round(time.time() - beat, 1) if beat else None,
            "active_pairs": list(meta.get("active_pairs") or [])}


def build(campaign) -> dict:
    rows, truncated, corrupt = events.scan(campaign)
    runner_info = _runner(campaign)
    runner_alive = bool(runner_info["pid_alive"]) and runner_info["status"] in ("running", "draining")
    receipts = transport.receipts(campaign)
    shortlist = (_json(campaign.path("shortlist.json")) or {}).get("pairs", [])
    scores = _scores(campaign)
    active = set()
    for path in sorted(campaign.path("active-calls").glob("*.json")) if campaign.path("active-calls").is_dir() else []:
        call = _json(path) or {}
        if call.get("thread"):
            active.add(call["thread"])
    last_by_unit = {}
    for row in rows:
        if row.get("unit"):
            last_by_unit[row["unit"]] = row.get("at")
    units, stages, blocks = [], {"research": Counter(), "edit": Counter(), "paper": Counter()}, {}
    for pair in shortlist:
        unit = pair["pair_id"]
        r_s = research.status(campaign, unit)
        d = campaign.thread_dir(unit)
        e_s = edit.status(campaign, unit) if (d / "edited" / "edit.json").exists() else {}
        p_s = paper.status(campaign, unit) if (d / "paper" / "paper.json").exists() else {}
        stages["research"][r_s.get("status", "new")] += 1
        if e_s:
            stages["edit"][e_s.get("status")] += 1
        elif r_s.get("status") in research.TERMINAL:
            stages["edit"]["queued"] += 1
        if p_s:
            stages["paper"][p_s.get("status")] += 1
        elif r_s.get("status") == "DRAFT" and e_s.get("status") == "done":
            stages["paper"]["queued"] += 1
        for status_doc in (r_s, e_s, p_s):
            if status_doc.get("status") in ("BLOCKED", "blocked"):
                blocks.setdefault(_block_key(status_doc), []).append(unit)
        units.append({"unit": unit, "score": scores.get(unit),
                      "research": {k: r_s.get(k) for k in ("status", "stage", "round", "reason")},
                      "editorial": {"status": e_s.get("status"), "reason": e_s.get("reason")},
                      "assessment": {"status": p_s.get("status"), "reason": p_s.get("reason")},
                      "controller": _controller(r_s, e_s, p_s, active, set(runner_info["active_pairs"]), runner_alive, unit),
                      "last_activity": last_by_unit.get(unit), "documents": _documents(campaign, unit)})
    stamps = [row["at"] for row in rows if isinstance(row.get("at"), str)]
    last = stamps[-1] if stamps else None
    try:
        age = (time.time() - calendar.timegm(time.strptime(last, "%Y-%m-%dT%H:%M:%SZ"))) if last else None
    except ValueError:
        age = None
    progress = ("unknown" if truncated else "active" if (active or runner_alive)
                else "recent" if (age is not None and age < ACTIVE_SECONDS) else "idle")
    run = _json(campaign.path("run.json")) or {}
    raw = campaign.raw or {}
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "campaign": {"name": campaign.root.name, "backend": campaign.backend, "model": campaign.model,
                     "seats": campaign.seats, "rounds": campaign.rounds, "allowances": campaign.allowances,
                     "research_scheme": raw.get("research_scheme", "eva"),
                     "budget": {"calls": len(receipts),
                                "input_tokens": sum(r.get("input_tokens") or 0 for r in receipts),
                                "output_tokens": sum(r.get("output_tokens") or 0 for r in receipts),
                                "cache_read": sum(r.get("cache_read") or 0 for r in receipts)},
                     "execution_id": run.get("execution_id"), "stop": _json(campaign.path("stop.json"))},
        "progress": {"status": progress, "last_event_at": last, "events_truncated": truncated, "events_corrupt": corrupt},
        "runner": runner_info,
        "stages": {name: dict(counts) for name, counts in stages.items()},
        "blocks": [{"class": cls, "cause": cause, "units": sorted(set(us)), "count": len(us)}
                   for (cls, cause), us in sorted(blocks.items(), key=lambda kv: -len(kv[1]))],
        "units": units,
    }


def write(campaign) -> Path:
    path = campaign.path("state.json")
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(build(campaign), indent=1, default=str))
    os.replace(temporary, path)
    return path


def text(state: dict) -> str:
    c, p = state["campaign"], state["progress"]
    lines = [f"{c['name']}  {c['backend']}/{c['model']}  scheme {c['research_scheme']}  execution {str(c['execution_id'])[:12]}",
             f"progress {p['status']}" + (f"  last event {p['last_event_at']}" if p["last_event_at"] else "")
             + ("  (event stream cut: read the full record before trusting progress)" if p["events_truncated"] else "")
             + (f"  ({p['events_corrupt']} unreadable event line{'s' if p['events_corrupt'] != 1 else ''} skipped)" if p.get("events_corrupt") else ""),
             f"budget {c['budget']['calls']} calls, {c['budget']['input_tokens']} input tokens "
             f"({c['budget']['cache_read']} cached), {c['budget']['output_tokens']} output",
             "stages " + "; ".join(f"{name}: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
                                    for name, counts in state["stages"].items() if counts)]
    if c["stop"]:
        lines.append(f"stopped: {c['stop'].get('reason')}")
    for block in state["blocks"]:
        lines.append(f"block {block['class']}: {block['cause']} x{block['count']} ({', '.join(block['units'])})")
    for u in state["units"]:
        lines.append(f"{u['unit']:>8} score {u['score'] if u['score'] is not None else '-':>4}  {u['controller']:<8} "
                     f"research {u['research']['status']}  edit {u['editorial']['status']}  paper {u['assessment']['status']}")
    return "\n".join(lines)
