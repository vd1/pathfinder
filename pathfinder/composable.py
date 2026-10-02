"""Composable EVA (phase 6): each pair is researched as N independent direct-EVA branches, each branch's
handoff is frozen as an immutable bundle, and one joint EVA thread then researches over all the bundles.

    "research_scheme": "composable", "branches": 3,
    "branch": {"rounds": 2, "ledger_reviews": 4},     # optional overrides for every branch
    "joint": {"rounds": 3}                            # optional overrides for the joint thread

Layout of a pair's thread directory: the joint thread lives in the directory itself (its ledger, peers,
account, edit and paper), each branch runs in branch-runs/<label>/ and is frozen into branches/<label>/.
Branches and the joint thread are views of the one campaign: the same root, receipts, events, stop marker
and admission, with their own research settings; a branch view also has its own thread directory and
names its branch on every receipt and event."""
from __future__ import annotations
import copy, hashlib, json, os, shutil, time
from pathlib import Path

SCHEME_KEYS = ("research_scheme", "research_bundles", "branches", "branch", "joint")


def labels(campaign) -> list[str]:
    return [f"branch-{n}" for n in range(1, int((campaign.raw or {}).get("branches", 3)) + 1)]


def _view(campaign, overrides: dict, scheme: dict):
    raw = {k: v for k, v in (campaign.raw or {}).items() if k not in SCHEME_KEYS}
    raw.update(overrides or {})
    raw.update(scheme)
    view = copy.copy(campaign)
    view.raw = raw
    view.rounds = raw.get("rounds", 3)
    if "allowances" in (overrides or {}):
        view.allowances = {**campaign.allowances, **overrides["allowances"]}
    return view


def branch_view(campaign, pair_id: str, label: str):
    view = _view(campaign, (campaign.raw or {}).get("branch"), {"research_scheme": "direct_eva"})
    base = campaign.thread_dir
    view.thread_dir = lambda pid: base(pid) / "branch-runs" / label
    view.branch = label
    return view


def joint_view(campaign, pair_id: str):
    return _view(campaign, (campaign.raw or {}).get("joint"),
                 {"research_scheme": "eva", "research_bundles": [f"branches/{label}" for label in labels(campaign)]})


class BundleError(Exception):
    """A branch that cannot be frozen, or a frozen bundle that no longer matches its inventory."""


HANDOFF_REASONS = ("no_further_requests", "research_allowance_exhausted", "review_allowance_exhausted")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _files(root: Path) -> list[Path]:
    out = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise BundleError(f"{label_of(root)}: {path.relative_to(root).as_posix()} is a symbolic link")
        if path.is_file():
            out.append(path)
    return out


def label_of(root: Path) -> str:
    return Path(root).name


def _check_handoff(campaign, pair_id: str, label: str) -> dict:
    from . import research
    b = branch_view(campaign, pair_id, label)
    s = research.status(b, pair_id)
    if s.get("status") != "HANDOFF":
        raise BundleError(f"{label}: research is {s.get('status')}, not HANDOFF")
    outcome = research.export_outcome(b, pair_id)
    if outcome.get("scientific_verdict") is not None:
        raise BundleError(f"{label}: a branch hands off without a scientific verdict")
    if s.get("handoff_reason") not in HANDOFF_REASONS:
        raise BundleError(f"{label}: unknown handoff reason {s.get('handoff_reason')!r}")
    if s.get("handoff_reason") == "no_further_requests" and any(
            r.get("status") == "active" for r in (s.get("requests") or {}).values()):
        raise BundleError(f"{label}: handed off with no further requests while a request is still active")
    return outcome


def freeze(campaign, pair_id: str, label: str) -> Path:
    """Copy a branch's handoff into branches/<label>/ once, read-only, with bundle.json written last; a bundle
    already complete is verified and returned as it is."""
    dst = campaign.thread_dir(pair_id) / "branches" / label
    if (dst / "bundle.json").exists():
        verify(dst)
        return dst
    outcome = _check_handoff(campaign, pair_id, label)
    src = branch_view(campaign, pair_id, label).thread_dir(pair_id)
    if dst.exists():                                # an interrupted freeze: start it again
        for path in dst.rglob("*"):
            if path.is_file() and not path.is_symlink():
                os.chmod(path, 0o644)
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    names = ["ledger.jsonl", "status.json", "external-references.json", "inputs", *campaign.peers]
    for name in names:
        source = src / name
        if source.is_symlink():
            raise BundleError(f"{label}: {name} is a symbolic link")
        if source.is_dir():
            (dst / name).mkdir(exist_ok=True)       # a peer that wrote no file keeps its (empty) directory
            for path in _files(source):
                if ".pathfinder" in path.relative_to(src).parts:
                    continue
                target = dst / path.relative_to(src)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
        elif source.is_file():
            shutil.copyfile(source, dst / name)
    (dst / "handoff.json").write_text(json.dumps(outcome, indent=1))
    inventory = {path.relative_to(dst).as_posix(): {"sha256": _sha(path), "bytes": path.stat().st_size}
                 for path in _files(dst)}
    record = {"label": label, "files": inventory, "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "inventory_sha256": hashlib.sha256(json.dumps(inventory, sort_keys=True).encode()).hexdigest()}
    (dst / "bundle.json").write_text(json.dumps(record, indent=1))
    for path in _files(dst):
        os.chmod(path, 0o444)
    return dst


def verify(bundle: Path) -> dict:
    """The bundle's record, after checking every file against it: none missing, none added, none changed."""
    bundle = Path(bundle)
    try:
        record = json.loads((bundle / "bundle.json").read_text())
    except (OSError, ValueError) as error:
        raise BundleError(f"{bundle.name}: unreadable bundle.json ({error})") from None
    present = {path.relative_to(bundle).as_posix(): path for path in _files(bundle) if path != bundle / "bundle.json"}
    for name in sorted(set(record["files"]) - set(present)):
        raise BundleError(f"{bundle.name}: {name} is missing")
    for name in sorted(set(present) - set(record["files"])):
        raise BundleError(f"{bundle.name}: {name} was added after the freeze")
    for name, entry in sorted(record["files"].items()):
        if _sha(present[name]) != entry["sha256"]:
            raise BundleError(f"{bundle.name}: {name} changed after the freeze")
    return record
