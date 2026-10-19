"""Papers through one shared cache, LaTeX whenever the paper is on arXiv (nobel, 18 October 2026). Standard library
only: the engine imports it, and each thread gets a copy (.pathfinder/paper_source.py) that its agents run as a
script, because their sandbox may not reach the environment that imports pathfinder.

A reference is an arXiv id, a DOI, a URL or a title ("title:..."). It is resolved to the paper's arXiv version
first (directly for an arXiv id or arxiv.org URL; through Semantic Scholar for a DOI, another URL or a title), and
a paper on arXiv is served as its LaTeX source: a hit returns the cached file, a miss fetches the e-print once,
flattens it to one file (latexpand, else a plain inlining of \\input and \\include), stores it and appends it to
the cache's index.jsonl. Only a paper with no LaTeX (a PDF-only submission, or a paper not on arXiv, whose open
PDF is fetched once) becomes text, with pdftotext. Every resolution is kept in aliases.jsonl, so asking again by
DOI, URL or title is a hit; a reference not found is asked again after a week. The arXiv identifiers and DOIs a
source's bibliography names are kept beside it (<name>.refs.json). One arXiv request every 3 seconds and one
Semantic Scholar request a second across every process sharing the cache (SEMANTIC_SCHOLAR_API_KEY is sent when
set), and one fetch per paper at a time.

    python3 -I paper_source.py --cache DIR [--also DIR ...] REF [REF ...]

prints "<ref> <path>" or "<ref> ERROR <reason>" per reference; exit status 1 if any failed.
PATHFINDER_OFFLINE=1 makes a miss an error instead of a download."""
from __future__ import annotations
import argparse, fcntl, gzip, hashlib, io, json, os, re, shutil, subprocess, sys, tarfile, tempfile, time
from contextlib import contextmanager
import urllib.error, urllib.parse, urllib.request
from pathlib import Path

ID = re.compile(r"^(?:arXiv:)?((?:[a-z][a-z\-]*(?:\.[A-Z]{2})?/\d{7})|(?:\d{4}\.\d{4,5}))(v\d+)?$")
_IN_TEXT = re.compile(r"(?:arXiv[:\s]*|arxiv\.org/(?:abs|pdf)/)((?:\d{4}\.\d{4,5})|(?:[a-z][a-z\-]*(?:\.[A-Z]{2})?/\d{7}))", re.I)
_INPUT = re.compile(r"\\(input|include)\s*\{([^}]+)\}")
_EPRINT_FIELD = re.compile(r"\beprint\s*=\s*[{\"]\s*(?:arXiv:)?((?:\d{4}\.\d{4,5})|(?:[a-z][a-z\-]*(?:\.[A-Z]{2})?/\d{7}))", re.I)
_DOI = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)?(10\.\d{4,9}/\S+)$", re.I)
_DOI_IN_TEXT = re.compile(r"\b(10\.\d{4,9}/[^\s,;{}\\\"']+)")
_ARXIV_URL = re.compile(r"arxiv\.org/(?:abs|pdf|e-print)/([^\s?#]+?)(?:\.pdf)?/?(?:[?#].*)?$", re.I)
S2 = "https://api.semanticscholar.org/graph/v1/paper/"
NOT_FOUND_RETRY = 7 * 24 * 3600                 # seconds before a reference not found is asked again
SPACING = 3.0                                    # seconds between arXiv requests
LOCK_WAIT = 600                                  # seconds to wait for another process fetching the same paper


def parse(text: str) -> str | None:
    """The identifier in an arXiv id as written (arXiv:2401.00001v2, math/0601001), version kept; None if none."""
    m = ID.match(str(text).strip())
    return m.group(1) + (m.group(2) or "") if m else None


def name(aid: str) -> str:
    return aid.replace("/", "_")


def lookup(aid: str, dirs) -> Path | None:
    """Check every local pool before downloading; prefer LaTeX, then a justified PDF extraction.

    Legacy arXiv .txt files may hide an available source. Leave them intact but recheck for LaTeX.
    Non-arXiv deployments may supply their own plain-text sources.
    """
    for suffix in (".tex", ".txt"):
        for d in dirs:
            for stem in (name(aid), aid):
                f = Path(d) / f"{stem}{suffix}"
                if f.is_file() and f.stat().st_size > 0 and (suffix == ".tex" or not parse(aid) or _pdf_text_ready(f)):
                    return f
    return None


