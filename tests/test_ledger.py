import subprocess, sys
from pathfinder.ledger import Ledger


def test_add_read_and_readiness(tmp_path):
    l = Ledger(tmp_path / "ledger.jsonl")
    assert l.add("ada", "idea", "first") == 1
    assert l.add("emmy", "finding", "second") == 2
    assert [e["seq"] for e in l.read(since=1)] == [2]
    assert l.latest_substantive() == 2
    l.add("ada", "ready", "done", seen=2)
    assert not l.ready(["ada", "emmy"])
    l.add("emmy", "ready", "done", seen=2)
    assert l.ready(["ada", "emmy"])
    l.add("emmy", "objection", "wait")          # reopens
    assert not l.ready(["ada", "emmy"])


def test_stale_ready_does_not_count(tmp_path):
    l = Ledger(tmp_path / "ledger.jsonl")
    l.add("ada", "idea", "x")
    l.add("ada", "ready", "ok", seen=0)         # saw nothing
    l.add("emmy", "ready", "ok", seen=1)
    assert not l.ready(["ada", "emmy"])


def test_cli_roundtrip(tmp_path):
    cmd = [sys.executable, "-m", "pathfinder.ledger", "--root", str(tmp_path), "--actor", "ada"]
    subprocess.run(cmd + ["add", "--kind", "idea", "--text", "hello"], check=True)
    out = subprocess.run(cmd + ["read"], check=True, capture_output=True, text=True).stdout
    assert "hello" in out and "#1" in out


def test_readiness_can_require_acknowledging_a_review(tmp_path):
    l = Ledger(tmp_path / "ledger.jsonl")
    l.add("ada", "finding", "result")
    l.add("ada", "ready", "done", seen=1)
    review = l.add("verifier", "review", "ITERATE: check boundary")
    assert l.latest_substantive() == 1
    assert l.ready(["ada"])  # Callers opt into a review barrier.
    assert not l.ready(["ada"], after=review)
    l.add("ada", "ready", "stale acknowledgment", seen=1)
    assert not l.ready(["ada"], after=review)
    l.add("ada", "ready", "read review, gap still open", seen=review)
    assert l.ready(["ada"], after=review)
    l.add("emmy", "objection", "new issue")
    assert not l.ready(["ada"], after=review)
