"""The papers a thread reads, fetched before research (nobel, 18 October 2026).

Peers downloaded PDFs (from arXiv and from publishers) and ran pdftotext inside their own calls: the mathematics
came out garbled, every peer repeated another's download, and retrieval ate their calls and seconds. Now the
engine fetches, before any agent starts and outside every allowance, the pair's two papers, the papers their
bibliographies name (by arXiv id or DOI) and the papers citing both (the campaign's novelty_citers file), as LaTeX
for every paper on arXiv, into one shared cache ("source_cache", default the campaign's sources/), and gives the
thread an index, inputs/library.jsonl. An agent that needs another paper runs the thread's copy of
pathfinder.paper_source with an arXiv id, a DOI, a URL or a title: a hit is returned at once, a miss is fetched
once and added to the cache for everyone; calls with tools may write that one directory. `pathfinder prefetch`
fills the cache for every shortlisted pair at once, before research."""
from __future__ import annotations
import json, re, shutil, sys, time
from pathlib import Path
from . import paper_source, net

LIMIT = 60                                       # papers per thread beyond the pair's two, most named first
HELPER = "paper_source.py"


def cache(campaign) -> Path:
    return campaign.path((campaign.raw or {}).get("source_cache", "sources"))


def _also(campaign) -> list[Path]:
    """Older places a text may already be in: the campaign's sources/ when the cache is elsewhere."""
    legacy = campaign.path("sources")
    return [legacy] if legacy.resolve() != cache(campaign).resolve() else []


def limit(campaign) -> int:
    return (campaign.raw or {}).get("prefetch_limit", LIMIT)


def validate(raw: dict) -> None:
    if "source_cache" in raw and (not isinstance(raw["source_cache"], str) or not raw["source_cache"].strip()):
        raise ValueError(f"source_cache must be a directory path, got {raw['source_cache']!r}")
    v = raw.get("prefetch_limit", LIMIT)
    if type(v) is not int or v < 0:
        raise ValueError(f"prefetch_limit must be a non-negative integer, got {v!r}")


def get(campaign, ref: str) -> Path:
    """Any paper (an arXiv id, a DOI, a URL, a title) through the cache: its LaTeX when it is on arXiv."""
    return paper_source.resolve(ref, cache(campaign), _also(campaign), urlopen=lambda r, timeout: net.urlopen(r, timeout))


def paper_text(campaign, row: dict) -> Path | None:
    """A corpus paper's full text: the row's own text, else its arXiv source through the cache (fetched once);
    None when there is none (not an arXiv paper, no e-print, or offline): the abstract is used."""
    if row.get("text") and campaign.path(row["text"]).is_file():
        return campaign.path(row["text"])
    aid = paper_source.parse(row.get("id", ""))
    if aid is None:
        return None
    try:
        return get(campaign, aid)
    except Exception as error:                   # no e-print, a network failure: the abstract is used
        print(f"{aid}: no source ({error}); the abstract will be used")
        return None


def _citers(campaign, pair_id) -> list[tuple[str, str]]:
    template = (campaign.raw or {}).get("novelty_citers")
    path = campaign.path(template.replace("{pair}", pair_id)) if template else None
    if not path or not path.is_file():
        return []
    out = []
    for line in path.read_text(errors="replace").splitlines():
        m = paper_source._IN_TEXT.search(line)
        if m:
            out.append((m.group(1), line.lstrip("-* ").split(" (")[0].strip()[:200]))
    return out


def wanted(campaign, pair_id, rows) -> list[dict]:
    """The papers worth fetching for a pair, beyond its own two: those citing both first, then the papers the
    two bibliographies name, those named by both before the others."""
    own = {paper_source.parse(r.get("id", "")) for r in rows} - {None}
    out = {}
    for aid, title in _citers(campaign, pair_id):
        out.setdefault(aid, {"id": aid, "title": title, "why": []})["why"].append("cites both papers")
    for side, row in zip("QP", rows):
        text = paper_text(campaign, row)
        aid = paper_source.parse(row.get("id", ""))
        for ref in paper_source.references(text, aid, cache(campaign), lambda r, timeout: net.urlopen(r, timeout)) if text else []:
            out.setdefault(ref, {"id": ref, "title": None, "why": []})["why"].append(f"cited by {side}")
    ranked = sorted((w for w in out.values() if w["id"] not in own),
                    key=lambda w: ("cites both papers" not in w["why"], -len(w["why"])))
    return ranked[:limit(campaign)]


def build(campaign, pair_id, rows) -> list[dict]:
    """Fetch what the pair needs (a cache hit costs nothing) and return the library's entries."""
    entries = []
    for want in wanted(campaign, pair_id, rows):
        try:
            path = get(campaign, want["id"])
        except Exception as error:
            entries.append({**want, "path": None, "error": str(error)[:200]}); continue
        entries.append({**want, "path": str(path.resolve())})
    return entries


def write(d: Path, entries: list[dict]) -> Path:
    path = d / "inputs" / "library.jsonl"
    path.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries))
    return path


