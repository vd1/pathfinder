# Phase 3b: Typed evidence citations, namespace and source resolution, typed errors, manifest

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evidence checks stop blocking on things that are not files and stop missing files that exist elsewhere: citations are typed (file, locator, number, DOI, URL, repository), a cited file missing in the thread is resolved through the branch bundles' namespaces and through the pair's registered campaign sources before it counts as missing, every problem is reported as a typed error and all of them at once, declared planned outputs are gaps rather than dependencies, and each review writes one evidence manifest that an operator can inspect with `pathfinder evidence PAIR`.

**Architecture:** A new `pathfinder/evidence.py` holds citation typing (`cited_files`), resolution (`resolve`) and the error type (`EvidenceError`, a subclass of `research.EvidenceUnavailable` so every existing catch still works). `research._assessment_evidence` keeps its signature and validations, delegates extraction and resolution to `evidence`, records one entry per file in an optional `record` list, collects strict-mode errors and raises them together. `external-references.json` gains the status `output`. `research._review_material` writes `evidence-manifest.json` in the thread. `pathfinder evidence` prints it with proposals.

**Tech Stack:** Python 3.13, pytest, behave.

**Spec:** `notes/pathfinder-friction.tex` section "Evidence and state failures from julien-2" (F01 to F06, F08, R01, R03), source `pathfinder-julien-2/reviews/pathfinder-failure-modes-2026-10-01T002939+0200.md`. F07 and R02 (reconciliation, atomic repair) are phase 4.

## Global Constraints

- Tests: `uv run --offline --locked pytest -q <files>`; full suite over two minutes; never edit engine files while it runs.
- Baseline: record the numbers of the full suite and behave on the base commit in the ledger before Task 1 (expected: 323 passed, 1 failed statarb deployment; behave 93 passed, 1 failed, 9 error).
- Existing behaviour must hold: aliased and outside paths always block; under `strict_evidence` missing, unreadable and non-text files block; otherwise they are listed. Existing messages keep their prefixes (`aliased evidence path:`, `evidence outside the investigation:`, `missing evidence:`, `unreadable evidence:`, `evidence not inlinable as text:`) because behave steps match them.
- Never execute scripts or mine paths from code files; citations come from ledger text and declarations only.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- `p.1653`, `prose/p.1653`, `Eq.1/p.1645`, `0.147008/0.707625`, `10.1103/PhysRevB.1.2`, `https://x.org/a.json`, `chemle/emle-engine.git` are not file dependencies; `ada/run.py` and `branches/b1/ada/out.json` are (Task 1 test).
- A joint citation `ada/audit.json` absent from the joint thread but present in exactly one bundle resolves to it; present in two bundles is an explicit ambiguity, never the first by sort order (Task 2 test).
- A cited campaign source `sources/P072/raw.json` registered for the pair resolves to the campaign file, by its own bytes; an unregistered campaign path stays missing (Task 2 test).
- Two missing files under `strict_evidence` produce one exception carrying both typed errors (Task 3 test).
- A declared planned output that does not exist is listed as a gap and does not block under strict mode (Task 4 test).

---

### Task 1: Typed citations

**Files:**
- Create: `pathfinder/evidence.py`
- Modify: `pathfinder/research.py` (`_evidence_references` delegates)
- Test: `tests/test_evidence.py`

**Interfaces:**
- Produces: `evidence.classify(token: str) -> str` returning one of `"file"`, `"locator"`, `"number"`, `"doi"`, `"url"`, `"repository"`; `evidence.cited_files(text: str) -> list[str]` (tokens of kind `file`, in order, duplicates kept once).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_evidence.py
import pytest
from pathfinder import evidence


@pytest.mark.parametrize("token,kind", [
    ("ada/run.py", "file"), ("branches/b1/ada/out.json", "file"), ("inputs/Q.tex", "file"),
    ("prose/p.1653", "locator"), ("Eq.1/p.1645", "locator"), ("ada/Fig.3", "locator"), ("sec/Table.2", "locator"),
    ("0.147008/0.707625", "number"), ("1.006/0.994", "number"),
    ("10.1103/PhysRevB.1.2", "doi"), ("chemle/emle-engine.git", "repository"),
])
def test_classify(token, kind):
    assert evidence.classify(token) == kind


