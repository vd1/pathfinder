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
import argparse, gzip, io, json, os, re, shutil, subprocess, sys, tarfile, tempfile, time
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
    """A cached text of the paper in any of dirs: <name>.tex, then <name>.txt, also the older nested layout
    (math/0601001.tex)."""
    for d in dirs:
        d = Path(d)
        for f in (d / f"{name(aid)}.tex", d / f"{aid}.tex", d / f"{name(aid)}.txt", d / f"{aid}.txt"):
            if f.is_file() and f.stat().st_size > 0:
                return f
    return None


def references(path: Path, aid: str | None = None, cache=None, urlopen=None) -> list[str]:
    """The arXiv ids and DOIs the paper's bibliography names: kept by the fetch beside the paper (or in the
    cache); for a text fetched before that was kept, read again from the e-print once (its .bbl and .bib are
    not in the flattened text) and kept, or offline read from the text itself."""
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


def get(aid: str, cache, also=(), urlopen=None) -> Path:
    """The paper's text: from the cache (or the extra read-only dirs), else fetched once into the cache."""
    cache = Path(cache)
    hit = lookup(aid, [cache, *also])
    if hit:
        return hit
    if os.environ.get("PATHFINDER_OFFLINE"):
        raise RuntimeError("not cached, and downloads are off (PATHFINDER_OFFLINE)")
    cache.mkdir(parents=True, exist_ok=True)
    lock = cache / f".{name(aid)}.lock"
    deadline = time.time() + LOCK_WAIT
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.close(fd); break
        except FileExistsError:                   # another process is fetching it: wait for its result
            if time.time() > deadline:
                lock.unlink(missing_ok=True)
            time.sleep(2)
            hit = lookup(aid, [cache])
            if hit:
                return hit
    try:
        hit = lookup(aid, [cache])
        return hit or _fetch(aid, cache, urlopen)
    finally:
        lock.unlink(missing_ok=True)


def _wait_turn(cache: Path, name: str = ".last-request", spacing: float = SPACING):
    """One request every `spacing` seconds to a service across processes: a timestamp file in the cache."""
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
    blob, ctype = _download(aid, cache, urlopen)
    with tempfile.TemporaryDirectory(prefix="arxiv-source-") as tmp:
        work = Path(tmp)
        if blob[:4] == b"%PDF" or "pdf" in ctype:
            (work / "paper.pdf").write_bytes(blob)     # a PDF-only submission: the one case for pdftotext
            text = subprocess.run(["pdftotext", "-layout", str(work / "paper.pdf"), "-"], capture_output=True,
                                  text=True, errors="replace", timeout=300, check=True).stdout
            return _store(aid, cache, text, ".txt", [])
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
            raise RuntimeError("the e-print holds no .tex file with \\documentclass")
        text = None
        if shutil.which("latexpand"):
            r = subprocess.run(["latexpand", "--empty-comments", main.name], cwd=main.parent, capture_output=True,
                               text=True, errors="replace", timeout=120)
            text = r.stdout if r.returncode == 0 and r.stdout.strip() else None
        if text is None:
            text = inline(main, work)
        return _store(aid, cache, text, ".tex", _refs(work, aid))


def _store(aid: str, cache: Path, text: str, suffix: str, refs: list[str]) -> Path:
    dst = cache / f"{name(aid)}{suffix}"
    tmp = dst.with_name(f".{dst.name}.{os.getpid()}")
    tmp.write_text(text); os.replace(tmp, dst)
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
    """The paper a reference names, from the cache or fetched once: its arXiv source when it is on arXiv, else
    the text of its open PDF; the resolution is recorded so that the same reference is a hit next time."""
    cache = Path(cache)
    k, v = kind(ref)
    if k == "arxiv":
        return get(v, cache, also, urlopen)
    known = _aliases(cache).get(_alias_key(ref))
    if known and known.get("arxiv"):
        return get(known["arxiv"], cache, also, urlopen)
    if known and known.get("path") and (cache / known["path"]).is_file():
        return cache / known["path"]
    if known and not known.get("found", True) and time.time() - known.get("at", 0) < NOT_FOUND_RETRY:
        raise RuntimeError(f"no open version found ({known.get('reason')})")
    if os.environ.get("PATHFINDER_OFFLINE"):
        raise RuntimeError("not cached, and downloads are off (PATHFINDER_OFFLINE)")
    cache.mkdir(parents=True, exist_ok=True)
    record = _record_for(k, v, cache, urlopen)
    arxiv = parse(((record or {}).get("externalIds") or {}).get("ArXiv") or "")
    if arxiv:
        path = get(arxiv, cache, also, urlopen)
        _record(cache, ref, arxiv=arxiv, path=path.name, found=True, title=(record or {}).get("title"))
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
    _record(cache, ref, path=path.relative_to(cache).as_posix(), found=True, pdf=pdf, title=(record or {}).get("title"))
    return path


def _pdf(ref: str, url: str, cache: Path, urlopen=None) -> Path:
    """A paper that is not on arXiv: its open PDF, fetched once and kept as text under other/."""
    import hashlib
    _wait_turn(cache, ".last-pdf", 1.0)
    req = urllib.request.Request(url, headers={"User-Agent": "pathfinder/0.1"})
    opener = urlopen or urllib.request.build_opener(urllib.request.ProxyHandler(urllib.request.getproxies_environment())).open
    with opener(req, timeout=120) as r:
        blob = r.read()
    if blob[:4] != b"%PDF":
        raise RuntimeError("the open copy is not a PDF")
    with tempfile.TemporaryDirectory(prefix="paper-source-") as tmp:
        (Path(tmp) / "paper.pdf").write_bytes(blob)
        text = subprocess.run(["pdftotext", "-layout", str(Path(tmp) / "paper.pdf"), "-"], capture_output=True,
                              text=True, errors="replace", timeout=300, check=True).stdout
    dst = cache / "other" / f"{hashlib.sha256(_alias_key(ref).encode()).hexdigest()[:20]}.txt"
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(f".{dst.name}.{os.getpid()}")
    tmp.write_text(text); os.replace(tmp, dst)
    return dst


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
