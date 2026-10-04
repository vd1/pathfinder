"""The material a composable review reads: the papers, the ledger, every cited and produced file, the branch
bundles, and the evidence errors that block a review before any call. Split from research.py in the
phase 9 sweep; research re-exports every name."""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from urllib.parse import urlsplit
from . import context
from .context import Section
from .thread import _now, _atomic_write, thread_sections, READING, evidence_by_reference, _inputs


class EvidenceUnavailable(Exception):
    """Evidence a composable review must inline cannot be supplied; the thread blocks before any call."""


class EvidenceError(EvidenceUnavailable):
    """Every evidence problem of one review, typed, so each can be repaired on its own (R03)."""

    def __init__(self, errors: list[dict]):
        self.errors = errors
        more = (f" (and {len(errors) - 1} more: " + "; ".join(e["message"] for e in errors[1:]) + ")") if len(errors) > 1 else ""
        super().__init__(errors[0]["message"] + more)


def _external_citations(d, path=None):
    """@planks("Then Vera receives the ledger and its external citation declaration")
    @planks("Then research blocks before provider dispatch because the citation binding is stale")
    @planks("Then the joint researcher receives the citation URL and unavailable status")
    """
    declaration = Path(path) if path is not None else d / "external-references.json"   # a candidate is checked the same way
    if declaration.is_symlink():
        raise EvidenceUnavailable("Aliased evidence declaration: external-references.json")
    if not declaration.exists():
        return None, set()
    try:
        content = declaration.read_text()
        data = json.loads(content)
        if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("references"), list):
            raise ValueError("external-references.json requires version 1 and a references array")
        citations = set()
        for record in data["references"]:
            if not isinstance(record, dict):
                raise ValueError("external citation must be a record")
            for field in ("document", "path"):
                name = record[field]
                if not isinstance(name, str) or not name or Path(name).is_absolute() or ".." in Path(name).parts:
                    raise ValueError(f"Unsafe external citation {field}: {name}")
            document = Path(record["document"])
            if any((d / parent).is_symlink() for parent in (document, *document.parents)):
                raise ValueError(f"Aliased external citation document: {document}")
            if record["status"] not in ("external", "unavailable", "output"):
                raise ValueError("external citation status must be external, unavailable or output")
            if record["status"] != "output":       # a planned output of the cited work has no URL
                url = urlsplit(record["url"])
                if url.scheme not in ("http", "https") or not url.netloc:
                    raise ValueError("external citation requires an absolute HTTP(S) URL and availability status")
            bound = (d / document).read_bytes()
            seq = None
            if str(document) == "ledger.jsonl":
                seq = record["ledger_seq"]
                if type(seq) is not int:
                    raise ValueError("ledger.jsonl citation requires an integer ledger_seq")
                rows = [json.loads(line) for line in bound.decode("utf-8").splitlines() if line.strip()]
                matches = [row for row in rows if row["seq"] == seq]
                if len(matches) != 1:
                    raise ValueError(f"Stale citation binding: ledger.jsonl entry {seq}")
                bound = matches[0]["text"].encode("utf-8")
            if hashlib.sha256(bound).hexdigest() != record["text_sha256"]:
                raise ValueError(f"Stale citation binding: {document}")
            if record["path"] not in bound.decode("utf-8"):
                raise ValueError(f"Citation path absent from bound text: {document}")
            citations.add((str(document), seq, record["path"]))
        return content, citations
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        raise EvidenceUnavailable(f"Invalid external citation declaration: {error}") from error


def _declared_outputs(d) -> set:
    """(document, ledger_seq, path) of every planned output in the declaration; call after _external_citations."""
    declaration = d / "external-references.json"
    if not declaration.is_file():
        return set()
    records = json.loads(declaration.read_text()).get("references", [])
    return {(r["document"], r.get("ledger_seq"), r["path"]) for r in records if r.get("status") == "output"}


EVIDENCE_PATH = re.compile(r"(?<![\w:/@.-])(?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9]+")
EVIDENCE_MAX_BYTES = 300_000


