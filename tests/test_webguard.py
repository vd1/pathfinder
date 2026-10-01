import os
import pytest
from pathfinder import webguard


def test_local_host_and_origin_only():
    ok = {"Host": "127.0.0.1:8791"}
    assert webguard.refusal(ok, 8791) is None
    assert webguard.refusal({"Host": "localhost:8791", "Origin": "http://localhost:8791"}, 8791) is None
    assert webguard.refusal({"Host": "evil.example:8791"}, 8791)
    assert webguard.refusal({"Host": "127.0.0.1:8791", "Origin": "http://evil.example"}, 8791)
    assert webguard.refusal({}, 8791)


def test_headers_frame_pdfs_only_from_self():
    page, pdf = webguard.headers("page"), webguard.headers("pdf", "note.pdf")
    assert "frame-ancestors 'none'" in page["Content-Security-Policy"] and page["X-Frame-Options"] == "DENY"
    assert pdf["Content-Security-Policy"] == "frame-ancestors 'self'" and pdf["X-Frame-Options"] == "SAMEORIGIN"
    assert pdf["Content-Disposition"] == 'inline; filename="note.pdf"'
    for h in (page, pdf, webguard.headers("text")):
        assert h["X-Content-Type-Options"] == "nosniff" and h["Cache-Control"] == "no-store"


def test_resolver_allows_thread_documents_only(tmp_path):
    d = tmp_path / "threads" / "Q1P1" / "edited"; d.mkdir(parents=True)
    (d / "note.pdf").write_bytes(b"%PDF"); (d / "note.tex").write_text("x"); (d / "run.sh").write_text("x")
    (tmp_path / ".env").write_text("SECRET=1")
    assert webguard.resolve(tmp_path, "threads/Q1P1/edited/note.pdf") == d / "note.pdf"
    for bad, code in [("../outside.pdf", 404), (".env", 404), ("threads/Q1P1/edited/run.sh", 404),
                      ("threads/../.env", 404), ("threads/Q1P1/edited/missing.pdf", 404)]:
        with pytest.raises(webguard.Refused) as refused:
            webguard.resolve(tmp_path, bad)
        assert refused.value.code == code


def test_resolver_refuses_symlinks_out_and_oversize(tmp_path):
    d = tmp_path / "threads" / "Q1P1"; d.mkdir(parents=True)
    (tmp_path / "secret.txt").write_text("s")
    os.symlink(tmp_path / "secret.txt", d / "link.txt")
    with pytest.raises(webguard.Refused):
        webguard.resolve(tmp_path, "threads/Q1P1/link.txt")
    big = d / "big.json"; big.write_bytes(b"0" * (webguard.MAX_BYTES + 1))
    with pytest.raises(webguard.Refused) as refused:
        webguard.resolve(tmp_path, "threads/Q1P1/big.json")
    assert refused.value.code == 413
