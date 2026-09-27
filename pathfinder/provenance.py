"""The run record: what a run actually executed, so a result can be traced to its whole deployment.

runner.run writes run.json (the current record) and appends it to runs.jsonl. Every receipt carries the
run_id. A record holds the engine (kind, commit, whether the working files differ from it, and a digest of
the runtime files actually loaded), the deployment (its repository commit and lock file, when campaign.json
names them under "deployment"), the extensions with their source digests, the resolved configuration, the
composed prompt and style digests, the TeX version and the corpus snapshot digests.

On resume the runner compares the new record's components with the previous run's. A difference refuses the
run unless the operator accepts it explicitly (accept_change), which is recorded with the reason and the
previous run_id; work recorded under earlier runs is kept, never re-attributed."""
from __future__ import annotations
import hashlib, json, subprocess, time
from contextlib import contextmanager
from importlib import metadata
from pathlib import Path
from . import extensions, freeze, resources

PACKAGE = resources.PACKAGE
COMPONENTS = ("engine", "deployment", "extensions", "config", "prompts", "styles", "tex", "corpus")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(repo: Path, *args) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def _runtime_digest() -> str:
    """sha256 over the runtime files the process loaded from: the package and the built-in prompts."""
    h = hashlib.sha256()
    for base, name in ((PACKAGE, "pathfinder"), (resources.engine_prompts(), "prompts")):
        for f in sorted(base.rglob("*")):
            rel = f"{name}/{f.relative_to(base).as_posix()}"
            if f.is_file() and not freeze._ignored(rel):
                h.update(rel.encode() + b"\0" + _sha(f.read_bytes()).encode() + b"\n")
    return h.hexdigest()


# taken when the engine is first imported: the files a long-lived process loaded, not later edits
_RUNTIME_AT_IMPORT = _runtime_digest()


def runtime_digest() -> str:
    return _RUNTIME_AT_IMPORT


def engine() -> dict:
    """kind: checkout (a git working tree), frozen (a freeze with its manifest), installed (a package with
    PEP 610 metadata) or copy (none of these: an unverified copy)."""
    out = {"runtime_sha256": runtime_digest(), "path": str(PACKAGE)}
    root = PACKAGE.parent
    frozen = root / freeze.MANIFEST
    if (root / ".git").exists() and _git(root, "rev-parse", "HEAD"):
        dirty = _git(root, "status", "--porcelain", "--", *freeze.RUNTIME)
        out.update(kind="checkout", commit=_git(root, "rev-parse", "HEAD"), modified=bool(dirty))
    elif frozen.is_file():
        manifest = json.loads(frozen.read_text())
        local = freeze.local_inventory(root)
        # the manifest is an editable file: matching it is not verification against the commit, which needs
        # the source repository (pathfinder verify-frozen); at run time that is reported as not established
        out.update(kind="frozen", commit=manifest.get("commit"), ref=manifest.get("ref"), modified=None,
                   matches_manifest=local == manifest.get("files"), verified_against_commit="unverifiable")
    else:
        commit = None
        try:
            direct = metadata.distribution("pathfinder").read_text("direct_url.json")
            commit = (json.loads(direct).get("vcs_info") or {}).get("commit_id") if direct else None
        except metadata.PackageNotFoundError:
            pass
        out.update(kind="installed" if commit else "copy", commit=commit, modified=None)
    return out


def deployment(campaign) -> dict:
    """Declared under "deployment" in campaign.json: name, repo (for tracing), lock, and files, a list of
    globs relative to the campaign root naming the deployment's runtime code (controllers, helpers); each
    matching file's digest is compared on resume."""
    spec = dict((campaign.raw or {}).get("deployment") or {})
    out = {"name": spec.get("name")}
    if spec.get("files"):
        root = Path(campaign.root)
        out["files"] = {f.relative_to(root).as_posix(): _sha(f.read_bytes())
                        for pattern in spec["files"] for f in sorted(root.glob(pattern)) if f.is_file()}
    if spec.get("repo"):
        repo = (Path(campaign.root) / spec["repo"]).resolve()
        out.update(repo=str(repo), commit=_git(repo, "rev-parse", "HEAD"),
                   modified=bool(_git(repo, "status", "--porcelain")) if _git(repo, "rev-parse", "HEAD") else None)
    if spec.get("lock"):
        lock = (Path(campaign.root) / spec["lock"]).resolve()
        out["lock_sha256"] = _sha(lock.read_bytes()) if lock.is_file() else None
    return out


