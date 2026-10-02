"""Engine downloads never consult the macOS system proxy configuration: after it, every child the engine
forks (the Codex CLI) died with signal 11 before its session (agQSL Q2P2, 2 October)."""
import http.server, threading, urllib.request
import pytest
from pathfinder import corpus, net


@pytest.fixture
def server():
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok")

        def log_message(self, *args):
            pass
    s = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{s.server_address[1]}/"
    s.shutdown()


def test_downloads_skip_the_system_proxy_lookup(server, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("system proxy configuration consulted")
    monkeypatch.setattr(urllib.request, "getproxies", forbidden)
    monkeypatch.setattr(urllib.request, "proxy_bypass", forbidden)
    for name in ("getproxies_macosx_sysconf", "proxy_bypass_macosx_sysconf"):
        if hasattr(urllib.request, name):
            monkeypatch.setattr(urllib.request, name, forbidden)
    with net.urlopen(server, timeout=5) as r:
        assert r.read() == b"ok"


def test_environment_proxies_are_still_honoured(monkeypatch):
    monkeypatch.setenv("https_proxy", "http://proxy.example:3128")
    handler = next(h for h in net.opener().handlers if isinstance(h, urllib.request.ProxyHandler))
    assert handler.proxies.get("https") == "http://proxy.example:3128"


def test_the_arxiv_api_is_https():
    assert corpus.API.startswith("https://")
