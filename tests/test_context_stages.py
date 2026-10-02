"""Every stage builds its prompt within its budget (J01)."""
import json
from pathfinder import research, transport
from stubcampaign import make


def _capture(monkeypatch, module=research):
    seen = {}
    real = module.transport.execute

    def capture(campaign, request):
        seen.setdefault(request.stage, []).append(request.prompt)
        return real(campaign, request)
    monkeypatch.setattr(module.transport, "execute", capture)
    return seen


def _long_papers(c, size):
    d = research.prepare(c, "Q1P1"); inp = research._inputs(d)
    (d / "inputs" / inp["Q"]).write_text("q" * size); (d / "inputs" / inp["P"]).write_text("p" * size)
    return d, inp


def test_consolidate_and_verify_prompts_fit_and_reference_the_papers(tmp_path, monkeypatch):
    c = make(tmp_path, prompt_budgets={"default": 6000})
    d, inp = _long_papers(c, 20_000)
    seen = _capture(monkeypatch)
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    for stage in ("consolidate", "verify"):
        prompt = seen[stage][0]
        assert len(prompt) <= 6000 and f"(file inputs/{inp['Q']}: 20000 bytes, sha256 " in prompt


def test_a_ledger_over_budget_is_referenced_not_pasted(tmp_path, monkeypatch):
    c = make(tmp_path, prompt_budgets={"default": 6000})
    d = research.prepare(c, "Q1P1")
    (d / "ledger.jsonl").write_text("".join(json.dumps({"seq": n, "actor": "ada", "kind": "note", "text": "x" * 200, "at": "t"}) + "\n"
                                            for n in range(1, 200)))
    seen = _capture(monkeypatch)
    research.run_thread(c, "Q1P1")
    assert "(file ledger.jsonl: " in seen["consolidate"][0] and len(seen["consolidate"][0]) <= 6000


def test_review_material_is_stable_and_a_check_is_not_recorded(tmp_path):
    c = make(tmp_path, research_scheme="direct_eva", imported_research=True, prompt_budgets={"default": 6000})
    _long_papers(c, 20_000)
    first = research._review_material(c, "Q1P1", record_manifest=False)
    assert first == research._review_material(c, "Q1P1", record_manifest=False)
    assert len(first) <= 6000
    events = c.path("events.jsonl")
    assert not events.exists() or "context_built" not in events.read_text()


def test_paper_review_fits_and_keeps_the_paper_whole(tmp_path, monkeypatch):
    from pathfinder import edit, paper
    c = make(tmp_path, prompt_budgets={"default": 9000})
    d, inp = _long_papers(c, 60_000)
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    edit._set(c, "Q1P1", status="done")
    monkeypatch.setattr(paper, "_arxiv_titles", lambda ids: {})
    seen = _capture(monkeypatch, paper)
    real_call = paper.transport.call
    prompts = {}

    def capture_call(prompt, **kw):
        prompts.setdefault(kw["stage"], []).append(prompt)
        return real_call(prompt, **kw)
    monkeypatch.setattr(paper.transport, "call", capture_call)
    paper.run(c, "Q1P1")
    review = prompts["review"][0]
    tex = (d / "paper" / "paper.tex").read_text()
    assert len(review) <= 9000 and tex in review and f"digest of {inp['Q']}: 60000 characters" in review


def test_a_scan_with_full_texts_over_budget_fits(tmp_path):
    from pathfinder import scan
    c = make(tmp_path, prompt_budgets={"default": 5000})
    q = {"id": "q1", "title": "Q", "abstract": "a", "text": None}
    p = {"id": "p1", "title": "P", "abstract": "b", "text": None}
    long = {"q1": "x" * 30_000, "p1": "y" * 30_000}
    import pathfinder.corpus as corpus
    real = corpus.body
    corpus.body = lambda campaign, row, full: long[row["id"]]
    try:
        prompt = scan.render(c, q, p)
    finally:
        corpus.body = real
    assert len(prompt) <= 5000 and prompt.count("characters omitted") == 2


def test_the_edit_stage_dispatch_fits(tmp_path, monkeypatch):
    from pathfinder import edit_stage
    c = make(tmp_path, prompt_budgets={"default": 4000})
    d = research.prepare(c, "Q1P1")
    (d / "Q1P1.tex").write_text("\\documentclass{article}" + "z" * 50_000)
    research._set(c, "Q1P1", status="DRAFT", stage="done")
    prompts = []
    real = edit_stage.transport.call
    monkeypatch.setattr(edit_stage.transport, "call", lambda prompt, **kw: prompts.append(prompt) or real(prompt, **kw))
    edit_stage.finish(c, "Q1P1")
    assert prompts and len(prompts[0]) <= 4000
