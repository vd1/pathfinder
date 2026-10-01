import json, os, py_compile, shutil, subprocess, sys
from pathlib import Path
import pytest
from pathfinder import freeze, provenance, runner, transport
from stubcampaign import make

needs_git = pytest.mark.skipif(not shutil.which("git"), reason="git not installed")


def _repo(tmp_path) -> Path:
    repo = tmp_path / "engine"
    (repo / "pathfinder").mkdir(parents=True); (repo / "prompts").mkdir()
    (repo / "pathfinder" / "__init__.py").write_text("")
    (repo / "pathfinder" / "core.py").write_text("VALUE = 'released'\n")
    (repo / "pathfinder" / "run.sh").write_text("#!/bin/sh\n"); (repo / "pathfinder" / "run.sh").chmod(0o755)
    (repo / "prompts" / "peer.md").write_text("peer prompt\n")
    (repo / "notes.md").write_text("not runtime\n")
    for cmd in (["init", "-q"], ["add", "."], ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "v1"],
                ["tag", "engine-v1.0"]):
        subprocess.run(["git", "-C", str(repo), *cmd], check=True)
    return repo


@needs_git
def test_freeze_writes_exactly_the_runtime_files_and_verifies(tmp_path):
    repo = _repo(tmp_path)
    manifest = freeze.freeze(repo, "engine-v1.0", tmp_path / "copy")
    assert set(manifest["files"]) == {"pathfinder/__init__.py", "pathfinder/core.py", "pathfinder/run.sh", "prompts/peer.md"}
    assert os.access(tmp_path / "copy/pathfinder/run.sh", os.X_OK) and not (tmp_path / "copy/notes.md").exists()
    result = freeze.verify(tmp_path / "copy", repo)
    assert result["status"] == "verified" and result["manifest_matches_commit"]


@needs_git
def test_changed_missing_added_and_sourceless_files_are_modifications(tmp_path):
    repo = _repo(tmp_path)
    copy = tmp_path / "copy"; freeze.freeze(repo, "engine-v1.0", copy)
    (copy / "pathfinder/core.py").write_text("VALUE = 'edited'\n")
    (copy / "prompts/peer.md").unlink()
    (copy / "pathfinder/new.py").write_text("")
    extra = copy / "pathfinder/extra.py"; extra.write_text("VALUE = 'runtime change'\n")
    py_compile.compile(str(extra), cfile=str(copy / "pathfinder/extra.pyc")); extra.unlink()
    (copy / "pathfinder/__pycache__").mkdir(); (copy / "pathfinder/__pycache__/core.cpython-312.pyc").write_bytes(b"x")
    result = freeze.verify(copy, repo)
    assert result["status"] == "modified"
    assert result["changed"] == ["pathfinder/core.py"] and result["missing"] == ["prompts/peer.md"]
    assert result["added"] == ["pathfinder/extra.pyc", "pathfinder/new.py"]          # __pycache__ ignored, .pyc not


@needs_git
def test_a_lost_executable_bit_and_a_symlink_are_modifications(tmp_path):
    repo = _repo(tmp_path)
    copy = tmp_path / "copy"; freeze.freeze(repo, "engine-v1.0", copy)
    (copy / "pathfinder/run.sh").chmod(0o644)
    (copy / "prompts/peer.md").unlink(); (copy / "prompts/peer.md").symlink_to(repo / "prompts/peer.md")
    result = freeze.verify(copy, repo)
    assert result["status"] == "modified" and result["changed"] == ["pathfinder/run.sh", "prompts/peer.md"]


@needs_git
def test_a_commit_holding_a_symlink_cannot_be_frozen(tmp_path):
    repo = _repo(tmp_path)
    (repo / "prompts/alias.md").symlink_to("peer.md")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "link"], check=True)
    with pytest.raises(ValueError, match="unsupported runtime entry"):
        freeze.freeze(repo, "HEAD", tmp_path / "copy")


@needs_git
def test_verification_never_trusts_the_manifest_and_reports_unverifiable(tmp_path):
    repo = _repo(tmp_path)
    copy = tmp_path / "copy"; freeze.freeze(repo, "engine-v1.0", copy)
    (copy / "pathfinder/core.py").write_text("VALUE = 'edited'\n")
    m = json.loads((copy / freeze.MANIFEST).read_text())
    m["files"]["pathfinder/core.py"] = "100644 " + freeze.blob_id(b"VALUE = 'edited'\n")     # a forged manifest
    (copy / freeze.MANIFEST).write_text(json.dumps(m))
    assert freeze.verify(copy, repo)["status"] == "modified"
    other = tmp_path / "other"; other.mkdir(); subprocess.run(["git", "-C", str(other), "init", "-q"], check=True)
    assert freeze.verify(copy, other)["status"] == "unverifiable"


