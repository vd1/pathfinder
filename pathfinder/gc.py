"""Garbage collection: what a finished cycle leaves that the record does not need.

A thread whose research is terminal and whose editing is done keeps its record (ledger, notes, PDFs, the
peers' derivations, verdicts, status). Removed: LaTeX by-products (the PDF and its sources stay), working
directories of model calls, and the prompt copied into every retained research response once that response
holds its result. Receipts keep the commands an agent ran, its answer and the usage, but not the full output
of each tool call: the first and last characters and the output's length, enough to see what was read and
how much. The runner collects each thread when it finishes; `pathfinder gc` collects every finished thread and
compacts receipts written before compaction existed. "gc": false in campaign.json turns collection off."""
from __future__ import annotations
import json, os, shutil, tempfile
from pathlib import Path

OUTPUT_KEEP = 400                         # characters of a tool output kept in a receipt, head and tail
BYPRODUCTS = (".aux", ".fls", ".fdb_latexmk", ".out", ".toc", ".blg", ".log", ".synctex.gz", ".xdv", ".nav", ".snm")
WORKING_DIRS = (".transport-input", ".tmp")


def _shorten(text, holder) -> bool:
    if not isinstance(text, str) or len(text) <= OUTPUT_KEEP:
        return False
    holder["output_chars"] = len(text)
    half = OUTPUT_KEEP // 2
    return text[:half] + f"\n[... {len(text) - OUTPUT_KEEP} characters dropped ...]\n" + text[-half:]


def compact_events(lines: list[str]) -> list[str]:
    """Raw events with every long tool output shortened; agent messages, commands and usage unchanged."""
    out = []
    for line in lines:
        try:
            row = json.loads(line)
        except (TypeError, json.JSONDecodeError):
            out.append(line); continue
        changed = False
        item = row.get("item") if isinstance(row, dict) else None
        if isinstance(item, dict) and item.get("type") in ("command_execution", "mcp_tool_call", "web_search"):
            for key in ("aggregated_output", "result"):
                short = _shorten(item.get(key), item)
                if short:
                    item[key] = short; changed = True
        if isinstance(row, dict) and row.get("type") == "user":
            for block in (row.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    content = block.get("content")
                    text = content if isinstance(content, str) else json.dumps(content)
                    short = _shorten(text, block)
                    if short:
                        block["content"] = short; changed = True
        out.append(json.dumps(row) if changed else line)
    return out


def enabled(campaign) -> bool:
    return (campaign.raw or {}).get("gc", True) is not False


def finished(campaign, pair_id) -> bool:
    from . import edit, research
    return (research.status(campaign, pair_id).get("status") in research.TERMINAL
            and edit.status(campaign, pair_id).get("status") == "done")


def _environment(path: Path) -> bool:
    """A peer's virtual environment, bytecode cache or cloned repository's .git (see composable.environment)."""
    from .composable import environment
    return environment(path)


def _size(path: Path) -> int:
    return sum(p.lstat().st_size for p in path.rglob("*") if p.is_file() or p.is_symlink()) if path.is_dir() else path.stat().st_size


def collect_thread(campaign, pair_id, *, dry_run: bool = False) -> dict | None:
    """Collect one finished thread; None when it is not finished. Returns {"files", "bytes", "stripped"}."""
    if not finished(campaign, pair_id):
        return None
    d = campaign.thread_dir(pair_id)
    files = size = stripped = 0
    for p in sorted(d.rglob("*"), key=lambda p: len(p.parts)):
        if not p.exists() or p.is_symlink():
            continue
        if p.is_dir() and (p.name in WORKING_DIRS or _environment(p) or (p.name == "tmp" and p.parent.name == ".pathfinder")):
            files += sum(1 for q in p.rglob("*") if q.is_file()); size += _size(p)
            if not dry_run:
                shutil.rmtree(p)
        elif p.is_file() and any(p.name.endswith(s) for s in BYPRODUCTS) and "branches" not in p.relative_to(d).parts:
            files += 1; size += p.stat().st_size
            if not dry_run:
                p.unlink()
        elif p.is_file() and p.parent.name == "research-requests" and p.suffix == ".json":
            try:
                saved = json.loads(p.read_text())
            except ValueError:
                continue
            if not isinstance(saved, dict) or saved.get("result") is None:
                continue                          # no result yet: the request may still be replayed
            request = saved.get("request")
            if isinstance(request, dict) and "dropped" not in request:
                before = p.stat().st_size
                saved["request"] = {"dropped": "prompt copy removed once the response held its result",
                                    "chars": len(json.dumps(request))}
                text = json.dumps(saved, indent=1)
                stripped += 1; size += max(before - len(text), 0)
                if not dry_run:
                    p.write_text(text)
    report = {"files": files, "bytes": size, "stripped": stripped}
    if not dry_run:
        from . import events
        events.emit(campaign, "garbage_collected", unit=pair_id, **report)
    return report


def compact_receipts(campaign, *, dry_run: bool = False) -> int:
    """Rewrite receipts.jsonl with compacted events; returns the bytes saved. Only while no runner holds a
    thread, since calls append to the file while they finish."""
    from . import runner
    path = campaign.path("receipts.jsonl")
    if not path.exists() or any(runner.Lock.holder(d) for d in campaign.path("threads").glob("*") if d.is_dir()):
        return 0
    before = path.read_text()
    rows = []
    for line in before.splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            rows.append(line); continue
        if isinstance(row, dict) and isinstance(row.get("raw_events"), list):
            row["raw_events"] = compact_events(row["raw_events"])
        rows.append(json.dumps(row))
    after = "".join(r + "\n" for r in rows)
    if not dry_run and len(after) < len(before):
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".receipts-")
        with os.fdopen(fd, "w") as f:
            f.write(after)
        os.replace(tmp, path)
    return max(len(before) - len(after), 0)


def collect(campaign, *, dry_run: bool = False) -> dict:
    """Every finished thread, then the receipts."""
    total = {"threads": 0, "files": 0, "bytes": 0, "stripped": 0}
    for d in sorted(campaign.path("threads").glob("*")) if campaign.path("threads").is_dir() else []:
        if not d.is_dir() or not (d / "status.json").exists():
            continue
        report = collect_thread(campaign, d.name, dry_run=dry_run)
        if report:
            total["threads"] += 1
            for k in ("files", "bytes", "stripped"):
                total[k] += report[k]
    total["receipt_bytes"] = compact_receipts(campaign, dry_run=dry_run)
    return total