def _pdf_text_ready(path: Path) -> bool:
    """Old text alone does not establish that a LaTeX source was unavailable."""
    try:
        return json.loads(path.with_suffix(".source.json").read_text()).get("latex_unavailable") is True
    except (OSError, ValueError):
        return False


def references(path: Path, aid: str | None = None, cache=None, urlopen=None) -> list[str]:
    """The arXiv ids and DOIs the paper's bibliography names: kept by the fetch beside the paper (or in the
    cache); for a text fetched before that was kept, read again from the e-print once (its .bbl and .bib are
    not in the flattened text) and kept, or offline read from the text itself."""
    if Path(path).suffix.lower() == ".pdf":
        return []                               # never decode or extract a pooled PDF as text
    for refs in [Path(str(path).rsplit(".", 1)[0] + ".refs.json"),
                 *([Path(cache) / f"{name(aid)}.refs.json"] if aid and cache else [])]:
        if refs.is_file():
            return json.loads(refs.read_text())
    if aid and cache and not os.environ.get("PATHFINDER_OFFLINE"):
        try:
            Path(cache).mkdir(parents=True, exist_ok=True)
            _wait_turn(Path(cache))                   # the shared arXiv spacing, though the fetch lands in a scratch directory
            with tempfile.TemporaryDirectory(prefix="paper-source-refs-") as tmp:
                _fetch(aid, Path(tmp), urlopen)
                found = json.loads((Path(tmp) / f"{name(aid)}.refs.json").read_text())
            Path(cache).mkdir(parents=True, exist_ok=True)
            (Path(cache) / f"{name(aid)}.refs.json").write_text(json.dumps(found))
            return found
        except Exception:
            pass
    return _refs_in([Path(path).read_text(errors="replace")], aid or "")


@contextmanager
def _locked(cache: Path, key: str):
    """Process-safe fetch ownership, released by the OS even if the downloader dies."""
    locks = cache / ".locks"
    locks.mkdir(parents=True, exist_ok=True)
    path = locks / hashlib.sha256(key.encode()).hexdigest()
    with path.open("a") as handle:
        deadline = time.monotonic() + LOCK_WAIT
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"another process is fetching {key}; try again later")
                time.sleep(0.1)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def get(aid: str, cache, also=(), urlopen=None) -> Path:
    """The paper's text: from the cache (or the extra read-only dirs), else fetched once into the cache."""
    cache = Path(cache)
    hit = lookup(aid, [cache, *also])
    if hit:
        return hit
    if os.environ.get("PATHFINDER_OFFLINE"):
        raise RuntimeError("not cached, and downloads are off (PATHFINDER_OFFLINE)")
    with _locked(cache, f"arxiv:{aid}"):
        hit = lookup(aid, [cache, *also])
        return hit or _fetch(aid, cache, urlopen)


def _wait_turn(cache: Path, name: str = ".last-request", spacing: float = SPACING):
    """One request every `spacing` seconds to a service across processes: a timestamp file in the cache."""
    with _locked(cache, f"rate:{name}"):
        stamp = cache / name
        try:
            last = float(stamp.read_text())
        except (OSError, ValueError):
            last = 0.0
        pause = last + spacing - time.time()
        if pause > 0:
            time.sleep(pause)
        stamp.write_text(str(time.time()))


def _download(aid: str, cache: Path, urlopen=None):
    _wait_turn(cache)
    req = urllib.request.Request(f"https://arxiv.org/e-print/{aid}", headers={"User-Agent": "pathfinder/0.1"})
    if urlopen is None:                           # proxies from the environment only (pathfinder.net)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler(urllib.request.getproxies_environment()))
        urlopen = opener.open
    with urlopen(req, timeout=120) as r:
        return r.read(), r.headers.get("Content-Type", "")


def _main_tex(work: Path) -> Path | None:
    found = [p for p in work.rglob("*.tex") if re.search(r"\\document(class|style)\b", p.read_text(errors="replace"))]
    return min(found, key=lambda p: (len(p.parts), p.name not in ("main.tex", "ms.tex", "paper.tex"))) if found else None


