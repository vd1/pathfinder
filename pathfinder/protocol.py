"""The protocol section that ends every shared document (the edited note and the paper), written by the engine
from the campaign's settings and receipts, never by an agent: how the research was run, which models proposed
(peers, consolidation, editing, the paper's author) and which verified (verifier, ledger reviewer, paper reviewers,
actionability), how the account was edited, calls served by the refusal fallback, the engine release, and the
date and time of production as dd-mm-yyyy-hh-mm in UTC. "protocol_section": false leaves it out."""
from __future__ import annotations
import json, time
from pathlib import Path

PROPOSERS = ("peer", "consolidate", "edit", "author")
VERIFIERS = ("verify", "ledger_review", "review", "actionability")
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}


def enabled(campaign) -> bool:
    return (campaign.raw or {}).get("protocol_section", True) is not False


def _models(campaign, pair_id, stages) -> list[str]:
    from . import transport
    seen = []
    for r in transport.receipts(campaign):
        if r.get("thread") == pair_id and r.get("stage") in stages and r.get("outcome") == "completed":
            name = f"{r.get('model')} ({r.get('backend')})"
            if name not in seen:
                seen.append(name)
    return seen


def _engine() -> str:
    from . import __file__ as package
    record = Path(package).resolve().parent.parent / "engine-freeze.json"
    try:
        data = json.loads(record.read_text())
        return f"{data.get('ref') or 'frozen'} ({str(data.get('commit', ''))[:7]})"
    except (OSError, ValueError):
        return "the development checkout"


def describe(campaign, pair_id: str, produced: str | None = None) -> str:
    """produced: the document's own completion time (ISO, UTC) when it is rebuilt later; now otherwise."""
    from . import edit, research
    raw = campaign.raw or {}
    peers = list(campaign.peers)
    team = (f"{WORDS.get(len(peers), len(peers))} peer{'s' if len(peers) != 1 else ''} ({', '.join(peers)}) "
            f"working on a shared ledger")
    if raw.get("research_scheme") == "composable":
        n = int(raw.get("branches", 3))
        how = (f"Research: {WORDS.get(n, n)} independent branches, each with {team}, reviewed by a ledger "
               "reviewer, then a joint thread over their frozen records")
    elif raw.get("research_scheme") == "direct_eva":
        how = f"Research: {team}, reviewed entry by entry by a ledger reviewer"
    else:
        how = f"Research: {team}, a consolidator writing the account and a verifier deciding"
    rounds = research.status(campaign, pair_id).get("round")
    how += f" ({rounds} round{'s' if rounds != 1 else ''})." if isinstance(rounds, int) and rounds else "."
    proposers = _models(campaign, pair_id, PROPOSERS) or [f"{campaign.model} ({campaign.backend})"]
    verifiers = _models(campaign, pair_id, VERIFIERS) or [f"{campaign.model} ({campaign.backend})"]
    e = edit.status(campaign, pair_id)
    editing = ("Editing: PCE (author, archivist, fact-checker, critic, editor)"
               + (", account accepted." if e.get("editorial_status") == "accepted" else
                  ", not accepted: the single editor's account is shown.")
               if e.get("scheme") == "pce" else "Editing: a single editor.")
    from . import transport
    rescued = sum(1 for r in transport.receipts(campaign) if r.get("thread") == pair_id
                  and (r.get("route") or {}).get("key") == "refusal_fallback" and r.get("outcome") == "completed")
    lines = [how, "Proposers: " + "; ".join(proposers) + ".", "Verifiers: " + "; ".join(verifiers) + ".", editing]
    if rescued:
        lines.append(f"{rescued} call{'s' if rescued != 1 else ''} refused by a provider's safety filter "
                     f"{'were' if rescued != 1 else 'was'} answered on the fallback route.")
    moment = time.gmtime()
    if produced:
        try:
            moment = time.strptime(produced[:16], "%Y-%m-%dT%H:%M")
        except ValueError:
            pass
    lines.append(f"Engine: Pathfinder {_engine()}. Produced {time.strftime('%d-%m-%Y-%H-%M', moment)} UTC.")
    return " ".join(lines)
