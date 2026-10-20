import json
import pytest
from pathfinder import notation_continuation as n, pce, presentation

SOURCE = r"""The residual \(R\) is defined by
\[
R=x-RT.
\]
The gas constant is \(R\). Compare \(R+C\) with \(R\).
"""


def fixture(tmp_path):
    pd = tmp_path
    d = pd / "presentation"
    (d / "correct-2").mkdir(parents=True)
    (d / "pass").mkdir()
    check = {"findings": [{"kind": "unclear", "where": '"The residual R"'}]}
    review = {"asked": [{"id": "C1", "issue": "Residual and gas constant share a symbol."}],
              "answers": [{"id": "C1", "decision": "presentation", "reason": "Consistent notation only."}]}
    paths = {"source_sha256": (d / "correct-2/paper.tex", SOURCE),
             "accepted_sha256": (pd / "paper.tex", SOURCE),
             "bibliography_sha256": (pd / "references.bib", ""),
             "check_sha256": (d / "correct-2/check.json", json.dumps(check)),
             "review_sha256": (d / "pass/claims.json", json.dumps(review))}
    p = dict(version=2, kind="reviewed-alpha-rename", stage="correct-2", review="pass/claims.json",
             review_id="C1", review_reason="Consistent notation only.", where='"The residual R"',
             old="R", new=r"\Delta_{\mathrm{res}}", state_sha256="bound-by-account-present")
    for key, (path, text) in paths.items():
        path.write_text(text)
        p[key] = n.digest(text)
    p["occurrences"] = [{"offset": i, "action": "preserve" if SOURCE[:i].endswith("constant is \\(") else "rename",
                         "meaning": "gas constant" if SOURCE[:i].endswith("constant is \\(") else "residual"}
                        for i in n.occurrences(SOURCE, "R")]
    target = SOURCE
    for row in reversed(p["occurrences"]):
        if row["action"] == "rename":
            i = row["offset"]
            target = target[:i] + p["new"] + target[i + 1:]
    p["target_sha256"] = n.digest(target)
    return pd, p, target


def test_exact_rename_projection_preserves_gas_constant_and_guard(tmp_path):
    pd, p, target = fixture(tmp_path)
    n.validate(pd, p)
    assert "-RT" in target and r"constant is \(R\)" in target
    assert n.projected_correction(SOURCE, target, "", p) == SOURCE
    assert presentation.guard(SOURCE, target, SOURCE, "")  # no generic guard exception
    assert not presentation.guard(SOURCE, n.projected_correction(SOURCE, target, "", p), SOURCE, "")


@pytest.mark.parametrize("damage", [None, "source", "result", "context", "pointer"])
def test_completed_notation_pause_requires_bound_terminal_evidence(tmp_path, damage):
    from pathfinder.account_present import _completed_notation_pause
    pd, context, target = fixture(tmp_path)
    root = pd / "presentation-continuations" / "rename"
    root.mkdir(parents=True)
    stage = pd / "presentation" / "correct-3"
    stage.mkdir()
    (stage / "paper.tex").write_text(target)
    state = {"state": "PAUSE-ON-PRESENT", "stage": "correct-3",
             "reason": "reviewed notation cycle not cleared: unclear"}
    result = {"state": "PAUSE-ON-PRESENT", "presentation": dict(state)}
    if damage == "source":
        (stage / "paper.tex").write_text(target + "\nUnrelated edit.")
    elif damage == "result":
        result["presentation"]["stage"] = "correct-4"
    elif damage == "context":
        context["review_sha256"] = "changed"
    (root / "grant.json").write_text(json.dumps(
        {"request": {"context": context}, "cycle_limit": 3}))
    (root / "result.json").write_text(json.dumps(result))
    (pd / "presentation-continuation.json").write_text(json.dumps(
        {"id": "../rename" if damage == "pointer" else "rename"}))
    assert _completed_notation_pause(pd, state) == (damage is None)


@pytest.mark.parametrize("change", [
    lambda s: s + "\nAn unrelated result.",
    lambda s: s.replace("-RT", "+RT"),
    lambda s: s.replace("-RT", "-2RT"),
    lambda s: s.replace(r"constant is \(R\)", r"constant is \(Q\)"),
    lambda s: SOURCE,
])
def test_extra_or_missing_changes_refused(tmp_path, change):
    _, p, target = fixture(tmp_path)
    with pytest.raises(pce.Changed, match="exact granted rename"):
        n.projected_correction(SOURCE, change(target), "", p)


def test_bibliography_change_refused(tmp_path):
    _, p, target = fixture(tmp_path)
    with pytest.raises(pce.Changed, match="bibliography"):
        n.projected_correction(SOURCE, target, "changed year", p)


@pytest.mark.parametrize("mutate", [
    lambda p: p["occurrences"].pop(),
    lambda p: p["occurrences"].append(p["occurrences"][0]),
    lambda p: p["occurrences"][0].update(offset=0),
    lambda p: p.update(new=r"\Delta+1"),
    lambda p: p.update(new=r"\mathrm"),
    lambda p: p.update(target_sha256="wrong"),
])
def test_invalid_or_incomplete_inventory_refused(tmp_path, mutate):
    pd, p, _ = fixture(tmp_path)
    mutate(p)
    with pytest.raises(pce.Changed):
        n.validate(pd, p)


@pytest.mark.parametrize("key", ["source_sha256", "accepted_sha256", "bibliography_sha256",
                                  "check_sha256", "review_sha256"])
def test_provenance_hashes_required(tmp_path, key):
    pd, p, _ = fixture(tmp_path)
    p[key] = "changed"
    with pytest.raises(pce.Changed, match="provenance"):
        n.validate(pd, p)


def test_review_must_be_exact_presentation_disposition(tmp_path):
    pd, p, _ = fixture(tmp_path)
    path = pd / "presentation/pass/claims.json"
    review = json.loads(path.read_text())
    review["answers"][0]["decision"] = "confirmed"
    path.write_text(json.dumps(review))
    p["review_sha256"] = n.digest(path.read_text())
    with pytest.raises(pce.Changed, match="presentation-only"):
        n.validate(pd, p)