def _tex_version() -> str | None:
    try:
        r = subprocess.run(["pdflatex", "--version"], capture_output=True, text=True, timeout=30)
        return r.stdout.splitlines()[0] if r.returncode == 0 and r.stdout else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def record(campaign, run_id: str) -> dict:
    raw = campaign.raw or {}
    resolved = {k: getattr(campaign, k) for k in ("backend", "model", "scan_model", "peer_search", "seats", "cut",
                                                  "rounds", "allowances", "budget_usd", "prices", "scan_fulltext",
                                                  "call_estimate_usd")}
    resolved["peers"] = list(campaign.peers)
    config_bytes = json.dumps({"resolved": resolved, "raw": raw}, sort_keys=True).encode()
    corpus = {side: _sha(campaign.path(f"{side}.jsonl").read_bytes())
              for side in ("Q", "P") if campaign.path(f"{side}.jsonl").exists()}
    return {"run_id": run_id, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "engine": engine(), "deployment": deployment(campaign), "extensions": extensions.digests(campaign),
            "config": {"sha256": _sha(config_bytes), "resolved": resolved, "raw": raw},
            "prompts": resources.prompt_digests(campaign), "styles": resources.style_digests(campaign),
            "tex": _tex_version(), "corpus": corpus}


def components(rec: dict) -> dict:
    """The parts of a record that decide what ran. The engine is compared by the content it loaded, not
    by commit, so a commit touching only notes or plans does not block a resume; the deployment by its
    lock and declared runtime files, its extension code (every Python file under the extension path) under
    extensions. Commits stay in the record for tracing."""
    e, d = rec.get("engine") or {}, rec.get("deployment") or {}
    return {"engine": {k: e.get(k) for k in ("kind", "runtime_sha256")},
            "deployment": {k: d.get(k) for k in ("name", "lock_sha256", "files")}, "extensions": rec.get("extensions"),
            "config": (rec.get("config") or {}).get("sha256"), "prompts": rec.get("prompts"),
            "styles": rec.get("styles"), "tex": rec.get("tex"), "corpus": rec.get("corpus")}


def changes(previous: dict, current: dict) -> list[str]:
    a, b = components(previous), components(current)
    return [k for k in COMPONENTS if a.get(k) != b.get(k)]


class RestartRequired(Exception):
    """Code on disk differs from the code this process loaded. No accepted change can cover it: the record
    would name code that is not running. Restart the process."""


def loaded_matches_disk(campaign) -> list[str]:
    """What differs between the code this process loaded and the files now on disk."""
    stale = []
    if _runtime_digest() != _RUNTIME_AT_IMPORT:
        stale.append("engine")
    if extensions.digests(campaign) != extensions.digests(campaign, fresh=True):
        stale.append("extensions")
    return stale


def start(campaign, run_id: str, accept_change: str | None = None) -> tuple[dict | None, list[str]]:
    """Write the run record, or refuse: returns (record, []) when written, (None, changed components)
    when the previous run differs and no change was accepted. Raises RestartRequired when the loaded
    engine or extension code no longer matches the files on disk."""
    stale = loaded_matches_disk(campaign)
    if stale:
        raise RestartRequired(f"{', '.join(stale)} changed on disk since this process loaded it; restart the process")
    current = record(campaign, run_id)
    path = campaign.path("run.json")
    previous = json.loads(path.read_text()) if path.exists() else None
    changed = changes(previous, current) if previous else []
    if changed and not accept_change:
        return None, changed
    if previous:
        current["previous_run_id"] = previous.get("run_id")
    if changed:
        current["accepted_change"] = {"components": changed, "reason": accept_change}
    path.write_text(json.dumps(current, indent=1))
    with campaign.path("runs.jsonl").open("a") as stream:
        stream.write(json.dumps(current) + "\n")
    return current, changed


class ChangeRefused(Exception):
    """The run record differs from the previous run's and the change was not accepted."""

    def __init__(self, changed):
        self.changed = changed
        super().__init__(f"{', '.join(changed)} changed since the previous run (see run.json); inspect, then rerun"
                         " with --accept-change REASON to start a linked run")


@contextmanager
def run_context(campaign, accept_change: str | None = None):
    """Every entry point that dispatches model calls runs inside one of these: it takes exclusive campaign
    ownership, then writes the run record or raises ChangeRefused, and sets campaign.run_id so every receipt
    names the run. Ownership is held for the whole dispatch. Nested entries (a bounded run inside run_pair,
    research inside a CLI command) share the outer run and its ownership."""
    import uuid
    from . import health
    current = getattr(campaign, "run_id", None)
    if current and health.owned_run(campaign) == current:     # nested in this thread's own run
        yield current
        return
    with health.owner(campaign, nested=True):   # ownership first: nothing is read or written unless we own it
        run_id = uuid.uuid4().hex
        rec, changed = start(campaign, run_id, accept_change)
        if rec is None:
            raise ChangeRefused(changed)
        campaign.run_id = run_id
        health.bind_run(campaign, run_id)
        try:
            yield run_id
        finally:
            health.bind_run(campaign, None)
            del campaign.run_id
