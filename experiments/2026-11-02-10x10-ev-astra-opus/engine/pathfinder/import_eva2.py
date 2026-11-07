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
- the joint campaign's prompts become the campaign's prompts; the receipts are merged from the campaigns'
  own logs, if any, and from eva2's runtime store (runtime/receipts/<call>.json, one file per call), each
  branch's marked with its label; import.json records where everything came from and how many receipts;
- an eva2 receipt's stage and actor come from its call identity (research calls name them; the account editor
  and the PCE roles are the edit stage with their own actor; an assessment is its own stage, actor assessor),
  its model from its route, and its "at" from the file's mtime, marked "at_source": "file mtime", since eva2
  kept no call time; eva2 rows are in that order and keep their identity as eva2_identity;
- the PCE round reports/index.md links as the reviewed account, when its delivery record says the editor
  accepted it, becomes the edited note: edited/note.tex and note.pdf, the round kept as edited/eva2-pce, the
  edit done, and import.json["edit"] records the source and digests. eva2 ran no paper stage; none is made.
- eva2's actionability assessment, the latest available, becomes the pair's actionability answer; its
  fidelity and reader comparisons have no engine stage and stay receipts.

Nothing in the experiment is changed. The imported pair then goes on through the engine: what is not done of
edit and paper. verify_bundle reads a bundle eva2 froze where it lies (a deployment's recorded campaigns), by
its inventory, without julien-2's code."""
from __future__ import annotations
import hashlib, json, os, re, shutil
from datetime import datetime, timezone
from pathlib import Path
from . import composable, config, edit, research

SCHEME = ("research_scheme", "research_bundles", "imported_research")
DOLLARS = ("budget_usd", "call_estimate_usd", "prices")   # subscription billing: eva2 set budget_usd 0, which would stop every call


def _raw(path: Path) -> dict:
    raw = json.loads((path / "campaign.json").read_text())
    if raw.get("research_scheme") == "eva_minus":
        raw["research_scheme"] = "direct_eva"
    return raw


def _differences(raw: dict, base: dict) -> dict:
    return {k: v for k, v in raw.items() if k not in SCHEME and k not in DOLLARS and base.get(k) != v}


STAGES = {"peers": "peer"}
ASSESSORS = {"actionability", "fidelity", "reader"}     # eva2's assessor stages, routed to its assessor


def _stage_actor(identity: str, experiment: str) -> tuple[str | None, str | None, str | None]:
    """(run, stage, actor) from an eva2 call identity. Research calls are
    [<experiment>/]<run>/.../<pair>:<stage>:<actor>:...; the later stages have no pair part:
    <run>/account/<n> (the account editor), <run>/pce*/[pass-NN/]<role> (a PCE role) and
    <run>/[<recovery>/]<assessment>/<n> (an assessor). The account and PCE are the engine's edit stage."""
    parts = identity.split("/")
    if parts and parts[0] == experiment:
        parts = parts[1:]
    run = parts[0] if parts else None
    if ":" in identity:
        head = identity.split(":")
        return run, STAGES.get(head[1], head[1]), head[2] if len(head) > 2 else None
    if len(parts) >= 3 and parts[1] == "account":
        return run, "edit", "account-editor"
    if len(parts) >= 3 and parts[1].startswith("pce"):
        return run, "edit", parts[-1]
    if len(parts) >= 3 and parts[-2] in ASSESSORS:
        return run, parts[-2], "assessor"
    return run, None, None


def _eva2_receipt(path: Path, labels: list[str], experiment: str) -> dict:
    """One eva2 runtime receipt as an engine receipt row. eva2 kept no call time: the receipt file's
    modification time (written when the call ended) stands in, marked as such in "at_source"."""
    r = json.loads(path.read_text())
    identity = str(r.get("identity", ""))
    run, stage, actor = _stage_actor(identity, experiment)
    usage = r.get("usage") or {}
    at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    row = {"v": 3, "call_id": path.stem, "at": at, "at_source": "file mtime", "thread": "Q1P1",
           "branch": run if run in labels else None, "stage": stage, "actor": actor,
           "backend": (r.get("route") or {}).get("runtime"), "model": (r.get("route") or {}).get("model"),
           "outcome": r.get("outcome"), "seconds": r.get("seconds"), "usage": usage,
           "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
           "cache_read": usage.get("cached_input_tokens"), "cost": r.get("cost"),
           "eva2_identity": identity, "imported_from": "eva2"}
    if r.get("error"):
        row["error"] = r["error"]
    return row


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_bundle(path: Path) -> dict:
    """A bundle eva2 froze (bundle.json with a list inventory, digested over its canonical JSON), checked by its
    inventory alone: every listed file present with its digest and size, nothing added, no symbolic link, no
    path leaving the bundle. eva2's handoff and reference checks are not repeated: the bundle was accepted when
    it was frozen, and reading it now asks only that it is unchanged. Returns eva2's record."""
    from pathlib import PurePosixPath
    root, name = Path(path), Path(path).name
    if root.is_symlink():
        raise composable.BundleError(f"{name}: the bundle is a symbolic link")
    try:
        record = json.loads((root / "bundle.json").read_text())
    except (OSError, ValueError) as error:
        raise composable.BundleError(f"{name}: unreadable bundle.json ({error})") from None
    rows = record.get("files")
    canonical = (json.dumps(rows, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    if not isinstance(rows, list) or record.get("inventory_sha256") != hashlib.sha256(canonical).hexdigest():
        raise composable.BundleError(f"{name}: bundle.json does not match its own inventory digest")
    listed = {}
    for row in rows:
        file = row.get("path") if isinstance(row, dict) else None
        p = PurePosixPath(file or "")
        if not file or p.is_absolute() or ".." in p.parts or "\\" in file or str(p) != file or file in listed:
            raise composable.BundleError(f"{name}: unsafe or repeated inventory path {file!r}")
        listed[file] = row
    present = {p.relative_to(root).as_posix(): p for p in composable._files(root, name) if p != root / "bundle.json"}
    for file in sorted(set(listed) - set(present)):
        raise composable.BundleError(f"{name}: {file} is missing")
    for file in sorted(set(present) - set(listed)):
        raise composable.BundleError(f"{name}: {file} was added after the freeze")
    for file, row in sorted(listed.items()):
        if present[file].stat().st_size != row.get("bytes") or _sha(present[file]) != row.get("sha256"):
            raise composable.BundleError(f"{name}: {file} changed after the freeze")
    return record


def _accepted_pce(experiment: Path) -> Path | None:
    """The PCE round reports/index.md links as the reviewed account, if its delivery record says the editor
    accepted it and its account.tex and account.pdf are there."""
    index = experiment / "reports" / "index.md"
    found = re.search(r"\[Reviewed PCE account\]\(([^)]+)\)", index.read_text()) if index.exists() else None
    if not found:
        return None
    d = (experiment / "reports" / found.group(1)).parent
    delivery = d / "delivery.json"
    if not delivery.exists() or not (d / "account.tex").exists() or not (d / "account.pdf").exists():
        return None
    record = json.loads(delivery.read_text())
    if record.get("editorial_status") != "accepted" or (record.get("pce_result") or {}).get("status") != "accepted":
        return None
    return d


def _import_edit(c, experiment: Path) -> dict | None:
    """eva2's accepted PCE account as the pair's edited note: note.tex and note.pdf are the accepted account,
    the whole accepted round is kept as edited/eva2-pce, and the edit is done."""
    d = _accepted_pce(experiment)
    if d is None:
        return None
    ed = c.thread_dir("Q1P1") / "edited"; ed.mkdir(exist_ok=True)
    shutil.copytree(d, ed / "eva2-pce")
    shutil.copy2(d / "account.tex", ed / "note.tex")
    shutil.copy2(d / "account.pdf", ed / "note.pdf")
    delivery = json.loads((d / "delivery.json").read_text())
    render = json.loads((d / "account.render.json").read_text()) if (d / "account.render.json").exists() else {}
    record = {"source": d.relative_to(experiment).as_posix(), "editorial_status": delivery.get("editorial_status"),
              "pce_result": (delivery.get("pce_result") or {}).get("status"),
              "note_sha256": _sha(ed / "note.tex"), "pdf_sha256": _sha(ed / "note.pdf"),
              "pdf_matches_render": render.get("pdf_sha256") == _sha(ed / "note.pdf") if render else None,
              "kept_as": "edited/eva2-pce"}
    edit._set(c, "Q1P1", status="done", imported_from="eva2 PCE", source=record["source"],
              editorial_status=record["editorial_status"], build_ok=bool(render.get("passed")) if render else None)
    return record


def _import_actionability(c, experiment: Path) -> str | None:
    """eva2's actionability assessment (the latest available under reports/assessments) as the pair's
    actionability answer, when it fits the engine's contract."""
    from . import actionability, contracts
    found = sorted((experiment / "reports" / "assessments").glob("*/actionability.json"))
    for path in reversed(found):
        record = json.loads(path.read_text())
        answer = record.get("assessment")
        if record.get("status") == "available" and isinstance(answer, dict) \
                and not contracts.violations(answer, actionability.SCHEMA):
            source = path.relative_to(experiment).as_posix()
            actionability._set(c, "Q1P1", status="done", decision=answer["decision"], assessment=answer,
                               imported_from=source)
            return source
    return None


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
    receipts, counts = [], {"campaign_logs": 0, "eva2_runtime": 0}
    for name in ["joint", *labels]:                  # receipts written by the campaigns themselves, if any
        path = runs / name / "receipts.jsonl"
        for line in path.read_text().splitlines() if path.exists() else []:
            if line.strip():
                row = json.loads(line)
                if name != "joint":
                    row["branch"] = name
                receipts.append(row); counts["campaign_logs"] += 1
    eva2 = [_eva2_receipt(path, labels, experiment.name)                        # eva2 keeps one file per call
            for path in (experiment / "runtime" / "receipts").glob("*.json")]
    receipts += sorted(eva2, key=lambda r: (r["at"], r["call_id"])); counts["eva2_runtime"] = len(eva2)
    (out / "receipts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in receipts))
    c = config.load(out)
    status = research.status(c, "Q1P1")
    research._set(c, "Q1P1", branches_frozen=frozen,
                  history=list(status.get("history") or []) + [{"at": research._now(), "action": "imported from eva2",
                                                               "from_status": status.get("status")}])
    edited = _import_edit(c, experiment)
    assessed = _import_actionability(c, experiment)
    (out / "import.json").write_text(json.dumps({
        "experiment": str(experiment), "branches": labels, "frozen": frozen, "joint_status": status.get("status"),
        "receipts": counts, "receipt_times": "eva2 kept no call time: each receipt's \"at\" is its file's mtime",
        "edit": edited,
        "paper": "not mapped: eva2's PCE accepted the readable account (the engine's edit); eva2 ran no paper stage",
        "actionability": assessed,
        "assessments": "eva2's fidelity and reader comparisons have no engine stage; their calls are receipts only"}, indent=1))
    return out
