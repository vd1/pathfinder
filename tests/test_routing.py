"""Per-stage routing: campaign.json "routes" picks backend, model and effort for a stage or one actor of it."""
import json, shutil, sys
from pathlib import Path
import pytest
from pathfinder import edit, paper, research, routing, transport
from stubcampaign import make

needs_tex = pytest.mark.skipif(not shutil.which("latexmk"), reason="latexmk not installed")
FAKE = str(Path(__file__).parent / "fake_cli.py")


def rows(root):
    return [json.loads(l) for l in (Path(root) / "receipts.jsonl").read_text().splitlines()]


@pytest.mark.parametrize("bad, match", [
    ("peer", "routes must be an object"),
    ({"peer": "codex"}, "routes.peer must be an object"),
    ({"peer": {}}, "routes.peer names none of"),
    ({"peer": {"backend": "openai"}}, "routes.peer.backend"),
    ({"peer": {"model": ""}}, "routes.peer.model"),
    ({"peer": {"effort": "extreme"}}, "routes.peer.effort"),
    ({"peer": {"model": "m", "temperature": 0}}, "routes.peer has unknown keys"),
    ({"assess": {"model": "m"}}, "routes key 'assess' names no stage"),
    ({"edit/": {"model": "m"}}, "routes key 'edit/'"),
])
def test_a_malformed_route_fails_at_load(tmp_path, bad, match):
    with pytest.raises(ValueError, match=match):
        make(tmp_path, routes=bad)


def test_a_route_inside_a_composable_override_is_checked_too(tmp_path):
    with pytest.raises(ValueError, match="routes.verify.effort"):
        make(tmp_path, research_scheme="composable", joint={"routes": {"verify": {"effort": "loud"}}})


def test_the_most_specific_route_wins(tmp_path):
    c = make(tmp_path, routes={"edit": {"model": "e"}, "edit/pce-critic": {"backend": "claude", "model": "c"}})
    assert routing.resolve(c, "edit", "pce-critic") == ("edit/pce-critic", {"backend": "claude", "model": "c"})
    assert routing.resolve(c, "edit", "pce-author") == ("edit", {"model": "e"})
    assert routing.resolve(c, "peer", "ada") is None


def test_no_routes_leave_the_request_and_campaign_untouched(tmp_path):
    c = make(tmp_path)
    request = transport.request("p", model="stub", tools=False, search=False, cwd=tmp_path, timeout=5,
                                thread="Q1P1", stage="peer", actor="ada")
    assert routing.apply(c, request) == (c, request)


def test_a_route_switches_backend_model_and_effort_for_its_request_only(tmp_path):
    c = make(tmp_path, backend="codex", routes={"verify": {"backend": "claude", "model": "claude-opus-5", "effort": "medium"},
                                                "peer": {"backend": "codex", "model": "gpt-6-astra", "effort": "high"}})
    verify = transport.request("p", model="stub", tools=False, search=False, cwd=tmp_path, timeout=5,
                               thread="Q1P1", stage="verify", actor="verifier")
    routed, request = routing.apply(c, verify)
    assert routed is not c and c.backend == "codex" and routed.backend == "claude" and request.model == "claude-opus-5"
    cmd = transport._command(routed, request.model, False, False, tmp_path)
    assert cmd[cmd.index("--effort") + 1] == "medium" and cmd[cmd.index("--model") + 1] == "claude-opus-5"
    peer = transport.request("p", model="stub", tools=True, search=True, cwd=tmp_path, timeout=5,
                             thread="Q1P1", stage="peer", actor="ada")
    routed, request = routing.apply(c, peer)
    cmd = transport._command(routed, request.model, True, True, tmp_path)
    assert cmd[0:2] != ["claude", "-p"] and 'model_reasoning_effort="high"' in cmd
    assert "--effort" not in transport._command(c, "m", False, False, tmp_path)     # an unrouted call is unchanged


