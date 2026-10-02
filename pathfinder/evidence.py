"""Evidence citations, their resolution, and typed evidence errors.

A ledger cites many things that look like paths: page and equation locators, ratios, DOIs, URLs and
repository names. Only file citations become dependencies. A file cited from a joint thread may live in
one of its branch bundles, and a campaign source may be cited by its campaign path; both resolve before a
citation counts as missing, and an ambiguity is reported, never settled by sort order. Paths are read
from ledger text and declarations only, never mined from code."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path

PATH = re.compile(r"(?<![\w:/@.-])(?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9]+")
URL = re.compile(r"\b[a-z][a-z0-9+.-]*://\S+", re.I)
# A locator needs a number after its dot (p.1653, Eq.1, Fig.3); app.py, table.csv and sec.data/ are files.
LOCATOR = re.compile(r"(?:^|/)(?:p|pp|eq|eqs|fig|figs|table|tab|sec|thm|lem|prop|def|ch|app|alg)\.\d[\w.-]*$", re.I)
FILE_EXTENSION = re.compile(r"\.[A-Za-z]{1,5}$")
NUMBER = re.compile(r"^[\d.]+(?:/[\d.]+)+$")
DOI = re.compile(r"^10\.\d{4,9}/")


def classify(token: str) -> str:
    if DOI.match(token):
        return "doi"
    if NUMBER.match(token):
        return "number"
    if token.endswith(".git"):
        return "repository"
    if FILE_EXTENSION.search(token):                 # fig.1.png ends like a file, whatever comes before
        return "file"
    if LOCATOR.search(token) or any(LOCATOR.search(part) for part in token.split("/")[:-1]):
        return "locator"
    return "file"


def cited_files(text: str) -> list[str]:
    stripped = URL.sub(" ", text)                       # a URL's path is not a local file
    out = []
    for token in PATH.findall(stripped):
        if classify(token) == "file" and token not in out:
            out.append(token)
    return out


@dataclass(frozen=True)
class Resolution:
    kind: str                                  # local, namespace, source, missing or ambiguous
    path: Path | None = None
    candidates: tuple = ()


def resolve(d: Path, name: str, bundles: list[str], sources: dict) -> Resolution:
    """Where a cited file is: in the thread, in exactly one branch bundle under the same relative name,
    or as a campaign source registered for this pair. Two bundle matches are an ambiguity."""
    if (d / name).is_file():
        return Resolution("local", d / name)
    matches = tuple(f"{b}/{name}" for b in bundles if (d / b / name).is_file())
    if len(matches) == 1:
        return Resolution("namespace", d / matches[0], matches)
    if len(matches) > 1:
        return Resolution("ambiguous", None, matches)
    if name in sources:
        return Resolution("source", sources[name])
    return Resolution("missing")


def registered_sources(campaign, pair_id: str) -> dict:
    """Campaign files named by the pair's corpus rows (text, raw, any string field), by campaign-relative path."""
    import json
    m = re.fullmatch(r"Q(\d+)P(\d+)", pair_id)
    if not m:
        return {}
    root = Path(campaign.root).resolve()
    out = {}
    for side, index in (("Q", int(m.group(1))), ("P", int(m.group(2)))):
        path = campaign.path(f"{side}.jsonl")
        rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.is_file() else []
        row = rows[index - 1] if 0 < index <= len(rows) else {}
        for key, value in row.items():
            # the pair's own text, or a manifestation kept under sources/; never '..', never another thread
            if not isinstance(value, str) or "/" not in value or Path(value).is_absolute() or ".." in Path(value).parts:
                continue
            if key != "text" and not value.startswith("sources/"):
                continue
            target = (root / value).resolve()
            if target.is_relative_to(root) and target.is_file():
                out[value] = target
    return out


def __getattr__(name):
    if name == "EvidenceError":                 # defined beside EvidenceUnavailable, so every existing catch holds
        from .research import EvidenceError
        return EvidenceError
    raise AttributeError(name)


def manifest(campaign, pair_id: str) -> dict:
    """Build the pair's review material once, which refreshes its evidence-manifest.json, and return it."""
    import json
    from . import research
    try:
        research._review_material(campaign, pair_id)
    except research.EvidenceUnavailable:
        pass
    return json.loads((campaign.thread_dir(pair_id) / "evidence-manifest.json").read_text())


