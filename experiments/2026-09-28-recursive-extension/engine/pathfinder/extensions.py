"""Deployment extensions: trusted code named in campaign.json and loaded by the engine.

    "extensions": {"path": "deploy", "admission": "policies:budget", "snapshot_extra": "monitor:extra"}

"path" (relative to the campaign root, optional) is put on sys.path; each other entry is "module:object".
Extension code runs in the engine's process and is trusted: the engine validates what it returns and keeps
its own records authoritative, but does not police what it does. Supported names: admission,
snapshot_extra."""
from __future__ import annotations
import hashlib, importlib, inspect, sys
from pathlib import Path

SUPPORTED = {"admission", "snapshot_extra"}


def _spec(campaign) -> dict:
    return dict((campaign.raw or {}).get("extensions") or {})


def load(campaign, name: str):
    """The object a campaign names for extension point `name`, or None."""
    if name not in SUPPORTED:
        raise ValueError(f"unknown extension point {name}")
    spec = _spec(campaign)
    target = spec.get(name)
    if not target:
        return None
    if spec.get("path"):
        path = str((Path(campaign.root) / spec["path"]).resolve())
        if path not in sys.path:
            sys.path.insert(0, path)
    module, _, attr = target.partition(":")
    if not attr:
        raise ValueError(f"extension {name} must be module:object, got {target!r}")
    if spec.get("path"):
        root = Path(path)
        loaded = sys.modules.get(module)
        if loaded is not None and not _within(loaded, root):
            raise ImportError(f"extension module {module!r} is already loaded from {getattr(loaded, '__file__', None)},"
                              f" not from {root}; give each deployment a uniquely named package")
        mod = importlib.import_module(module)
        if not _within(mod, root):
            raise ImportError(f"extension module {module!r} resolved to {getattr(mod, '__file__', None)}, outside {root}")
        return getattr(mod, attr)
    return getattr(importlib.import_module(module), attr)


def _within(module, root: Path) -> bool:
    origin = getattr(module, "__file__", None)
    return bool(origin) and Path(origin).resolve().is_relative_to(root)


_first_seen: dict = {}


def _tree_digest(root: Path) -> dict:
    """sha256 of every Python file under a deployment's extension path, helpers included."""
    return {f.relative_to(root).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(root.rglob("*.py")) if "__pycache__" not in f.parts}


def digests(campaign, fresh: bool = False) -> dict:
    """For the run record: each configured extension's target and module file, and the digest of every
    Python file under the extension path. Digests are taken when this process first loads a campaign's
    extensions and kept, so a file edited later, which the process has not re-imported, does not pass for
    the code actually running."""
    spec = _spec(campaign)
    key = (str(Path(campaign.root).resolve()), json_key(spec))
    if key in _first_seen and not fresh:
        return _first_seen[key]
    out = {}
    for name in sorted(set(spec) & SUPPORTED):
        if not spec[name]:
            continue
        obj = load(campaign, name)
        try:
            source = Path(inspect.getfile(obj if inspect.ismodule(obj) else inspect.getmodule(obj)))
            source = source if source.exists() else None
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
        except (TypeError, OSError):
            source, digest = None, None
        out[name] = {"target": spec[name], "file": str(source) if source else None, "sha256": digest}
    if spec.get("path"):
        out["path_files"] = _tree_digest((Path(campaign.root) / spec["path"]).resolve())
    if not fresh:
        _first_seen[key] = out
    return out


def json_key(spec) -> str:
    import json
    return json.dumps(spec, sort_keys=True)