def test_every_receipt_names_its_run_and_the_record_is_written(tmp_path):
    c = make(tmp_path, stub={"verify": "PAUSE"})
    runner.request_stop(c, "operator"); (tmp_path / "stop.json").unlink()
    assert runner.run(c, interval=0.05, pairs=["Q1P1"]) in (0, 1)
    rec = json.loads((tmp_path / "run.json").read_text())
    assert rec["engine"]["runtime_sha256"] and rec["prompts"]["peer"] and rec["config"]["sha256"]
    rows = transport.receipts(c)
    assert rows and {r["run_id"] for r in rows} == {rec["run_id"]}


def test_resume_refuses_a_changed_component_until_accepted(tmp_path, capsys):
    c = make(tmp_path, stub={"verify": "PAUSE"})
    provenance.start(c, "first")
    (tmp_path / "prompts").mkdir(); (tmp_path / "prompts/peer.append.md").write_text("changed brief")
    assert runner.run(c, interval=0.05) == 1
    assert "prompts changed" in capsys.readouterr().out and not transport.receipts(c)
    rec, changed = provenance.start(c, "second", accept_change="new brief agreed")
    assert changed == ["prompts"] and rec["previous_run_id"] == "first"
    assert rec["accepted_change"] == {"components": ["prompts"], "reason": "new brief agreed"}
    assert [json.loads(l)["run_id"] for l in (tmp_path / "runs.jsonl").read_text().splitlines()] == ["first", "second"]


def test_an_unchanged_resume_links_to_the_previous_run(tmp_path):
    c = make(tmp_path)
    provenance.start(c, "first")
    rec, changed = provenance.start(c, "second")
    assert changed == [] and rec["previous_run_id"] == "first" and "accepted_change" not in rec


def test_the_engine_record_of_a_checkout(tmp_path):
    e = provenance.engine()
    assert e["kind"] in ("checkout", "installed", "copy", "frozen") and len(e["runtime_sha256"]) == 64


needs_tex = pytest.mark.skipif(not shutil.which("latexmk"), reason="latexmk not installed")


@needs_tex
def test_a_paper_only_resume_is_recorded_and_gated(tmp_path):
    from pathfinder import paper
    c = make(tmp_path)
    assert runner.run(c, interval=0.05, pairs=["Q1P1"]) == 0          # DRAFT, edit done; paper still due
    (tmp_path / "prompts").mkdir(); (tmp_path / "prompts/author.append.md").write_text("new author brief")
    before = len(transport.receipts(c))
    with pytest.raises(provenance.ChangeRefused, match="prompts"):
        runner.run_pair(c, "Q1P1", interval=0.05)
    assert len(transport.receipts(c)) == before and paper.status(c, "Q1P1")["status"] == "none"
    out = runner.run_pair(c, "Q1P1", interval=0.05, accept_change="author brief agreed")
    rows = transport.receipts(c)[before:]
    rec = json.loads((tmp_path / "run.json").read_text())
    assert out["paper"] == "ACCEPTED" and rows and {r["run_id"] for r in rows} == {rec["run_id"]}


def test_cli_dispatch_refuses_a_changed_record(tmp_path, capsys):
    from pathfinder import cli
    c = make(tmp_path)
    provenance.start(c, "first")
    (tmp_path / "campaign.json").write_text(json.dumps({**json.loads((tmp_path / "campaign.json").read_text()), "rounds": 2}))
    assert cli.main(["--root", str(tmp_path), "edit"]) == 1
    assert "config" in capsys.readouterr().out


def test_declared_deployment_files_and_extension_helpers_are_compared(tmp_path):
    from pathfinder import extensions
    c = make(tmp_path, deployment={"name": "demo", "files": ["controller/*.py"]},
             extensions={"path": "deploy", "admission": "demo_policy:policy"})
    (tmp_path / "controller").mkdir(); (tmp_path / "controller/loop.py").write_text("STEP = 1\n")
    pkg = tmp_path / "deploy/demo_policy"; pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("from pathfinder.admission import ADMIT\nfrom .helper import X\n"
                                     "def policy(*a):\n    return ADMIT\n")
    (pkg / "helper.py").write_text("X = 1\n")
    provenance.start(c, "first")
    (tmp_path / "controller/loop.py").write_text("STEP = 2\n")
    assert provenance.changes(json.loads((tmp_path / "run.json").read_text()), provenance.record(c, "x")) == ["deployment"]
    (tmp_path / "controller/loop.py").write_text("STEP = 1\n")
    (pkg / "helper.py").write_text("X = 2\n")
    extensions._first_seen.clear()                                   # as a new process would see it
    assert provenance.changes(json.loads((tmp_path / "run.json").read_text()), provenance.record(c, "x")) == ["extensions"]


