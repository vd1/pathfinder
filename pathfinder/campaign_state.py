"""The campaign state document: what the operator's page and the apex agent read.

Derived, never authoritative: status files say where each unit stands, receipts what was spent, events
when things happened. Research, editorial and assessment states stay separate, so "DRAFT" research with
a blocked edit reads as both. A cut event stream makes progress "unknown" rather than inferred."""
from __future__ import annotations
import calendar, json, os, re, time
from collections import Counter
from pathlib import Path
from . import actionability, budget, admission, edit, events, paper, research, transport

ACTIVE_SECONDS = 600                       # an event this recent means the campaign is active
DOCUMENTS = (("research note", "{u}.tex", "{u}.pdf"), ("readable note", "edited/note.tex", "edited/note.pdf"),
             ("paper", "paper/paper.tex", "paper/paper.pdf"))


def _json(path: Path):
    try:
        return json.loads(path.read_text()) if path.is_file() else None
    except (ValueError, OSError):
        return None


def _scan(campaign) -> dict:
    """The scan row per pair (feasibility, gain, connexion, rationale)."""
    out = {}
    path = campaign.path("scan.jsonl")
    for line in (path.read_text().splitlines() if path.is_file() else []):
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("pair_id"):
            out[row["pair_id"]] = row
    return out


def _corpus(campaign, side: str) -> list[dict]:
    path = campaign.path(f"{side}.jsonl")
    rows = []
    for line in (path.read_text().splitlines() if path.is_file() else []):
        try:
            row = json.loads(line)
        except ValueError:
            row = {}
        rows.append(row if isinstance(row, dict) else {})
    return rows


def _paper(rows: list[dict], index: int) -> dict:
    row = rows[index - 1] if 0 < index <= len(rows) else {}
    return {"id": row.get("id"), "title": row.get("title"), "abstract": row.get("abstract")}


def _summary(campaign, unit: str, research_s: dict) -> str | None:
    verdicts = _json(campaign.thread_dir(unit) / f"{unit}.verdict.json") or []
    if isinstance(verdicts, list) and verdicts and isinstance(verdicts[-1], dict) and verdicts[-1].get("reason"):
        return verdicts[-1]["reason"]
    return research_s.get("reason")


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


PIPELINE = [
    ("Selected", [("waiting", "Waiting")]),
    ("Research", [("researching", "In progress"), ("stopped", "Stopped"), ("orphaned", "Orphaned")]),
    ("Outcome", [("draft", "DRAFT"), ("pause", "Paused"), ("handoff", "Handed off"), ("blocked", "Blocked")]),
    ("Readable note", [("editing", "Editing"), ("noted", "Note ready"), ("note-blocked", "Note blocked")]),
    ("Paper", [("writing", "Writing"), ("accepted", "Accepted"), ("amend", "Amendments asked"), ("paper-blocked", "Paper blocked")]),
]


def lifecycle(research_s: dict, edit_s: dict, paper_s: dict, controller: str) -> str:
    """The unit's single pipeline position: the furthest stage it has reached, then that stage's state."""
    p, e, r = paper_s.get("status"), edit_s.get("status"), research_s.get("status", "new")
    if p:
        return {"ACCEPTED": "accepted", "PAUSE-ON-AMEND": "amend", "blocked": "paper-blocked",
                "stopped": "paper-blocked"}.get(p, "writing")
    if e and e != "none":
        return {"done": "noted", "blocked": "note-blocked", "stopped": "note-blocked"}.get(e, "editing")
    if r in research.TERMINAL:
        return "draft" if r == "DRAFT" else "pause"
    if r == "BLOCKED":
        return "blocked"
    if r == "HANDOFF":
        return "handoff"
    if r == "new":
        return "waiting"
    return {"running": "researching", "orphaned": "orphaned"}.get(controller, "stopped")


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


def _branches(campaign, unit) -> list[dict]:
    """A composable pair's branches, each with where its direct-EVA research stands."""
    from . import composable
    out = []
    for label in composable.labels(campaign):
        b = research.status(composable.branch_view(campaign, unit, label), unit)
        out.append({"label": label, **{k: b.get(k) for k in ("status", "stage", "round", "reviews", "handoff_reason", "reason")}})
    return out


def _account(campaign) -> dict | None:
    """The shared account the campaign draws its seats from, with the seats in use across processes."""
    from . import seats
    try:
        spec = seats.account(campaign)
    except ValueError as error:
        return {"error": str(error)}
    return {"name": spec["name"], "seats": spec["seats"], "in_use": seats.in_use(campaign)} if spec else None


PANEL_KINDS = {   # kind -> the list field it must carry; rendered in the page's own designs
    "table": "rows", "cards": "cards", "metrics": "items", "pipeline": "stages"}


