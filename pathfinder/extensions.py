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


def digests(campaign) -> dict:
    """For the run record: each configured extension's target and the sha256 of its module source."""
    out = {}
    for name in sorted(set(_spec(campaign)) & SUPPORTED):
        obj = load(campaign, name)
        try:
            source = Path(inspect.getfile(obj if inspect.ismodule(obj) else inspect.getmodule(obj)))
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
        except (TypeError, OSError):
            source, digest = None, None
        out[name] = {"target": _spec(campaign)[name], "file": str(source) if source else None, "sha256": digest}
    return out
