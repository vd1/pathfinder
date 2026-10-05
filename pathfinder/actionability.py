"""Actionability, the end of the pipeline: once a pair is edited, one tool-less assessor call decides whether
its result can be acted on (ACTIONABLE, NEEDS_INPUTS or NO_CASE) and names the inputs still missing, the next
experiment and what would falsify the case. Opt-in with "actionability": true in campaign.json; the
deployment's rubric is prompts/actionability.append.md, its model a route on the "actionability" stage. The
answer is threads/<pair>/actionability.json. An answer that stays unreadable after the contract's repair turn
is recorded as blocked and does not hold the campaign: the pair's research and account are already done."""
from __future__ import annotations
import hashlib, json, time
from . import contracts, context, transport
from .context import Section

SCHEMA = {"title": "actionability", "type": "object",
          "required": ["decision", "rationale", "evidence", "required_inputs", "next_experiment", "falsification"],
          "properties": {"decision": {"enum": ["ACTIONABLE", "NEEDS_INPUTS", "NO_CASE"]},
                         "rationale": {"type": "string"},
                         "evidence": {"type": "array"}, "required_inputs": {"type": "array"},   # items: text or records
                         "next_experiment": {"type": ["string", "array", "object"]},
                         "falsification": {"type": ["string", "array", "object"]}}}


def enabled(campaign) -> bool:
    return (campaign.raw or {}).get("actionability") is True


def validate(raw: dict) -> None:
    if "actionability" in raw and not isinstance(raw["actionability"], bool):
        raise ValueError(f"actionability must be true or false, got {raw['actionability']!r}")


def status(campaign, pair_id) -> dict:
    p = campaign.thread_dir(pair_id) / "actionability.json"
    return json.loads(p.read_text()) if p.exists() else {"status": "none"}


def _set(campaign, pair_id, **kw) -> dict:
    before = status(campaign, pair_id)
    s = {**kw, "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (campaign.thread_dir(pair_id) / "actionability.json").write_text(json.dumps(s, indent=1))
    from . import events
    events.transition(campaign, pair_id, "actionability", before, s)
    return s


def pending(campaign, pair_id) -> bool:
    """Enabled, the pair edited, and no answer recorded yet (done or blocked)."""
    from . import edit
    return (enabled(campaign) and edit.status(campaign, pair_id).get("status") == "done"
            and status(campaign, pair_id).get("status") == "none")


def run(campaign, pair_id) -> str:
    from . import research, thread
    d = campaign.thread_dir(pair_id)
    inp = thread._inputs(d)
    note = d / "edited" / "note.tex"
    task = thread._prompt(campaign, "actionability", Q_INPUT=f"inputs/{inp['Q']}", P_INPUT=f"inputs/{inp['P']}",
                          NOTE="edited/note.tex", STATUS=research.status(campaign, pair_id).get("status", "?"))
    prompt = context.build(campaign, "actionability", thread.thread_sections(d, inp)
                           + [Section("edited/note.tex", path=note, keep=True),
                              Section("", text="## your task\n\n" + task, keep=True)], tools=False, cwd=d, unit=pair_id)
    seconds = int(((campaign.raw or {}).get("allowances") or {}).get("actionability_seconds", 600))
    request = transport.ModelRequest(identity=f"{pair_id}:actionability:0", prompt=prompt, model=campaign.model,
                                     tools=False, search=False, cwd=d, timeout=seconds, thread=pair_id,
                                     stage="actionability", actor="assessor", schema=SCHEMA)
    value, result = contracts.ensure(campaign, request, transport.execute(campaign, request), SCHEMA)
    if value is None:
        _set(campaign, pair_id, status="blocked", reason=str(result.get("error") or "no readable answer")[:500])
        return "blocked"
    _set(campaign, pair_id, status="done", decision=value["decision"], assessment=value,
         note_sha256=hashlib.sha256(note.read_bytes()).hexdigest())
    return "done"
