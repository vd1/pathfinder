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
