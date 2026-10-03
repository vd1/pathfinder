import json, threading, urllib.error, urllib.request
import pytest
from pathfinder import view
from stubcampaign import make


@pytest.fixture
def server(tmp_path):
    c = make(tmp_path)
    d = c.thread_dir("Q1P1") / "edited"; d.mkdir(parents=True)
    (d / "note.pdf").write_bytes(b"%PDF-1.4 fake"); (d / "note.tex").write_text("\\section{x}")
    srv = view.make_server(c, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv, srv.server_address[1]
    srv.shutdown()


def get(port, path, headers=None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", headers=headers or {})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def test_page_script_and_style_are_served_with_a_strict_policy(server):
    _, port = server
    status, headers, body = get(port, "/")
    assert status == 200 and b'src="view.js"' in body and b"<script>" not in body
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert get(port, "/view.js")[0] == 200 and get(port, "/view.css")[0] == 200


def test_state_endpoint_returns_the_state_document(server):
    _, port = server
    status, _, body = get(port, "/api/state")
    doc = json.loads(body)
    assert status == 200 and doc["units"][0]["unit"] == "Q1P1"
    assert doc["units"][0]["documents"][0]["pdf"] == "threads/Q1P1/edited/note.pdf"


def test_pdf_is_inline_and_framable_by_self_only(server):
    _, port = server
    status, headers, body = get(port, "/doc?path=threads/Q1P1/edited/note.pdf")
    assert status == 200 and body.startswith(b"%PDF") and headers["Content-Type"] == "application/pdf"
    assert headers["Content-Security-Policy"] == "frame-ancestors 'self'"
    status, headers, body = get(port, "/doc?path=threads/Q1P1/edited/note.tex")
    assert status == 200 and headers["Content-Type"].startswith("text/plain") and body == b"\\section{x}"


def test_foreign_host_origin_and_paths_are_refused(server):
    _, port = server
    assert get(port, "/api/state", {"Host": "evil.example"})[0] == 403
    assert get(port, "/api/state", {"Origin": "http://evil.example"})[0] == 403
    assert get(port, "/doc?path=campaign.json")[0] == 404
    assert get(port, "/campaign.json")[0] == 404


def test_page_has_the_operator_sections_and_valid_script(server):
    import shutil, subprocess
    from pathlib import Path
    _, port = server
    body = get(port, "/")[2].decode()
    for section in ('id="params"', 'id="pipeline"', 'id="queue-body"', 'id="research-list"', 'id="usage"',
                    'id="blocks"', 'id="detail-dialog"'):
        assert section in body
    script = Path(view.__file__).with_name("view.js")
    assert "#note=" in script.read_text() and "stale" in script.read_text()
    node = shutil.which("node")
    if node:
        assert subprocess.run([node, "--check", str(script)], capture_output=True).returncode == 0


def test_cli_has_a_view_command():
    from pathfinder import cli
    with pytest.raises(SystemExit) as done:
        cli.main(["view", "--help"])
    assert done.value.code == 0


def _harness():
    import shutil, subprocess
    from pathlib import Path
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    out = subprocess.run([node, str(Path(__file__).parent / "js" / "view_harness.js")], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


@pytest.mark.parametrize("scenario", ["hash_opens_document", "dialog_survives_refresh", "close_clears_hash",
                                      "failed_refresh_keeps_snapshot", "pipeline_counts_from_server", "escaped",
                                      "filter_select_not_rebuilt_on_refresh", "no_arxiv_link_for_local_ids", "no_null_scores", "usage_in_human_units", "arms_select_shown",
                                      "arm_switch_requests_that_arm", "panel_view", "unit_view_keeps_sections",
                                      "panel_pdf_opens_in_viewer", "unit_pdf_has_open_button",
                                      "panel_kinds_use_page_designs", "boxes_collapsible", "one_toggle_per_box"])
def test_page_scenarios(scenario):
    assert _harness()[scenario] is True


def test_monitor_file_links_for_scripts_and_tables_resolve(tmp_path):
    from pathfinder import webguard
    d = tmp_path / "threads" / "Q1P1" / "ada"; d.mkdir(parents=True)
    (d / "check.py").write_text("print(1)"); (d / "table.csv").write_text("a,b")
    assert webguard.resolve(tmp_path, "threads/Q1P1/ada/check.py").name == "check.py"
    assert webguard.resolve(tmp_path, "threads/Q1P1/ada/table.csv").name == "table.csv"


def test_a_nul_byte_in_a_document_path_is_a_404(tmp_path):
    from pathfinder import webguard
    (tmp_path / "threads" / "Q1P1").mkdir(parents=True)
    with pytest.raises(webguard.Refused) as refused:
        webguard.resolve(tmp_path, "threads/Q1P1/x\x00.pdf")
    assert refused.value.code == 404


@pytest.fixture
def arms_server(tmp_path):
    a1, a2 = make(tmp_path / "a1"), make(tmp_path / "a2", pairs=("Q1P1", "Q1P2"))
    d = a1.thread_dir("Q1P1") / "edited"; d.mkdir(parents=True); (d / "note.tex").write_text("only in a1")
    e = a2.thread_dir("Q1P2") / "edited"; e.mkdir(parents=True); (e / "note.tex").write_text("only in a2")
    srv = view.make_server({"a1": a1, "a2": a2}, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown()


def test_the_view_lists_and_selects_arms(arms_server):
    port = arms_server
    arms = json.loads(get(port, "/api/arms")[2])
    assert [a["arm"] for a in arms] == ["a1", "a2"]
    assert len(json.loads(get(port, "/api/state?arm=a2")[2])["units"]) == 2
    assert get(port, "/doc?arm=a1&path=threads/Q1P1/edited/note.tex")[2] == b"only in a1"
    assert get(port, "/doc?arm=a1&path=threads/Q1P2/edited/note.tex")[0] == 404
    assert get(port, "/api/state?arm=nope")[0] == 404


@pytest.fixture
def panel_server(tmp_path, monkeypatch):
    outside = tmp_path / "deployment" / "notes"; outside.mkdir(parents=True)
    (outside / "strategy.pdf").write_bytes(b"%PDF-1.4 fake")
    (outside / "secret.pdf").write_bytes(b"%PDF-1.4 other")
    c = make(tmp_path / "c", extensions={"path": "deploy", "panels": "pdf_panels:panels"})
    (tmp_path / "c" / "deploy").mkdir()
    (tmp_path / "c" / "deploy" / "pdf_panels.py").write_text(
        "def panels(campaign):\n"
        f"    return [{{'title': 'Research desk', 'columns': ['note'], 'rows': [[{{'text': 'note', 'pdf': {str(outside / 'strategy.pdf')!r}}}]]}}]\n")
    opened = []
    monkeypatch.setattr(view, "open_with_system", lambda path: opened.append(path))
    srv = view.make_server(c, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1], outside, opened
    srv.shutdown()


def post(port, path, body, origin=True):
    headers = {"Content-Type": "application/json"}
    if origin:
        headers["Origin"] = f"http://127.0.0.1:{port}"
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def test_a_pdf_a_panel_lists_opens_in_the_system_viewer(panel_server):
    port, outside, opened = panel_server
    assert post(port, "/open", {"path": str(outside / "strategy.pdf")}) == 204
    assert opened == [str((outside / "strategy.pdf").resolve())]


def test_only_listed_pdfs_open_and_only_from_this_page(panel_server):
    port, outside, opened = panel_server
    assert post(port, "/open", {"path": str(outside / "secret.pdf")}) == 404
    assert post(port, "/open", {"path": str(outside / "strategy.pdf")}, origin=False) == 403
    assert opened == []


def test_a_units_pdf_opens_in_the_system_viewer(server, monkeypatch):
    srv, port = server
    opened = []
    monkeypatch.setattr(view, "open_with_system", lambda path: opened.append(path))
    assert post(port, "/open", {"path": "threads/Q1P1/edited/note.pdf"}) == 204
    assert opened and opened[0].endswith("threads/Q1P1/edited/note.pdf")