def test_a_routed_call_runs_on_the_routed_backend_and_its_receipt_records_the_route(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHFINDER_CLAUDE", f"{sys.executable} {FAKE}")
    monkeypatch.setenv("FAKE_MODE", "claude"); monkeypatch.setenv("FAKE_REPLY", "routed")
    monkeypatch.setattr(transport, "SESSION_GRACE", 5)
    c = make(tmp_path, backend="codex", model="gpt-6-astra",
             routes={"edit/pce-critic": {"backend": "claude", "model": "claude-opus-5", "effort": "medium"}})
    r = transport.call("p", campaign=c, model=c.model, tools=False, search=False, cwd=tmp_path, timeout=10,
                       thread="Q1P1", stage="edit", actor="pce-critic")
    assert r["text"] == "routed"
    row = rows(tmp_path)[-1]
    assert row["backend"] == "claude" and row["model"] == "claude-opus-5"
    assert row["route"] == {"key": "edit/pce-critic", "backend": "claude", "model": "claude-opus-5", "effort": "medium"}


def test_unrouted_receipts_carry_no_route(tmp_path):
    c = make(tmp_path)
    research.run_thread(c, "Q1P1")
    assert all("route" not in row for row in rows(tmp_path))


@needs_tex
def test_routes_reach_every_engine_stage_through_execute(tmp_path):
    """Research, edit and paper on the stub backend, with a model route per stage: each receipt names its
    stage's routed model, so no stage builds its request around the router."""
    stages = ("peer", "consolidate", "verify", "edit", "author", "review")
    c = make(tmp_path, routes={s: {"model": f"stub-{s}"} for s in stages})
    research.run_thread(c, "Q1P1")
    edit.run(c, "Q1P1")
    assert paper.run(c, "Q1P1") == "ACCEPTED"
    seen = {row["stage"]: row for row in rows(tmp_path)}
    for s in stages:
        assert seen[s]["model"] == f"stub-{s}" and seen[s]["route"]["key"] == s, s


def test_a_stub_campaign_stays_on_the_stub_whatever_its_routes_say(tmp_path):
    """A deployment's contract switches a copy to the stub backend: a route to Claude must not make a real call."""
    from pathfinder import routing, transport
    c = make(tmp_path, routes={"verify": {"backend": "claude", "model": "claude-opus-5-5"}})
    request = transport.ModelRequest(identity="x", prompt="p", model="stub", tools=False, search=False, cwd=tmp_path,
                                     timeout=10, thread="Q1P1", stage="verify", actor="verifier")
    routed, req = routing.apply(c, request)
    assert routed.backend == "stub" and req.model == "claude-opus-5-5" and routed.route["backend"] == "stub"


def _fake_attempts(monkeypatch, replies):
    """transport._attempt answered in turn: "refused" (OpenAI's safety filter) or "ok"."""
    seen = []
    def attempt(campaign, request):
        kind = replies[len(seen)]
        seen.append((campaign.backend, request.model))
        if kind == "refused":
            r = {"outcome": "failed", "error": "This content was flagged for possible biological risk.", "text": "",
                 "transport_failed": True, "session": "s", "raw_events": []}
        else:
            r = {"outcome": "completed", "error": None, "text": "fine", "transport_failed": False, "session": "s", "raw_events": []}
        transport._receipt(campaign, request.thread, request.stage, request.actor, request.model, r)
        return r
    monkeypatch.setattr(transport, "_attempt", attempt)
    return seen


def test_a_refused_call_is_retried_once_on_the_fallback_route(tmp_path, monkeypatch):
    c = make(tmp_path, backend="codex", refusal_fallback={"backend": "claude", "model": "claude-opus-5-5"})
    seen = _fake_attempts(monkeypatch, ["refused", "ok"])
    r = transport.execute(c, transport.request("p", model="gpt-6.1-sol", tools=True, search=False, cwd=tmp_path,
                                               timeout=5, thread="Q1P1", stage="peer", actor="ada"))
    assert r["outcome"] == "completed" and seen == [("codex", "gpt-6.1-sol"), ("claude", "claude-opus-5-5")]
    rows = transport.receipts(c)
    assert rows[-1]["route"]["key"] == "refusal_fallback" and rows[0]["failure"]["class"] == "refusal"


def test_without_a_fallback_a_refusal_stands(tmp_path, monkeypatch):
    c = make(tmp_path, backend="codex")
    seen = _fake_attempts(monkeypatch, ["refused", "ok"])
    r = transport.execute(c, transport.request("p", model="m", tools=True, search=False, cwd=tmp_path, timeout=5,
                                               thread="Q1P1", stage="peer", actor="ada"))
    assert (r.get("failure") or {}).get("class") == "refusal" and len(seen) == 1


def test_a_refusal_on_the_fallback_is_not_retried_again(tmp_path, monkeypatch):
    c = make(tmp_path, backend="codex", refusal_fallback={"backend": "claude", "model": "claude-opus-5-5"})
    seen = _fake_attempts(monkeypatch, ["refused", "refused", "ok"])
    r = transport.execute(c, transport.request("p", model="m", tools=True, search=False, cwd=tmp_path, timeout=5,
                                               thread="Q1P1", stage="peer", actor="ada"))
    assert (r.get("failure") or {}).get("class") == "refusal" and len(seen) == 2


def test_a_bad_fallback_is_refused_at_load(tmp_path):
    with pytest.raises(ValueError, match="refusal_fallback"):
        make(tmp_path, refusal_fallback={"backend": "openai"})


def test_a_call_routed_to_claude_with_a_contract_is_told_to_answer_with_json_only(tmp_path, monkeypatch):
    """Codex enforces a reply schema; Claude's CLI does not, and Opus reviews often needed the contract's repair
    turn (statarb and julien-2, October). A Claude call with a schema carries the schema and a JSON-only rule."""
    c = make(tmp_path, backend="codex", routes={"review": {"backend": "claude", "model": "claude-opus-5-5"}})
    seen = []
    monkeypatch.setattr(transport, "_attempt", lambda campaign, request: seen.append((campaign.backend, request.prompt))
                        or {"outcome": "completed", "text": "{}", "transport_failed": False, "session": "s", "raw_events": []})
    schema = {"type": "object", "required": ["approved"], "properties": {"approved": {"type": "boolean"}}}
    for stage in ("review", "peer"):
        transport.execute(c, transport.request("Judge it.", model="m", tools=False, search=False, cwd=tmp_path,
                                               timeout=5, thread="Q1P1", stage=stage, actor="x", schema=schema))
    (claude_backend, claude_prompt), (codex_backend, codex_prompt) = seen
    assert claude_backend == "claude" and "exactly one JSON object" in claude_prompt and '"approved"' in claude_prompt
    assert codex_backend == "codex" and codex_prompt == "Judge it."
