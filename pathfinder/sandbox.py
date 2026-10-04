"""A Codex filesystem permission profile for one request, in place of a sandbox mode (julien-2's eva2 profile).

    "codex": {"filesystem_profile": true}                       # or {"read": [...], "deny": [...]}

--sandbox workspace-write lets an agent write its whole working directory and read the whole disk. A profile
says which paths it sees: its working directory (writable with tools, else read-only), the engine package and
the Python framework, nothing else beyond the CLI's minimal set. A sibling branch is absent, since nothing
grants it; /tmp and the parent's TMPDIR are denied (the agent's TMPDIR is inside its workspace); and with tools
the thread's control files stay read-only, so a joint peer cannot write into branch-runs/ or a frozen bundle.
A deployment adds its own read and denied paths (a TeX tree, an interpreter prefix)."""
from __future__ import annotations
import json, os
from pathlib import Path

NAME = "pathfinder"
# The record a thread's agents read but never write: inputs, frozen bundles, the branches' own runs, status
# and the evidence declarations (as eva2 kept them read-only).
CONTROL = ("inputs", "branches", "branch-runs", "imported", "consolidation", "reviews", "status.json", "handoff.json",
           "bundle.json", "external-references.json", "local-reference-links.json", "reference-declarations.json",
           ".transport-input")


def profile(cwd, engine_root, tools: bool, read=(), deny=(), network: bool = False) -> dict:
    """The profile's Codex settings, {config key: value}; engine_root is the directory holding the pathfinder package."""
    cwd = Path(cwd).resolve()
    fs = {":minimal": "read", str(cwd): "write" if tools else "read"}
    if tools:
        fs.update({str(Path(engine_root).resolve() / "pathfinder"): "read",
                   "/Library/Frameworks/Python.framework": "read", "/usr/local": "read"})
    temporary = ["/private/tmp", "/tmp"] + ([str(Path(os.environ["TMPDIR"]).resolve())] if os.environ.get("TMPDIR") else [])
    for path in temporary:
        tmp = Path(path).resolve()
        if not (cwd.is_relative_to(tmp) or tmp.is_relative_to(cwd)):   # neither the workspace nor its own TMPDIR
            fs[path] = "none"
    if tools:
        for name in CONTROL:
            fs[str(cwd / name)] = "read"
    fs.update({os.path.abspath(path): "read" for path in read})
    fs.update({os.path.abspath(path): "none" for path in deny})
    return {"default_permissions": NAME, f"permissions.{NAME}.filesystem": fs, f"permissions.{NAME}.network.enabled": network}


def toml(value) -> str:
    """A value as a TOML inline value for codex -c (strings, booleans and numbers as JSON writes them)."""
    if isinstance(value, dict):
        return "{" + ", ".join(json.dumps(k) + " = " + toml(v) for k, v in value.items()) + "}"
    return json.dumps(value)


def args(cwd, tools: bool, setting=True, network: bool = False) -> list[str]:
    """The -c arguments of the campaign's profile setting (true, or {"read": [...], "deny": [...]}) for one request."""
    extra = setting if isinstance(setting, dict) else {}
    engine_root = Path(__file__).resolve().parent.parent
    out = []
    for key, value in profile(cwd, engine_root, tools, extra.get("read", ()), extra.get("deny", ()), network).items():
        out += ["-c", f"{key}={toml(value)}"]
    return out