def proposals(m: dict, d: Path) -> list[dict]:
    """One proposed declaration per evidence error; nothing is written. The ledger entry binding (seq and
    text_sha256) is filled in so a declaration can be pasted into external-references.json."""
    import hashlib, json
    def ledger(origin):
        path = (d / origin / "ledger.jsonl") if origin else (d / "ledger.jsonl")
        return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.is_file() else []

    out = []
    for error in m.get("errors", []):
        path, origin = error.get("path"), error.get("origin")
        cited = error.get("cited") or (path[len(origin) + 1:] if origin and path and path.startswith(origin + "/") else path)
        entry = next((r for r in ledger(origin) if cited and cited in cited_files(r.get("text", ""))), None)
        binding = {"ledger_seq": entry["seq"], "text_sha256": hashlib.sha256(entry["text"].encode()).hexdigest()} if entry else {}
        if error["code"] == "missing":
            out.append({"path": path, **binding, "choices": ["unavailable (give the URL where it should be)",
                                                            "output (the cited work writes it; it was not produced)",
                                                            "external (give the URL)"]})
        elif error["code"] == "ambiguous":
            out.append({"path": path, **binding, "candidates": error.get("detail"),
                        "choices": ["declare which candidate the entry means"]})
        else:
            out.append({"path": path, **binding, "choices": [f"repair the file: {error['message']}"]})
    return out


def text(m: dict, proposed: list[dict]) -> str:
    lines = [f"evidence manifest, {m.get('generated_at')}: {len(m.get('files', []))} entries, {len(m.get('errors', []))} errors"]
    for f in m.get("files", []):
        size = f" {f['bytes']} bytes" if f.get("bytes") is not None else ""
        lines.append(f"  {f['kind']:<15} {f['path']}{size}" + (f"  (cited as {f['cited']})" if f.get("cited") and f["cited"] != f["path"] else ""))
    for e in m.get("errors", []):
        lines.append(f"error {e['code']}: {e['message']}")
    for p in proposed:
        lines.append(f"proposal for {p['path']}: " + " | ".join(p["choices"]) + (f" (ledger entry {p['ledger_seq']})" if p.get("ledger_seq") else ""))
    return "\n".join(lines)


def apply_declarations(campaign, pair_id: str, records: list[dict]) -> dict:
    """Merge declarations into external-references.json as one validated change (R02): records replace those
    with the same (document, ledger_seq, path); the merged file is checked by the same parser on a temporary
    copy, then swapped in atomically, and the change is appended to declarations-history.jsonl. Applying the
    same records again changes nothing."""
    import hashlib, json, os, tempfile, time
    from . import research
    if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
        raise research.EvidenceUnavailable("declarations must be a list of JSON objects")
    d = campaign.thread_dir(pair_id)
    target = d / "external-references.json"
    before = target.read_bytes() if target.is_file() else None
    current = json.loads(before) if before else {"version": 1, "references": []}
    key = lambda r: (r.get("document"), r.get("ledger_seq"), r.get("path"))
    merged = {key(r): r for r in current.get("references", [])}
    for record in records:
        merged[key(record)] = record
    content = json.dumps({"version": 1, "references": list(merged.values())}, indent=1).encode()
    digest = lambda data: hashlib.sha256(data).hexdigest() if data is not None else None
    if before is not None and digest(before) == digest(content):
        return {"changed": False, "before_sha256": digest(before), "after_sha256": digest(before)}
    handle, temporary = tempfile.mkstemp(dir=d, prefix=".external-references.", suffix=".json")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
        research._external_citations(d, path=temporary)        # raises before anything is replaced
        if before is not None and json.loads(before) == json.loads(content):
            return {"changed": False, "before_sha256": digest(before), "after_sha256": digest(before)}
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    change = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "before_sha256": digest(before),
              "after_sha256": digest(content), "records": records}
    with (d / "declarations-history.jsonl").open("a") as stream:
        stream.write(json.dumps(change) + "\n")
    return {"changed": True, "before_sha256": change["before_sha256"], "after_sha256": change["after_sha256"]}
