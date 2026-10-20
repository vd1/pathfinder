"""Exact, reviewed alpha-renames in a paused account presentation."""
import hashlib
import json
import re
from . import pce


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def occurrences(text, symbol):
    """Standalone symbols in explicit inline/display math, never prose or commands."""
    found = []
    for block in re.finditer(r"\\\((.*?)\\\)|\\\[(.*?)\\\]", text, re.S):
        group = 1 if block.group(1) is not None else 2
        for match in re.finditer(r"(?<![A-Za-z\\])" + re.escape(symbol) + r"(?![A-Za-z])",
                                 block.group(group)):
            found.append(block.start(group) + match.start())
    return found


def target(source, packet):
    old, new = packet["old"], packet["new"]
    if (not re.fullmatch(r"[A-Za-z]", old)
            or not re.fullmatch(r"\\(?:Delta|Gamma|Lambda|Omega|Sigma|Phi|Psi|alpha|beta|gamma|delta|epsilon|theta|lambda|mu|nu|rho|sigma|tau|phi|psi|omega)(?:_\{\\mathrm\{[a-z]+\}\})?", new)
            or new in source):
        raise pce.Changed("notation rename needs a single symbol and a fresh atomic TeX name")
    rows = packet["occurrences"]
    positions = occurrences(source, old)
    if (not isinstance(rows, list) or not positions or len(rows) > 100
            or any(not isinstance(row, dict) or set(row) != {"offset", "action", "meaning"}
                   or type(row["offset"]) is not int
                   or row["action"] not in ("rename", "preserve")
                   or not isinstance(row["meaning"], str) or not row["meaning"].strip()
                   for row in rows)
            or [row["offset"] for row in rows] != positions
            or not any(row["action"] == "rename" for row in rows)):
        raise pce.Changed("classify every math-symbol occurrence exactly once")
    result = source
    for row in reversed(rows):
        if row["action"] == "rename":
            i = row["offset"]
            result = result[:i] + new + result[i + len(old):]
    if digest(result) != packet["target_sha256"]:
        raise pce.Changed("notation target hash differs")
    return result


def validate(pd, packet):
    keys = {"version", "kind", "stage", "source_sha256", "accepted_sha256",
            "bibliography_sha256", "state_sha256", "check_sha256", "review",
            "review_sha256", "review_id", "review_reason", "where", "old", "new",
            "occurrences", "target_sha256"}
    if set(packet) != keys or packet["version"] != 2 or packet["kind"] != "reviewed-alpha-rename":
        raise pce.Changed("invalid reviewed notation packet")
    if (not re.fullmatch(r"correct-[0-9]+", packet["stage"])
            or not re.fullmatch(r"(?:pass|correct-[0-9]+)/claims(?:-[a-f0-9]+)?\.json", packet["review"])):
        raise pce.Changed("notation sources must be retained presentation stages")
    d = pd / "presentation"
    paths = {"source_sha256": d / packet["stage"] / "paper.tex",
             "accepted_sha256": pd / "paper.tex", "bibliography_sha256": pd / "references.bib",
             "check_sha256": d / packet["stage"] / "check.json",
             "review_sha256": d / packet["review"]}
    for key, path in paths.items():
        if (path.is_symlink() or not path.resolve().is_relative_to(pd.resolve())
                or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != packet[key]):
            raise pce.Changed("notation provenance changed: " + key)
    checked = json.loads(paths["check_sha256"].read_text())
    if not any(f.get("where") == packet["where"] and f.get("kind") in ("unclear", "notation")
               for f in checked["findings"]):
        raise pce.Changed("notation packet must bind the current clarity finding")
    review = json.loads(paths["review_sha256"].read_text())
    asked = [r for r in review["asked"] if r.get("id") == packet["review_id"]]
    answers = [r for r in review["answers"] if r.get("id") == packet["review_id"]]
    if (len(asked) != 1 or len(answers) != 1 or answers[0].get("decision") != "presentation"
            or answers[0].get("reason") != packet["review_reason"]):
        raise pce.Changed("notation requires the exact prior presentation-only disposition")
    source = paths["source_sha256"].read_text()
    target(source, packet)
    return packet, {k: packet[k] for k in paths}, {packet["where"]}


def projected_correction(before, after, bib, packet):
    """Undo only the granted alpha-renames before applying the ordinary guard."""
    if digest(before) != packet["source_sha256"] or digest(bib) != packet["bibliography_sha256"]:
        raise pce.Changed("notation correction source or bibliography changed")
    expected = target(before, packet)
    if after != expected:
        raise pce.Changed("notation correction must equal the exact granted rename; unrelated edits refused")
    # Exact target equality proves no other token changed. Reverse only granted sites.
    projected = after
    shift = 0
    sites = []
    for row in packet["occurrences"]:
        if row["action"] == "rename":
            sites.append(row["offset"] + shift)
            shift += len(packet["new"]) - len(packet["old"])
    for offset in reversed(sites):
        projected = projected[:offset] + packet["old"] + projected[offset + len(packet["new"]):]
    return projected
