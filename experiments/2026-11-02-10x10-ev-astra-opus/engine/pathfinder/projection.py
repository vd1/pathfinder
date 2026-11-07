"""Deterministic projections the context builder tries on a section before it shrinks it blindly (proofTree's
compact packet, generalised): a projection keeps what a reader judges by in full and shortens records that are
history, each with what was cut, so the result is smaller and nothing is lost silently. The evidence a review is
bound to is always the full text (review_evidence hashes the sections' bodies, not what the budget sent).

ledger: every ledger row (a JSON line with seq, actor, kind and text, in a ledger section or in material that
inlines bundle ledgers) is written as one readable entry. Findings, corrections, objections and ideas stay in
full; a row a later row supersedes becomes a pointer to it; ready markers become one line; intentions keep their
first INTENTION_CHARS characters; a review keeps its structure with each long string cut to REVIEW_STRING_CHARS.
Any other line is kept as it is."""
from __future__ import annotations
import json

INTENTION_CHARS = 240
REVIEW_STRING_CHARS = 240
NOTE = ("(projection of the ledger rows that follow, to fit the prompt budget: findings, corrections, objections "
        "and ideas in full; superseded rows point to the row that replaced them; ready markers, intentions and "
        "reviews shortened, each cut marked; the full rows are in ledger.jsonl)")


def _row(line: str):
    if not line.startswith('{"seq"'):
        return None
    try:
        row = json.loads(line)
    except ValueError:
        return None
    return row if isinstance(row, dict) and {"seq", "actor", "kind", "text"} <= set(row) else None


def _cut(text: str, limit: int) -> str:
    return text if len(text) <= limit else f"{text[:limit]} [... {len(text) - limit} characters omitted]"


def _shorten(value):
    if isinstance(value, str):
        return _cut(value, REVIEW_STRING_CHARS)
    if isinstance(value, list):
        return [_shorten(v) for v in value]
    if isinstance(value, dict):
        return {k: _shorten(v) for k, v in value.items() if k != "evidence_id"}
    return value


def _entry(row: dict, replaced_by: int | None) -> str:
    head = f"#{row['seq']} {row['actor']} {row['kind']}"
    if row.get("supersedes") is not None:
        head += f" (supersedes #{row['supersedes']})"
    text = row["text"] if isinstance(row["text"], str) else json.dumps(row["text"])
    if replaced_by is not None:
        return f"{head}: superseded by #{replaced_by} [{len(text)} characters omitted]"
    if row["kind"] == "ready":
        return f"{head}" + (f" at #{row['seen']}" if row.get("seen") is not None else "")
    if row["kind"] == "intention":
        return f"{head}: {_cut(text, INTENTION_CHARS)}"
    if row["kind"] == "review":
        try:
            return f"{head}: {json.dumps(_shorten(json.loads(text)), ensure_ascii=False)}"
        except ValueError:
            return f"{head}: {_cut(text, INTENTION_CHARS)}"
    return f"{head}: {text}"


def ledger(text: str) -> str:
    """The text with each ledger row projected; text without ledger rows comes back unchanged."""
    lines = text.split("\n")
    rows = [_row(line) for line in lines]
    if not any(rows):
        return text
    out, block = [], []                            # rows are numbered per ledger: a block is a run of rows
    def flush():
        replaced = {}
        for r in block:
            if r.get("supersedes") is not None:
                replaced[r["supersedes"]] = r["seq"]
        out.append(NOTE)
        out.extend(_entry(r, replaced.get(r["seq"])) for r in block)
        block.clear()
    for line, row in zip(lines, rows):
        if row is not None:
            block.append(row); continue
        if block:
            flush()
        out.append(line)
    if block:
        flush()
    return "\n".join(out)
