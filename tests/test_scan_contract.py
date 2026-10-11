"""Conditional scans (repl, 11 October 2026). proofTree's planar campaign saturated because every link was scored
once, against nothing the campaign had learned: S54 repeated S55's route on B2 at a frozen gain. A deployment can
now declare typed fields of its own in the scan reply (the scan contract), give the judge its state of play (the
scan context, stamped on every row by revision and digest), and score a pair again when that state moves (a
rescan, appended, never rewriting the earlier score). With none of these set the scan is unchanged."""
import json, threading, urllib.request
from pathlib import Path
from pathfinder import campaign_state, config, monitor, scan, select, stub, thread, view
from stubcampaign import make

ROUTE = {"type": "object", "required": ["principle", "relation"], "properties": {
    "principle": {"type": "string"}, "relation": {"enum": ["new", "confirmation", "variant"]},
    "relative_to": {"type": ["string", "null"]}}}
CONTRACT = {"name": "repl/1", "fields": {"targets": {"type": "array", "items": {"type": "string"}},
                                         "needs": {"type": "array", "items": {"type": "string"}}, "route": ROUTE}}
EXTRA = {"targets": ["B2.f1"], "needs": [], "route": {"principle": "Perov", "relation": "variant", "relative_to": "R7"}}


def _replies(monkeypatch, extra=None, seen=None, scores=(50, 50)):
    def reply(campaign, request):
        if seen is not None:
            seen.append(request)
        out = {"feasibility": scores[0], "gain": scores[1], "connexion": "c", "rationale": "r"}
        if extra is not None and ":contract-repair" not in request.identity:
            out["extra"] = extra
        elif extra is not None:
            out["extra"] = EXTRA
        return json.dumps(out)
    monkeypatch.setattr(stub, "reply", reply)


def _rows(c):
    return [json.loads(l) for l in c.path("scan.jsonl").read_text().splitlines() if l.strip()]


def _context(c, revision, text):
    c.path("scan-context.json").write_text(json.dumps({"revision": revision, "text": text}))


def test_without_the_new_keys_a_scan_row_is_unchanged(tmp_path, monkeypatch):
    c = make(tmp_path, pairs=("Q1P1",))
    seen = []
    _replies(monkeypatch, seen=seen)
    scan.run(c)
    row = _rows(c)[0]
    assert set(row) == {"pair_id", "q", "p", "feasibility", "gain", "connexion", "rationale", "model", "seconds",
                        "cost", "error"}
    assert "SCAN_CONTEXT" not in seen[0].prompt and "extra" not in json.dumps(seen[0].schema)


def test_a_scan_contract_keeps_the_deployment_fields_and_names_the_contract(tmp_path, monkeypatch):
    c = make(tmp_path, pairs=("Q1P1",), scan_contract=CONTRACT)
    seen = []
    _replies(monkeypatch, extra=EXTRA, seen=seen)
    scan.run(c)
    row = _rows(c)[0]
    assert row["extra"] == EXTRA and row["contract"]["name"] == "repl/1" and len(row["contract"]["schema_sha256"]) == 64
    schema = seen[0].schema
    assert schema["properties"]["extra"]["properties"]["route"] == ROUTE and "extra" in schema["required"]


def test_a_reply_without_its_extra_fields_is_repaired_once(tmp_path, monkeypatch):
    c = make(tmp_path, pairs=("Q1P1",), scan_contract=CONTRACT)
    seen = []
    _replies(monkeypatch, extra={"targets": ["x"]}, seen=seen)          # needs and route missing; the repair supplies them
    scan.run(c)
    assert _rows(c)[0]["extra"] == EXTRA and any(":contract-repair" in r.identity for r in seen)