def inline(path: Path, base: Path, depth: int = 0) -> str:
    """\\input and \\include inlined from files inside base, comment lines left alone: latexpand's fallback."""
    out = []
    for line in path.read_text(errors="replace").splitlines():
        if line.lstrip().startswith("%") or depth > 20:
            out.append(line); continue

        def sub(m):
            given = m.group(2).strip()
            for cand in (path.parent / given, path.parent / f"{given}.tex", base / given, base / f"{given}.tex"):
                if cand.is_file() and cand.resolve().is_relative_to(base.resolve()):
                    return inline(cand, base, depth + 1)
            return m.group(0)
        out.append(_INPUT.sub(sub, line))
    return "\n".join(out) + "\n"


def _refs(work: Path, own: str) -> list[str]:
    """The arXiv ids, and as "doi:..." the DOIs of entries with no arXiv id, that the bibliography names."""
    return _refs_in([p.read_text(errors="replace") for p in [*work.rglob("*.bbl"), *work.rglob("*.bib"),
                                                               *work.rglob("*.tex")]], own)


def _refs_in(texts, own: str) -> list[str]:
    found = []
    for text in texts:
        for entry in re.split(r"\\bibitem|\n@", text):
            ids = [m.group(1) for m in (*_IN_TEXT.finditer(entry), *_EPRINT_FIELD.finditer(entry))]
            refs = ids or [f"doi:{m.group(1).rstrip('.')}" for m in _DOI_IN_TEXT.finditer(entry)][:1]
            for r in refs:
                if r not in found and r != re.sub(r"v\d+$", "", own):
                    found.append(r)
    return found


def _fetch(aid: str, cache: Path, urlopen=None) -> Path:
    try:
        blob, ctype = _download(aid, cache, urlopen)
    except urllib.error.HTTPError as error:
        if error.code not in (404, 410):
            raise                               # a transient failure does not mean LaTeX is unavailable
        return _arxiv_pdf(aid, cache, urlopen)
    with tempfile.TemporaryDirectory(prefix="arxiv-source-") as tmp:
        work = Path(tmp)
        if blob[:4] == b"%PDF" or "pdf" in ctype:
            if not blob.startswith(b"%PDF"):
                raise RuntimeError("the e-print response is not a PDF")
            return _store_pdf(aid, cache, blob)
        try:
            with tarfile.open(fileobj=io.BytesIO(blob), mode="r:*") as tf:
                tf.extractall(work, filter="data")
        except tarfile.ReadError:
            try:
                (work / "main.tex").write_bytes(gzip.decompress(blob))
            except OSError:
                (work / "main.tex").write_bytes(blob)
        main = _main_tex(work)
        if main is None:
            return _arxiv_pdf(aid, cache, urlopen)
        text = None
        if shutil.which("latexpand"):
            try:
                r = subprocess.run(["latexpand", "--empty-comments", main.name], cwd=main.parent, capture_output=True,
                                   text=True, errors="replace", timeout=120)
                text = r.stdout if r.returncode == 0 and r.stdout.strip() else None
            except subprocess.TimeoutExpired:
                pass
        if text is None:
            text = inline(main, work)
        return _store(aid, cache, text, ".tex", _refs(work, aid))


def _arxiv_pdf(aid: str, cache: Path, urlopen=None) -> Path:
    _wait_turn(cache)
    existing = cache / f"{name(aid)}.pdf"
    blob = existing.read_bytes() if existing.is_file() else _pdf_bytes(f"https://arxiv.org/pdf/{aid}", urlopen)
    return _store_pdf(aid, cache, blob)


def _store_pdf(aid: str, cache: Path, blob: bytes) -> Path:
    """Called only after the source lookup establishes that LaTeX is unavailable."""
    original = _store(aid, cache, blob, ".pdf", [])
    text = subprocess.run(["pdftotext", "-layout", str(original), "-"], capture_output=True,
                          text=True, errors="replace", timeout=300, check=True).stdout
    if not text.strip():
        raise RuntimeError("the PDF has no extractable text")
    path = _store(aid, cache, text, ".txt", [])
    marker = path.with_suffix(".source.json")
    temporary = marker.with_name(f".{marker.name}.{os.getpid()}")
    temporary.write_text(json.dumps({"latex_unavailable": True, "pdf": original.name}))
    os.replace(temporary, marker)
    return path


