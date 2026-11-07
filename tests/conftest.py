import pytest

from pathfinder import alerts, research


@pytest.fixture(autouse=True)
def no_real_desktop_notifications(monkeypatch):
    """Failure tests must not notify the user's desktop."""
    monkeypatch.setattr(alerts, "_desktop", lambda *args: "test-suppressed")


@pytest.fixture(autouse=True)
def private_accounts(tmp_path_factory, monkeypatch):
    """Seat pools and subscription pauses live under $PATHFINDER_ACCOUNTS: never the user's own."""
    monkeypatch.setenv("PATHFINDER_ACCOUNTS", str(tmp_path_factory.mktemp("accounts")))


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """No test downloads a paper: the source service answers from its cache only (pathfinder.paper_source)."""
    monkeypatch.setenv("PATHFINDER_OFFLINE", "1")


@pytest.fixture(autouse=True)
def private_paper_pool(tmp_path, monkeypatch):
    """Tests never read or populate the user's shared paper pool."""
    monkeypatch.setenv("PATHFINDER_SOURCE_CACHE", str(tmp_path / "paper-pool"))


@pytest.fixture(autouse=True)
def quick_partner_poll(monkeypatch):
    """A ready peer looks at its partners every 15 s in a run; tests have no reason to wait that long."""
    monkeypatch.setattr(research, "PARTNER_POLL", 0.05)


@pytest.fixture(autouse=True)
def private_package_cache(tmp_path, monkeypatch):
    """Tests never write the user's shared uv cache."""
    monkeypatch.setenv("PATHFINDER_PACKAGE_CACHE", str(tmp_path / "package-cache"))


_real_run = None


def _latex_key(argv, cwd):
    import hashlib
    from pathlib import Path
    h = hashlib.sha256(repr(list(argv)).encode())
    root = Path(cwd)
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


@pytest.fixture(autouse=True)
def shared_latex_builds(tmp_path_factory, monkeypatch):
    """A LaTeX build of the same files gives the same result, so the suite's workers share one store of builds
    (a real build takes about 3 s, and most tests build the same stub notes). The first build of any input is
    real. PATHFINDER_TEST_LATEX_CACHE=0 turns the store off."""
    import os, pickle, subprocess
    from pathlib import Path
    if os.environ.get("PATHFINDER_TEST_LATEX_CACHE") == "0":
        return
    store = tmp_path_factory.getbasetemp().parent / "latex-builds"
    store.mkdir(exist_ok=True)
    real = subprocess.run

    def run(args, *a, **kw):
        cwd = kw.get("cwd")
        if (not isinstance(args, (list, tuple)) or not args or args[0] not in ("latexmk", "pdflatex")
                or cwd is None or "--version" in args or a or kw.get("input") is not None):
            return real(args, *a, **kw)
        root = Path(cwd)
        key = _latex_key(args, root)
        entry = store / f"{key}.pickle"
        if entry.is_file():
            rc, out, err, files = pickle.loads(entry.read_bytes())
            for rel, data in files.items():
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_bytes(data)
        else:
            before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
            r = real(args, *a, **kw)
            if kw.get("check") and r.returncode:
                return r
            files = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*")
                     if p.is_file() and before.get(p) != p.read_bytes()}
            rc, out, err = r.returncode, r.stdout, r.stderr
            tmp = entry.with_suffix(f".{os.getpid()}.tmp")
            tmp.write_bytes(pickle.dumps((rc, out, err, files))); tmp.replace(entry)
        return subprocess.CompletedProcess(args, rc, out, err)
    monkeypatch.setattr(subprocess, "run", run)


SLOW_FIRST = ("test_deployments.py", "test_presentation.py", "test_paper_amend.py", "test_coordinator.py")


def pytest_collection_modifyitems(items):
    """The deployment contracts and the paper-pass tests take longest: started first, they do not leave one
    worker running alone at the end of a parallel run."""
    items.sort(key=lambda item: next((i for i, name in enumerate(SLOW_FIRST) if item.path.name == name), len(SLOW_FIRST)))