def test_the_record_holds_resolved_settings(tmp_path):
    c = make(tmp_path)
    rec = provenance.record(c, "r")
    assert rec["config"]["resolved"]["peers"] == ["ada"] and rec["config"]["resolved"]["scan_model"] == "stub"
    assert "raw" in rec["config"]


def test_an_extension_helper_edited_within_one_process_requires_a_restart(tmp_path):
    from pathfinder import extensions
    c = make(tmp_path, extensions={"path": "deploy", "admission": "sameproc_policy:policy"})
    pkg = tmp_path / "deploy/sameproc_policy"; pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("from pathfinder.admission import ADMIT\ndef policy(*a):\n    return ADMIT\n")
    (pkg / "helper.py").write_text("X = 1\n")
    provenance.start(c, "first")
    (pkg / "helper.py").write_text("X = 2\n")                       # edited while this process keeps running
    with pytest.raises(provenance.RestartRequired, match="extensions"):
        provenance.start(c, "second", accept_change="cannot cover cached code")
    with pytest.raises(provenance.RestartRequired):
        runner.run(c, interval=0.05)


HOLD = r"""
import fcntl, sys, time
handle = open(sys.argv[1], "a+"); fcntl.flock(handle, fcntl.LOCK_EX); print("held", flush=True); time.sleep(30)
"""


def test_another_owner_rejects_dispatch_before_the_record_is_touched(tmp_path):
    from pathfinder import cli
    c = make(tmp_path)
    provenance.start(c, "first")
    before = ((tmp_path / "run.json").read_bytes(), (tmp_path / "runs.jsonl").read_bytes())
    holder = subprocess.Popen([sys.executable, "-c", HOLD, str(tmp_path / "runner.lock")], stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "held"
        with pytest.raises(RuntimeError, match="already owns"):
            runner.run_pair(c, "Q1P1", interval=0.05)
        with pytest.raises(RuntimeError, match="already owns"):
            cli.main(["--root", str(tmp_path), "edit"])
        assert ((tmp_path / "run.json").read_bytes(), (tmp_path / "runs.jsonl").read_bytes()) == before
    finally:
        holder.kill(); holder.wait()


def test_ownership_is_per_thread_and_nesting_is_explicit(tmp_path):
    import threading
    from pathfinder import health
    c = make(tmp_path)
    entered, release, errors = threading.Event(), threading.Event(), []

    def a():
        with health.owner(c):
            entered.set(); release.wait(5)

    t = threading.Thread(target=a); t.start(); entered.wait(5)
    try:
        with pytest.raises(RuntimeError, match="already owns"):
            with health.owner(c, nested=True):          # another thread is never a nested owner
                pass
    finally:
        release.set(); t.join(5)
    with health.owner(c):
        with health.owner(c, nested=True):              # the same thread may nest when it asks to
            pass
        with pytest.raises(RuntimeError, match="already owns"):
            with health.owner(c):                       # and is refused when it does not
                pass


def test_a_foreign_run_id_on_a_shared_campaign_object_is_not_a_nested_run(tmp_path):
    c = make(tmp_path)
    c.run_id = "someone-else"
    with provenance.run_context(c) as run_id:
        assert run_id != "someone-else" and json.loads((tmp_path / "run.json").read_text())["run_id"] == run_id


def test_execution_id_follows_the_running_bytes_not_the_commit():
    from pathfinder import provenance
    rec = {"engine": {"kind": "checkout", "runtime_sha256": "a" * 64}, "config": {"sha256": "c"}}
    same = {"engine": {"kind": "checkout", "runtime_sha256": "a" * 64, "commit": "different"}, "config": {"sha256": "c"}}
    dirty = {"engine": {"kind": "checkout", "runtime_sha256": "b" * 64}, "config": {"sha256": "c"}}
    assert provenance.execution_id(rec) == provenance.execution_id(same)
    assert provenance.execution_id(rec) != provenance.execution_id(dirty)


def test_a_run_record_carries_its_execution_id_and_emits_run_started(tmp_path):
    from pathfinder import events, provenance
    from stubcampaign import make
    c = make(tmp_path)
    rec, _ = provenance.start(c, "run-1")
    assert rec["execution_id"] == provenance.execution_id(rec)
    started = [r for r in events.read(c)[0] if r["kind"] == "run_started"]
    assert started[-1]["execution_id"] == rec["execution_id"]
