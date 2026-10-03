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
    research._set(c, "Q1P1", status="BLOCKED", reason="consolidate: input too large: 1200 characters exceed 10",
                  failure={"class": "input_too_large", "scope": "call", "retry": False, "reset_at": None})
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
    research._set(c, "Q1P1", status="BLOCKED", reason="consolidate: input too large: 12 characters exceed 10",
                  failure={"class": "input_too_large", "scope": "call", "retry": False, "reset_at": None})
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


def test_run_started_carries_the_run_id(tmp_path):
    from pathfinder import provenance
    c = make(tmp_path)
    provenance.start(c, "run-7")
    started = [r for r in events.read(c)[0] if r["kind"] == "run_started"]
    assert started[-1]["run_id"] == "run-7"


def test_a_corrupt_interior_line_is_counted_not_fatal(tmp_path):
    c = make(tmp_path)
    events.emit(c, "run_started")
    with c.path("events.jsonl").open("a") as f:
        f.write("garbage\n")
    events.emit(c, "run_finished")
    rows, truncated = events.read(c)
    assert not truncated and len(rows) == 2
    s = campaign_state.build(c)
    assert s["progress"]["status"] != "unknown" and s["progress"]["events_corrupt"] == 1
    assert "1 unreadable event line" in campaign_state.text(s)


def test_an_event_without_a_timestamp_does_not_break_the_state(tmp_path):
    c = make(tmp_path)
    c.path("events.jsonl").write_text('{"v": 1, "kind": "run_started"}\n')
    assert campaign_state.build(c)["progress"]["last_event_at"] is None


def _runner(c, alive, pairs):
    import os
    c.path("runner.json").write_text(json.dumps({"status": "running", "pid": os.getpid() if alive else 999999,
                                                 "heartbeat_at": time.time(), "active_pairs": pairs}))


def test_a_seated_unit_between_calls_is_running_and_without_a_runner_is_orphaned(tmp_path):
    c = make(tmp_path, pairs=("Q1P1", "Q1P2"))
    for unit in ("Q1P1", "Q1P2"):
        c.thread_dir(unit).mkdir(parents=True)
    research._set(c, "Q1P1", status="running")
    research._set(c, "Q1P2", status="PAUSE")
    _runner(c, True, ["Q1P1"])
    s = campaign_state.build(c)
    assert {u["unit"]: u["controller"] for u in s["units"]} == {"Q1P1": "running", "Q1P2": "queued"}
    assert s["runner"]["pid_alive"] is True and s["progress"]["status"] == "active"
    _runner(c, False, ["Q1P1"])
    s = campaign_state.build(c)
    assert s["units"][0]["controller"] == "orphaned" and s["progress"]["status"] != "active"


def test_recent_events_without_a_live_runner_are_not_active(tmp_path):
    c = make(tmp_path)
    events.emit(c, "run_finished")
    assert campaign_state.build(c)["progress"]["status"] == "recent"


def test_blocks_use_structured_failures_not_prose(tmp_path):
    c = make(tmp_path, pairs=("Q1P1", "Q1P2"))
    for unit in ("Q1P1", "Q1P2"):
        c.thread_dir(unit).mkdir(parents=True)
    research._set(c, "Q1P1", status="BLOCKED", reason="review: overloaded with citations")
    research._set(c, "Q1P2", status="BLOCKED", reason="consolidate: input too large",
                  failure={"class": "input_too_large", "scope": "call", "retry": False, "reset_at": None})
    blocks = {b["units"][0]: (b["class"], b["cause"]) for b in campaign_state.build(c)["blocks"]}
    assert blocks == {"Q1P1": ("undiagnosed", "review"), "Q1P2": ("input_too_large", "consolidate")}


def test_oversized_prompt_blocks_carry_a_structured_failure(tmp_path):
    c = make(tmp_path, max_prompt_chars=10)
    research.run_thread(c, "Q1P1")
    assert research.status(c, "Q1P1")["failure"]["class"] == "input_too_large"


def test_terminal_research_awaiting_edit_is_queued_in_the_edit_stage(tmp_path):
    c = make(tmp_path, pairs=("Q1P1", "Q1P2"))
    for unit in ("Q1P1", "Q1P2"):
        c.thread_dir(unit).mkdir(parents=True)
    research._set(c, "Q1P1", status="PAUSE")
    research._set(c, "Q1P2", status="DRAFT")
    edit._set(c, "Q1P2", status="done")
    s = campaign_state.build(c)
    assert s["stages"]["edit"] == {"queued": 1, "done": 1}
    assert s["stages"]["paper"] == {"queued": 1}