def install(campaign, d: Path) -> str:
    """Copy the source helper into the thread; returns the command an agent runs (an id or more after it)."""
    from .thread import HELPER_DIR, _atomic_write
    target = d / HELPER_DIR / HELPER
    source = Path(paper_source.__file__).read_bytes()
    if not target.is_file() or target.read_bytes() != source:
        target.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(target, source)
    also = "".join(f" --also {p.resolve()}" for p in _also(campaign))
    return f"{sys.executable} -I {HELPER_DIR}/{HELPER} --cache {cache(campaign).resolve()}{also}"


def reading(campaign, d: Path) -> str:
    """The reading rule for an agent with tools in a thread, with its library and the helper command."""
    lib = d / "inputs" / "library.jsonl"
    entries = [json.loads(l) for l in lib.read_text().splitlines() if l.strip()] if lib.is_file() else []
    listed = "".join(f"- {e['id']}: {e.get('title') or 'untitled'} ({', '.join(e.get('why') or [])}) {e['path']}\n"
                     for e in entries if e.get("path"))
    return ("\n\nReading papers. Read every paper through the engine's source service, never by downloading it: do "
            "not download a PDF, from arXiv or a publisher, and do not run pdftotext; the engine has fetched the "
            "sources for you, as LaTeX for every paper on arXiv. The two papers are in inputs/. " + (f"inputs/library.jsonl lists {len(entries)} more papers fetched for this thread "
            "(papers citing both, and the papers their bibliographies name), each with the path of its source:\n"
            + listed if listed else "")
            + f"For any other paper run\n    {install(campaign, d)} REF [REF ...]\nwith an arXiv id, a DOI, a URL or "
            "title:<the title> as REF; it prints the path of each paper's text from the shared cache (its LaTeX when "
            "the paper is on arXiv), fetching it once if nobody has, and waits for it. Read texts in bounded slices "
            "(search for the theorem or section you need).\n")


def prefetch(campaign, pairs, out=print) -> dict:
    """Fill the cache for the given pairs before research: their two papers, then each one's library."""
    from . import corpus
    totals = {"pairs": 0, "papers": 0, "failed": 0}
    for pair_id in pairs:
        rows = corpus.pair_rows(campaign, pair_id)
        texts = [paper_text(campaign, r) for r in rows]
        entries = build(campaign, pair_id, rows)
        failed = sum(1 for e in entries if not e.get("path")) + sum(1 for r, t in zip(rows, texts)
                                                                     if t is None and paper_source.parse(r.get("id", "")))
        totals["pairs"] += 1; totals["papers"] += len(entries) + 2; totals["failed"] += failed
        out(f"{pair_id}: Q {'source' if texts[0] else 'abstract'}, P {'source' if texts[1] else 'abstract'}, "
            f"library {len(entries)} ({failed} failed)")
    return totals


def add_to_inputs(campaign, pair_id) -> dict:
    """`pathfinder sources PAIR --into-inputs`: the full text and the library added to an existing thread's
    inputs/, beside its files, never replacing them; recorded in inputs/added.json and as an event."""
    from . import corpus, events, runner
    d = campaign.thread_dir(pair_id)
    if not (d / "status.json").exists():
        raise SystemExit(f"{pair_id}: no thread yet; it gets its sources when it opens")
    if runner.Lock.holder(d):
        raise SystemExit(f"{pair_id}: the thread is held by a running process; add its sources when it stops")
    record_path = d / "inputs" / "added.json"
    record = json.loads(record_path.read_text()) if record_path.is_file() else {"added": []}
    rows = [json.loads((d / "inputs" / f"{s}.json").read_text()) if (d / "inputs" / f"{s}.json").is_file() else r
            for s, r in zip("QP", corpus.pair_rows(campaign, pair_id))]
    added = []
    for side, row in zip("QP", rows):
        text = paper_text(campaign, row)
        if text is None:
            continue
        target = d / "inputs" / f"{side}{text.suffix}"
        if target.exists():
            if target.read_bytes() == text.read_bytes():
                record.setdefault("inputs", {})[side] = target.name
                continue
            target = d / "inputs" / f"{side}-source{text.suffix}"
        shutil.copy(text, target)
        record.setdefault("inputs", {})[side] = target.name
        added.append(target.name)
    if not (d / "inputs" / "library.jsonl").exists():
        write(d, build(campaign, pair_id, rows)); added.append("library.jsonl")
    record["added"].append({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": added})
    record_path.write_text(json.dumps(record, indent=1))
    events.emit(campaign, "inputs_added", unit=pair_id, files=added)
    return {"added": added, "inputs": record.get("inputs", {})}


def abstract_only(path: Path) -> bool:
    """A thread input holding the corpus row's title and abstract only (thread.prepare's fallback)."""
    try:
        head = path.read_text(errors="replace")[:4000]
    except OSError:
        return False
    return path.suffix == ".txt" and head.startswith("Title: ") and "\n\nAbstract: " in head and len(head) < 4000