def _evidence_references(text: str) -> list[str]:
    """Relative file paths cited in ledger text; locators, numbers, DOIs, URLs and repositories are not files."""
    from . import evidence
    return evidence.cited_files(text)


def _assessment_evidence(campaign, d, references=None, by_reference=False, record=None, pair_id=None) -> str:
    """            @planks("Then Vera receives the ledger and its external citation declaration")
    @planks("Then research blocks before provider dispatch and identifies \"{path}\"")
    @planks("Then research blocks before reading the aliased citation file")
    @planks("Then the external citation is resolved only in its originating branch namespace")
    

    Everything the tool-less consolidator and verifier are told is complete: every file in each peer's
    directory, and every file the ledger (or `references`) cites by relative path, inlined under its path.
    A path declared external in external-references.json for one ledger entry is not read for that entry.

    A cited path that leaves the thread, goes through a symlink or uses '..' always blocks the thread
    (EvidenceUnavailable): inlining it could read another investigation. With "strict_evidence": true in
    campaign.json a cited file that is missing, unreadable, not UTF-8 text or larger than
    "evidence_max_bytes" also blocks; otherwise readable binary or oversized files are listed with
    size and digest, while missing or unreadable files are explicitly named as unavailable.

    A cited build by-product that is absent (a PDF whose .tex is present, an .aux) is not missing evidence; with
    "evidence_byproducts": "exclude" no by-product is listed or inlined, cited or not (evidence.byproduct)."""
    from . import evidence
    strict = bool(campaign.raw.get("strict_evidence"))
    limit = int(campaign.raw.get("evidence_max_bytes", EVIDENCE_MAX_BYTES))
    bundles = list((campaign.raw or {}).get("research_bundles") or [])
    sources = evidence.registered_sources(campaign, pair_id or d.name)   # a bundle reads its pair's registrations
    resolved, ambiguous = {}, {}            # path -> (cited name, kind); cited name -> candidate paths
    paths = {p for actor in campaign.peers for p in (d / actor).rglob("*") if p.is_file() or p.is_symlink()}
    exclude = (campaign.raw or {}).get("evidence_byproducts") == "exclude"
    if exclude:                                     # a symbolic link is always listed, to be refused
        tree = {p.relative_to(d).as_posix() for p in paths}
        paths = {p for p in paths if p.is_symlink() or not evidence.byproduct(p.relative_to(d).as_posix(), tree)}
    declaration, citations = _external_citations(d)
    for _, _, name in citations:                    # present declared files keep the ordinary checks
        relative = Path(name)
        if (d / relative).exists() or any((d / parent).is_symlink() for parent in (relative, *relative.parents)):
            paths.add(d / relative)
    if references is None:
        ledger = d / "ledger.jsonl"
        references = ledger.read_text(errors="replace") if ledger.exists() else ""
    for line in references.splitlines():            # exempt only the declared entry; another may need the file
        if line.strip():
            row = json.loads(line)
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
    errors = []                              # every problem of this review, typed, raised together at the end

    def problem(code, path, message, detail=None):
        errors.append({"code": code, "path": str(path), "detail": detail, "message": message})
        keep(None, path, code)

    def keep(cited, path, kind, data=None):           # one manifest entry per decision, when asked for
        if record is not None:
            record.append({"cited": cited, "path": str(path), "kind": kind, "bytes": len(data) if data is not None else None,
                           "sha256": hashlib.sha256(data).hexdigest() if data is not None else None})

    parts = ["## external-references.json\n\n" + declaration] if declaration is not None else []
    for document, seq, name in sorted(_declared_outputs(d), key=str):
        if not (d / name).exists():                 # planned but not produced: a gap in the record, not a dependency
            keep(name, name, "declared-output")
            parts.append(f"## {name}\n\n(declared planned output of {document} entry {seq}; not produced, so not evidence)")
    for name, candidates in sorted(ambiguous.items()):
        if strict:
            problem("ambiguous", name, f"missing evidence: {name} (ambiguous: {', '.join(candidates)})", list(candidates))
            continue
        keep(name, name, "ambiguous")
        parts.append(f"## {name}\n\n(cited in the ledger; ambiguous between {', '.join(candidates)}; declare which one)")
    for path in sorted(paths):
        cited, how = resolved.get(path, (None, "local"))
        if how == "source":                      # a campaign file registered for this pair, read by its own bytes
            data = path.read_bytes()
            keep(cited, "campaign:" + str(path.relative_to(Path(campaign.root).resolve())), "source", data)
            label = f"{cited} (resolved to campaign:{path.relative_to(Path(campaign.root).resolve())}, sha256 {hashlib.sha256(data).hexdigest()})"
            # outside the reader's working directory, so inlined even by reference; same text rules as thread files
            try:
                if len(data) > limit:
                    raise UnicodeError(f"{len(data)} bytes, over the {limit}-byte inline limit")
                parts.append(f"## {label}\n\n{data.decode('utf-8')}")
            except UnicodeError as error:
                if strict:
                    problem("not_text", cited, f"evidence not inlinable as text: {cited}: {error}", str(error))
                else:
                    parts.append(f"## {label}\n\n(not inlined: {len(data)} bytes)")
            continue
        relative = path.relative_to(d)
        heading = f"{cited} (resolved to {relative})" if how == "namespace" else str(relative)
        if ".." in relative.parts or any((d / parent).is_symlink() for parent in (relative, *relative.parents)):
            problem("aliased", relative, f"aliased evidence path: {relative}")
            continue
        if path.exists() and not path.resolve().is_relative_to(d.resolve()):
            problem("outside", relative, f"evidence outside the investigation: {relative}")
            continue
        tex = relative.with_suffix(".tex").as_posix()
        if (exclude or not path.is_file()) and evidence.byproduct(relative.as_posix(), {tex} if (d / tex).is_file() else ()):
            keep(cited, relative, "byproduct")           # a cited PDF whose .tex is present is not missing
            parts.append(f"## {heading}\n\n(cited in the ledger; a build by-product, not evidence)")
            continue
        if not path.is_file():
            if strict:
                problem("missing", relative, f"missing evidence: {relative}")
                continue
            keep(None, relative, "missing")
            parts.append(f"## {relative}\n\n(cited in the ledger; no such file)")
            continue
        try:
            data = path.read_bytes()
        except OSError as error:
            if strict:
                problem("unreadable", relative, f"unreadable evidence: {relative}: {error}", str(error))
                continue
            parts.append(f"## {relative}\n\n(not inlined: unreadable file: {error})")
            continue
        keep(cited, relative, "namespace" if how == "namespace" else "local", data)
        if by_reference:
            parts.append(f"## {heading}\n\n(file in your working directory: {len(data)} bytes, "
                         f"sha256 {hashlib.sha256(data).hexdigest()}; read it with your tools)")
            continue
        try:
            if len(data) > limit:
                raise UnicodeError(f"{len(data)} bytes, over the {limit}-byte inline limit")
            text = data.decode("utf-8")
        except UnicodeError as error:
            if strict:
                problem("not_text", relative, f"evidence not inlinable as text: {relative}: {error}", str(error))
                continue
            parts.append(f"## {heading}\n\n(not inlined: {len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()})")
            continue
        parts.append(f"## {heading}\n\n{text}")
    if errors:
        raise EvidenceError(errors)
    return "\n\n".join(parts)


