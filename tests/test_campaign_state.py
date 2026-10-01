import json, os, time
from pathfinder import campaign_state, edit, events, research
from stubcampaign import make


def test_states_are_separated_per_axis(tmp_path):
    c = make(tmp_path)
    research.run_thread(c, "Q1P1")
    edit._set(c, "Q1P1", status="blocked", reason="editor wrote no note.tex")
    unit = campaign_state.build(c)["units"][0]
    assert unit["research"]["status"] == research.status(c, "Q1P1")["status"]
    assert unit["editorial"] == {"status": "blocked", "reason": "editor wrote no note.tex"}
    assert unit["assessment"]["status"] is None
    assert unit["controller"] == "blocked"


def test_stage_counts_and_blocks(tmp_path):
    c = make(tmp_path, pairs=("Q1P1", "Q1P2"))
    for unit in ("Q1P1", "Q1P2"):
        c.thread_dir(unit).mkdir(parents=True)
    research._set(c, "Q1P1", status="BLOCKED", reason="consolidate: input too large: 1200 characters exceed 10")
    research._set(c, "Q1P2", status="DRAFT")
    s = campaign_state.build(c)
    assert s["stages"]["research"] == {"BLOCKED": 1, "DRAFT": 1}
    assert s["blocks"][0]["units"] == ["Q1P1"] and s["blocks"][0]["class"] == "input_too_large"


def test_budget_is_in_tokens_and_calls(tmp_path):
    c = make(tmp_path)
    research.run_thread(c, "Q1P1")
    budget = campaign_state.build(c)["campaign"]["budget"]
    assert budget["calls"] > 0 and budget["input_tokens"] == 0     # the stub reports zero tokens


def test_truncated_events_mean_unknown_progress(tmp_path):
    c = make(tmp_path)
    events.emit(c, "run_started", execution_id="e")
    with c.path("events.jsonl").open("a") as f:
        f.write('{"v": 1, "kind": "call_')
    assert campaign_state.build(c)["progress"]["status"] == "unknown"


def test_a_pdf_older_than_its_source_is_stale(tmp_path):
    c = make(tmp_path)
    ed = c.thread_dir("Q1P1") / "edited"; ed.mkdir(parents=True)
    (ed / "note.pdf").write_bytes(b"%PDF"); (ed / "note.tex").write_text("x")
    old = time.time() - 100
    os.utime(ed / "note.pdf", (old, old))
    docs = {d["kind"]: d for d in campaign_state.build(c)["units"][0]["documents"]}
    assert docs["readable note"]["pdf"] == "threads/Q1P1/edited/note.pdf"
    assert docs["readable note"]["source"] == "threads/Q1P1/edited/note.tex"
    assert docs["readable note"]["stale"] is True


def test_scores_come_from_the_scan(tmp_path):
    c = make(tmp_path)
    c.path("scan.jsonl").write_text(json.dumps({"pair_id": "Q1P1", "feasibility": 7, "gain": 6}) + "\n")
    assert campaign_state.build(c)["units"][0]["score"] == 42


def test_write_is_atomic_json(tmp_path):
    c = make(tmp_path)
    path = campaign_state.write(c)
    assert json.loads(path.read_text())["campaign"]["name"] == tmp_path.name


def test_text_view_names_unknown_progress_and_blocks(tmp_path):
    c = make(tmp_path)
    c.thread_dir("Q1P1").mkdir(parents=True)
    research._set(c, "Q1P1", status="BLOCKED", reason="consolidate: input too large: 12 characters exceed 10")
    events.emit(c, "run_started")
    with c.path("events.jsonl").open("a") as f:
        f.write("{")
    out = campaign_state.text(campaign_state.build(c))
    assert "progress unknown" in out and "input_too_large" in out and "Q1P1" in out


def test_cli_state_json(tmp_path, capsys):
    from pathfinder import cli
    make(tmp_path)
    assert cli.main(["--root", str(tmp_path), "state", "--json"]) in (0, None)
    assert json.loads(capsys.readouterr().out)["campaign"]["name"] == tmp_path.name