def test_cited_files_keeps_only_files_and_skips_urls():
    text = ("see ada/run.py and https://x.org/data/a.json, eq. prose/p.1653, ratio 0.147008/0.707625, "
            "doi 10.1103/PhysRevB.1.2, repo chemle/emle-engine.git, and ada/run.py again")
    assert evidence.cited_files(text) == ["ada/run.py"]


def test_research_uses_typed_citations():
    from pathfinder import research
    assert research._evidence_references("prose/p.1653 and emmy/derivation.tex") == ["emmy/derivation.tex"]
```

- [ ] **Step 2: Run them and see them fail**

Run: `uv run --offline --locked pytest -q tests/test_evidence.py`
Expected: FAIL with `ImportError: cannot import name 'evidence'`.

- [ ] **Step 3: Implement**

```python
# pathfinder/evidence.py
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
LOCATOR = re.compile(r"(?:^|/)(?:p|pp|eq|eqs|fig|figs|table|tab|sec|thm|lem|prop|def|ch|app|alg)\.[\w.-]*$", re.I)
NUMBER = re.compile(r"^[\d.]+(?:/[\d.]+)+$")
DOI = re.compile(r"^10\.\d{4,9}/")


def classify(token: str) -> str:
    if DOI.match(token):
        return "doi"
    if NUMBER.match(token):
        return "number"
    if token.endswith(".git"):
        return "repository"
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
```

In `pathfinder/research.py`, replace the body of `_evidence_references`:

```python
def _evidence_references(text: str) -> list[str]:
    """Relative file paths cited in ledger text; locators, numbers, DOIs, URLs and repositories are not files."""
    from . import evidence
    return evidence.cited_files(text)
```

Keep `EVIDENCE_PATH` (other code may import it) as an alias: `EVIDENCE_PATH = evidence.PATH` is not possible without a circular import at module load, so leave the existing constant in place unchanged.

- [ ] **Step 4: Run, then the research tests and behave**

Run: `uv run --offline --locked pytest -q tests/test_evidence.py tests/test_research_revisions.py tests/test_agent_workspace.py` and the behave command.
Expected: all PASS; behave at baseline. If a scenario relied on a figure locator such as `/Fig.3` being exempt, it still is (locator).

- [ ] **Step 5: Commit**

```bash
git add pathfinder/evidence.py pathfinder/research.py tests/test_evidence.py
git commit -m "Typed evidence citations: locators, numbers, DOIs, URLs and repositories are not files

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Resolution through branch namespaces and registered sources

**Files:**
- Modify: `pathfinder/evidence.py` (`Resolution`, `resolve`, `registered_sources`), `pathfinder/research.py` (`_assessment_evidence`)
- Test: `tests/test_evidence.py`

