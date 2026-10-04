"""One budgeted context builder for every stage (J01).

A prompt is a list of sections in a fixed order: the static material first, so that a prompt cache serves
it, the task last. Within the stage's budget every section is pasted. Above it, the largest sections that
are not kept are shrunk first, without moving anything: a file becomes a reference (path, size, sha256)
for an agent with tools to read; anything else, or any section of a tool-less stage, becomes a digest of
its beginning and end with its full size and digest. A prompt that still does not fit is refused with
transport.PromptTooLarge, which every stage records as an input_too_large block.

Budgets come from "prompt_budgets" in campaign.json, {"default": N, "<stage>": N}, never above
max_prompt_chars."""
from __future__ import annotations
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from . import transport

DEFAULT_BUDGET = 300_000


@dataclass(frozen=True)
class Section:
    name: str
    text: str | None = None        # material held in memory
    path: Path | None = None       # material in a file an agent with tools can read
    keep: bool = False             # never shrunk: the task, the object under review

    def body(self) -> str:
        return self.text if self.text is not None else Path(self.path).read_text(errors="replace")


def budget(campaign, stage: str) -> int:
    raw = (campaign.raw or {}).get("prompt_budgets") or {}
    return min(int(raw.get(stage, raw.get("default", DEFAULT_BUDGET))), transport.max_prompt_chars(campaign))


def digest_text(name: str, text: str, share: int) -> str:
    """The beginning and the end of `text` in about `share` characters, with its full size and sha256."""
    sha = hashlib.sha256(text.encode()).hexdigest()
    note = f"(digest of {name}: {len(text)} characters, sha256 {sha}; the beginning and the end follow)"
    room = max(share - len(note) - 80, 0)
    head = text[: room * 2 // 3]
    tail = text[len(text) - room // 3:] if room // 3 else ""
    return f"{note}\n{head}\n[... {len(text) - len(head) - len(tail)} characters omitted ...]\n{tail}"


OUTLINE_ENTRIES = 80
_TEX_LEVELS = {"part": 0, "chapter": 0, "section": 0, "subsection": 1, "subsubsection": 2}
_TEX_HEADING = re.compile(r"\\(part|chapter|section|subsection|subsubsection)\*?\s*(?:\[[^\]]*\])?\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}")
_MD_HEADING = re.compile(r"(#{1,4})\s+(\S.*)")


def outline(text: str) -> str:
    """The headings of a TeX or Markdown text, one per line as "line: title", indented by depth; "" when it
    has none. An agent reading by reference jumps to the lines it needs instead of printing the file."""
    rows = []
    for number, line in enumerate(text.splitlines(), 1):
        tex = _TEX_HEADING.search(line)
        md = None if tex else _MD_HEADING.match(line)
        if tex and not line.lstrip().startswith("%"):
            depth, title = _TEX_LEVELS[tex.group(1)], tex.group(2)
        elif md:
            depth, title = len(md.group(1)) - 1, md.group(2)
        else:
            continue
        rows.append(f"{number}: {'  ' * depth}{' '.join(title.split())}")
    if len(rows) > OUTLINE_ENTRIES:
        rows = rows[:OUTLINE_ENTRIES] + [f"... and {len(rows) - OUTLINE_ENTRIES} more headings"]
    return "\n".join(rows)


def _reference(section: Section, cwd) -> str:
    data = Path(section.path).read_bytes()
    where = Path(section.path)
    if cwd is not None and where.is_relative_to(cwd):
        where = where.relative_to(cwd)
    return f"(file {where.as_posix()}: {len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()}; read it with your tools)"


def _render(section: Section, body: str) -> str:
    return f"## {section.name}\n\n{body}" if section.name else body


def build(campaign, stage: str, sections: list[Section], *, tools: bool, cwd: Path | None = None,
          unit: str | None = None, record: bool = True) -> str:
    limit = budget(campaign, stage)
    bodies = [s.body() for s in sections]
    rendered = [_render(s, b) for s, b in zip(sections, bodies)]
    modes = ["inline"] * len(sections)
    total = lambda: sum(len(r) for r in rendered) + 2 * max(len(rendered) - 1, 0)
    for i in sorted((i for i, s in enumerate(sections) if not s.keep), key=lambda i: (-len(rendered[i]), i)):
        if total() <= limit:
            break
        if tools and sections[i].path is not None:
            rendered[i], modes[i] = _render(sections[i], _reference(sections[i], cwd)), "reference"
        else:
            excess = total() - limit
            share = max(len(bodies[i]) - excess, 0)            # at the least, the size and digest alone
            if share < len(bodies[i]):
                rendered[i], modes[i] = _render(sections[i], digest_text(sections[i].name or "material", bodies[i], share)), "digest"
    if total() > limit:
        raise transport.PromptTooLarge(f"input too large: {stage} context is {total()} characters after shrinking, budget {limit}")
    prompt = "\n\n".join(rendered)
    if record:
        from . import events
        events.emit(campaign, "context_built", unit=unit, stage=stage, budget=limit, chars=len(prompt),
                    sections=[{"name": s.name, "mode": m, "chars": len(r)} for s, m, r in zip(sections, modes, rendered)])
    return prompt
