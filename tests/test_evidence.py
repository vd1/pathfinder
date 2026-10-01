import pytest
from pathfinder import evidence


@pytest.mark.parametrize("token,kind", [
    ("ada/run.py", "file"), ("branches/b1/ada/out.json", "file"), ("inputs/Q.tex", "file"),
    ("prose/p.1653", "locator"), ("Eq.1/p.1645", "locator"), ("ada/Fig.3", "locator"), ("sec/Table.2", "locator"),
    ("0.147008/0.707625", "number"), ("1.006/0.994", "number"),
    ("10.1103/PhysRevB.1.2", "doi"), ("chemle/emle-engine.git", "repository"),
])
def test_classify(token, kind):
    assert evidence.classify(token) == kind


def test_cited_files_keeps_only_files_and_skips_urls():
    text = ("see ada/run.py and https://x.org/data/a.json, eq. prose/p.1653, ratio 0.147008/0.707625, "
            "doi 10.1103/PhysRevB.1.2, repo chemle/emle-engine.git, and ada/run.py again")
    assert evidence.cited_files(text) == ["ada/run.py"]


def test_research_uses_typed_citations():
    from pathfinder import research
    assert research._evidence_references("prose/p.1653 and emmy/derivation.tex") == ["emmy/derivation.tex"]


from pathlib import Path


def _tree(tmp_path, files):
    for name in files:
        p = tmp_path / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(name)
    return tmp_path


def test_resolution_order_and_ambiguity(tmp_path):
    d = _tree(tmp_path, ["ada/local.json", "branches/b1/ada/one.json", "branches/b1/ada/two.json", "branches/b2/ada/two.json"])
    bundles = ["branches/b1", "branches/b2"]
    assert evidence.resolve(d, "ada/local.json", bundles, {}).kind == "local"
    one = evidence.resolve(d, "ada/one.json", bundles, {})
    assert one.kind == "namespace" and one.path == d / "branches/b1/ada/one.json"
    two = evidence.resolve(d, "ada/two.json", bundles, {})
    assert two.kind == "ambiguous" and two.candidates == ("branches/b1/ada/two.json", "branches/b2/ada/two.json")
    assert evidence.resolve(d, "ada/none.json", bundles, {}).kind == "missing"


def test_registered_sources_resolve_by_their_own_bytes(tmp_path):
    import json, sys
    sys.path.insert(0, str(Path(__file__).parent))
    from stubcampaign import make
    c = make(tmp_path)
    raw = tmp_path / "sources" / "P001" / "raw.json"; raw.parent.mkdir(parents=True); raw.write_text("{}")
    rows = [json.loads(l) for l in c.path("P.jsonl").read_text().splitlines()]
    rows[0]["raw"] = "sources/P001/raw.json"
    c.path("P.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    sources = evidence.registered_sources(c, "Q1P1")
    d = c.thread_dir("Q1P1"); d.mkdir(parents=True)
    got = evidence.resolve(d, "sources/P001/raw.json", [], sources)
    assert got.kind == "source" and got.path == raw
    assert evidence.resolve(d, "sources/P002/raw.json", [], sources).kind == "missing"


def test_strict_review_reads_a_namespaced_file_instead_of_blocking(tmp_path):
    from pathfinder import research
    from stubcampaign import make
    c = make(tmp_path, research_scheme="eva_minus", strict_evidence=True, research_bundles=["branches/b1"])
    d = research.prepare(c, "Q1P1")
    _tree(d, ["branches/b1/ledger.jsonl", "branches/b1/ada/audit.json"])
    (d / "branches/b1/ledger.jsonl").write_text("")
    from pathfinder.ledger import Ledger
    Ledger(d / "ledger.jsonl").add("ada", "finding", "see ada/audit.json")
    material = research._review_material(c, "Q1P1")
    assert "branches/b1/ada/audit.json" in material


def test_all_strict_errors_are_reported_together(tmp_path):
    from pathfinder import research
    from pathfinder.ledger import Ledger
    from stubcampaign import make
    c = make(tmp_path, research_scheme="eva_minus", strict_evidence=True)
    d = research.prepare(c, "Q1P1")
    Ledger(d / "ledger.jsonl").add("ada", "finding", "see ada/one.json and ada/two.json")
    with pytest.raises(research.EvidenceUnavailable) as raised:
        research._review_material(c, "Q1P1")
    error = raised.value
    assert isinstance(error, evidence.EvidenceError)
    assert [e["path"] for e in error.errors] == ["ada/one.json", "ada/two.json"]
    assert all(e["code"] == "missing" for e in error.errors)
    assert str(error).startswith("missing evidence: ada/one.json") and "and 1 more" in str(error)


def test_a_declared_output_that_does_not_exist_is_a_gap(tmp_path):
    import hashlib, json
    from pathfinder import research
    from pathfinder.ledger import Ledger
    from stubcampaign import make
    c = make(tmp_path, research_scheme="eva_minus", strict_evidence=True)
    d = research.prepare(c, "Q1P1")
    text = "the script ada/audit.py writes ada/coverage.json"
    (d / "ada" / "audit.py").write_text("print(1)")
    seq = Ledger(d / "ledger.jsonl").add("ada", "finding", text)
    (d / "external-references.json").write_text(json.dumps({"version": 1, "references": [
        {"document": "ledger.jsonl", "ledger_seq": seq, "path": "ada/coverage.json", "status": "output",
         "text_sha256": hashlib.sha256(text.encode()).hexdigest()}]}))
    material = research._review_material(c, "Q1P1")
    assert "declared planned output" in material and "ada/coverage.json" in material


def test_manifest_and_proposals(tmp_path, capsys):
    import json
    from pathfinder import cli, research
    from pathfinder.ledger import Ledger
    from stubcampaign import make
    c = make(tmp_path, research_scheme="eva_minus", strict_evidence=True)
    d = research.prepare(c, "Q1P1")
    (d / "ada" / "run.py").write_text("print(1)")
    Ledger(d / "ledger.jsonl").add("ada", "finding", "ran ada/run.py, see ada/missing.json")
    m = evidence.manifest(c, "Q1P1")
    kinds = {f["path"]: f["kind"] for f in m["files"]}
    assert kinds["ada/run.py"] == "local" and kinds["ada/missing.json"] == "missing"
    assert m["errors"][0]["code"] == "missing"
    assert json.loads((d / "evidence-manifest.json").read_text())["files"] == m["files"]
    p = evidence.proposals(m, c.thread_dir("Q1P1"))[0]
    assert p["path"] == "ada/missing.json" and p["ledger_seq"] == 1 and len(p["text_sha256"]) == 64
    assert cli.main(["--root", str(tmp_path), "evidence", "Q1P1", "--json"]) in (0, None)
    assert json.loads(capsys.readouterr().out)["errors"][0]["path"] == "ada/missing.json"