def _panels(campaign) -> list[dict]:
    """A deployment's own content for the operator page (extension "panels": panels(campaign) returning a list).
    Each panel has a title and a kind, drawn in the page's own designs: "table" (columns, rows), "cards"
    (cards of status, badge, meta, title, summary, issue, actions; "grid" for a card grid), "metrics" (items
    of label, value, small) or "pipeline" (stages of title and states of key, label, count). A failing
    extension is one panel that says so; the core state never fails over it."""
    from . import extensions
    try:
        make = extensions.load(campaign, "panels")
        if make is None:
            return []
        out = []
        for p in make(campaign):
            kind = p.get("kind", "table") if isinstance(p, dict) else None
            field = PANEL_KINDS.get(kind)
            if field is None or not isinstance(p.get(field), list) or (kind == "table" and not isinstance(p.get("columns"), list)):
                raise TypeError(f"a panel needs a title and a known kind with its list ({', '.join(PANEL_KINDS)}): {str(p)[:200]}")
            out.append({**p, "kind": kind, "title": str(p.get("title") or "Panel")})
        return json.loads(json.dumps(out, default=str))
    except Exception as error:
        return [{"kind": "table", "title": "Deployment panels", "columns": [], "rows": [], "note": f"panels failed: {error!r}"}]


def build(campaign) -> dict:
    rows, truncated, corrupt = events.scan(campaign)
    runner_info = _runner(campaign)
    runner_alive = bool(runner_info["pid_alive"]) and runner_info["status"] in ("running", "draining")
    receipts = transport.receipts(campaign)
    shortlist = (_json(campaign.path("shortlist.json")) or {}).get("pairs", [])
    scan = _scan(campaign)
    Q, P = _corpus(campaign, "Q"), _corpus(campaign, "P")
    per_unit = {}
    for r in receipts:
        u = per_unit.setdefault(r.get("thread"), {"calls": 0, "input_tokens": 0, "output_tokens": 0, "seconds": 0.0})
        u["calls"] += 1
        u["input_tokens"] += r.get("input_tokens") or 0
        u["output_tokens"] += r.get("output_tokens") or 0
        u["seconds"] += r.get("seconds") or 0
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
        controller = _controller(r_s, e_s, p_s, active, set(runner_info["active_pairs"]), runner_alive, unit)
        row = scan.get(unit, {})
        f, g = row.get("feasibility"), row.get("gain")
        match = re.fullmatch(r"Q(\d+)P(\d+)", unit)
        q, p = (_paper(Q, int(match.group(1))), _paper(P, int(match.group(2)))) if match else ({}, {})
        units.append({"unit": unit, "score": f * g if f is not None and g is not None else None,
                      "feasibility": f, "gain": g, "connexion": row.get("connexion"), "q": q, "p": p,
                      "summary": _summary(campaign, unit, r_s),
                      "usage": per_unit.get(unit, {"calls": 0, "input_tokens": 0, "output_tokens": 0, "seconds": 0.0}),
                      "research": {k: r_s.get(k) for k in ("status", "stage", "round", "reason")},
                      "editorial": {"status": e_s.get("status"), "reason": e_s.get("reason")},
                      "assessment": {"status": p_s.get("status"), "reason": p_s.get("reason")},
                      **({"actionability": {k: a_s.get(k) for k in ("status", "decision", "reason")}}
                         if (a_s := actionability.status(campaign, unit)).get("status") != "none" else {}),
                      "controller": controller, "lifecycle": lifecycle(r_s, e_s, p_s, controller),
                      "last_activity": last_by_unit.get(unit), "documents": _documents(campaign, unit),
                      **({"branches": _branches(campaign, unit)} if campaign.raw.get("research_scheme") == "composable" else {})})
    counts = Counter(u["lifecycle"] for u in units)
    pipeline = [{"title": title, "count": sum(counts[k] for k, _ in states),
                 "states": [{"key": k, "label": label, "count": counts[k]} for k, label in states]}
                for title, states in PIPELINE]
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
        "panels": _panels(campaign),
        "campaign": {"name": campaign.root.name, "title": raw.get("title"), "description": raw.get("description"),
                     "backend": campaign.backend, "model": campaign.model,
                     "seats": campaign.seats, "rounds": campaign.rounds, "allowances": campaign.allowances,
                     "research_scheme": raw.get("research_scheme", "eva"),
                     "account": _account(campaign),
                     "budget": {**budget.usage(campaign), "limits": budget.limits(raw)},
                     "execution_id": run.get("execution_id"), "stop": _json(campaign.path("stop.json"))},
        "progress": {"cooldown_seconds": admission.cooldown(campaign), "status": progress, "last_event_at": last, "events_truncated": truncated, "events_corrupt": corrupt},
        "runner": runner_info,
        "stages": {name: dict(c) for name, c in stages.items()},
        "pipeline": pipeline,
        "usage": {"calls": len(receipts), "completed": sum(r.get("outcome") == "completed" for r in receipts),
                  "calls_with_usage": sum(r.get("input_tokens") is not None for r in receipts),
                  "input_tokens": sum(r.get("input_tokens") or 0 for r in receipts),
                  "cache_read": sum(r.get("cache_read") or 0 for r in receipts),
                  "output_tokens": sum(r.get("output_tokens") or 0 for r in receipts),
                  "seconds": round(sum(r.get("seconds") or 0 for r in receipts), 1)},
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
