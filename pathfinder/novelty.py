"""The novelty check (NEVA, nobel): with "novelty_stage": true, an EVA thread (the joint thread of a composable
campaign) has one more stage between consolidate and verify. A fresh call with web search and read-only tools
reads the note, the two abstracts and, if the deployment supplies one, a list of papers citing both (a file
inside the campaign, registered as a source of its pair, so a ledger entry citing it resolves), never the
ledger or the full papers, and returns a short JSON report: per result known, partly_known or new with the
closest work, the closest works the note does not cite, overclaims, and the queries run. The report goes into
verify's prompt as evidence. It is asked again only when the note has changed since the last check, and a check
that fails or cannot be read never blocks verify: the record and verify's prompt say there is no report.

    "novelty_stage": true, "novelty_citers": "sources/citers/{pair}.md",   # optional, inside the campaign
    "allowances": {"novelty_seconds": 900}, "routes": {"novelty": {...}}     # prompts/novelty.append.md overlays"""
from __future__ import annotations
import hashlib, json
from . import context, contracts, corpus
from .context import Section

SECONDS = 900


def validate(raw: dict) -> None:
    on = raw.get("novelty_stage", False)
    if type(on) is not bool:
        raise ValueError(f"novelty_stage must be true or false, got {on!r}")
    if on and raw.get("research_scheme") not in ("composable", "eva"):
        raise ValueError("novelty_stage needs research_scheme composable or eva: it runs between consolidate and verify")
    citers = raw.get("novelty_citers")
    if citers is not None and not isinstance(citers, str):
        raise ValueError(f"novelty_citers must be a path template such as 'sources/citers/{{pair}}.md', got {citers!r}")
    if isinstance(citers, str) and (citers.startswith("/") or ".." in citers.split("/")):
        raise ValueError(f"novelty_citers must name a file inside the campaign, such as 'sources/citers/{{pair}}.md', "
                         f"got {citers!r}: a path outside it cannot be cited as evidence")


def enabled(campaign) -> bool:
    return bool((campaign.raw or {}).get("novelty_stage"))


def _path(d, pair_id):
    return d / f"{pair_id}.novelty.json"


def records(d, pair_id) -> list:
    p = _path(d, pair_id)
    return json.loads(p.read_text()) if p.exists() else []


def note_sha(d, pair_id) -> str | None:
    note = d / f"{pair_id}.tex"
    return hashlib.sha256(note.read_bytes()).hexdigest() if note.exists() else None


def current(d, pair_id) -> dict | None:
    """The latest check of the note as it stands, or None when the note has changed since."""
    rec = records(d, pair_id)
    return rec[-1] if rec and rec[-1].get("note_sha256") == note_sha(d, pair_id) else None


def _abstract(campaign, pair_id, side) -> str:
    try:
        row = corpus.row_for(corpus.read(campaign.path(f"{side}.jsonl")), corpus.numbers(pair_id)["QP".index(side)])
        return f"{row.get('title', '')} ({row.get('id', '')})\n\n{row.get('abstract') or 'no abstract recorded'}"
    except Exception as error:                    # a missing row narrows the check, it does not stop it
        return f"abstract unavailable: {error}"


def prompt(campaign, pair_id, d) -> str:
    from .thread import _prompt
    template = (campaign.raw or {}).get("novelty_citers")
    citers = "no list of citers was supplied"
    if template:
        path = campaign.path(template.replace("{pair}", pair_id))
        citers = path.read_text(errors="replace") if path.is_file() else f"no list of citers at {template.replace('{pair}', pair_id)}"
    sections = [Section("Q: title and abstract", text=_abstract(campaign, pair_id, "Q")),
                Section("P: title and abstract", text=_abstract(campaign, pair_id, "P")),
                Section("papers citing both Q and P", text=citers),
                Section(f"{pair_id}.tex (the note to check)", path=d / f"{pair_id}.tex", keep=True),
                Section("your task", text=_prompt(campaign, "novelty"), keep=True)]
    return context.build(campaign, "novelty", sections, tools=True, cwd=d, unit=pair_id)


def apply(campaign, pair_id, d, item, round_) -> dict:
    """Record a returned check, read or not; the thread then goes to verify either way."""
    result, report, error = item["result"], None, None
    if result.get("transport_failed") or result.get("error"):
        error = result.get("error") or "transport failed"
    else:
        try:
            report = contracts.parse("novelty", result.get("text") or "")
        except contracts.ContractViolation as violation:
            error = f"contract: {violation}"
    entry = {"at": item.get("at") or _now(), "round": round_, "request_id": item["request"]["identity"],
             "note_sha256": note_sha(d, pair_id), "report": report, "error": error}
    rec = records(d, pair_id)
    if not any(r.get("request_id") == entry["request_id"] for r in rec):
        _path(d, pair_id).write_text(json.dumps(rec + [entry], indent=1))
    return {"status": "failed" if error else "ok", "note_sha256": entry["note_sha256"], "reason": error}


def verify_section(campaign, d, pair_id) -> str:
    """The section verify reads after the material, or "" when the campaign has no novelty stage."""
    if not enabled(campaign):
        return ""
    from .thread import _prompt
    entry = current(d, pair_id)
    if entry and entry.get("report") is not None:
        body = _prompt(campaign, "novelty-evidence") + "\n\n" + json.dumps(entry["report"], indent=1)
    else:
        why = (entry or {}).get("error") or "no check was made of this version of the note"
        body = f"The novelty check for this note failed ({why}); there is no report. Judge novelty from the material."
    return "\n\n## Novelty check\n\n" + body


def _now():
    from .thread import _now as now
    return now()