**Interfaces:**
- Produces: `evidence.Resolution(kind: str, path: Path | None, candidates: tuple[str, ...])` with kinds `"local"`, `"namespace"`, `"source"`, `"missing"`, `"ambiguous"`; `evidence.resolve(d: Path, name: str, bundles: list[str], sources: dict[str, Path]) -> Resolution`; `evidence.registered_sources(campaign, pair_id: str) -> dict[str, Path]` (every string value of the pair's Q and P corpus rows that names an existing file under the campaign root, mapped to that file).

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_evidence.py
from pathlib import Path


def _tree(tmp_path, files):
    for name in files:
        p = tmp_path / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(name)
    return tmp_path


def test_resolution_order_and_ambiguity(tmp_path):
    d = _tree(tmp_path, ["ada/local.json", "branches/b1/ada/one.json", "branches/b1/ada/two.json", "branches/b2/ada/two.json"])
    bundles = ["branches/b1", "branches/b2"]
    assert evidence.resolve(d, "ada/local.json", bundles, {}).kind == "local"
    one = evidence.resolve(d, "ada/one.json", bundles, {})
    assert one.kind == "namespace" and one.path == d / "branches/b1/ada/one.json"
    two = evidence.resolve(d, "ada/two.json", bundles, {})
    assert two.kind == "ambiguous" and two.candidates == ("branches/b1/ada/two.json", "branches/b2/ada/two.json")
    assert evidence.resolve(d, "ada/none.json", bundles, {}).kind == "missing"


def test_registered_sources_resolve_by_their_own_bytes(tmp_path):
    import json, sys
    sys.path.insert(0, str(Path(__file__).parent))
    from stubcampaign import make
    c = make(tmp_path)
    raw = tmp_path / "sources" / "P001" / "raw.json"; raw.parent.mkdir(parents=True); raw.write_text("{}")
    rows = [json.loads(l) for l in c.path("P.jsonl").read_text().splitlines()]
    rows[0]["raw"] = "sources/P001/raw.json"
    c.path("P.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    sources = evidence.registered_sources(c, "Q1P1")
    d = c.thread_dir("Q1P1"); d.mkdir(parents=True)
    got = evidence.resolve(d, "sources/P001/raw.json", [], sources)
    assert got.kind == "source" and got.path == raw
    assert evidence.resolve(d, "sources/P002/raw.json", [], sources).kind == "missing"


def test_strict_review_reads_a_namespaced_file_instead_of_blocking(tmp_path):
    from pathfinder import research
    from stubcampaign import make
    c = make(tmp_path, research_scheme="eva_minus", strict_evidence=True, research_bundles=["branches/b1"])
    d = research.prepare(c, "Q1P1")
    _tree(d, ["branches/b1/ledger.jsonl", "branches/b1/ada/audit.json"])
    (d / "branches/b1/ledger.jsonl").write_text("")
    from pathfinder.ledger import Ledger
    Ledger(d / "ledger.jsonl").add("ada", "finding", "see ada/audit.json")
    material = research._review_material(c, "Q1P1")
    assert "branches/b1/ada/audit.json" in material
```

- [ ] **Step 2: Run them and see them fail**

Run: `uv run --offline --locked pytest -q tests/test_evidence.py -k "resolution or registered or namespaced"`
Expected: FAIL (`resolve` missing; strict review raises `missing evidence: ada/audit.json`).

- [ ] **Step 3: Implement**

Append to `pathfinder/evidence.py`:

```python
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
        for value in row.values():
            if isinstance(value, str) and "/" in value and not value.startswith(("http://", "https://")):
                target = (root / value).resolve()
                if target.is_relative_to(root) and target.is_file():
                    out[value] = target
    return out
```

In `research._assessment_evidence`, keep `paths` as the set of candidate paths, but build it from names: replace

```python
            paths.update(d / name for name in _evidence_references(row["text"])
                         if ("ledger.jsonl", row["seq"], name) not in citations)
```

with

```python
            for name in _evidence_references(row["text"]):
                if ("ledger.jsonl", row["seq"], name) in citations:
                    continue
                found = evidence.resolve(d, name, bundles, sources)
                if found.kind in ("namespace", "source"):
                    resolved[found.path] = (name, found.kind)
                    paths.add(found.path)
                elif found.kind == "ambiguous":
                    ambiguous[name] = found.candidates
                else:
                    paths.add(d / name)
```

with, before the loop, `from . import evidence`, `bundles = list((campaign.raw or {}).get("research_bundles") or [])`, `sources = evidence.registered_sources(campaign, d.name)`, `resolved, ambiguous = {}, {}`. In the per-path loop, compute `relative` as today for thread paths; for a path in `resolved`, render its heading as `## {cited name} (resolved to {path relative to d, or "campaign:" + path relative to campaign root for a source})` and skip the outside-the-investigation check for kind `source` only (it is registered). For each `ambiguous` name, under `strict_evidence` raise (Task 3 collects it) `missing evidence: {name} (ambiguous: {", ".join(candidates)})`; otherwise append `## {name}\n\n(cited in the ledger; ambiguous between {candidates}; declare which one)`.

- [ ] **Step 4: Run, then the research tests and behave**

Run: `uv run --offline --locked pytest -q tests/test_evidence.py tests/test_research_revisions.py tests/test_agent_workspace.py` and the behave command.
Expected: all PASS; behave at baseline.

- [ ] **Step 5: Commit**

```bash
git add pathfinder/evidence.py pathfinder/research.py tests/test_evidence.py
git commit -m "Cited files resolve through branch namespaces and registered campaign sources; ambiguity is explicit

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Typed errors, all of them at once

**Files:**
- Modify: `pathfinder/evidence.py` (`EvidenceError`), `pathfinder/research.py` (`_assessment_evidence` raises at the end)
- Test: `tests/test_evidence.py`

**Interfaces:**
- Produces: `evidence.EvidenceError(errors: list[dict])`, subclass of `research.EvidenceUnavailable`, whose `str()` is the first error's message plus `" (and N more: ...)"`; each error dict has `code` (`aliased`, `outside`, `missing`, `ambiguous`, `unreadable`, `not_text`), `path`, `detail`, `message`.

`EvidenceError` must subclass `research.EvidenceUnavailable`; define it in `evidence.py` with a function-level import to avoid a cycle, or define the class in `research.py` next to `EvidenceUnavailable` and re-export it from `evidence` (`from .research import EvidenceError` inside `evidence` functions). Choose the second: `class EvidenceError(EvidenceUnavailable)` in `research.py`, and `evidence.EvidenceError` resolved lazily through `__getattr__` in `evidence.py`:

```python
def __getattr__(name):
    if name == "EvidenceError":
        from .research import EvidenceError
        return EvidenceError
    raise AttributeError(name)
```

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_evidence.py
def test_all_strict_errors_are_reported_together(tmp_path):
    from pathfinder import research
    from pathfinder.ledger import Ledger
    from stubcampaign import make
    c = make(tmp_path, research_scheme="eva_minus", strict_evidence=True)
    d = research.prepare(c, "Q1P1")
    Ledger(d / "ledger.jsonl").add("ada", "finding", "see ada/one.json and ada/two.json")
    with pytest.raises(research.EvidenceUnavailable) as raised:
        research._review_material(c, "Q1P1")
    error = raised.value
    assert isinstance(error, evidence.EvidenceError)
    assert [e["path"] for e in error.errors] == ["ada/one.json", "ada/two.json"]
    assert all(e["code"] == "missing" for e in error.errors)
    assert str(error).startswith("missing evidence: ada/one.json") and "and 1 more" in str(error)
```

- [ ] **Step 2: Run and see it fail**

Run: `uv run --offline --locked pytest -q tests/test_evidence.py -k together`
Expected: FAIL (the first missing file raises alone; no `EvidenceError`).

- [ ] **Step 3: Implement**

In `research.py`, after `EvidenceUnavailable`:

```python
class EvidenceError(EvidenceUnavailable):
    """Every evidence problem of one review, typed, so each can be repaired on its own (R03)."""

    def __init__(self, errors: list[dict]):
        self.errors = errors
        first = errors[0]["message"]
        more = f" (and {len(errors) - 1} more: " + "; ".join(e["message"] for e in errors[1:]) + ")" if len(errors) > 1 else ""
        super().__init__(first + more)
```

In `_assessment_evidence`, replace each `raise EvidenceUnavailable(f"<prefix> {relative}...")` inside the per-path loop by appending `{"code": ..., "path": str(relative), "detail": ..., "message": <the same text>}` to an `errors` list and `continue`; keep the immediate `raise` only for problems in `_external_citations` (a broken declaration). After the loop: `if errors: raise EvidenceError(errors)`. The ambiguity errors from Task 2 join the same list with code `ambiguous`. Aliased and outside paths are appended under both strict and non-strict modes (they always block); missing, unreadable and not-text only under strict, as today.

- [ ] **Step 4: Run, then research tests and behave**

Run: `uv run --offline --locked pytest -q tests/test_evidence.py tests/test_research_revisions.py tests/test_agent_workspace.py` and behave.
Expected: all PASS; behave at baseline (messages keep their prefixes).

- [ ] **Step 5: Commit**

```bash
git add pathfinder/evidence.py pathfinder/research.py tests/test_evidence.py
git commit -m "Typed evidence errors, every problem of a review reported together

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Declared planned outputs are gaps, not dependencies

**Files:**
- Modify: `pathfinder/research.py` (`_external_citations` accepts status `output` without a URL; `_assessment_evidence` lists a missing declared output as a gap)
- Test: `tests/test_evidence.py`

**Interfaces:**
- Produces: `external-references.json` record with `"status": "output"` (no `url` required); in review material, `## <path>\n\n(declared planned output of ledger entry <seq>; not produced, so not evidence)`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_evidence.py
def test_a_declared_output_that_does_not_exist_is_a_gap(tmp_path):
    import hashlib, json
    from pathfinder import research
    from pathfinder.ledger import Ledger
    from stubcampaign import make
    c = make(tmp_path, research_scheme="eva_minus", strict_evidence=True)
    d = research.prepare(c, "Q1P1")
    text = "the script ada/audit.py writes ada/coverage.json"
    (d / "ada" / "audit.py").write_text("print(1)")
    seq = Ledger(d / "ledger.jsonl").add("ada", "finding", text)
    (d / "external-references.json").write_text(json.dumps({"version": 1, "references": [
        {"document": "ledger.jsonl", "ledger_seq": seq, "path": "ada/coverage.json", "status": "output",
         "text_sha256": hashlib.sha256(text.encode()).hexdigest()}]}))
    material = research._review_material(c, "Q1P1")
    assert "declared planned output" in material and "ada/coverage.json" in material
```

- [ ] **Step 2: Run and see it fail**

Run: `uv run --offline --locked pytest -q tests/test_evidence.py -k declared_output`
Expected: FAIL with `Invalid external citation declaration` (URL required, status not allowed).

- [ ] **Step 3: Implement**

In `_external_citations`, replace the URL and status check with:

```python
            if record["status"] not in ("external", "unavailable", "output"):
                raise ValueError("external citation status must be external, unavailable or output")
            if record["status"] != "output":
                url = urlsplit(record["url"])
                if url.scheme not in ("http", "https") or not url.netloc:
                    raise ValueError("external citation requires an absolute HTTP(S) URL and availability status")
```

and add the status to the citation tuple: keep `citations` as a set of `(document, seq, path)` for compatibility and add a second return value is not allowed (callers unpack two values); instead record outputs in a module-level helper: return `(content, citations)` where `citations` is a set of 3-tuples and build `outputs = {(doc, seq, path) for record ... if status == "output"}` in a new helper `_declared_outputs(d) -> set` that re-reads the same validated declaration (call it only after `_external_citations` succeeded). In `_assessment_evidence`, after the citations handling, for each declared output whose file does not exist append the gap section; an existing declared output file is treated as an ordinary local file.

- [ ] **Step 4: Run, then research tests and behave; commit**

Run: `uv run --offline --locked pytest -q tests/test_evidence.py tests/test_research_revisions.py` and behave.
Expected: all PASS; behave at baseline.

```bash
git add pathfinder/research.py tests/test_evidence.py
git commit -m "Declared planned outputs are gaps, not dependencies

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Evidence manifest and `pathfinder evidence`

**Files:**
- Modify: `pathfinder/research.py` (`_assessment_evidence` gains `record: list | None = None`; `_review_material` writes the manifest), `pathfinder/evidence.py` (`manifest`, `proposals`, `text`), `pathfinder/cli.py`
- Test: `tests/test_evidence.py`

**Interfaces:**
- Produces: each recorded entry `{"cited": name or None, "path": str, "kind": "local"|"namespace"|"source"|"declared-output"|"missing"|"ambiguous"|"aliased"|"outside", "bytes": int|None, "sha256": str|None}`; `evidence.manifest(campaign, pair_id) -> dict` with `files`, `errors` (from an `EvidenceError`, else `[]`), `generated_at`; `evidence-manifest.json` in the thread, written by `_review_material` (atomic) before it raises or returns; `evidence.proposals(manifest) -> list[dict]` (for `missing`: declare it `unavailable` with a URL, or `output` if the ledger entry describes a file the work writes, with the entry `seq` and its `text_sha256` filled in; for `ambiguous`: name the candidates and ask for a declaration choosing one); `pathfinder evidence PAIR [--json]`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_evidence.py
def test_manifest_and_proposals(tmp_path, capsys):
    import json
    from pathfinder import cli, research
    from pathfinder.ledger import Ledger
    from stubcampaign import make
    c = make(tmp_path, research_scheme="eva_minus", strict_evidence=True)
    d = research.prepare(c, "Q1P1")
    (d / "ada" / "run.py").write_text("print(1)")
    Ledger(d / "ledger.jsonl").add("ada", "finding", "ran ada/run.py, see ada/missing.json")
    m = evidence.manifest(c, "Q1P1")
    kinds = {f["path"]: f["kind"] for f in m["files"]}
    assert kinds["ada/run.py"] == "local" and kinds["ada/missing.json"] == "missing"
    assert m["errors"][0]["code"] == "missing"
    assert json.loads((d / "evidence-manifest.json").read_text())["files"] == m["files"]
    p = evidence.proposals(m)[0]
    assert p["path"] == "ada/missing.json" and p["ledger_seq"] == 1 and len(p["text_sha256"]) == 64
    assert cli.main(["--root", str(tmp_path), "evidence", "Q1P1", "--json"]) in (0, None)
    assert json.loads(capsys.readouterr().out)["errors"][0]["path"] == "ada/missing.json"
```

- [ ] **Step 2: Run and see it fail**

Run: `uv run --offline --locked pytest -q tests/test_evidence.py -k manifest`
Expected: FAIL (`manifest` missing).

- [ ] **Step 3: Implement**

In `_assessment_evidence`, when `record` is a list, append one entry per path decision (local, namespace, source, declared-output gap, missing, ambiguous, aliased, outside) with bytes and sha256 of the file when it was read. `_review_material(campaign, pair_id, review_id=None)` passes a `record` list and, in a `try/finally`, writes `d / "evidence-manifest.json"` with `{"generated_at", "files": record, "errors": getattr(error, "errors", [])}` using `_atomic_write`.

In `evidence.py`:

```python
def manifest(campaign, pair_id: str) -> dict:
    """Build the review material once to refresh the thread's manifest, and return it."""
    import json
    from . import research
    try:
        research._review_material(campaign, pair_id)
    except research.EvidenceUnavailable:
        pass
    return json.loads((campaign.thread_dir(pair_id) / "evidence-manifest.json").read_text())


def proposals(m: dict, d: Path | None = None) -> list[dict]:
    """One proposed declaration per error; nothing is written."""
    ...
```

`proposals` finds, for each `missing` error, the ledger entry citing the path (read `ledger.jsonl` of the thread through `d`, defaulting to the manifest's thread passed by the CLI), and returns `{"path", "ledger_seq", "text_sha256", "choices": ["unavailable (give the URL)", "output (the work writes it)", "external (give the URL)"]}`; for `ambiguous`, `{"path", "candidates", "choices": ["declare which candidate is meant"]}`. Give `manifest` the thread directory so `proposals(manifest, d)` can read the ledger; adjust the test call to `evidence.proposals(m, c.thread_dir("Q1P1"))` and record the ruling.

In `cli.py`: parser `evidence` with `pair` and `--json`; dispatch prints `json.dumps({**m, "proposals": evidence.proposals(m, c.thread_dir(ns.pair))}, indent=1)` or a text listing of files, errors and proposals.

- [ ] **Step 4: Run, then the full suite and behave; commit**

Run: `uv run --offline --locked pytest -q tests/test_evidence.py` then the full suite and behave.
Expected: all PASS except the baseline failure; behave at baseline.

```bash
git add pathfinder/evidence.py pathfinder/research.py pathfinder/cli.py tests/test_evidence.py
git commit -m "Evidence manifest per review and pathfinder evidence with repair proposals

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Spec

- [ ] In `notes/pathfinder-friction.tex`, mark F01, F02, F03, F04, F05, F06, F08 (manifest part), R01 (proposals) and R03 as done in phase 3b with commit ids; note that F08's "validate before spending at delivery" applies to julien-2's own collector and moves with its migration; rebuild; style gate; commit.