def _bundle_evidence(campaign, d, by_reference=False, record=None, errors=None):
    """@planks("Then each stage receives all three ledgers and their referenced evidence")
    @planks("Then it includes those thread-relative bundle directories with their original reference namespaces")
    """
    parts = []
    for name in campaign.raw.get("research_bundles", []):
        root = d / name
        relative = root.relative_to(d)
        if ".." in relative.parts or any((d / parent).is_symlink() for parent in (relative, *relative.parents)):
            raise EvidenceUnavailable(f"Aliased evidence bundle: {name}")
        ledger = root / "ledger.jsonl"
        if ledger.is_symlink():
            raise EvidenceUnavailable(f"Aliased evidence ledger: {name}/ledger.jsonl")
        try:
            content = ledger.read_text()
        except (OSError, UnicodeError) as error:
            raise EvidenceUnavailable(f"Unreadable evidence {name}/ledger.jsonl: {error}") from error
        parts.append(f"## {name}/ledger.jsonl\n\n{content}")
        inner = [] if record is not None else None
        try:
            evidence = _assessment_evidence(campaign, root, by_reference=by_reference, record=inner, pair_id=d.name)
        except EvidenceError as failure:            # keep the bundle's namespace on each error, and go on
            if errors is None:
                raise
            for e in failure.errors:
                errors.append({**e, "path": f"{name}/{e['path']}", "origin": name, "cited": e["path"],
                               "message": e["message"].replace(e["path"], f"{name}/{e['path']}", 1)})
            evidence = ""
        finally:
            for entry in inner or []:
                record.append({**entry, "path": f"{name}/{entry['path']}"})
        parts.append(evidence.replace("## ", f"## {name}/"))
    return "\n\n".join(parts)