def test_the_check_hook_validates_against_the_context_and_its_rejection_is_recorded(tmp_path, monkeypatch):
    deploy = tmp_path / "deploy"; deploy.mkdir()
    (deploy / "replcheck.py").write_text(
        "def check(campaign, value, context):\n"
        "    known = set(context['text'].split()) if context else set()\n"
        "    missing = [t for t in value['extra']['targets'] if t not in known]\n"
        "    if missing:\n"
        "        raise ValueError('unknown facets: ' + ', '.join(missing))\n")
    c = make(tmp_path, pairs=("Q1P1", "Q1P2"), scan_contract={**CONTRACT, "check": "replcheck:check"},
             extensions={"path": "deploy"})
    _context(c, "r1", "B1.f1 B3.f2")
    _replies(monkeypatch, extra=EXTRA)                                  # targets B2.f1, unknown at r1, also after repair
    scan.run(c)
    rows = _rows(c)
    assert all(r["feasibility"] is None and "unknown facets: B2.f1" in r["error"] for r in rows)
    _context(c, "r2", "B2.f1")
    scan.rescan(c, ["Q1P1"])
    assert _rows(c)[-1]["extra"] == EXTRA and _rows(c)[-1]["revision"] == "r2"


def test_the_context_reaches_the_judge_and_stamps_each_row(tmp_path, monkeypatch):
    c = make(tmp_path, pairs=("Q1P1",))
    _context(c, "r3", "B2 has routes R1 (interval) and R7 (Perov).")
    seen = []
    _replies(monkeypatch, seen=seen)
    scan.run(c)
    row = _rows(c)[0]
    assert "R7 (Perov)" in seen[0].prompt and "r3" in seen[0].prompt
    assert row["revision"] == "r3" and len(row["context_sha256"]) == 64
    archived = json.loads(c.path(f"scan-contexts/{row['context_sha256']}.json").read_text())
    assert archived == {"revision": "r3", "text": "B2 has routes R1 (interval) and R7 (Perov)."}


def test_a_replacement_prompt_places_the_context_where_it_names_it(tmp_path, monkeypatch):
    c = make(tmp_path, pairs=("Q1P1",))
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "scan.md").write_text("STATE\n{{SCAN_CONTEXT}}\nPAIR {{Q_TITLE}} / {{P_TITLE}}\n")
    _context(c, "r1", "the ledger")
    seen = []
    _replies(monkeypatch, seen=seen)
    scan.run(c)
    assert seen[0].prompt.startswith("STATE\n") and "the ledger" in seen[0].prompt.split("PAIR")[0]


def test_a_rescan_appends_resumes_and_keeps_the_earlier_score(tmp_path, monkeypatch):
    c = make(tmp_path, pairs=("Q1P1", "Q1P2"))
    _replies(monkeypatch, scores=(80, 90))
    scan.run(c)                                                          # no context: unconditioned priors
    _context(c, "r1", "S55 recorded the Perov route on B2.")
    cur = {r["pair_id"]: r for r in scan.current(c)}
    assert cur["Q1P1"]["unconditioned"] and not cur["Q1P1"]["stale"]
    seen = []
    _replies(monkeypatch, seen=seen, scores=(80, 20))
    scan.rescan(c, ["Q1P1"])
    scan.rescan(c, ["Q1P1"])                                             # resumed: nothing to do at this context
    assert len(seen) == 1
    hist = scan.history(c, "Q1P1")
    assert [(r.get("revision"), r["gain"]) for r in hist] == [(None, 90), ("r1", 20)]
    cur = {r["pair_id"]: r for r in scan.current(c)}
    assert cur["Q1P1"]["gain"] == 20 and not cur["Q1P1"]["stale"] and not cur["Q1P1"]["unconditioned"]
    _context(c, "r2", "S54 repeated it.")
    cur = {r["pair_id"]: r for r in scan.current(c)}
    assert cur["Q1P1"]["stale"] and cur["Q1P2"]["unconditioned"]


