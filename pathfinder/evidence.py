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


def __getattr__(name):
    if name == "EvidenceError":                 # defined beside EvidenceUnavailable, so every existing catch holds
        from .research import EvidenceError
        return EvidenceError
    raise AttributeError(name)
