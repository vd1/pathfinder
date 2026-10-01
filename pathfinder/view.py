"""The operator's page: the campaign state document and the units' documents, read-only, on 127.0.0.1."""
from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from . import campaign_state, webguard

HERE = Path(__file__).parent
STATIC = {"/": ("view.html", "text/html; charset=utf-8"), "/view.js": ("view.js", "text/javascript; charset=utf-8"),
          "/view.css": ("view.css", "text/css; charset=utf-8")}


def make_server(campaign, port: int) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def reply(self, code: int, body: bytes, ctype: str, kind: str = "page", filename: str | None = None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            for name, value in webguard.headers(kind, filename).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            refused = webguard.refusal(self.headers, self.server.server_address[1])
            if refused:
                return self.reply(403, refused.encode(), "text/plain; charset=utf-8")
            request = urlsplit(self.path)
            if request.path in STATIC:
                name, ctype = STATIC[request.path]
                return self.reply(200, (HERE / name).read_bytes(), ctype)
            if request.path == "/api/state":
                try:
                    body = json.dumps(campaign_state.build(campaign), default=str).encode()
                except Exception as error:               # the page shows the error instead of a blank screen
                    return self.reply(503, json.dumps({"error": repr(error)}).encode(), "application/json")
                return self.reply(200, body, "application/json")
            if request.path == "/doc":
                try:
                    target = webguard.resolve(campaign.root, parse_qs(request.query).get("path", [""])[0])
                except webguard.Refused as error:
                    return self.reply(error.code, str(error).encode(), "text/plain; charset=utf-8")
                if target.suffix == ".pdf":
                    return self.reply(200, target.read_bytes(), "application/pdf", "pdf", target.name)
                return self.reply(200, target.read_bytes(), "text/plain; charset=utf-8", "text")
            return self.reply(404, b"not found", "text/plain; charset=utf-8")

        def log_message(self, *args):
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(campaign, port: int = 8791):
    server = make_server(campaign, port)
    print(f"operator view at http://127.0.0.1:{server.server_address[1]}/  (state at /api/state)")
    server.serve_forever()
