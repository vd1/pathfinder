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
