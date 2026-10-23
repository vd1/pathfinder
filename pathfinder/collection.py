"""Pinned, offline collections for classic research; pooled files stay in place.

This is an explicit mode, not an extra paper-fetch preference. The host validates
the manifest and every file before each call. Codex tool processes receive only
the current thread, runtime files and individually admitted source files.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

PROFILE = "pathfinder_collection"
RUNTIME_ROOTS = ("/usr", "/bin", "/sbin", "/System", "/Library", "/opt", "/private/tmp",
                 "/tmp", "/private/var")
DISABLED_FEATURES = ("apps", "browser_use", "browser_use_external", "browser_use_full_cdp_access",
                     "computer_use", "in_app_browser", "plugins", "remote_plugin", "hooks",
                     "multi_agent", "multi_agent_v2", "shell_snapshot", "shell_snapshot_v2",
                     "skill_search", "skill_mcp_dependency_install", "external_agent_memory_import",
                     "image_generation", "in_app_local_automation", "agent_message_board",
                     "workspace_dependencies")


class Refused(ValueError):
    pass


def enabled(campaign):
    return "restricted_collection" in campaign.raw


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _date(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise Refused("collection dates require explicit UTC timestamps ending in Z")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise Refused("invalid collection date") from error


def _outside_runtime(path):
    return not any(path.is_relative_to(Path(p).resolve()) for p in (*RUNTIME_ROOTS, sys.base_prefix))


def _file(row):
    if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
        raise Refused("collection file needs only an absolute path and sha256")
    path = Path(row["path"])
    if not path.is_absolute() or path != path.resolve() or not path.is_file() or path.is_symlink():
        raise Refused("collection file must be an existing canonical regular file")
    if not re.fullmatch("[0-9a-f]{64}", row["sha256"]) or _sha(path) != row["sha256"]:
        raise Refused(f"collection file hash differs: {path}")
    if not _outside_runtime(path):
        raise Refused("collection evidence cannot live inside runtime-readable directories")
    return path


def load(campaign):
    spec = campaign.raw.get("restricted_collection")
    if not isinstance(spec, dict) or set(spec) != {"manifest", "sha256"}:
        raise Refused("restricted_collection needs manifest and sha256")
    path = campaign.path(spec["manifest"]).resolve()
    if _sha(path) != spec["sha256"]:
        raise Refused("restricted collection manifest hash differs")
    data = json.loads(path.read_text())
    if set(data) != {"version", "pair_id", "pool_roots", "cutoff_utc", "sources", "inputs"} or data["version"] != 1:
        raise Refused("unsupported restricted collection manifest")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", data["pair_id"]):
        raise Refused("invalid collection pair ID")
    cutoff = _date(data["cutoff_utc"])
    if not isinstance(data["pool_roots"], list) or not data["pool_roots"]:
        raise Refused("pool_roots must name the audited logical pool directories")
    pools = [Path(p) for p in data["pool_roots"]]
    if (len(set(pools)) != len(pools) or any(not p.is_absolute() or p != p.resolve()
            or not p.is_dir() or not _outside_runtime(p) for p in pools)):
        raise Refused("pools must be unique canonical directories outside runtime-readable paths")
    root = Path(campaign.root).resolve()
    if any(pool.is_relative_to(root) or root.is_relative_to(pool) for pool in pools):
        raise Refused("shared pool and restricted campaign must be disjoint")
    if not isinstance(data["sources"], list) or not data["sources"]:
        raise Refused("collection has no admitted sources")
    ids, paths = set(), set()
    for source in data["sources"]:
        if set(source) != {"id", "version", "first_appearance_utc", "version_appearance_utc", "files"}:
            raise Refused("source needs pinned identity/version, both dates and exact files")
        if not all(isinstance(source[k], str) and source[k].strip() for k in ("id", "version")):
            raise Refused("unversioned source refused")
        if source["version"].lower() in ("latest", "unknown", "unversioned"):
            raise Refused("source needs an audited pinned version")
        if source["id"] in ids:
            raise Refused("duplicate source identity")
        ids.add(source["id"])
        first, version = _date(source["first_appearance_utc"]), _date(source["version_appearance_utc"])
        if not first <= version < cutoff:
            raise Refused("source version must appear strictly before cutoff")
        if not isinstance(source["files"], list) or not source["files"]:
            raise Refused("source needs admitted files")
        for row in source["files"]:
            file = _file(row)
            if not any(file.is_relative_to(pool) for pool in pools) or file in paths:
                raise Refused("source file is outside pool or duplicated")
            paths.add(file)
    if not isinstance(data["inputs"], dict) or set(data["inputs"]) != {"Q", "P"}:
        raise Refused("collection needs Q and P input contracts")
    for row in data["inputs"].values():
        if set(row) != {"id", "title", "path", "sha256", "source_ids"}:
            raise Refused("input contract needs id/title/path/hash/source_ids")
        input_path = _file({k: row[k] for k in ("path", "sha256")})
        if input_path.is_relative_to(campaign.root):
            raise Refused("immutable input contracts must be outside the writable campaign")
        if input_path.suffix not in (".txt", ".md", ".tex"):
            raise Refused("input contract must be a text document")
        if not row["source_ids"] or not set(row["source_ids"]) <= ids:
            raise Refused("input contract cites unadmitted sources")
    return data


def validate_config(campaign):
    """Reject routes that could escape the enforced backend and runtime profile."""
    if campaign.backend not in ("codex", "stub") or campaign.raw.get("research_scheme") is not None:
        raise Refused("restricted collections currently support classic Codex research only")
    if campaign.raw.get("extensions") or campaign.raw.get("refusal_fallback"):
        raise Refused("restricted collection disallows deployment dispatch/extensions and fallback")
    for route in (campaign.raw.get("routes") or {}).values():
        if isinstance(route, dict) and (route.get("backend", campaign.backend) != campaign.backend
                                      or route.get("config") or route.get("codex")):
            raise Refused("restricted route cannot override backend or Codex configuration")
    prov = campaign.raw.get("codex") or {}
    if (prov.get("config") or isinstance(prov.get("filesystem_profile"), dict)
            or prov.get("persist_sessions") or prov.get("base_url")):
        raise Refused("restricted collection disallows permission/config overrides and persistent sessions")
    root = Path(campaign.root).resolve()
    if not _outside_runtime(root):
        raise Refused("restricted campaign must be outside runtime-readable directories")
    # Codex ignores user config, but project/system layers must not introduce tools.
    user_config = (Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml").resolve()
    for ancestor in (root, *root.parents):
        candidate = ancestor / ".codex/config.toml"
        if candidate.exists() and candidate.resolve() != user_config:
            raise Refused("restricted campaign cannot inherit a project Codex config")
    if Path("/etc/codex/config.toml").exists():
        raise Refused("restricted mode needs an audited system configuration without extra tools")
    if os.environ.get("PATHFINDER_CODEX"):
        raise Refused("restricted mode does not accept an overridden Codex executable")
    return load(campaign)


def inspect(campaign):
    """Read-only preflight: no preparation, provider access or source execution."""
    data = validate_config(campaign)
    d = campaign.thread_dir(data["pair_id"])
    if d.exists():
        seal = d / "inputs/restricted-collection.json"
        if not seal.is_file() or json.loads(seal.read_text()) != data:
            raise Refused("existing thread has no matching collection seal")
        check_inputs(d, data)
    group = None
    if "budget_group" in campaign.raw:
        from . import budget_group
        path, roots, cap = budget_group.load(campaign)
        accounting = budget_group.report(campaign)
        group = dict(manifest=str(path), campaigns=[str(p) for p in roots],
                     limits=cap, refusal=accounting["refusal"],
                     accounting=accounting,
                     semantics="receipt-based projected admission; no hard in-flight token truncation")
    return dict(status="blocked" if group and group["refusal"] else "verified",
                pair_id=data["pair_id"], cutoff_utc=data["cutoff_utc"],
                source_count=len(data["sources"]),
                admitted_file_count=sum(len(s["files"]) for s in data["sources"]),
                permission_settings=settings(campaign, d, True), budget_group=group,
                limitations=["Cutoff dates and source identity require operator audit.",
                             "Model pretrained knowledge is not erased by source-access restrictions."])


def prepare(campaign, pair_id, rows):
    from . import thread
    data = validate_config(campaign)
    if data["pair_id"] != pair_id:
        raise Refused("collection belongs to another pair")
    d = campaign.thread_dir(pair_id)
    seal = d / "inputs/restricted-collection.json"
    manifest = json.dumps(data, sort_keys=True, indent=1) + "\n"
    if (d / "status.json").exists():
        if not seal.is_file() or seal.read_text() != manifest:
            raise Refused("existing thread has no matching immutable collection")
        check_inputs(d, data)
        thread.install_helper(d)
        return d
    # The native runner acquires its thread lock before initialisation. Only that
    # regular, current-process lock is administrative; no existing content is admitted.
    def runner_lock(p):
        return (p.name == "lock" and not p.is_symlink() and p.is_file()
                and p.read_text() == str(os.getpid()))
    if d.exists() and any(not runner_lock(p) for p in d.iterdir()):
        raise Refused("restricted collection requires a fresh thread")
    if any(row["id"] != data["inputs"][side]["id"] for side, row in zip("QP", rows)):
        raise Refused("corpus row does not match admitted input contract")
    (d / "inputs").mkdir(parents=True)
    for side, row in zip("QP", rows):
        admitted = data["inputs"][side]
        src = Path(admitted["path"])
        (d / "inputs" / f"{side}{src.suffix}").symlink_to(src)
        # Do not import corpus abstracts, rank metadata or target-related context.
        (d / "inputs" / f"{side}.json").write_text(json.dumps(
            {"id": row["id"], "title": admitted["title"], "text": str(src)}, indent=1))
    seal.write_text(manifest)
    for actor in campaign.peers:
        (d / actor).mkdir()
    thread._set(campaign, pair_id, round=1, stage="peers", status="running", reason=None, started=thread._now())
    thread.install_helper(d)
    return d


def check_inputs(d, data):
    for side, row in data["inputs"].items():
        src = Path(row["path"])
        link = d / "inputs" / f"{side}{src.suffix}"
        if not link.is_symlink() or link.resolve() != src:
            raise Refused("restricted input reference changed")
    if (d / "inputs/added.json").exists() or (d / "inputs/pair-context.md").exists():
        raise Refused("restricted thread has additional unadmitted inputs")


def check_request(campaign, request):
    data = validate_config(campaign)
    if request.thread != data["pair_id"] or request.stage not in ("peer", "consolidate", "verify"):
        raise Refused("restricted collection admits only its pair's classic research stages")
    d = campaign.thread_dir(request.thread).resolve()
    if Path(request.cwd).resolve() != d:
        raise Refused("restricted research must use the sealed thread cwd")
    seal = d / "inputs/restricted-collection.json"
    if not seal.is_file() or json.loads(seal.read_text()) != data:
        raise Refused("restricted collection seal differs")
    check_inputs(d, data)
    return data


def settings(campaign, cwd, tools):
    from . import sandbox
    data = validate_config(campaign)
    d = campaign.thread_dir(data["pair_id"]).resolve()
    if Path(cwd).resolve() != d:
        raise Refused("restricted cwd differs from collection")
    fs = {":minimal": "read", str(d): "write" if tools else "read",
          str(Path(__file__).resolve().parent): "read", "/opt/homebrew": "read",
          str(Path(sys.base_prefix).resolve()): "read",
          "/Library/Frameworks/Python.framework": "read",
          "/private/tmp": "deny", "/tmp": "deny", "/private/var/folders": "deny"}
    for name in sandbox.CONTROL:
        fs[str(d / name)] = "read"
    fs[str(d / "inputs/restricted-collection.json")] = "deny"
    fs[str(d / ".pathfinder")] = "read"
    for name in ("tmp", "texmf-var"):
        fs[str(d / ".pathfinder" / name)] = "write" if tools else "read"
    for source in data["sources"]:
        for row in source["files"]:
            fs[row["path"]] = "read"
    for row in data["inputs"].values():
        fs[row["path"]] = "read"
    settings = {"default_permissions": PROFILE, f"permissions.{PROFILE}.filesystem": fs,
                f"permissions.{PROFILE}.network.enabled": False, "web_search": "disabled",
                "project_doc_max_bytes": 0, "features.skip_host_skill_discovery": True,
                "shell_environment_policy.inherit": "none",
                "shell_environment_policy.set": {
                    "PATH": "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
                    "TMPDIR": str(d / ".pathfinder/tmp"),
                    "TMPPREFIX": str(d / ".pathfinder/tmp/zsh"),
                    "TEXMFVAR": str(d / ".pathfinder/texmf-var"),
                    "UV_CACHE_DIR": str(d / ".pathfinder/tmp/uv-cache"),
                    "PYTHONDONTWRITEBYTECODE": "1"}}
    settings.update({f"features.{name}": False for name in DISABLED_FEATURES})
    return settings


def args(campaign, cwd, tools):
    from .sandbox import toml
    out = ["--strict-config", "--ignore-rules"]
    for key, value in settings(campaign, cwd, tools).items():
        out += ["-c", f"{key}={toml(value)}"]
    return out


def rule(campaign, d):
    data = load(campaign)
    return ("\n\nApproved research collection: use only the admitted input contracts and source files below. "
            "No retrieval, web search, network access or full-pool browsing. Missing-source requests are requests "
            "only: when your role permits writes, append the requested reference and reason to "
            "source-requests.jsonl; otherwise report it in your response. Do not fetch it. "
            + "\n" + json.dumps({"sources": [
                {"id": s["id"], "version": s["version"], "paths": [f["path"] for f in s["files"]]}
                for s in data["sources"]]}, ensure_ascii=False) + "\n")
