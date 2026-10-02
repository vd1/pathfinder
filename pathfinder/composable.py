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
import copy, hashlib, json, os, re, shutil, time
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


def run(campaign, pair_id: str, stop=lambda: False) -> str:
    """The pair's research: the branches until every one has handed off, then the joint thread over their
    frozen bundles. A stopped branch stops the pair; another unfinished branch blocks it, named; the branches
    already handed off are never run again."""
    from concurrent.futures import ThreadPoolExecutor
    from . import research
    joint = joint_view(campaign, pair_id)
    d = campaign.thread_dir(pair_id)
    s = research.status(campaign, pair_id)
    if s.get("branches_frozen"):
        if s.get("status") in research.TERMINAL | {"HANDOFF", "BLOCKED"}:
            return s["status"]
        try:
            for label in labels(campaign):
                verify(d / "branches" / label)
        except BundleError as error:
            research._set(campaign, pair_id, status="BLOCKED", reason=f"frozen bundle changed: {error}")
            return "BLOCKED"
        return research.run_thread(joint, pair_id, stop)
    if not (d / "status.json").exists():
        research.prepare(joint, pair_id)            # the joint thread's inputs and peer directories, waiting
    if s.get("stage") != "branches" or s.get("status") != "running":
        research._set(campaign, pair_id, stage="branches", status="running", round=0, reason=None, failure=None)
    todo = [label for label in labels(campaign)
            if research.status(branch_view(campaign, pair_id, label), pair_id).get("status") != "HANDOFF"]

    def one(label):
        view = branch_view(campaign, pair_id, label)
        research.prepare(view, pair_id)
        return research.run_thread(view, pair_id, stop)
    errors = []
    if todo:
        with ThreadPoolExecutor(len(todo)) as pool:
            for future in [pool.submit(one, label) for label in todo]:
                try:
                    future.result()
                except Exception as error:          # drain the others first: their paid work is kept
                    errors.append(error)
    states = {label: research.status(branch_view(campaign, pair_id, label), pair_id) for label in labels(campaign)}
    waiting = {label: b for label, b in states.items() if b.get("status") != "HANDOFF"}
    stopped = [label for label, b in waiting.items() if b.get("status") in ("stopped", "running")]
    if errors or stopped:
        label = stopped[0] if stopped else next(iter(waiting), None)
        b = waiting.get(label) or {}
        research._set(campaign, pair_id, status="stopped", reason=f"{label}: {b.get('reason') or 'stopped'}",
                      failure=b.get("failure"))
        if errors:
            raise errors[0]
        return "stopped"
    if waiting:
        label, b = next(iter(waiting.items()))
        research._set(campaign, pair_id, status="BLOCKED", reason=f"{label}: {b.get('reason') or b.get('status')}",
                      failure=b.get("failure"))
        return "BLOCKED"
    try:
        frozen = {label: verify(freeze(campaign, pair_id, label))["inventory_sha256"] for label in labels(campaign)}
    except BundleError as error:
        research._set(campaign, pair_id, status="BLOCKED", reason=f"freeze: {error}")
        return "BLOCKED"
    (d / "branches" / "metrics.json").write_text(json.dumps(metrics(campaign, pair_id), indent=1))
    research._set(campaign, pair_id, stage="peers", round=1, status="running", reason=None, failure=None,
                  branches_frozen=frozen)
    return research.run_thread(joint, pair_id, stop)


def _shingles(text: str, n: int = 3) -> set:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {tuple(words[i:i + n]) for i in range(max(len(words) - n + 1, 1))} if words else set()


def metrics(campaign, pair_id: str) -> dict:
    """The D10 measurements over the frozen bundles: per branch, its reviews, the requests they issued and how
    those ended; Vera's rejection rate (the share of reviews that asked for more work); and thread divergence,
    the mean pairwise Jaccard distance between the branches' word 3-grams over their substantive ledger text
    (0 when the branches wrote the same, 1 when they share nothing, null with fewer than two branches)."""
    from .ledger import SUBSTANTIVE, Ledger
    root = campaign.thread_dir(pair_id) / "branches"
    per, grams, reviews_total, rejecting_total = {}, {}, 0, 0
    for label in labels(campaign):
        rows = Ledger(root / label / "ledger.jsonl").read() if (root / label / "ledger.jsonl").exists() else []
        status = json.loads((root / label / "status.json").read_text()) if (root / label / "status.json").exists() else {}
        responses = []
        for row in rows:
            if row["kind"] == "review":
                try:
                    responses.append(json.loads(row["text"]).get("response") or {})
                except ValueError:
                    responses.append({})
        rejecting = sum(1 for r in responses if r.get("requests"))
        requests = (status.get("requests") or {}).values()
        substantive = [r["text"] for r in rows if r["kind"] in SUBSTANTIVE]
        per[label] = {"reviews": len(responses), "rejecting_reviews": rejecting,
                      "rejection_rate": rejecting / len(responses) if responses else None,
                      "requests_issued": sum(len(r.get("requests") or []) for r in responses),
                      "resolved": sum(1 for r in requests if r.get("status") == "resolved"),
                      "deferred": sum(1 for r in requests if r.get("status") == "deferred"),
                      "handoff_reason": status.get("handoff_reason"), "substantive_entries": len(substantive)}
        grams[label] = _shingles("\n".join(substantive))
        reviews_total += len(responses); rejecting_total += rejecting
    pairs = [(a, b) for i, a in enumerate(grams) for b in list(grams)[i + 1:]]
    distances = [1 - len(grams[a] & grams[b]) / len(grams[a] | grams[b]) if grams[a] | grams[b] else 0.0 for a, b in pairs]
    return {"branches": per, "rejection_rate": rejecting_total / reviews_total if reviews_total else None,
            "divergence": sum(distances) / len(distances) if distances else None,
            "pairwise": {f"{a}|{b}": d for (a, b), d in zip(pairs, distances)}}
