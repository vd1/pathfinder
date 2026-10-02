"""A deployment's consumer runs after a pair is edited and cannot overturn the verifier (H9)."""
import json
from pathfinder import consumer, edit, research
from stubcampaign import make


def _campaign(tmp_path, body):
    c = make(tmp_path, extensions={"path": "deploy", "consumer": "consume_mod:consume"})
    (tmp_path / "deploy").mkdir(exist_ok=True)
    (tmp_path / "deploy" / "consume_mod.py").write_text(body)
    import sys; sys.modules.pop("consume_mod", None)
    return c


def _record(c):
    return json.loads((c.thread_dir("Q1P1") / "consumer.json").read_text())


def test_no_consumer_is_skipped(tmp_path):
    c = make(tmp_path)
    research.run_thread(c, "Q1P1")
    assert consumer.run(c, "Q1P1") == "skipped"


def test_the_consumer_runs_after_the_edit_and_is_recorded(tmp_path):
    c = _campaign(tmp_path, "def consume(campaign, pair_id, edited):\n    return {'implemented': (edited / 'note.tex').exists()}\n")
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    assert edit.run(c, "Q1P1") == "done"
    r = _record(c)
    assert r["status"] == "done" and r["result"] == {"implemented": True}


def test_a_consumer_that_raises_leaves_the_pair_as_it_was(tmp_path):
    c = _campaign(tmp_path, "def consume(campaign, pair_id, edited):\n    raise RuntimeError('no feeds')\n")
    research.run_thread(c, "Q1P1")
    assert edit.run(c, "Q1P1") == "done"
    assert _record(c)["status"] == "failed" and "no feeds" in _record(c)["error"]
    assert research.status(c, "Q1P1")["status"] == "DRAFT"


def test_a_consumer_cannot_overturn_the_verifier(tmp_path):
    c = _campaign(tmp_path, "from pathfinder import research, edit\n"
                            "def consume(campaign, pair_id, edited):\n"
                            "    research._set(campaign, pair_id, status='PAUSE', reason='consumer disagrees')\n"
                            "    edit._set(campaign, pair_id, status='blocked')\n"
                            "    return {'verdict': 'reject'}\n")
    research.run_thread(c, "Q1P1")
    edit.run(c, "Q1P1")
    assert research.status(c, "Q1P1")["status"] == "DRAFT" and edit.status(c, "Q1P1")["status"] == "done"
    assert _record(c)["overturn_refused"] is True
