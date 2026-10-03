"""D10, second half: does Vera notice a planted flaw? Sound and flawed copies of finished ledgers, one review each."""
import json
from pathfinder import probe, research
from stubcampaign import make
from pathfinder.ledger import Ledger


def _finished(tmp_path):
    c = make(tmp_path / "source", pairs=("Q1P1",))
    d = research.prepare(c, "Q1P1")
    Ledger(d / "ledger.jsonl").add("ada", "finding", "The bound gives a variance of 0.125 at lag 4, so 32 samples suffice.")
    Ledger(d / "ledger.jsonl").add("emmy", "finding", "Agreed: with 32 samples the error is below 2 percent.")
    return c


def test_a_planted_flaw_changes_one_number_in_one_finding():
    text = "The bound gives a variance of 0.125 at lag 4, so 32 samples suffice."
    flawed, planted = probe.plant(text)
    assert flawed != text and planted["before"] in text and planted["after"] in flawed
    assert flawed.replace(planted["after"], planted["before"], 1) == text


def test_the_probe_builds_sound_and_flawed_copies_and_reports(tmp_path):
    source = _finished(tmp_path)
    report = probe.run(source, ["Q1P1"], tmp_path / "probe")
    assert set(report["units"]) == {"Q1P1-sound", "Q1P1-flawed"}
    flawed = report["units"]["Q1P1-flawed"]
    assert flawed["planted"]["before"] != flawed["planted"]["after"]
    assert report["detection_rate"] == 0.0 and report["false_alarm_rate"] == 0.0     # the stub never asks for anything
    assert json.loads((tmp_path / "probe" / "probe-report.json").read_text()) == report
    sound = (tmp_path / "probe" / "threads" / report["units"]["Q1P1-sound"]["pair"] / "ledger.jsonl").read_text()
    assert sound.startswith((source.thread_dir("Q1P1") / "ledger.jsonl").read_text())   # then the review row
