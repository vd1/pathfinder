"""A deployment whose contract reads its recorded commit (reads = "recorded") is tested at that commit: the
release check no longer needs its live checkout to stand still. proofTree committed during two release checks
on 8 October 2026, each time failing them with "checkout is at X, deployments.toml pins Y"."""
import subprocess
import pytest
import deployment_matrix


def _repo(tmp_path):
    repo = tmp_path / "deployment"
    repo.mkdir()
    git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True).stdout.strip()
    git("init", "-q"); git("config", "user.email", "t@t"); git("config", "user.name", "t")
    (repo / "code.py").write_text("RECORDED = True\n"); git("add", "."); git("commit", "-qm", "recorded")
    pinned = git("rev-parse", "HEAD")
    (repo / "code.py").write_text("RECORDED = False\n"); git("commit", "-qam", "later")
    return repo, pinned


def test_a_recorded_deployment_is_read_at_its_commit_while_its_checkout_moves_on(tmp_path, monkeypatch):
    repo, pinned = _repo(tmp_path)
    monkeypatch.setattr(deployment_matrix, "RELEASE", True)
    monkeypatch.setattr(deployment_matrix, "load", lambda: {"d": {"checkout": str(repo), "revision": pinned, "reads": "recorded"}})
    assert deployment_matrix.checkout("d") == repo.resolve()                 # no refusal: HEAD has moved on
    code = deployment_matrix.recorded("d", tmp_path / "out")
    assert (code / "code.py").read_text() == "RECORDED = True\n"


def test_a_live_deployment_still_refuses_a_moved_checkout(tmp_path, monkeypatch):
    repo, pinned = _repo(tmp_path)
    monkeypatch.setattr(deployment_matrix, "RELEASE", True)
    monkeypatch.setattr(deployment_matrix, "load", lambda: {"d": {"checkout": str(repo), "revision": pinned}})
    with pytest.raises(pytest.fail.Exception, match="checkout is at"):
        deployment_matrix.checkout("d")


def test_a_recorded_commit_that_does_not_exist_is_refused(tmp_path, monkeypatch):
    repo, _ = _repo(tmp_path)
    monkeypatch.setattr(deployment_matrix, "RELEASE", True)
    monkeypatch.setattr(deployment_matrix, "load", lambda: {"d": {"checkout": str(repo), "revision": "0" * 40, "reads": "recorded"}})
    with pytest.raises(pytest.fail.Exception, match="not in the checkout"):
        deployment_matrix.checkout("d")