def _states(c, unit, research_status, edit_status=None, paper_status=None):
    c.thread_dir(unit).mkdir(parents=True, exist_ok=True)
    research._set(c, unit, status=research_status)
    if edit_status:
        edit._set(c, unit, status=edit_status)
    if paper_status:
        from pathfinder import paper
        paper._set(c, unit, status=paper_status)


def test_every_unit_has_exactly_one_pipeline_position(tmp_path):
    units = ("Q1P1", "Q1P2", "Q1P3", "Q1P4", "Q1P5")
    c = make(tmp_path, pairs=units)
    _states(c, "Q1P1", "DRAFT", "done", "ACCEPTED")
    _states(c, "Q1P2", "PAUSE", "done")
    _states(c, "Q1P3", "BLOCKED")
    _states(c, "Q1P4", "running")
    s = campaign_state.build(c)
    position = {u["unit"]: u["lifecycle"] for u in s["units"]}
    assert position == {"Q1P1": "accepted", "Q1P2": "noted", "Q1P3": "blocked", "Q1P4": "orphaned", "Q1P5": "waiting"}
    assert sum(stage["count"] for stage in s["pipeline"]) == len(units)
    assert [stage["title"] for stage in s["pipeline"]] == [t for t, _ in campaign_state.PIPELINE]


def test_units_carry_titles_scores_summary_and_usage(tmp_path):
    c = make(tmp_path)
    c.path("scan.jsonl").write_text(json.dumps({"pair_id": "Q1P1", "feasibility": 7, "gain": 6, "connexion": "a bridge"}) + "\n")
    c.path("receipts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in (
        {"thread": "Q1P1", "stage": "peer", "outcome": "completed", "input_tokens": 100, "output_tokens": 5, "seconds": 3.0},
        {"thread": "Q1P1", "stage": "verify", "outcome": "timeout", "input_tokens": None, "output_tokens": None, "seconds": 9.0})))
    d = c.thread_dir("Q1P1"); d.mkdir(parents=True)
    (d / "Q1P1.verdict.json").write_text(json.dumps([{"decision": "PAUSE", "reason": "missing proof"}]))
    u = campaign_state.build(c)["units"][0]
    assert u["q"]["title"] == "Q paper 1" and u["p"]["abstract"] == "Abstract of P1."
    assert (u["feasibility"], u["gain"], u["connexion"]) == (7, 6, "a bridge")
    assert u["summary"] == "missing proof"
    assert u["usage"] == {"calls": 2, "input_tokens": 100, "output_tokens": 5, "seconds": 12.0}
    usage = campaign_state.build(c)["usage"]
    assert (usage["calls"], usage["completed"], usage["calls_with_usage"]) == (2, 1, 1)


def test_handed_off_research_is_an_outcome_not_a_stop(tmp_path):
    assert campaign_state.lifecycle({"status": "HANDOFF"}, {}, {}, "waiting") == "handoff"
    assert "handoff" in [k for _, states in campaign_state.PIPELINE for k, _ in states]


def test_a_deployment_adds_its_own_panels(tmp_path):
    from pathfinder import campaign_state
    from stubcampaign import make
    c = make(tmp_path, extensions={"path": "deploy", "panels": "drip_panels:panels"})
    (tmp_path / "deploy").mkdir()
    (tmp_path / "deploy" / "drip_panels.py").write_text(
        "def panels(campaign):\n"
        "    return [{'title': 'Paper trading', 'columns': ['paper', 'events'], 'rows': [['2601.06499v3', 12]],"
        " 'note': 'live strategies'}]\n")
    panels = campaign_state.build(c)["panels"]
    assert panels == [{"title": "Paper trading", "columns": ["paper", "events"], "rows": [["2601.06499v3", 12]],
                       "note": "live strategies"}]


def test_a_failing_panel_extension_shows_its_error_not_a_broken_state(tmp_path):
    from pathfinder import campaign_state
    from stubcampaign import make
    c = make(tmp_path, extensions={"path": "deploy", "panels": "bad_panels:panels"})
    (tmp_path / "deploy").mkdir()
    (tmp_path / "deploy" / "bad_panels.py").write_text("def panels(campaign):\n    raise RuntimeError('queue locked')\n")
    [panel] = campaign_state.build(c)["panels"]
    assert panel["title"] == "Deployment panels" and "queue locked" in panel["note"]


def test_no_extension_no_panels(tmp_path):
    from pathfinder import campaign_state
    from stubcampaign import make
    assert campaign_state.build(make(tmp_path))["panels"] == []