def test_a_failed_rescan_keeps_the_earlier_score_current_and_can_be_retried(tmp_path, monkeypatch):
    c = make(tmp_path, pairs=("Q1P1",))
    _replies(monkeypatch, scores=(70, 70))
    scan.run(c)
    _context(c, "r1", "state")
    monkeypatch.setattr(stub, "reply", lambda campaign, request: "no JSON here")
    scan.rescan(c, ["Q1P1"])
    assert _rows(c)[-1]["error"] and scan.current(c)[0]["gain"] == 70
    _replies(monkeypatch, scores=(70, 10))
    scan.rescan(c, ["Q1P1"])
    assert scan.current(c)[0]["gain"] == 10


def test_a_rescan_needs_a_context_and_a_known_pair(tmp_path, monkeypatch):
    c = make(tmp_path, pairs=("Q1P1",))
    _replies(monkeypatch)
    try:
        scan.rescan(c, ["Q1P1"]); raise AssertionError("rescan without a context")
    except ValueError as e:
        assert "scan-context.json" in str(e)
    _context(c, "r1", "state")
    try:
        scan.rescan(c, ["Q9P9"]); raise AssertionError("rescan of an unknown pair")
    except ValueError as e:
        assert "Q9P9" in str(e)


def test_readers_take_the_current_score_of_a_rescanned_pair(tmp_path, monkeypatch):
    c = make(tmp_path, pairs=("Q1P1", "Q1P2"))
    _replies(monkeypatch, scores=(90, 90))
    scan.run(c)
    _context(c, "r1", "state")
    _replies(monkeypatch, scores=(10, 10))
    scan.rescan(c, ["Q1P1"])
    out = select.run(c, cut=50)
    assert out["n_scored"] == 2 and [p["pair_id"] for p in out["pairs"]] == ["Q1P2"]
    assert monitor.state(c)["scan"]["done"] == 2
    assert campaign_state.build(c)["scan"]["done"] == 2
    assert thread._scan_row(c, "Q1P1")["gain"] == 10
    doc = campaign_state.scan_document(c)
    rows = {r[0]: dict(zip(doc["columns"], r)) for r in doc["rows"]}
    assert rows["Q1P1"]["score"] == 100 and rows["Q1P1"]["revision"] == "r1" and rows["Q1P2"]["unconditioned"]
    assert [h["gain"] for h in doc["history"]["Q1P1"]] == [90, 10] and "Q1P2" not in doc["history"]
    assert doc["context"]["revision"] == "r1"


def test_the_cli_rescans_named_pairs(tmp_path, monkeypatch):
    from pathfinder import cli
    c = make(tmp_path, pairs=("Q1P1", "Q1P2"))
    _replies(monkeypatch)
    cli.main(["--root", str(tmp_path), "scan"])
    _context(c, "r1", "state")
    cli.main(["--root", str(tmp_path), "scan", "--rescan", "Q1P2"])
    assert [(r["pair_id"], r.get("revision")) for r in _rows(c)] == [("Q1P1", None), ("Q1P2", None), ("Q1P2", "r1")]


def test_the_view_marks_stale_scores_and_shows_a_pair_history():
    js = (Path(view.__file__).parent / "view-scan.js").read_text()
    assert "stale" in js and "unconditioned" in js and "history" in js


def test_a_context_too_large_for_the_budget_is_refused_not_shortened(tmp_path, monkeypatch):
    from pathfinder import transport
    c = make(tmp_path, pairs=("Q1P1",), prompt_budgets={"scan": 6000})
    _context(c, "r1", "x" * 8000)
    _replies(monkeypatch)
    try:
        scan.rescan(c, ["Q1P1"]); raise AssertionError("an oversized context was sent")
    except transport.PromptTooLarge as e:
        assert "input too large" in str(e)
    _context(c, "r2", "x" * 100)
    c.path("Q.jsonl").write_text(json.dumps({"id": "q1", "title": "Q paper 1", "abstract": "y" * 9000}) + "\n")
    scan.rescan(c, ["Q1P1"])                                             # the paper is digested, the context kept whole
    assert _rows(c)[-1]["gain"] == 50
