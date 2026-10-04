"""Garbage collection: each finished cycle removes what the record does not need (LaTeX by-products, prompt
copies inside retained responses), and receipts keep the commands an agent ran without their full output."""
import json
import pytest
from pathfinder import cli, config, edit, events, gc, research, runner, transport
from stubcampaign import make

LONG = "x" * 50_000


def _events(output=LONG):
    return [json.dumps({"type": "thread.started", "thread_id": "t"}),
            json.dumps({"type": "item.completed", "item": {"id": "i1", "type": "command_execution",
                                                           "command": "sed -n '1,9p' inputs/Q.tex",
                                                           "aggregated_output": output, "exit_code": 0}}),
            json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "content": output}]}}),
            json.dumps({"type": "item.completed", "item": {"id": "i2", "type": "agent_message", "text": "final answer"}}),
            json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 2}})]


def test_compacted_events_keep_commands_and_answers_without_full_outputs():
    lines = _events()
    compact = gc.compact_events(lines)
    command = json.loads(compact[1])["item"]
    assert command["command"] == "sed -n '1,9p' inputs/Q.tex" and command["output_chars"] == len(LONG)
    assert len(command["aggregated_output"]) < 1000
    assert json.loads(compact[2])["message"]["content"][0]["output_chars"] == len(LONG)
    assert sum(map(len, compact)) < 3000
    assert transport._parse(None, "m", compact)[0] == transport._parse(None, "m", lines)[0] == "final answer"


def test_short_outputs_and_unreadable_lines_are_kept_as_they_are():
    lines = _events("ok") + ["not json"]
    assert gc.compact_events(lines) == lines


def test_a_receipt_records_compacted_events(tmp_path):
    c = make(tmp_path)
    transport._receipt(c, "Q1P1", "peer", "ada", "m", {"outcome": "completed", "raw_events": _events()})
    row = json.loads(c.path("receipts.jsonl").read_text().splitlines()[-1])
    assert len(json.dumps(row)) < 5000 and json.loads(row["raw_events"][1])["item"]["output_chars"] == len(LONG)


def _finished(tmp_path):
    c = make(tmp_path)
    research.run_thread(c, "Q1P1")
    assert edit.run(c, "Q1P1") == "done"
    d = c.thread_dir("Q1P1")
    for name in ("Q1P1.aux", "edited/note.fls", "edited/note.fdb_latexmk", "ada/derivation.synctex.gz",
                 "ada/build.log", ".transport-input/x/prompt.txt"):
        (d / name).parent.mkdir(parents=True, exist_ok=True)
        (d / name).write_text("by-product")
    (d / "research-requests").mkdir(exist_ok=True)
    (d / "research-requests/a.json").write_text(json.dumps({"request": {"prompt": LONG}, "result": {"ok": 1}}))
    (d / "research-requests/open.json").write_text(json.dumps({"request": {"prompt": LONG}}))
    return c, d


def test_a_finished_thread_is_collected(tmp_path):
    c, d = _finished(tmp_path)
    report = gc.collect_thread(c, "Q1P1")
    for name in ("Q1P1.aux", "edited/note.fls", "edited/note.fdb_latexmk", "ada/derivation.synctex.gz",
                 "ada/build.log", ".transport-input"):
        assert not (d / name).exists(), name
    assert (d / "Q1P1.tex").exists() and (d / "ledger.jsonl").exists() and (d / "edited/note.tex").exists()
    kept = json.loads((d / "research-requests/a.json").read_text())
    assert kept["result"] == {"ok": 1} and kept["request"]["chars"] > len(LONG)
    assert "prompt" in json.loads((d / "research-requests/open.json").read_text())["request"]   # no result yet
    assert report["files"] >= 6 and report["bytes"] > 40_000 and report["stripped"] == 1
    assert any(e.get("kind") == "garbage_collected" and e.get("unit") == "Q1P1" for e in events.read(c)[0])


def test_an_unfinished_thread_is_left_alone(tmp_path):
    c = make(tmp_path)
    research.prepare(c, "Q1P1")
    d = c.thread_dir("Q1P1")
    (d / "note.aux").write_text("by-product")
    assert gc.collect_thread(c, "Q1P1") is None and (d / "note.aux").exists()


def test_the_runner_collects_each_finished_thread(tmp_path):
    c = make(tmp_path)
    (tmp_path / "threads/Q1P1").mkdir(parents=True)
    runner.run(c, interval=0)
    assert any(e.get("kind") == "garbage_collected" for e in events.read(c)[0])


def test_collection_can_be_turned_off(tmp_path):
    c = make(tmp_path, gc=False)
    runner.run(c, interval=0)
    assert not any(e.get("kind") == "garbage_collected" for e in events.read(c)[0])


def test_a_bad_gc_setting_is_refused(tmp_path):
    with pytest.raises(ValueError, match="gc"):
        make(tmp_path, gc="yes")


def test_the_gc_command_collects_finished_threads_and_compacts_old_receipts(tmp_path, capsys):
    c, d = _finished(tmp_path)
    with c.path("receipts.jsonl").open("a") as f:
        f.write(json.dumps({"call_id": "old", "stage": "peer", "raw_events": _events()}) + "\n")
    assert cli.main(["--root", str(tmp_path), "gc", "--dry-run"]) in (0, None)
    assert (d / "Q1P1.aux").exists() and "old" in c.path("receipts.jsonl").read_text()
    before = len(c.path("receipts.jsonl").read_text())
    assert cli.main(["--root", str(tmp_path), "gc"]) in (0, None)
    assert not (d / "Q1P1.aux").exists()
    after = c.path("receipts.jsonl").read_text()
    assert len(after) < before - 90_000 and len(transport.receipts(c)) == len(after.splitlines())
    assert "collected" in capsys.readouterr().out
