"""Corpora: JSONL rows from the arXiv API, e-print sources flattened to one file."""
from __future__ import annotations
import gzip, io, json, re, shutil, subprocess, tarfile, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {"a": "http://www.w3.org/2005/Atom"}
API = "http://export.arxiv.org/api/query?"


def pair_id(i: int, j: int) -> str:
    return f"Q{i}P{j}"


def _clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def parse_atom(xml: str) -> list[dict]:
    rows = []
    for e in ET.fromstring(xml).findall("a:entry", NS):
        aid = e.findtext("a:id", "", NS).rsplit("/", 1)[-1]
        aid = re.sub(r"v\d+$", "", aid)
        rows.append({"id": aid, "title": _clean(e.findtext("a:title", "", NS)),
                     "abstract": _clean(e.findtext("a:summary", "", NS)),
                     "authors": [_clean(a.findtext("a:name", "", NS)) for a in e.findall("a:author", NS)],
                     "date": e.findtext("a:published", "", NS)[:10], "text": None})
    return rows


def fetch(query: str, n: int, start: int = 0) -> list[dict]:
    """The n most recent papers matching query, skipping the first `start` (older pages have larger start)."""
    q = urllib.parse.urlencode({"search_query": f'all:"{query}"', "sortBy": "submittedDate",
                                "sortOrder": "descending", "max_results": n, "start": start})
    with urllib.request.urlopen(API + q, timeout=60) as r:
        return parse_atom(r.read().decode())


def more(campaign, side: str, n: int, fetch_fn=fetch) -> list[dict]:
    """@planks("When its next page contains papers \"q2\" and \"q3\"")

    Append the next n older papers for one side, never reordering or dropping existing rows.
    """
    queries = json.loads(campaign.path("fetch.json").read_text())
    path = campaign.path(f"{side}.jsonl"); rows = read(path) if path.exists() else []
    have = {r["id"] for r in rows}
    new = [r for r in fetch_fn(queries[side.lower()], n, start=queries.get(f"{side.lower()}_start", len(rows))) if r["id"] not in have]
    write(rows + new, path)
    queries[f"{side.lower()}_start"] = queries.get(f"{side.lower()}_start", len(rows)) + n
    campaign.path("fetch.json").write_text(json.dumps(queries, indent=1))
    return new


def write(rows, path: Path):
    Path(path).write_text("".join(json.dumps(r) + "\n" for r in rows))


def read(path: Path) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def validate_snapshot(path: Path) -> list[dict]:
    """@planks("When Pathfinder validates the snapshot")"""
    rows = read(path)
    for row in rows:
        for key in ("id", "title", "abstract"):
            if not row.get(key):
                raise ValueError(f"snapshot record requires {key}")
    return rows


def body(campaign, row: dict, fulltext: bool) -> str:
    if fulltext and row.get("text"):
        p = campaign.path(row["text"])
        if p.exists():
            return p.read_text(errors="replace")
    return row["abstract"]


def _main_tex(d: Path) -> Path | None:
    cands = [p for p in d.rglob("*.tex") if "\\documentclass" in p.read_text(errors="replace")]
    return min(cands, key=lambda p: len(p.parts)) if cands else None


def flatten(aid: str, out_dir: Path) -> str:
    """Download the e-print for aid, flatten to out_dir/aid.tex or .txt; return the relative name."""
    out_dir.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(f"https://arxiv.org/e-print/{aid}", headers={"User-Agent": "pathfinder/0.1"})
    with urllib.request.urlopen(req, timeout=120) as r:
        blob, ctype = r.read(), r.headers.get("Content-Type", "")
    work = out_dir / aid; shutil.rmtree(work, ignore_errors=True); work.mkdir()
    if blob[:4] == b"%PDF" or "pdf" in ctype:
        return _pdf_text(aid, out_dir, blob)
    try:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:*") as tf:
            tf.extractall(work, filter="data")
    except tarfile.ReadError:
        (work / "main.tex").write_bytes(gzip.decompress(blob))
    main = _main_tex(work)
    if main is None:
        raise RuntimeError(f"{aid}: no .tex with \\documentclass in e-print")
    try:
        with open(out_dir / f"{aid}.tex", "w") as f:
            subprocess.run(["latexpand", "--empty-comments", main.name], cwd=main.parent, stdout=f, check=True, timeout=120)
        return f"sources/{aid}.tex"
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:   # latexpand can crash on odd templates
        (out_dir / f"{aid}.tex").unlink(missing_ok=True)
        print(f"{aid}: latexpand failed ({e.__class__.__name__}); using the PDF text instead")
        req = urllib.request.Request(f"https://arxiv.org/pdf/{aid}", headers={"User-Agent": "pathfinder/0.1"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return _pdf_text(aid, out_dir, r.read())


def _pdf_text(aid: str, out_dir: Path, blob: bytes) -> str:
    work = out_dir / aid; work.mkdir(parents=True, exist_ok=True)
    (work / "paper.pdf").write_bytes(blob)
    subprocess.run(["pdftotext", "-layout", str(work / "paper.pdf"), str(out_dir / f"{aid}.txt")], check=True)
    return f"sources/{aid}.txt"


def sources(campaign, side: str):
    path = campaign.path(f"{side}.jsonl"); rows = read(path)
    for row in rows:
        if row.get("text") and campaign.path(row["text"]).exists():
            continue
        try:
            row["text"] = flatten(row["id"], campaign.path("sources"))
            print(f"{side} {row['id']}: {row['text']}")
        except Exception as e:                       # one bad e-print must not stop the side; the abstract is used
            print(f"{side} {row['id']}: no source ({e}); the abstract will be used")
        write(rows, path)
        time.sleep(3)
