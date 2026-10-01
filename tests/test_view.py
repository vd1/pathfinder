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
    for section in ('id="params"', 'id="pipeline"', 'id="blocks"', 'id="units"', 'id="reader"'):
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


def test_reader_is_not_rebuilt_when_an_unrelated_unit_changes():
    assert _harness()["reader_rebuilt_on_unrelated_change"] is False


def test_opening_a_unit_keeps_the_pipeline_filter():
    assert _harness()["unit_link_keeps_filter"] is True


def test_parameters_show_allowances_and_scores_are_rounded():
    result = _harness()
    assert result["allowances_shown"] and result["score_rounded"]


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
