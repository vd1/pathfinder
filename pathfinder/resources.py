"""Where the engine's prompts and styles live, and how a campaign overlays them.

In a checkout the built-in prompts are the repository's top-level prompts/; an installed wheel carries
the same files as pathfinder/resources/prompts. A campaign adjusts them one file at a time: for role R,
prompts/R.md in the campaign replaces the engine's prompt, prompts/R.append.md is appended to whichever
prompt applies, and placeholders are substituted in the composed text. Styles resolve the same way:
the campaign's styles/ is searched before the engine's."""
from __future__ import annotations
import hashlib, os
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent


def engine_prompts() -> Path:
    """The built-in prompts: the packaged copy when installed; the repository's prompts/ only in the
    source layout, where the package has no packaged copy. An unrelated prompts/ beside an installed
    package can never override the installed defaults."""
    packaged = PACKAGE / "resources" / "prompts"
    return packaged if packaged.is_dir() else PACKAGE.parent / "prompts"


def engine_styles() -> Path:
    return PACKAGE / "styles"


def roles(campaign=None) -> list[str]:
    """Every role with a prompt, built-in or supplied by the campaign."""
    names = {p.stem for p in engine_prompts().glob("*.md")}
    local = campaign.path("prompts") if campaign is not None else None
    if local is not None and local.is_dir():
        names |= {p.name[:-len(".append.md")] if p.name.endswith(".append.md") else p.stem for p in local.glob("*.md")}
    return sorted(names)


def prompt_template(campaign, role: str) -> str:
    """The composed, unsubstituted prompt for a role: replacement or built-in, then the append overlay."""
    local = campaign.path("prompts") if campaign is not None else None
    replacement = local / f"{role}.md" if local is not None else None
    base = replacement if replacement is not None and replacement.is_file() else engine_prompts() / f"{role}.md"
    text = base.read_text()
    append = local / f"{role}.append.md" if local is not None else None
    if append is not None and append.is_file():
        text = text.rstrip("\n") + "\n\n" + append.read_text()
    return text


def prompt(campaign, role: str, **values) -> str:
    """The prompt a role receives: composed first, then every {{KEY}} replaced by its value."""
    text = prompt_template(campaign, role)
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def prompt_digests(campaign) -> dict:
    """sha256 of each role's composed template, the part of a prompt a deployment controls."""
    out = {}
    for role in roles(campaign):
        try:
            out[role] = hashlib.sha256(prompt_template(campaign, role).encode()).hexdigest()
        except FileNotFoundError:           # an append overlay for a role the engine does not have
            continue
    return out


def campaign_root(path) -> Path | None:
    """The campaign a file or directory belongs to: the nearest ancestor holding campaign.json."""
    for d in [Path(path).resolve(), *Path(path).resolve().parents]:
        if (d / "campaign.json").is_file():
            return d
    return None


def _root(campaign=None, where=None) -> Path | None:
    if campaign is not None:
        return Path(campaign.root)
    return campaign_root(where) if where is not None else None


def style_dirs(campaign=None, where=None) -> list[Path]:
    """Directories TeX searches for the Pathfinder styles, the campaign's first. The campaign is given,
    or found from a path inside it."""
    root = _root(campaign, where)
    dirs = [root / "styles"] if root is not None and (root / "styles").is_dir() else []
    return dirs + [engine_styles()]


def texinputs(campaign=None, existing: str | None = None, where=None) -> str:
    """A TEXINPUTS value with the style directories first; the trailing separator keeps TeX's defaults."""
    existing = os.environ.get("TEXINPUTS", "") if existing is None else existing
    return os.pathsep.join(str(d) for d in style_dirs(campaign, where)) + os.pathsep + existing


def style_digests(campaign=None, where=None) -> dict:
    """sha256 of every style file TeX would find first, by name."""
    out = {}
    for d in reversed(style_dirs(campaign, where)):   # campaign files override engine files of the same name
        for f in sorted(d.glob("*.sty")):
            out[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out
