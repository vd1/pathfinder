import pytest
from pathfinder import failures


@pytest.mark.parametrize("outcome,error,cls,scope", [
    ("error", "You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage ... try again at Oct 4th, 2026 2:07 AM.", "quota", "campaign"),
    ("error", "You've hit your session limit · resets 2:30pm", "quota", "campaign"),
    ("error", "unexpected status 401 Unauthorized: Incorrect API key provided", "auth", "campaign"),
    ("error", "Missing environment variable: ELM_API_KEY", "auth", "campaign"),
    ("error", "turn/start failed: Input exceeds the maximum length of 1048576 characters. input_too_large", "input_too_large", "call"),
    ("error", "This content was flagged for possible biological risk. If this seems wrong, try rephrasing", "refusal", "pair"),
    ("error", "API Error: Opus 5's safeguards flagged this message", "refusal", "pair"),
    ("error", "Selected model is at capacity. Please try a different model.", "rate", "call"),
    ("error", "HTTP 429 Too Many Requests", "rate", "call"),
    ("launch failed", "error: unexpected argument '--search' found", "launch", "campaign"),
    ("no session", "no session", "no_session", "call"),
    ("timeout", "timeout", "timeout", "call"),
    ("error", "CLI exited without a completed turn", "undiagnosed", "call"),
])
def test_catalogue_signatures(outcome, error, cls, scope):
    f = failures.classify(outcome, error)
    assert (f.cls, f.scope) == (cls, scope)


def test_completed_call_is_not_a_failure_whatever_it_says():
    assert failures.classify("completed", None) is None


def test_admission_refusal_is_not_classified_unless_oversize():
    assert failures.classify("refused", "budget: 9.10 projected against cap 9.00") is None
    assert failures.classify("refused", "input too large: 1000001 characters exceed 1000000").cls == "input_too_large"


def test_quota_reset_time_is_parsed():
    f = failures.classify("error", "You've hit your usage limit ... try again at Oct 4th, 2026 2:07 AM.")
    assert f.reset_at == "Oct 4th, 2026 2:07 AM"
    assert failures.classify("error", "You've hit your session limit · resets 2:30pm").reset_at == "2:30pm"


def test_record_is_plain_json():
    assert failures.classify("timeout", "timeout").record() == {
        "class": "timeout", "scope": "call", "retry": True, "reset_at": None}


def test_deployment_rules_come_first_and_must_name_a_known_class():
    import re
    rule = [("auth", re.compile(r"key file mode 0644"))]
    assert failures.classify("error", "key file mode 0644", extra_rules=rule).cls == "auth"
    with pytest.raises(ValueError):
        failures.classify("error", "x", extra_rules=[("mystery", re.compile("x"))])


def test_campaign_failure_rules_extension(tmp_path):
    from stubcampaign import make
    c = make(tmp_path, extensions={"path": "deploy", "failure_rules": "drip_rules:RULES"})
    d = tmp_path / "deploy"; d.mkdir(exist_ok=True)
    (d / "drip_rules.py").write_text("RULES = [('contract', 'READY needs code and feeds')]\n")
    with pytest.raises(ValueError):                       # 'contract' is not a transport failure class
        failures.rules_for(c)
    (d / "drip_rules.py").write_text("RULES = [('auth', 'key file .* not 0600')]\n")
    import sys; sys.modules.pop("drip_rules", None)
    rules = failures.rules_for(c)
    assert failures.classify("error", "key file x not 0600", extra_rules=rules).cls == "auth"


def test_no_extension_means_no_extra_rules(tmp_path):
    from stubcampaign import make
    assert failures.rules_for(make(tmp_path)) == ()
