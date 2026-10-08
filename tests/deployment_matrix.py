"""deployments.toml, read by the deployment contract tests and the release check.

Outside a release a supported deployment whose checkout is absent is skipped, and a present checkout is tested
as it stands, so local runs work without pinning the siblings. With PATHFINDER_RELEASE=1 nothing is skipped: a missing checkout, a revision other than the pinned
one, or uncommitted changes under its clean_paths fail the test. A deployment with reads = "recorded" is read at
its pinned commit through git archive (recorded()), so its checkout may move on during a release check; the
commit only has to exist in it."""
import os, subprocess, tomllib
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
RELEASE = os.environ.get("PATHFINDER_RELEASE") == "1"


def load() -> dict:
    return tomllib.loads((ROOT / "deployments.toml").read_text())["deployments"]


def checkout(name: str) -> Path:
    """The pinned checkout of a supported deployment, or a skip (outside a release) or failure (in one)."""
    entry = load()[name]
    path = (ROOT / entry["checkout"]).resolve()

    def refuse(reason):
        if RELEASE:
            pytest.fail(f"{name}: {reason}")
        pytest.skip(f"{name}: {reason}")

    if not path.exists():
        refuse(f"checkout {path} is absent")
    if entry["revision"] != "candidate" and RELEASE and entry.get("reads") == "recorded":
        known = subprocess.run(["git", "-C", str(path), "cat-file", "-e", entry["revision"] + "^{commit}"],
                               capture_output=True).returncode == 0
        if not known:
            refuse(f"pinned commit {entry['revision'][:12]} is not in the checkout")
    elif entry["revision"] != "candidate" and RELEASE:        # locally the current checkout is tested as it is
        head = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        if head != entry["revision"]:
            refuse(f"checkout is at {head[:12]}, deployments.toml pins {entry['revision'][:12]}")
        for sub in entry.get("clean_paths", []):
            dirty = subprocess.run(["git", "-C", str(path), "status", "--porcelain", "--", sub],
                                   capture_output=True, text=True).stdout.strip()
            if dirty:
                refuse(f"uncommitted changes under {sub}")
    return path


def recorded(name: str, target: Path) -> Path:
    """The deployment's tracked files at its pinned commit (HEAD outside a release), extracted into target."""
    import io, tarfile
    entry, path = load()[name], checkout(name)
    rev = entry["revision"] if RELEASE and entry["revision"] != "candidate" else "HEAD"
    data = subprocess.run(["git", "-C", str(path), "archive", "--format=tar", rev], capture_output=True, check=True).stdout
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(target, filter="tar")
    return target
