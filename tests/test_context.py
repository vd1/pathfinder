"""One budgeted context builder: references for agents with tools, digests for those without (J01)."""
import json
import pytest
from pathfinder import context, transport
from pathfinder.context import Section
from stubcampaign import make


def _files(tmp_path, **sizes):
    d = tmp_path / "work"; d.mkdir(exist_ok=True)
    for name, size in sizes.items():
        (d / f"{name}.txt").write_text(name[0] * size)
    return d


def _events(c):
    p = c.path("events.jsonl")
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


def test_within_budget_everything_is_inline_in_order(tmp_path):
    c = make(tmp_path / "c")
    d = _files(tmp_path, alpha=100, beta=50)
    out = context.build(c, "verify", [Section("alpha", path=d / "alpha.txt"), Section("beta", path=d / "beta.txt"),
                                      Section("", text="## your task\n\ndo it", keep=True)], tools=True, cwd=d)
    assert out == "## alpha\n\n" + "a" * 100 + "\n\n## beta\n\n" + "b" * 50 + "\n\n## your task\n\ndo it"


def test_over_budget_with_tools_the_largest_file_is_referenced(tmp_path):
    c = make(tmp_path / "c", prompt_budgets={"default": 3000})
    d = _files(tmp_path, alpha=10_000, beta=500)
    out = context.build(c, "verify", [Section("alpha", path=d / "alpha.txt"), Section("beta", path=d / "beta.txt")],
                        tools=True, cwd=d)
    assert len(out) <= 3000 and "b" * 500 in out
    assert "(file alpha.txt: 10000 bytes, sha256 " in out and "read it with your tools" in out
    assert out.index("## alpha") < out.index("## beta")


def test_over_budget_without_tools_the_largest_section_is_digested(tmp_path):
    c = make(tmp_path / "c", prompt_budgets={"default": 5000})
    d = _files(tmp_path, alpha=20_000, beta=500)
    out = context.build(c, "review", [Section("alpha", path=d / "alpha.txt"), Section("beta", path=d / "beta.txt")],
                        tools=False, cwd=d)
    assert len(out) <= 5000 and "b" * 500 in out
    assert "digest of alpha: 20000 characters" in out and "characters omitted" in out


def test_a_kept_section_is_never_shrunk_and_nothing_left_raises(tmp_path):
    c = make(tmp_path / "c", prompt_budgets={"default": 5000})
    d = _files(tmp_path, alpha=20_000, beta=4_000)
    out = context.build(c, "review", [Section("alpha", path=d / "alpha.txt"), Section("beta", path=d / "beta.txt", keep=True)],
                        tools=False)
    assert "b" * 4000 in out and len(out) <= 5000
    with pytest.raises(transport.PromptTooLarge):
        context.build(c, "review", [Section("beta", text="b" * 6000, keep=True)], tools=False)


def test_equal_inputs_give_identical_prompts(tmp_path):
    c = make(tmp_path / "c", prompt_budgets={"default": 4000})
    d = _files(tmp_path, alpha=9_000, beta=9_000)
    sections = [Section("alpha", path=d / "alpha.txt"), Section("beta", text="b" * 9000)]
    assert context.build(c, "review", sections, tools=False) == context.build(c, "review", sections, tools=False)


def test_budget_default_stage_and_ceiling(tmp_path):
    assert context.budget(make(tmp_path / "a"), "verify") == context.DEFAULT_BUDGET
    c = make(tmp_path / "b", prompt_budgets={"default": 1000, "review": 2000})
    assert context.budget(c, "verify") == 1000 and context.budget(c, "review") == 2000
    c = make(tmp_path / "c", prompt_budgets={"default": 900_000}, max_prompt_chars=500_000)
    assert context.budget(c, "verify") == 500_000


def test_the_build_is_recorded_only_when_asked(tmp_path):
    c = make(tmp_path / "c", prompt_budgets={"default": 3000})
    d = _files(tmp_path, alpha=10_000)
    context.build(c, "verify", [Section("alpha", path=d / "alpha.txt")], tools=True, cwd=d, unit="Q1P1", record=False)
    assert not [e for e in _events(c) if e["kind"] == "context_built"]
    context.build(c, "verify", [Section("alpha", path=d / "alpha.txt")], tools=True, cwd=d, unit="Q1P1")
    [event] = [e for e in _events(c) if e["kind"] == "context_built"]
    assert event["unit"] == "Q1P1" and event["budget"] == 3000 and event["sections"][0]["mode"] == "reference"
