"""Per-pair entries in the scan context (nobel, 11 October 2026). A literature check found that many top pairs were
already done, or done in part, after both papers appeared: the scan, reading two abstracts, cannot see that. Its
verdict for one pair goes in scan-context.json under "pairs"; a rescan of that pair sees the shared text and its
own entry, and research starts from the entry (the prior work and the open part), frozen into the pair's inputs."""
import json
from pathfinder import campaign_state, research, scan, stub
from stubcampaign import make

ENTRY = ("Verdict: partly done. Tong et al. (arXiv:2110.06942) already combine the two decompositions. "
         "Open part: is the dependence on Delta polylogarithmic when V is only quasi-local?")


def _rows(c):
    return [json.loads(l) for l in c.path("scan.jsonl").read_text().splitlines() if l.strip()]


def _context(c, revision="novelty-1", text="Novelty verdicts from the literature check.", pairs=None):
    doc = {"revision": revision, "text": text}
    if pairs is not None:
        doc["pairs"] = pairs
    c.path("scan-context.json").write_text(json.dumps(doc))


def _recording(monkeypatch):
    seen, original = [], stub.reply
    def reply(campaign, request):
        seen.append(request)
        return original(campaign, request)
    monkeypatch.setattr(stub, "reply", reply)
    return seen


def test_a_rescan_sees_the_shared_text_and_its_own_entry_only(tmp_path, monkeypatch):
    c = make(tmp_path, pairs=("Q1P1", "Q1P2"))
    scan.run(c)
    _context(c, pairs={"Q1P1": ENTRY})
    seen = _recording(monkeypatch)
    scan.rescan(c, ["Q1P1", "Q1P2"])
    by_pair = {r.thread: r.prompt for r in seen}
    assert ENTRY in by_pair["Q1P1"] and "Novelty verdicts" in by_pair["Q1P1"]
    assert ENTRY not in by_pair["Q1P2"] and "Novelty verdicts" in by_pair["Q1P2"]
    rows = {r["pair_id"]: r for r in _rows(c)[2:]}
    assert rows["Q1P1"]["context_sha256"] != rows["Q1P2"]["context_sha256"]
    archived = json.loads(c.path(f"scan-contexts/{rows['Q1P1']['context_sha256']}.json").read_text())
    assert archived["pair_id"] == "Q1P1" and archived["entry"] == ENTRY


def test_the_entry_asks_the_judge_to_keep_its_open_question(tmp_path, monkeypatch):
    c = make(tmp_path, pairs=("Q1P1",))
    _context(c, pairs={"Q1P1": ENTRY})
    seen = _recording(monkeypatch)
    scan.run(c)
    prompt = seen[0].prompt
    tail = prompt[prompt.index(ENTRY):]
    assert prompt.index(ENTRY) > prompt.index("Abstract of P1")          # after the papers, the last word
    assert "rather than constructing a connexion from the papers alone" in tail and "abstracts" not in tail.replace(ENTRY, "")


def test_adding_one_pair_entry_leaves_the_other_scores_current(tmp_path, monkeypatch):
    c = make(tmp_path, pairs=("Q1P1", "Q1P2"))
    _context(c, pairs={})
    scan.run(c)
    _context(c, pairs={"Q1P1": ENTRY})
    cur = {r["pair_id"]: r for r in scan.current(c)}
    assert cur["Q1P1"]["stale"] and not cur["Q1P2"]["stale"]
    seen = _recording(monkeypatch)
    scan.rescan(c, ["Q1P1", "Q1P2"])
    assert [r.thread for r in seen] == ["Q1P1"]                          # Q1P2 is already current
    assert not any(r["stale"] for r in scan.current(c))


def test_without_pair_entries_the_digest_is_the_shared_one(tmp_path):
    c = make(tmp_path, pairs=("Q1P1",))
    _context(c)
    scan.run(c)
    sha = _rows(c)[0]["context_sha256"]
    _context(c, pairs={"Q1P2": ENTRY})                                   # an entry for another pair only
    assert not scan.current(c)[0]["stale"] and _rows(c)[0]["context_sha256"] == sha


def test_research_starts_from_the_entry_and_freezes_it_into_the_inputs(tmp_path, monkeypatch):
    c = make(tmp_path, pairs=("Q1P1",))
    scan.run(c)
    _context(c, pairs={"Q1P1": ENTRY})
    scan.rescan(c, ["Q1P1"])
    seen = _recording(monkeypatch)
    research.run_thread(c, "Q1P1")
    frozen = c.thread_dir("Q1P1") / "inputs" / "pair-context.md"
    assert ENTRY in frozen.read_text() and "novelty-1" in frozen.read_text()
    peers = [r for r in seen if r.stage == "peer"]
    assert peers and all(ENTRY in r.prompt for r in peers)
    _context(c, revision="novelty-2", pairs={"Q1P1": "changed later"})     # a started thread keeps what it froze
    assert ENTRY in frozen.read_text()


def test_a_composable_pair_gives_every_branch_the_entry(tmp_path, monkeypatch):
    c = make(tmp_path, pairs=("Q1P1",), research_scheme="composable", branches=2)
    scan.run(c)
    _context(c, pairs={"Q1P1": ENTRY})
    scan.rescan(c, ["Q1P1"])
    seen = _recording(monkeypatch)
    research.run_thread(c, "Q1P1")
    d = c.thread_dir("Q1P1")
    assert all(ENTRY in (d / "branches" / b / "inputs" / "pair-context.md").read_text() for b in ("branch-1", "branch-2"))
    peers = [r for r in seen if r.stage == "peer"]
    assert peers and all(ENTRY in r.prompt for r in peers)


def test_a_pair_without_an_entry_researches_as_before(tmp_path, monkeypatch):
    c = make(tmp_path, pairs=("Q1P1",))
    _context(c, pairs={"Q1P2": ENTRY})
    scan.run(c)
    research.run_thread(c, "Q1P1")
    assert not (c.thread_dir("Q1P1") / "inputs" / "pair-context.md").exists()


def test_malformed_pair_entries_are_refused(tmp_path):
    c = make(tmp_path, pairs=("Q1P1",))
    c.path("scan-context.json").write_text(json.dumps({"revision": "r", "text": "t", "pairs": {"Q1P1": 3}}))
    try:
        scan.run(c); raise AssertionError("a malformed context was used")
    except ValueError as e:
        assert "pairs" in str(e)
    assert campaign_state.scan_document(c)["context"] is None            # the page still renders
