"""julien-2's eva2 experiments as canonical composable pairs.

    pathfinder import-eva2 EXPERIMENT --out DIR

An eva2 experiment holds four sibling campaigns, runs/branch-1..N (direct EVA) and runs/joint (EVA over the
branches' frozen bundles, copied into its thread as branches/branch-N). DIR becomes one canonical composable
campaign with that pair as Q1P1:

- campaign.json is the joint campaign's settings with "research_scheme": "composable", "branches": N, and the
  branch and joint settings that differ from them as the "branch" and "joint" overrides;
- the joint thread is the pair's thread; its branches/branch-N copies keep eva2's exact files (the joint
  ledger cites them), with eva2's bundle.json kept as eva2-bundle.json and a canonical bundle.json written
  over the same files, made read-only and recorded in the pair's status as branches_frozen;
- each branch campaign's thread is kept as branch-runs/branch-N, for the record;
- the joint campaign's prompts become the campaign's prompts; receipts of all four campaigns are merged,
  each branch's marked with its label; import.json records where everything came from.

Nothing in the experiment is changed. The imported pair then goes on through the engine: edit and paper."""
from __future__ import annotations
import json, os, shutil
from pathlib import Path
from . import composable, config, research

SCHEME = ("research_scheme", "research_bundles", "imported_research")
DOLLARS = ("budget_usd", "call_estimate_usd", "prices")   # subscription billing: eva2 set budget_usd 0, which would stop every call


def _raw(path: Path) -> dict:
    raw = json.loads((path / "campaign.json").read_text())
    if raw.get("research_scheme") == "eva_minus":
        raw["research_scheme"] = "direct_eva"
    return raw


def _differences(raw: dict, base: dict) -> dict:
    return {k: v for k, v in raw.items() if k not in SCHEME and k not in DOLLARS and base.get(k) != v}


def run(experiment: Path, out: Path) -> Path:
    experiment, out = Path(experiment).resolve(), Path(out)
    runs = experiment / "runs"
    labels = sorted(p.name for p in runs.glob("branch-*") if p.is_dir())
    if not labels or not (runs / "joint").is_dir():
        raise SystemExit(f"{experiment}: not an eva2 experiment (runs/branch-N and runs/joint)")
    if out.exists():
        raise SystemExit(f"{out} exists: an import is made once")
    out.mkdir(parents=True)
    joint_raw = _raw(runs / "joint")
    branch_raw = _raw(runs / labels[0])
    base = {k: v for k, v in joint_raw.items() if k not in SCHEME and k not in DOLLARS}
    raw = {**base, "research_scheme": "composable", "branches": len(labels),
           "branch": {**_differences(branch_raw, base), **({"imported_research": True} if branch_raw.get("imported_research") else {})},
           "joint": _differences(joint_raw, base)}
    raw["branch"] = {k: v for k, v in raw["branch"].items() if k not in ("research_bundles",)}
    (out / "campaign.json").write_text(json.dumps(raw, indent=1))
    for name in ("Q.jsonl", "P.jsonl", "scan.jsonl"):
        if (runs / "joint" / name).exists():
            shutil.copy2(runs / "joint" / name, out / name)
    for name in ("prompts", "sources"):
        if (runs / "joint" / name).is_dir():
            shutil.copytree(runs / "joint" / name, out / name)
    (out / "shortlist.json").write_text(json.dumps({"pairs": [{"pair_id": "Q1P1"}]}))
    pair = out / "threads" / "Q1P1"
    shutil.copytree(runs / "joint" / "threads" / "Q1P1", pair, ignore=shutil.ignore_patterns(".pathfinder", "*.lock"))
    for label in labels:
        shutil.copytree(runs / label / "threads" / "Q1P1", pair / "branch-runs" / label,
                        ignore=shutil.ignore_patterns(".pathfinder", "*.lock"))
    frozen = {}
    for label in labels:
        bundle = pair / "branches" / label
        if not bundle.is_dir():
            raise SystemExit(f"{experiment}: the joint thread has no branches/{label}")
        for path in bundle.rglob("*"):
            if path.is_file():
                os.chmod(path, 0o644)
        if (bundle / "bundle.json").exists():
            (bundle / "bundle.json").rename(bundle / "eva2-bundle.json")
        inventory = {p.relative_to(bundle).as_posix(): {"sha256": composable._sha(p), "bytes": p.stat().st_size}
                     for p in composable._files(bundle, label)}
        record = {"label": label, "files": inventory, "frozen_at": "imported from eva2",
                  "inventory_sha256": composable._inventory_sha(inventory)}
        (bundle / "bundle.json").write_text(json.dumps(record, indent=1))
        for path in bundle.rglob("*"):
            if path.is_file():
                os.chmod(path, 0o444)
        frozen[label] = record["inventory_sha256"]
    receipts = []
    for name in ["joint", *labels]:
        path = runs / name / "receipts.jsonl"
        for line in path.read_text().splitlines() if path.exists() else []:
            if line.strip():
                row = json.loads(line)
                if name != "joint":
                    row["branch"] = name
                receipts.append(json.dumps(row))
    (out / "receipts.jsonl").write_text("".join(r + "\n" for r in receipts))
    c = config.load(out)
    status = research.status(c, "Q1P1")
    research._set(c, "Q1P1", branches_frozen=frozen,
                  history=list(status.get("history") or []) + [{"at": research._now(), "action": "imported from eva2",
                                                               "from_status": status.get("status")}])
    (out / "import.json").write_text(json.dumps({"experiment": str(experiment), "branches": labels, "frozen": frozen,
                                                 "joint_status": status.get("status")}, indent=1))
    return out