def _store(aid: str, cache: Path, text: str | bytes, suffix: str, refs: list[str]) -> Path:
    dst = cache / f"{name(aid)}{suffix}"
    tmp = dst.with_name(f".{dst.name}.{os.getpid()}")
    tmp.write_bytes(text if isinstance(text, bytes) else text.encode()); os.replace(tmp, dst)
    (cache / f"{name(aid)}.refs.json").write_text(json.dumps(refs))
    with open(cache / "index.jsonl", "a") as f:
        f.write(json.dumps({"id": aid, "path": dst.name, "kind": suffix[1:], "references": len(refs),
                            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")
    return dst


def kind(ref: str) -> tuple[str, str]:
    """("arxiv", id), ("doi", doi), ("url", url) or ("title", title) for a reference as written."""
    ref = " ".join(str(ref).split())
    if parse(ref):
        return "arxiv", parse(ref)
    m = _ARXIV_URL.search(ref)
    if m and parse(m.group(1)):
        return "arxiv", parse(m.group(1))
    m = _DOI.match(ref)
    if m:
        return "doi", m.group(1).rstrip(".")
    if re.match(r"https?://", ref):
        return "url", ref
    return "title", re.sub(r"^title:\s*", "", ref, flags=re.I)


def _alias_key(ref: str) -> str:
    k, v = kind(ref)
    return f"{k}:{v.lower()}"


def _aliases(cache: Path) -> dict:
    out = {}
    path = cache / "aliases.jsonl"
    for line in path.read_text().splitlines() if path.is_file() else []:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        out[row.get("ref")] = row                  # the latest resolution of a reference wins
    return out


def _record(cache: Path, ref: str, **fields):
    with open(cache / "aliases.jsonl", "a") as f:
        f.write(json.dumps({"ref": _alias_key(ref), **fields, "at": time.time()}) + "\n")


def _s2(path: str, cache: Path, urlopen=None):
    """One Semantic Scholar lookup: the record, or None when it has none."""
    _wait_turn(cache, ".last-s2", 1.0)
    headers = {"User-Agent": "pathfinder/0.1"}
    if os.environ.get("SEMANTIC_SCHOLAR_API_KEY"):
        headers["x-api-key"] = os.environ["SEMANTIC_SCHOLAR_API_KEY"]
    req = urllib.request.Request(S2 + path, headers=headers)
    opener = urlopen or urllib.request.build_opener(urllib.request.ProxyHandler(urllib.request.getproxies_environment())).open
    try:
        with opener(req, timeout=60) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise
    return data.get("data", [None])[0] if "data" in data else data


def _record_for(k: str, v: str, cache: Path, urlopen=None):
    fields = "?fields=externalIds,title,openAccessPdf"
    if k == "doi":
        return _s2(f"DOI:{urllib.parse.quote(v, safe='/')}{fields}", cache, urlopen)
    if k == "url":
        return _s2(f"URL:{urllib.parse.quote(v, safe='')}{fields}", cache, urlopen)
    return _s2(f"search/match?query={urllib.parse.quote(v)}&fields=externalIds,title,openAccessPdf", cache, urlopen)


def resolve(ref: str, cache, also=(), urlopen=None) -> Path:
    """Local pool first, then LaTeX, then PDF extraction when no LaTeX source is available."""
    cache = Path(cache)
    k, v = kind(ref)
    if k == "arxiv":
        return get(v, cache, also, urlopen)
    hit, known = _known(ref, [cache, *also])
    if hit:
        return hit
    if known and known.get("arxiv"):
        return get(known["arxiv"], cache, also, urlopen)
    if known and not known.get("found", True) and time.time() - known.get("at", 0) < NOT_FOUND_RETRY:
        raise RuntimeError(f"no open version found ({known.get('reason')})")
    if os.environ.get("PATHFINDER_OFFLINE"):
        raise RuntimeError("not cached, and downloads are off (PATHFINDER_OFFLINE)")
    with _locked(cache, _alias_key(ref)):
        hit, known = _known(ref, [cache, *also])
        if hit:
            return hit
        return _resolve(ref, cache, also, urlopen)


def _known(ref: str, dirs) -> tuple[Path | None, dict | None]:
    known = None
    hits = []
    for directory in dirs:
        row = _aliases(Path(directory)).get(_alias_key(ref))
        if not row:
            continue
        known = known or row
        if row.get("arxiv"):
            path = lookup(row["arxiv"], dirs)
        else:
            path = Path(directory) / row["path"] if row.get("path") else None
            if path and path.with_suffix(".tex").is_file():
                path = path.with_suffix(".tex")
        if (path and path.is_file() and path.stat().st_size
                and (path.suffix.lower() == ".tex" or (path.suffix.lower() == ".txt" and _pdf_text_ready(path)))):
            hits.append(path)
    return (min(hits, key=lambda p: p.suffix != ".tex") if hits else None), known


def _resolve(ref: str, cache: Path, also, urlopen) -> Path:
    k, v = kind(ref)
    record = _record_for(k, v, cache, urlopen)
    arxiv = parse(((record or {}).get("externalIds") or {}).get("ArXiv") or "")
    if arxiv:
        path = get(arxiv, cache, also, urlopen)
        _remember(cache, ref, path, record, arxiv=arxiv)
        return path
    pdf = ((record or {}).get("openAccessPdf") or {}).get("url") or (v if k == "url" else None)
    if not pdf:
        _record(cache, ref, found=False, reason="not on arXiv and no open PDF")
        raise RuntimeError("not on arXiv and no open PDF")
    try:
        path = _pdf(ref, pdf, cache, urlopen)
    except Exception as error:
        _record(cache, ref, found=False, reason=f"open PDF failed: {error}"[:200])
        raise
    _remember(cache, ref, path, record, pdf=pdf)
    return path


def _remember(cache, ref, path, record, **fields):
    """Index the known DOI, title and open-copy URL so other agents can find this paper locally."""
    record = record or {}
    refs = []
    doi = (record.get("externalIds") or {}).get("DOI")
    if doi:
        refs.append(f"doi:{doi}")
    if record.get("title"):
        refs.append(f"title:{record['title']}")
    if (record.get("openAccessPdf") or {}).get("url"):
        refs.append(record["openAccessPdf"]["url"])
    for alias in dict.fromkeys([*refs, ref]):
        _record(cache, alias, path=str(path.resolve()), found=True, title=record.get("title"), **fields)


def _pdf(ref: str, url: str, cache: Path, urlopen=None) -> Path:
    """Share a PDF and its extracted text by URL, including different DOI/title aliases."""
    key = hashlib.sha256(url.encode()).hexdigest()[:20]
    target = cache / "other"
    dst = target / f"{key}.txt"
    with _locked(cache, f"pdf:{url}"):
        if dst.is_file() and dst.stat().st_size and _pdf_text_ready(dst):
            return dst
        _wait_turn(cache, ".last-pdf", 1.0)
        original = dst.with_suffix(".pdf")
        blob = original.read_bytes() if original.is_file() else _pdf_bytes(url, urlopen)
        target.mkdir(parents=True, exist_ok=True)
        return _store_pdf(key, target, blob)


def _pdf_bytes(url: str, urlopen=None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "pathfinder/0.1"})
    opener = urlopen or urllib.request.build_opener(urllib.request.ProxyHandler(urllib.request.getproxies_environment())).open
    with opener(req, timeout=120) as r:
        blob = r.read()
    if blob[:4] != b"%PDF":
        raise RuntimeError("the open copy is not a PDF")
    return blob


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="paper_source", description=__doc__.split("\n\n")[0])
    ap.add_argument("--cache", required=True); ap.add_argument("--also", action="append", default=[])
    ap.add_argument("ids", nargs="+", metavar="REF", help="an arXiv id, a DOI, a URL or title:...")
    ns = ap.parse_args(argv)
    failed = False
    for raw in ns.ids:
        try:
            print(f"{raw} {resolve(raw, ns.cache, ns.also)}")
        except Exception as error:
            print(f"{raw} ERROR {error}"); failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
