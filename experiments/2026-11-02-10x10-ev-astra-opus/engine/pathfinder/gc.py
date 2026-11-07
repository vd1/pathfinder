"""Garbage collection: what a finished cycle leaves that the record does not need.

A thread whose research is terminal and whose editing is done keeps its record (ledger, notes, PDFs, the
peers' derivations, run logs, verdicts, status). Removed: LaTeX by-products (build files, and a log or outline
only beside its .tex; the PDF and its sources stay), papers agents downloaded into their folders (a PDF they did
not build, the pdftotext text of one; in a frozen bundle recorded in branches-pruned.json), never a file a ledger
or note cites; working
directories of model calls, and the prompt copied into every retained research response once that response
holds its result. Receipts keep the commands an agent ran, its answer and the usage, but not the full output
of each tool call: the first and last characters and the output's length, enough to see what was read and
how much. Each garbage_collected event names the paths it removed. The runner collects each thread when it finishes; `pathfinder gc` collects every finished thread and
compacts receipts written before compaction existed. "gc": false in campaign.json turns collection off."""
from __future__ import annotations
import json, os, shutil, tempfile
from pathlib import Path

OUTPUT_KEEP = 400                         # characters of a tool output kept in a receipt, head and tail
BYPRODUCTS = (".aux", ".fls", ".fdb_latexmk", ".out", ".toc", ".blg", ".log", ".synctex.gz", ".xdv", ".nav", ".snm")
WORKING_DIRS = (".transport-input", ".tmp")
PATHS_KEPT = 500                          # removed paths named in the garbage_collected event


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


def _byproduct(name: str, names) -> bool:
    """A LaTeX by-product: a build file, or a log or outline beside its .tex (evidence.byproduct). A script's
    run log is a data output, and a PDF is kept (the record's PDFs stay)."""
    from .evidence import byproduct
    return name.endswith(BYPRODUCTS) and byproduct(name, names)


def _cited(d: Path) -> set:
    """Every file a ledger or a note in the thread cites, relative to the thread, read as the citing file's
    directory or the thread sees it: collection never removes evidence."""
    from .evidence import cited_files
    out = set()
    for f in [*d.rglob("ledger.jsonl"), *d.rglob("*.tex")]:
        if not f.is_file() or any(part in WORKING_DIRS for part in f.relative_to(d).parts):
            continue
        for name in cited_files(f.read_text(errors="replace")):
            for base in {d, f.parent}:
                path = (base / name)
                try:
                    out.add(path.resolve().relative_to(d.resolve()))
                except ValueError:
                    continue
    return out


RECORD_DIRS = ("inputs", "paper", "edited", "reopened")   # the thread's own documents, never downloads
PRUNED = "branches-pruned.json"                  # files collection removed from frozen bundles, by label


def downloaded(path: Path, rel: Path, peers) -> bool:
    """A paper an agent downloaded into its folder: a PDF with no .tex of its name beside it (the agent did not
    build it), or the text pdftotext made of one (form feeds between pages). The engine now gives agents the
    LaTeX sources (pathfinder.library); these are what agents fetched before it did."""
    if not set(rel.parts[:-1]) & set(peers) or rel.parts[0] in RECORD_DIRS:
        return False
    if path.suffix.lower() == ".pdf":
        return not path.with_suffix(".tex").exists()
    if path.suffix.lower() == ".txt":
        with open(path, "rb") as f:
            return f.read(400_000).count(b"\f") >= 2
    return False


def _prune(d: Path, rel: Path) -> None:
    """Record a file removed from a frozen bundle, so that the bundle still verifies (composable.verify)."""
    label, name = rel.parts[1], Path(*rel.parts[2:]).as_posix()
    path = d / PRUNED
    pruned = json.loads(path.read_text()) if path.exists() else {}
    pruned.setdefault(label, [])
    if name not in pruned[label]:
        pruned[label].append(name)
    path.write_text(json.dumps(pruned, indent=1))


def _size(path: Path) -> int:
    return sum(p.lstat().st_size for p in path.rglob("*") if p.is_file() or p.is_symlink()) if path.is_dir() else path.stat().st_size


def collect_thread(campaign, pair_id, *, dry_run: bool = False) -> dict | None:
    """Collect one finished thread; None when it is not finished. Returns {"files", "bytes", "stripped"}."""
    if not finished(campaign, pair_id):
        return None
    d = campaign.thread_dir(pair_id)
    files = size = stripped = 0
    keep, removed = _cited(d), []
    names = {p.relative_to(d).as_posix() for p in d.rglob("*")}
    for p in sorted(d.rglob("*"), key=lambda p: len(p.parts)):
        if not p.exists() or p.is_symlink():
            continue
        rel = p.relative_to(d)
        if p.is_dir() and (p.name in WORKING_DIRS or _environment(p) or (p.name == "tmp" and p.parent.name == ".pathfinder")):
            if any(k == rel or rel in k.parents for k in keep):
                continue
            files += sum(1 for q in p.rglob("*") if q.is_file()); size += _size(p); removed.append(rel.as_posix())
            if not dry_run:
                shutil.rmtree(p)
        elif p.is_file() and rel not in keep and downloaded(p, rel, campaign.peers):
            files += 1; size += p.stat().st_size; removed.append(rel.as_posix())
            if not dry_run:
                if rel.parts[0] == "branches":
                    _prune(d, rel)
                p.unlink()
        elif (p.is_file() and _byproduct(rel.as_posix(), names) and "branches" not in rel.parts and rel not in keep):
            files += 1; size += p.stat().st_size; removed.append(rel.as_posix())
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
        events.emit(campaign, "garbage_collected", unit=pair_id, paths=removed[:PATHS_KEPT], **report)
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
