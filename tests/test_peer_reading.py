"""A peer's first call reads the papers: an outline by line lets it jump to what it needs instead of printing the
whole file, and every later turn of its session resends whatever it printed."""
import json
from pathfinder import config, context, research, transport
from stubcampaign import make

TEX = "\n".join(["\\documentclass{article}", "\\begin{document}", "\\section{Introduction}", "text", "",
                 "\\subsection{Setting}\\label{s}", "more", "\\section*{Funding-rate persistence}", "x",
                 "\\appendix", "\\section{Proofs}", "\\end{document}"])


def test_outline_lists_tex_sections_with_their_lines():
    lines = context.outline(TEX).splitlines()
    assert lines == ["3: Introduction", "6:   Setting", "8: Funding-rate persistence", "11: Proofs"]


def test_outline_lists_markdown_headings_and_nothing_for_plain_text():
    assert context.outline("# Title\nbody\n## Part\n") == "1: Title\n3:   Part"
    assert context.outline('{"a": 1, "b": [1, 2]}') == ""


def test_outline_is_capped():
    text = "\n".join(f"\\section{{S{i}}}" for i in range(500))
    out = context.outline(text)
    assert len(out.splitlines()) <= context.OUTLINE_ENTRIES + 1 and "more" in out.splitlines()[-1]


def _peer_prompt(tmp_path, monkeypatch, **overrides):
    c = make(tmp_path, **overrides)
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources/Q.tex").write_text(TEX)
    rows = [json.loads(l) for l in (tmp_path / "Q.jsonl").read_text().splitlines()]
    rows[0]["text"] = "sources/Q.tex"
    (tmp_path / "Q.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    c = config.load(tmp_path)
    seen = {}
    real = transport.execute
    monkeypatch.setattr(transport, "execute",
                        lambda campaign, request: seen.setdefault(request.stage, request.prompt) and None or real(campaign, request))
    research.run_thread(c, "Q1P1")
    return seen["peer"]


def test_a_peer_reading_by_reference_gets_the_outline_of_each_paper(tmp_path, monkeypatch):
    prompt = _peer_prompt(tmp_path, monkeypatch)
    assert "Outline of inputs/Q.tex (12 lines)" in prompt and "8: Funding-rate persistence" in prompt


def test_a_budgeted_role_is_told_to_bound_what_it_prints(tmp_path, monkeypatch):
    prompt = _peer_prompt(tmp_path, monkeypatch, tool_call_budgets={"peer": 15})
    assert "never print a whole file or an unbounded search" in prompt and "cut -c" in prompt


def test_peers_keep_working_files_plain_and_ungated(tmp_path, monkeypatch):
    prompt = _peer_prompt(tmp_path, monkeypatch)
    assert "do not compile documents" in prompt and "no style gate" in prompt
    assert "several ledger commands in one shell command" in prompt