def _review_material(campaign, pair_id, review_id=None, record_manifest=True, with_id=False):
    """@planks("Then Vera receives both papers and the complete attributed research ledger")
    @planks("Then Vera receives all referenced peer evidence without a consolidated account")
    @planks("Then Pathfinder blocks the stale response before a research transition")
    @planks("Then the review occurs once in the ledger")
    """
    d = campaign.thread_dir(pair_id)
    ledger = d / "ledger.jsonl"
    lines = ledger.read_text().splitlines(keepends=True) if ledger.exists() else []
    # The feedback appended during a replay belongs to the transition, not its input.
    if review_id:
        lines = [line for line in lines if not (
            json.loads(line)["kind"] == "review" and
            json.loads(line)["text"].startswith('{"review_id": ' + json.dumps(review_id) + ','))]
    ledger_text = "".join(lines)
    unfiltered = ledger.exists() and ledger_text == ledger.read_text()
    sections = thread_sections(d, _inputs(d), ledger=False) + [
        Section("ledger.jsonl", path=ledger) if unfiltered else Section("ledger.jsonl", text=ledger_text)]
    material = ""
    by_reference = evidence_by_reference(campaign)
    record, failure, collected = [], None, []
    try:
        try:
            material += "\n\n" + _assessment_evidence(campaign, d, references=ledger_text, by_reference=by_reference, record=record)
        except EvidenceError as joint:              # report the bundles' problems too, all together
            collected.extend(joint.errors)
        material += "\n\n" + _bundle_evidence(campaign, d, by_reference=by_reference, record=record, errors=collected)
        if collected:
            raise EvidenceError(collected)
    except EvidenceUnavailable as error:
        failure = error
        raise
    finally:                                      # the manifest records what this review found, blocked or not
        if record_manifest:
            _atomic_write(d / "evidence-manifest.json", json.dumps({
                "generated_at": _now(), "files": record,
                "errors": getattr(failure, "errors", [{"code": "declaration", "path": None, "detail": None,
                                                       "message": str(failure)}] if failure else [])}, indent=1).encode())
    if material.strip():
        sections.append(Section("", text=material.lstrip("\n")))
    if by_reference:
        sections.append(Section("", text=READING, keep=True))
    if campaign.raw.get("research_scheme", "eva") == "eva":
        note = d / f"{pair_id}.tex"
        if note.exists():
            sections.append(Section(note.name, path=note))
    # the review's task follows this material. The evidence identifier hashes what the sections hold, not how the
    # budget presented them: a ledger given by path at request time and as filtered text on replay is the same evidence
    material = context.build(campaign, "verify", sections, tools=True, cwd=d, unit=pair_id, record=record_manifest)
    if not with_id:
        return material
    return material, hashlib.sha256(json.dumps([[x.name, x.body()] for x in sections]).encode()).hexdigest()
