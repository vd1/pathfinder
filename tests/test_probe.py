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
    assert report["request_rate_flawed"] == 0.0 and report["correction_rate"] == 0.0 and report["request_rate_sound"] == 0.0
    assert json.loads((tmp_path / "probe" / "probe-report.json").read_text()) == report
    sound = (tmp_path / "probe" / "threads" / report["units"]["Q1P1-sound"]["pair"] / "ledger.jsonl").read_text()
    assert sound.startswith((source.thread_dir("Q1P1") / "ledger.jsonl").read_text())   # then the review row


import pytest


@pytest.mark.parametrize("text", [
    "Hidden transfer (01-q-paper.txt q0001:963, 000351-000355) and the 4m+1 count.",
    "Correction to seq 33 wording, prompted by Ada seq 10 and entries 20-21.",
    "Re-read Q prefixed lines 733-788 and P lines 193-212.",
    "I agree with emmy 36, and P p0007:000065,000095 supplies the costs.",
])
def test_locators_are_never_the_planted_flaw(text):
    with pytest.raises(ValueError):
        probe.plant(text)


def test_a_quantity_in_a_relation_is_the_planted_flaw():
    flawed, planted = probe.plant("See entry 12: with B = 16 the bound is 0.125, which needs 32 samples.")
    assert planted["before"] == "16" and "B = 48" in flawed



def test_a_correction_names_both_values():
    planted = {"before": "38", "after": "114"}
    assert probe._corrects({"text": "the script reports 38 checks, not 114"}, planted)
    assert not probe._corrects({"text": "rerun with 1140 samples and 380 seeds"}, planted)
