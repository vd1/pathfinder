"""Frozen engine copies bound to a commit.

The engine artifact is the runtime paths of this repository (RUNTIME: the package and the built-in prompts)
at one commit. `freeze` writes exactly the files git holds for those paths at the resolved commit, plus
engine-freeze.json. `verify` never trusts that manifest's file list: it recomputes the inventory from the
commit itself and compares the copy with it, file set and contents, reporting

    verified      same files, same contents
    modified      files changed, missing or added, each listed
    unverifiable  the commit cannot be read (offline, a deleted tag, another repository)

A copy is a cache of a commit; a copy that does not verify is a fork.

Entries are compared as "mode blob-id". Only regular files (100644) and executables (100755) are supported:
a commit whose runtime paths hold a symlink or a submodule cannot be frozen, and a symlink in a copy is
reported as a changed or added file, never followed. __pycache__ directories are ignored; a standalone
.pyc elsewhere is importable code and counts like any other file."""
from __future__ import annotations
import hashlib, json, os, subprocess
from pathlib import Path

RUNTIME = ("pathfinder", "prompts")
MANIFEST = "engine-freeze.json"
IGNORED_PARTS = {"__pycache__"}
MODES = {"100644", "100755"}


def _git(repo: Path, *args, binary=False):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False)
    if r.returncode:
        raise LookupError(r.stderr.decode(errors="replace").strip() or f"git {' '.join(args)} failed")
    return r.stdout if binary else r.stdout.decode()


def _ignored(rel: str) -> bool:
    return any(p in IGNORED_PARTS for p in rel.split("/")[:-1])


def blob_id(data: bytes) -> str:
    """git's object id for a blob with these bytes, so a local file can be compared with a commit's tree."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def resolve(repo: Path, ref: str) -> str:
    return _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}").strip()


def inventory(repo: Path, commit: str) -> dict:
    """path -> "mode blob-id" for every runtime file at the commit, read from git, not from any copy."""
    out = {}
    for line in _git(repo, "ls-tree", "-r", "--full-tree", commit, "--", *RUNTIME).splitlines():
        meta, _, path = line.partition("\t")
        mode, kind, oid = meta.split()
        if _ignored(path):
            continue
        if kind != "blob" or mode not in MODES:
            raise ValueError(f"unsupported runtime entry {path} (mode {mode}, {kind}); only regular files are frozen")
        out[path] = f"{mode} {oid}"
    if not out:
        raise LookupError(f"no runtime files at {commit}")
    return out


def local_inventory(dest: Path) -> dict:
    out = {}
    for top in RUNTIME:
        base = dest / top
        if not base.exists():
            continue
        for f in sorted(base.rglob("*")):
            rel = f.relative_to(dest).as_posix()
            if _ignored(rel) or f.is_dir() and not f.is_symlink():
                continue
            if f.is_symlink():
                out[rel] = f"symlink {os.readlink(f)}"         # never followed; always differs from a commit's blob
            elif f.is_file():
                mode = "100755" if os.access(f, os.X_OK) else "100644"
                out[rel] = f"{mode} {blob_id(f.read_bytes())}"
    return out


def freeze(repo: Path, ref: str, dest: Path) -> dict:
    repo, dest = Path(repo), Path(dest)
    commit = resolve(repo, ref)
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError(f"{dest} is not empty; freeze into a new directory")
    files = inventory(repo, commit)
    for path, entry in files.items():
        mode, oid = entry.split()
        target = dest / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_git(repo, "cat-file", "blob", oid, binary=True))
        target.chmod(0o755 if mode == "100755" else 0o644)
    manifest = {"commit": commit, "ref": ref, "runtime": list(RUNTIME), "files": files}
    (dest / MANIFEST).write_text(json.dumps(manifest, indent=1, sort_keys=True))
    return manifest


def verify(dest: Path, repo: Path) -> dict:
    dest = Path(dest)
    manifest = json.loads((dest / MANIFEST).read_text())
    commit = manifest["commit"]
    try:
        expected = inventory(Path(repo), commit)
    except LookupError as error:
        return {"status": "unverifiable", "commit": commit, "reason": str(error)}
    actual = local_inventory(dest)
    changed = sorted(p for p in expected.keys() & actual.keys() if expected[p] != actual[p])
    missing = sorted(expected.keys() - actual.keys())
    added = sorted(actual.keys() - expected.keys())
    status = "verified" if not (changed or missing or added) else "modified"
    return {"status": status, "commit": commit, "changed": changed, "missing": missing, "added": added,
            "manifest_matches_commit": manifest.get("files") == expected}
