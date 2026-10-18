"""Papers as LaTeX, fetched before research, through one shared cache (nobel, 18 October 2026). Peers downloaded
about 6000 PDFs (arXiv and publishers) and ran pdftotext inside their own calls: garbled mathematics, repeated
downloads, and retrieval spent from the peers' allowances. Now every thread opens with the LaTeX of its two
papers, of the papers their bibliographies name and of the papers citing both, fetched by the engine into the
shared cache with an index (inputs/library.jsonl); an agent asks the thread's copy of pathfinder.paper_source for
any other paper by arXiv id, DOI, URL or title and gets the LaTeX of its arXiv version, else the text of one open
PDF, each fetched once and kept for everyone, with every resolution recorded."""
import io, json, shutil, subprocess, sys, tarfile, urllib.error
from pathlib import Path
import pytest
from pathfinder import cli, composable, gc, health, library, net, paper_source, playbook, research, runner, sandbox, thread, transport
from stubcampaign import make

needs_pdftotext = pytest.mark.skipif(not shutil.which("pdftotext"), reason="pdftotext not installed")


def tarball(files: dict) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, text in files.items():
            data = text.encode(); info = tarfile.TarInfo(name); info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def pdf(text: str) -> bytes:
    """A one-page PDF holding `text`, enough for pdftotext."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out)); out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offsets)
    return out + b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)


class Net:
    """The network as a table, url prefix -> bytes or a JSON value; every request is recorded."""
    def __init__(self, table):
        self.table, self.calls = table, []

    def __call__(self, request, timeout=None):
        url = request.full_url if hasattr(request, "full_url") else request
        self.calls.append(url)
        for prefix, value in self.table.items():
            if url.startswith(prefix):
                blob = value if isinstance(value, bytes) else json.dumps(value).encode()
                return _Reply(blob)
        raise urllib.error.HTTPError(url, 404, "not found", {}, None)


class _Reply:
    def __init__(self, blob):
        self.blob, self.headers = blob, {"Content-Type": "application/pdf" if blob[:4] == b"%PDF" else "application/x-tar"}

    def read(self):
        return self.blob

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


EPRINT = "https://arxiv.org/e-print/"
S2 = "https://api.semanticscholar.org/graph/v1/paper/"
Q_SOURCE = tarball({"main.tex": "\\documentclass{article}\\begin{document}\\input{body}\\end{document}\n",
                    "body.tex": "Theorem of Q.\n",
                    "main.bbl": "\\bibitem{a} A. Author, arXiv:2301.00007.\n\\bibitem{b} B. Author, J. Phys. 10.1103/PhysRev.1.1.\n"})
P_SOURCE = tarball({"p.tex": "\\documentclass{article}\\begin{document}Lemma of P \\cite{x}.\\end{document}\n",
                    "refs.bib": "@article{x, eprint = {2301.00007}}\n"})


@pytest.fixture
def online(monkeypatch):
    """The network, from the moment a test gives it its table."""
    monkeypatch.setattr(paper_source, "_wait_turn", lambda *a, **k: None)
    def use(table):
        monkeypatch.delenv("PATHFINDER_OFFLINE", raising=False)
        n = Net(table)
        monkeypatch.setattr(net, "urlopen", n)
        return n
    return use


def _campaign(tmp_path, **kw):
    c = make(tmp_path, **kw)
    for side, aid in (("Q", "2401.00001"), ("P", "2402.00002")):
        (c.root / f"{side}.jsonl").write_text(json.dumps({"id": aid, "title": f"{side} paper", "abstract": f"About {side}.",
                                                          "authors": [f"{side} Author"]}) + "\n")
    return c


# ---- flattening

def test_a_latex_eprint_is_never_read_from_its_pdf(tmp_path, online, monkeypatch):
    monkeypatch.setattr(paper_source.shutil, "which", lambda name: None)       # no latexpand: the plain inlining
    online({EPRINT + "2401.00001": Q_SOURCE})
    path = paper_source.get("2401.00001", tmp_path, urlopen=net.urlopen)
    assert path.suffix == ".tex" and "Theorem of Q." in path.read_text() and "\\input" not in path.read_text()


def test_an_eprint_without_latex_is_an_error_not_a_pdf_fallback(tmp_path, online):
    n = online({EPRINT + "2401.00001": tarball({"notes.txt": "no tex here"})})
    with pytest.raises(RuntimeError, match="no .tex"):
        paper_source.get("2401.00001", tmp_path, urlopen=net.urlopen)
    assert not [u for u in n.calls if "/pdf/" in u]


@needs_pdftotext
def test_a_pdf_only_submission_becomes_text_once(tmp_path, online):
    n = online({EPRINT + "2401.00001": pdf("Only a PDF")})
    first = paper_source.get("2401.00001", tmp_path, urlopen=net.urlopen)
    assert first.suffix == ".txt" and "Only a PDF" in first.read_text()
    assert paper_source.get("2401.00001", tmp_path, urlopen=net.urlopen) == first and len(n.calls) == 1


def test_a_source_keeps_the_arxiv_ids_and_dois_its_bibliography_names(tmp_path, online):
    online({EPRINT + "2401.00001": Q_SOURCE})
    path = paper_source.get("2401.00001", tmp_path, urlopen=net.urlopen)
    assert paper_source.references(path) == ["2301.00007", "doi:10.1103/PhysRev.1.1"]
    index = [json.loads(l) for l in (tmp_path / "index.jsonl").read_text().splitlines()]
    assert index[0]["id"] == "2401.00001" and index[0]["kind"] == "tex"


def test_offline_a_miss_is_an_error(tmp_path):
    with pytest.raises(RuntimeError, match="downloads are off"):
        paper_source.get("2401.00001", tmp_path)


# ---- any reference

def test_a_doi_is_served_as_the_latex_of_its_arxiv_version_and_remembered(tmp_path, online):
    n = online({S2 + "DOI:10.1103/PRXQuantum.3.010318": {"externalIds": {"ArXiv": "2102.11340"}, "title": "Lin and Tong"},
                EPRINT + "2102.11340": Q_SOURCE})
    path = paper_source.resolve("https://doi.org/10.1103/PRXQuantum.3.010318", tmp_path, urlopen=net.urlopen)
    assert path.name == "2102.11340.tex"
    calls = len(n.calls)
    assert paper_source.resolve("doi:10.1103/prxquantum.3.010318", tmp_path, urlopen=net.urlopen) == path
    assert len(n.calls) == calls                                 # asked again by the same DOI: a hit
    alias = json.loads((tmp_path / "aliases.jsonl").read_text().splitlines()[-1])
    assert alias["arxiv"] == "2102.11340" and alias["ref"] == "doi:10.1103/prxquantum.3.010318"


@needs_pdftotext
def test_a_paper_not_on_arxiv_is_its_open_pdf_as_text_fetched_once(tmp_path, online):
    n = online({S2 + "search/match": {"data": [{"externalIds": {}, "title": "A journal paper",
                                                "openAccessPdf": {"url": "https://example.org/paper.pdf"}}]},
                "https://example.org/paper.pdf": pdf("Journal text")})
    path = paper_source.resolve("title:A journal paper", tmp_path, urlopen=net.urlopen)
    assert path.parent.name == "other" and "Journal text" in path.read_text()
    calls = len(n.calls)
    assert paper_source.resolve("title:A journal paper", tmp_path, urlopen=net.urlopen) == path and len(n.calls) == calls


def test_a_reference_not_found_is_not_asked_again_for_a_week(tmp_path, online):
    n = online({})
    with pytest.raises(RuntimeError, match="no open PDF"):
        paper_source.resolve("10.9999/nowhere", tmp_path, urlopen=net.urlopen)
    calls = len(n.calls)
    with pytest.raises(RuntimeError, match="no open version found"):
        paper_source.resolve("10.9999/nowhere", tmp_path, urlopen=net.urlopen)
    assert len(n.calls) == calls


# ---- before research

def test_a_thread_opens_with_its_papers_and_library_fetched_by_the_engine(tmp_path, online):
    c = _campaign(tmp_path, novelty_citers="citers/{pair}.md")
    (c.root / "citers").mkdir(); (c.root / "citers" / "Q1P1.md").write_text("- Both at once (arXiv:2305.00009)\n")
    online({EPRINT + "2401.00001": Q_SOURCE, EPRINT + "2402.00002": P_SOURCE,
            EPRINT + "2301.00007": P_SOURCE, EPRINT + "2305.00009": P_SOURCE,
            S2 + "DOI:10.1103/PhysRev.1.1": {"externalIds": {"ArXiv": "2310.00011"}}, EPRINT + "2310.00011": P_SOURCE})
    d = thread.prepare(c, "Q1P1")
    assert "Theorem of Q." in (d / "inputs" / "Q.tex").read_text() and (d / "inputs" / "P.tex").exists()
    lib = [json.loads(l) for l in (d / "inputs" / "library.jsonl").read_text().splitlines()]
    assert [e["id"] for e in lib] == ["2305.00009", "2301.00007", "doi:10.1103/PhysRev.1.1"]
    assert lib[0]["why"] == ["cites both papers"] and lib[1]["why"] == ["cited by Q", "cited by P"]
    assert all(Path(e["path"]).is_file() for e in lib)
    assert (c.root / "sources" / "2301.00007.tex").exists()       # the shared cache, not the thread


def test_peers_get_the_reading_rule_the_library_and_the_helper(tmp_path, online, monkeypatch):
    c = _campaign(tmp_path)
    online({EPRINT + "2401.00001": Q_SOURCE, EPRINT + "2402.00002": P_SOURCE, EPRINT + "2301.00007": P_SOURCE})
    seen, real = [], transport.execute
    monkeypatch.setattr(transport, "execute", lambda campaign, request: seen.append(request) or real(campaign, request))
    research.run_thread(c, "Q1P1")
    peer = " ".join([r for r in seen if r.stage == "peer"][0].prompt.split())
    assert "do not download a PDF" in peer and "2301.00007" in peer and ".pathfinder/paper_source.py --cache" in peer
    assert (c.thread_dir("Q1P1") / ".pathfinder" / "paper_source.py").read_bytes() == Path(paper_source.__file__).read_bytes()


def test_the_helper_answers_a_hit_from_the_cache_as_a_script(tmp_path):
    (tmp_path / "2301.00007.tex").write_text("cached")
    r = subprocess.run([sys.executable, "-I", paper_source.__file__, "--cache", str(tmp_path), "arXiv:2301.00007", "bogus"],
                       capture_output=True, text=True, env={"PATHFINDER_OFFLINE": "1"})
    assert r.returncode == 1 and f"arXiv:2301.00007 {tmp_path / '2301.00007.tex'}" in r.stdout and "bogus ERROR" in r.stdout


def test_prefetch_fills_the_cache_for_the_shortlist_before_research(tmp_path, online, capsys):
    c = _campaign(tmp_path)
    online({EPRINT + "2401.00001": Q_SOURCE, EPRINT + "2402.00002": P_SOURCE, EPRINT + "2301.00007": P_SOURCE})
    cli.main(["--root", str(c.root), "prefetch"])
    assert "1 pairs" in capsys.readouterr().out and (c.root / "sources" / "2301.00007.tex").exists()
    assert not c.thread_dir("Q1P1").exists()


def test_the_cache_can_live_outside_the_campaign(tmp_path, online):
    c = _campaign(tmp_path / "c", source_cache=str(tmp_path / "arxiv-cache"))
    online({EPRINT + "2401.00001": Q_SOURCE, EPRINT + "2402.00002": P_SOURCE, EPRINT + "2301.00007": P_SOURCE})
    d = thread.prepare(c, "Q1P1")
    assert (tmp_path / "arxiv-cache" / "2401.00001.tex").exists()
    assert json.loads((d / "inputs" / "Q.json").read_text())["text"] == str((tmp_path / "arxiv-cache" / "2401.00001.tex").resolve())


# ---- agents may write the cache

def test_calls_with_tools_may_write_the_cache_and_no_other_outside_directory(tmp_path):
    c = make(tmp_path, backend="codex", source_cache=str(tmp_path / "cache"))
    cmd = transport._command(c, "m", True, True, tmp_path / "t")
    assert cmd[cmd.index("--add-dir") + 1] == str((tmp_path / "cache").resolve())
    assert "--add-dir" not in transport._command(c, "m", False, False, tmp_path / "t")
    c.backend = "claude"
    cmd = transport._command(c, "m", True, False, tmp_path / "t")
    assert cmd[cmd.index("--add-dir") + 1] == str((tmp_path / "cache").resolve())
    args = " ".join(sandbox.args(tmp_path / "t", True, True, cache=tmp_path / "cache"))
    assert f'"{(tmp_path / "cache").resolve()}" = "write"' in args or f"'{(tmp_path / 'cache').resolve()}'" in args or str((tmp_path / "cache").resolve()) in args


# ---- threads opened before

def _abstract_thread(tmp_path):
    c = _campaign(tmp_path)
    d = thread.prepare(c, "Q1P1")                                # offline: abstracts, an empty library
    (d / "inputs" / "library.jsonl").unlink()
    return c, d


def test_health_and_the_playbook_name_threads_without_their_sources(tmp_path):
    c, d = _abstract_thread(tmp_path)
    snap = health.snapshot(c)
    assert snap["sources"] == {"abstract_only": ["Q1P1"], "no_library": ["Q1P1"]}
    assert any("without their fetched sources" in a["action"] and a["command"].endswith("sources Q1P1 --into-inputs")
               for a in playbook.next_actions(c))


def test_sources_into_inputs_adds_the_full_text_beside_the_abstract(tmp_path, online, capsys):
    c, d = _abstract_thread(tmp_path)
    online({EPRINT + "2401.00001": Q_SOURCE, EPRINT + "2402.00002": P_SOURCE, EPRINT + "2301.00007": P_SOURCE})
    cli.main(["--root", str(c.root), "sources", "Q1P1", "--into-inputs"])
    names = sorted(p.name for p in (d / "inputs").iterdir())
    assert {"Q.txt", "Q.tex", "P.txt", "P.tex", "library.jsonl", "added.json"} <= set(names)
    assert thread._inputs(d) == {"Q": "Q.tex", "P": "P.tex"}
    assert health.snapshot(c)["sources"] == {"abstract_only": [], "no_library": []}


def test_sources_into_inputs_waits_for_a_running_thread(tmp_path, monkeypatch):
    c, d = _abstract_thread(tmp_path)
    monkeypatch.setattr(runner.Lock, "holder", staticmethod(lambda d: {"pid": 1}))
    with pytest.raises(SystemExit, match="running process"):
        library.add_to_inputs(c, "Q1P1")


# ---- collection

def test_collection_removes_downloaded_papers_from_agent_folders_only(tmp_path):
    c = make(tmp_path)
    research.run_thread(c, "Q1P1")
    from pathfinder import edit
    assert edit.run(c, "Q1P1") == "done"
    d = c.thread_dir("Q1P1")
    (d / "ada" / "2301.00007.pdf").write_bytes(b"%PDF-1.4 downloaded")
    (d / "ada" / "lin-tong.txt").write_text("page one\fpage two\fpage three")
    (d / "ada" / "derivation.tex").write_text("mine"); (d / "ada" / "derivation.pdf").write_bytes(b"%PDF built")
    (d / "ada" / "cited.pdf").write_bytes(b"%PDF cited")
    (d / "ada" / "notes.txt").write_text("my own notes")
    from pathfinder.ledger import Ledger
    Ledger(d / "ledger.jsonl").add("ada", "finding", "see ada/cited.pdf")
    gc.collect_thread(c, "Q1P1")
    left = {p.name for p in (d / "ada").iterdir()}
    assert {"derivation.tex", "derivation.pdf", "cited.pdf", "notes.txt"} <= left
    assert not {"2301.00007.pdf", "lin-tong.txt"} & left
    assert (d / "edited" / "note.pdf").exists() or not (d / "edited" / "note.tex").exists()


def test_collection_prunes_a_frozen_bundle_and_the_bundle_still_verifies(tmp_path):
    c = make(tmp_path, research_scheme="composable", branches=1)
    research.run_thread(c, "Q1P1")
    from pathfinder import edit
    assert edit.run(c, "Q1P1") == "done"
    bundle = c.thread_dir("Q1P1") / "branches" / "branch-1"
    composable.verify(bundle)
    (bundle / "ada").mkdir(exist_ok=True)
    download = bundle / "ada" / "paper.pdf"
    # a download frozen into the bundle: rebuild the bundle's record as the freeze would have written it
    download.write_bytes(b"%PDF downloaded")
    record = json.loads((bundle / "bundle.json").read_text())
    record["files"]["ada/paper.pdf"] = {"sha256": composable._sha(download), "bytes": download.stat().st_size}
    record["inventory_sha256"] = composable._inventory_sha(record["files"])
    (bundle / "bundle.json").chmod(0o644); (bundle / "bundle.json").write_text(json.dumps(record))
    composable.verify(bundle)
    gc.collect_thread(c, "Q1P1")
    assert not download.exists()
    assert json.loads((c.thread_dir("Q1P1") / "branches-pruned.json").read_text()) == {"branch-1": ["ada/paper.pdf"]}
    composable.verify(bundle)


@pytest.mark.parametrize("key, value", [("source_cache", ""), ("prefetch_limit", -1)])
def test_bad_source_settings_are_refused(tmp_path, key, value):
    with pytest.raises(ValueError, match=key):
        make(tmp_path, **{key: value})
