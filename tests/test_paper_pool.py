"""The shared pool reuses sources and extracts PDFs only after exhausting LaTeX availability."""
from concurrent.futures import ThreadPoolExecutor
import json
import subprocess

import pytest

from pathfinder import library, net, paper_source, transport
from stubcampaign import make
from test_paper_source import EPRINT, S2, Q_SOURCE, P_SOURCE, online, pdf, needs_pdftotext


def test_latex_in_another_pool_beats_cached_pdf_text(tmp_path, online):
    primary, legacy = tmp_path / "pool", tmp_path / "legacy"
    primary.mkdir(); legacy.mkdir()
    (primary / "2401.00001.txt").write_text("extracted")
    (primary / "2401.00001.source.json").write_text('{"latex_unavailable": true}')
    source = legacy / "2401.00001.tex"
    source.write_text("source")
    n = online({})
    assert paper_source.get("2401.00001", primary, [legacy], net.urlopen) == source
    assert n.calls == []


def test_legacy_extraction_does_not_hide_available_latex(tmp_path, online, monkeypatch):
    (tmp_path / "2401.00001.txt").write_text("old PDF extraction")
    n = online({EPRINT + "2401.00001": Q_SOURCE})
    monkeypatch.setattr(paper_source.shutil, "which", lambda _: None)
    monkeypatch.setattr(paper_source.subprocess, "run", lambda *a, **k: pytest.fail("must not extract PDF"))
    result = paper_source.get("2401.00001", tmp_path, urlopen=net.urlopen)
    assert result.suffix == ".tex" and "Theorem of Q" in result.read_text()
    assert (tmp_path / "2401.00001.txt").read_text() == "old PDF extraction"
    assert n.calls == [EPRINT + "2401.00001"]


def test_failed_latex_flattener_uses_source_inlining_not_pdf(tmp_path, online, monkeypatch):
    n = online({EPRINT + "2401.00001": Q_SOURCE})
    monkeypatch.setattr(paper_source.shutil, "which", lambda _: "latexpand")

    def failed(cmd, **kwargs):
        assert cmd[0] == "latexpand"
        raise subprocess.TimeoutExpired(cmd, 120)

    monkeypatch.setattr(paper_source.subprocess, "run", failed)
    result = paper_source.get("2401.00001", tmp_path, urlopen=net.urlopen)
    assert result.suffix == ".tex" and "Theorem of Q" in result.read_text()
    assert n.calls == [EPRINT + "2401.00001"]


def test_transient_source_failure_does_not_trigger_pdf(tmp_path, online):
    import urllib.error
    n = online({})

    def unavailable(*args, **kwargs):
        raise urllib.error.HTTPError(EPRINT, 503, "try later", {}, None)

    with pytest.raises(urllib.error.HTTPError):
        paper_source.get("2401.00001", tmp_path, urlopen=unavailable)
    assert n.calls == [] and not list(tmp_path.glob("*.txt"))


@needs_pdftotext
def test_concurrent_requests_share_one_pdf_download_and_extraction(tmp_path, online, monkeypatch):
    url = "https://example.org/paper.pdf"
    n = online({S2 + "search/match": {"data": [{"title": "Journal paper", "externalIds": {"DOI": "10.1234/test"},
                                               "openAccessPdf": {"url": url}}]}, url: pdf("Only PDF available")})
    real, conversions = paper_source.subprocess.run, []

    def counted(cmd, **kwargs):
        conversions.append(cmd[0])
        return real(cmd, **kwargs)

    monkeypatch.setattr(paper_source.subprocess, "run", counted)
    with ThreadPoolExecutor(max_workers=6) as pool:
        paths = list(pool.map(lambda _: paper_source.resolve("title:Journal paper", tmp_path, urlopen=net.urlopen), range(6)))
    assert len(set(paths)) == 1 and "Only PDF available" in paths[0].read_text()
    assert n.calls.count(url) == 1 and conversions == ["pdftotext"]
    assert paths[0].with_suffix(".pdf").read_bytes() == pdf("Only PDF available")
    before = len(n.calls)
    assert paper_source.resolve("doi:10.1234/test", tmp_path, urlopen=net.urlopen) == paths[0]
    assert paper_source.resolve(url, tmp_path, urlopen=net.urlopen) == paths[0]
    assert len(n.calls) == before


def test_concurrent_arxiv_requests_share_source_download(tmp_path, online, monkeypatch):
    n = online({EPRINT + "2401.00001": Q_SOURCE})
    monkeypatch.setattr(paper_source.shutil, "which", lambda _: None)
    with ThreadPoolExecutor(max_workers=6) as pool:
        paths = list(pool.map(lambda _: paper_source.get("2401.00001", tmp_path, urlopen=net.urlopen), range(6)))
    assert len(set(paths)) == 1 and n.calls == [EPRINT + "2401.00001"]


def test_pdf_alias_from_old_cache_is_resolved_to_latex(tmp_path, online, monkeypatch):
    old = tmp_path / "old.txt"; old.write_text("old extraction")
    (tmp_path / "aliases.jsonl").write_text(json.dumps({"ref": "doi:10.1234/test", "path": "old.txt", "found": True}) + "\n")
    n = online({S2 + "DOI:10.1234/test": {"externalIds": {"ArXiv": "2401.00001"}}, EPRINT + "2401.00001": Q_SOURCE})
    monkeypatch.setattr(paper_source.shutil, "which", lambda _: None)
    result = paper_source.resolve("10.1234/test", tmp_path, urlopen=net.urlopen)
    assert result.suffix == ".tex" and len(n.calls) == 2
    assert old.read_text() == "old extraction"


def test_corpus_text_override_cannot_hide_pooled_latex(tmp_path):
    c = make(tmp_path)
    pool = library.cache(c); pool.mkdir()
    source = pool / "2401.00001.tex"; source.write_text("source")
    (tmp_path / "old.txt").write_text("extraction")
    assert library.paper_text(c, {"id": "2401.00001", "text": "old.txt"}) == source


def test_default_pool_is_shared_across_campaigns(tmp_path, monkeypatch):
    a, b = make(tmp_path / "a"), make(tmp_path / "b")
    a.raw.pop("source_cache"); b.raw.pop("source_cache")
    assert library.cache(a) == library.cache(b)
    monkeypatch.delenv("PATHFINDER_SOURCE_CACHE")
    assert library.cache(a) == library.cache(b) == paper_source.Path.home() / ".cache/pathfinder/papers"


@pytest.mark.parametrize("stage,tools,reads", [("peer", True, False), ("edit", True, False),
    ("author", True, False), ("verify", False, False), ("present_lookup", True, True), ("pce-critic", False, False)])
def test_every_agent_gets_pool_rule_without_extra_permissions(tmp_path, monkeypatch, stage, tools, reads):
    c = make(tmp_path)
    captured = []
    monkeypatch.setattr(transport, "_attempt", lambda campaign, request: captured.append(request) or {"text": "ok"})
    transport.call("Task", campaign=c, model=c.model, tools=tools, reads=reads, search=False, cwd=tmp_path,
                   timeout=1, thread="Q1P1", stage=stage, actor="agent")
    r = captured[0]
    assert library.POOL_RULE in r.prompt and r.prompt.endswith("Task")
    assert (r.tools, r.reads) == (tools, reads)
    assert ("Run:" in r.prompt) == (tools and not reads)
