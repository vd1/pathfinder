"""Shrinking by structure before shrinking blindly: a section with a projection is projected first when the prompt
is over budget (the ledger projection keeps findings in full and shortens history), recorded with the full text's
digest; a prompt within budget is unchanged, and the evidence a review is bound to stays the full ledger."""
import hashlib, json
from pathfinder import context, projection, research
from pathfinder.context import Section
from pathfinder.ledger import Ledger
from stubcampaign import make

FINDING = "The bound holds for every n >= 3 by induction on the block size. " * 20


def _ledger(path, intentions=6):
    led = Ledger(path)
    for k in range(intentions):
        led.add("ada", "intention", f"I will check case {k}. " + "x" * 2000)
    first = led.add("ada", "finding", "an early claim, later corrected. " + "y" * 1500)
    led.add("emmy", "correction", "the early claim needs n >= 3.", supersedes=first)
    led.add("ada", "finding", FINDING)
    led.add("verifier", "review", json.dumps({"review_id": "r1", "evidence_id": "e" * 64,
                                              "response": {"requests": [{"id": "R1", "action": "ITERATE", "text": "z" * 3000}]}}))
    seq = led.add("ada", "ready", "ready at #10", seen=10)
    return path, seq


def _events(c):
    return [json.loads(l) for l in c.path("events.jsonl").read_text().splitlines() if '"context_built"' in l]


def test_the_ledger_projection_keeps_findings_and_marks_every_cut(tmp_path):
    path, _ = _ledger(tmp_path / "ledger.jsonl")
    full = path.read_text()
    out = projection.ledger(full)
    assert len(out) < len(full) / 2
    assert FINDING in out and "the early claim needs n >= 3." in out
    assert "#7 ada finding: superseded by #8" in out and "y" * 100 not in out
    assert "#1 ada intention: I will check case 0." in out and "characters omitted" in out
    assert '"id": "R1"' in out and "e" * 64 not in out and "z" * 300 not in out
    assert "#11 ada ready at #10" in out
    assert projection.ledger("plain text\nno rows") == "plain text\nno rows"


def test_within_budget_the_ledger_is_sent_as_it_is(tmp_path):
    c = make(tmp_path / "c")
    path, _ = _ledger(tmp_path / "ledger.jsonl")
    out = context.build(c, "verify", [Section("ledger.jsonl", path=path, project=projection.ledger)], tools=True, cwd=tmp_path)
    assert out == "## ledger.jsonl\n\n" + path.read_text()


def test_over_budget_the_projection_comes_before_a_reference_and_is_recorded(tmp_path):
    path, _ = _ledger(tmp_path / "ledger.jsonl")
    full = path.read_text()
    c = make(tmp_path / "c", prompt_budgets={"default": len(projection.ledger(full)) + 200})
    out = context.build(c, "verify", [Section("ledger.jsonl", path=path, project=projection.ledger)], tools=True, cwd=tmp_path)
    assert FINDING in out and "read it with your tools" not in out
    s = _events(c)[-1]["sections"][0]
    assert s["mode"] == "projection" and s["projection"] == "ledger"
    assert s["full_chars"] == len(full) and s["sha256"] == hashlib.sha256(full.encode()).hexdigest()


def test_a_projection_too_large_still_falls_back_to_a_reference(tmp_path):
    path, _ = _ledger(tmp_path / "ledger.jsonl")
    c = make(tmp_path / "c", prompt_budgets={"default": 1000})
    out = context.build(c, "verify", [Section("ledger.jsonl", path=path, project=projection.ledger)], tools=True, cwd=tmp_path)
    assert "read it with your tools" in out and _events(c)[-1]["sections"][0]["mode"] == "reference"


def test_a_review_over_budget_reads_the_projected_ledger_bound_to_the_full_one(tmp_path):
    c = make(tmp_path / "c", research_scheme="direct_eva")
    d = research.prepare(c, "Q1P1")
    _ledger(d / "ledger.jsonl", intentions=40)
    _, small = research._review_material(c, "Q1P1", with_id=True)
    full = (d / "ledger.jsonl").read_text()
    raw = json.loads(c.path("campaign.json").read_text())
    raw["prompt_budgets"] = {"verify": len(full) - 20_000}
    c.path("campaign.json").write_text(json.dumps(raw))
    from pathfinder import config
    c2 = config.load(c.root)
    material, evidence_id = research._review_material(c2, "Q1P1", with_id=True)
    assert FINDING in material and "superseded by #42" in material and evidence_id == small


def test_bundle_ledgers_inlined_in_a_joint_review_are_projected(tmp_path):
    text = "## branches/b1/ledger.jsonl\n\n" + _ledger(tmp_path / "b1.jsonl")[0].read_text() + "\n## branches/b1/ada/x.md\n\nnotes"
    out = projection.ledger(text)
    assert out.startswith("## branches/b1/ledger.jsonl\n\n" + projection.NOTE) and out.endswith("## branches/b1/ada/x.md\n\nnotes")
    assert FINDING in out and "superseded by #8" in out
