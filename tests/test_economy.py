"""Session economy: what a pair's calls cost in input tokens, by stage, and how much of it was cached."""
import json
from pathfinder import cli, economy
from stubcampaign import make


ROWS = [{"call_id": "a", "thread": "Q1P1", "stage": "peer", "outcome": "completed", "input_tokens": 1000, "cache_read": 900,
         "output_tokens": 50, "prompt_chars": 4000, "tool_calls": 12},
        {"call_id": "b", "thread": "Q1P1", "stage": "verify", "outcome": "completed", "input_tokens": 500, "cache_read": 0,
         "output_tokens": 20, "prompt_chars": 9000, "tool_calls": 3},
        {"call_id": "c", "thread": "Q2P1", "stage": "peer", "outcome": "launch failed", "input_tokens": None},
        {"call_id": "d", "thread": "Q2P1", "stage": "peer", "outcome": "completed", "input_tokens": 3000, "cache_read": 1500,
         "output_tokens": 70, "prompt_chars": 4000, "tool_calls": 20}]


def test_the_summary_is_by_stage_and_by_pair_over_calls_that_reached_a_model():
    s = economy.summary(ROWS)
    assert s["stages"]["peer"] == {"calls": 2, "input_tokens": 4000, "cached_share": 0.6, "output_tokens": 120,
                                   "mean_prompt_chars": 4000, "mean_tool_calls": 16.0, "mean_input_tokens": 2000}
    assert s["pairs"] == {"Q1P1": 1500, "Q2P1": 3000} and s["mean_input_tokens_per_pair"] == 2250


def test_the_economy_command_prints_the_campaign_summary(tmp_path, capsys):
    c = make(tmp_path)
    c.path("receipts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in ROWS))
    cli.main(["--root", str(tmp_path), "economy", "--json"])
    assert json.loads(capsys.readouterr().out)["pairs"]["Q2P1"] == 3000
