"""Corpora: JSONL rows from the arXiv API, e-print sources flattened to one file."""
from __future__ import annotations
import gzip, io, json, re, shutil, subprocess, tarfile, time, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from . import net

NS = {"a": "http://www.w3.org/2005/Atom"}
API = "https://export.arxiv.org/api/query?"


PAIR = re.compile(r"Q(\d+)-?P(\d+)")


def pair_id(i: int, j: int) -> str:
    """The id of the pair of Q line i and P line j in a corpus without numbers."""
    return f"Q{i}P{j}"


def numbers(pair_id: str) -> tuple[int, int]:
    """The two numbers a pair id names: Q1P15, or Q002-P072 for a corpus whose rows carry their own numbers."""
    m = PAIR.fullmatch(pair_id or "")
    if not m:
        raise ValueError(f"not a pair id: {pair_id!r} (Q<number>P<number>, optionally zero-padded with a hyphen)")
    return int(m.group(1)), int(m.group(2))


def numbered(rows: list[dict]) -> bool:
    return any("n" in r for r in rows)


def row_for(rows: list[dict], number: int) -> dict:
    """The row a pair id's number names: the row whose "n" it is in a numbered corpus, else that line."""
    if numbered(rows):
        return next((r for r in rows if r.get("n") == number), {})
    return rows[number - 1] if 0 < number <= len(rows) else {}


def pair_rows(campaign, pair_id: str) -> tuple[dict, dict]:
    i, j = numbers(pair_id)
    return (row_for(read(campaign.path("Q.jsonl")), i), row_for(read(campaign.path("P.jsonl")), j))


def pair_id_for(campaign, qi: int, pj: int, Q=None, P=None) -> str:
    """The id of the pair of Q row qi and P row pj (0-based): by their numbers when the corpus carries them."""
    Q = read(campaign.path("Q.jsonl")) if Q is None else Q
    P = read(campaign.path("P.jsonl")) if P is None else P
    if numbered(Q) or numbered(P):
        return f"Q{Q[qi].get('n', qi + 1):03d}-P{P[pj].get('n', pj + 1):03d}"
    return pair_id(qi + 1, pj + 1)


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


USER_AGENT = "pathfinder/0.1"
BACKOFF = 10                                     # seconds before the second attempt, twice that before the third


def query(params: dict, timeout: float = 60, attempts: int = 3) -> str:
    """The arXiv API's Atom response to `params`. A rate limit (HTTP 429) is asked again after 10 s, then 20 s;
    any other error, or the last 429, is raised. Requests name their client, as arXiv asks."""
    request = urllib.request.Request(API + urllib.parse.urlencode(params), headers={"User-Agent": USER_AGENT})
    for attempt in range(attempts):
        try:
            with net.urlopen(request, timeout=timeout) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == attempts - 1:
                raise
            time.sleep(BACKOFF * (attempt + 1))


def fetch(query: str, n: int, start: int = 0) -> list[dict]:
    """The n most recent papers matching query, skipping the first `start` (older pages have larger start)."""
    q = urllib.parse.urlencode({"search_query": f'all:"{query}"', "sortBy": "submittedDate",
                                "sortOrder": "descending", "max_results": n, "start": start})
    with net.urlopen(API + q, timeout=60) as r:
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
    cands = [p for p in d.rglob("*.tex") if re.search(r"\\document(class|style)\b", p.read_text(errors="replace"))]   # LaTeX 2.09 too
    return min(cands, key=lambda p: len(p.parts)) if cands else None


def flatten(aid: str, out_dir: Path) -> str:
    """Download the e-print for aid, flatten to out_dir/aid.tex or .txt; return the relative name."""
    out_dir.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(f"https://arxiv.org/e-print/{aid}", headers={"User-Agent": "pathfinder/0.1"})
    with net.urlopen(req, timeout=120) as r:
        blob, ctype = r.read(), r.headers.get("Content-Type", "")
    work = out_dir / aid; shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)   # math/0110009v3
    if blob[:4] == b"%PDF" or "pdf" in ctype:
        return _pdf_text(aid, out_dir, blob)
    try:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:*") as tf:
            tf.extractall(work, filter="data")
    except tarfile.ReadError:
        (work / "main.tex").write_bytes(gzip.decompress(blob))
    main = _main_tex(work)
    if main is None:
        raise RuntimeError(f"{aid}: no .tex with \\documentclass or \\documentstyle in e-print")
    try:
        with open(out_dir / f"{aid}.tex", "w") as f:
            subprocess.run(["latexpand", "--empty-comments", main.name], cwd=main.parent, stdout=f, check=True, timeout=120)
        return f"sources/{aid}.tex"
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:   # latexpand can crash on odd templates
        (out_dir / f"{aid}.tex").unlink(missing_ok=True)
        print(f"{aid}: latexpand failed ({e.__class__.__name__}); using the PDF text instead")
        req = urllib.request.Request(f"https://arxiv.org/pdf/{aid}", headers={"User-Agent": "pathfinder/0.1"})
        with net.urlopen(req, timeout=120) as r:
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
