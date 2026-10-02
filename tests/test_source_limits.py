"""Rate limits that agents meet inside their own tool calls (arXiv), recorded and surfaced."""
import json
from pathfinder import health, playbook, transport
from stubcampaign import make


def _codex(output, code=0, command="curl -s 'https://export.arxiv.org/api/query?search_query=all:ising'"):
    return json.dumps({"type": "item.completed", "item": {"type": "command_execution", "command": command,
                                                          "aggregated_output": output, "exit_code": code}})


def test_arxiv_rate_limits_are_counted_even_when_the_command_succeeds():
    lines = [_codex("Rate exceeded."), _codex("<feed>ok</feed>"),
             _codex("HTTP/2 429 Too Many Requests", code=22, command="curl -sf https://arxiv.org/abs/2401.00001"),
             _codex("Rate exceeded.", command="echo not arxiv")]
    assert transport._source_limits(lines) == {"arxiv": 2}


def test_claude_tool_results_count_too():
    line = json.dumps({"type": "user", "message": {"content": [
        {"type": "tool_result", "content": "Request failed with status code 429 for https://export.arxiv.org/api/query", "is_error": True}]}})
    assert transport._source_limits([line]) == {"arxiv": 1}


def test_recent_hits_reach_health_and_the_playbook(tmp_path):
    c = make(tmp_path)
    with c.path("receipts.jsonl").open("a") as stream:
        for n in range(3):
            stream.write(json.dumps({"v": 3, "thread": "Q1P1", "stage": "peer", "actor": "ada", "outcome": "completed",
                                     "source_limits": {"arxiv": 2}}) + "\n")
    assert health.snapshot(c)["source_limits"] == {"arxiv": 6}
    advice = [a for a in playbook.next_actions(c) if "arXiv" in a["action"]]
    assert advice and advice[0]["owner"] == "apex"


def test_the_peer_prompt_tells_agents_how_to_query_arxiv():
    from pathfinder import resources
    text = resources.prompt(None, "peer")
    assert "export.arxiv.org" in text and "Rate exceeded" in text
