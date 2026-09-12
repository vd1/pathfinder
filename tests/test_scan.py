import json, sys
from pathlib import Path
from pathfinder import scan, transport
from pathfinder.config import Campaign


def test_scan_is_resumable_and_parses(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHFINDER_CLAUDE", f"{sys.executable} {Path(__file__).parent / 'fake_cli.py'}")
    monkeypatch.setenv("FAKE_REPLY", '```json\n{"feasibility": 70, "gain": 40, "connexion": "c", "rationale": "r"}\n```')
    monkeypatch.setattr(transport, "SESSION_GRACE", 2)
    (tmp_path / "prompts").mkdir(); (tmp_path / "prompts" / "scan.md").write_text("{{Q_TITLE}}|{{Q_BODY}}|{{P_TITLE}}|{{P_BODY}}")
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=True, seats=1, cut=1,
                 rounds=1, allowances={}, budget_usd=1, prices={}, scan_fulltext=None)
    (tmp_path / "Q.jsonl").write_text('{"id":"a","title":"A","abstract":"aa"}\n')
    (tmp_path / "P.jsonl").write_text('{"id":"b","title":"B","abstract":"bb"}\n{"id":"c","title":"C","abstract":"cc"}\n')
    (tmp_path / "scan.jsonl").write_text(json.dumps({"pair_id": "Q1P1", "feasibility": 1, "gain": 1}) + "\n")
    scan.run(c)
    rows = [json.loads(l) for l in (tmp_path / "scan.jsonl").read_text().splitlines()]
    assert [r["pair_id"] for r in rows] == ["Q1P1", "Q1P2"] and rows[1]["feasibility"] == 70


def test_parse_json_tolerates_tex_backslashes():
    assert scan.parse_json('{"decision": "PAUSE", "reason": "the bound \\( e_s/\\delta \\) fails", "action": null}')["reason"].startswith("the bound")
    assert scan.parse_json('{"a": "line\\nbreak", "b": 1}') == {"a": "line\nbreak", "b": 1}
