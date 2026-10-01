"""Request checks and response headers for the local pages, and the one way they read campaign files.

The servers bind to 127.0.0.1, but a browser page elsewhere can still reach them through DNS rebinding
or a cross-site request, so every request must name this server as Host and, when it has one, as Origin.
Pages may not be framed; PDFs may be framed by this origin only, for the in-page reader. Files are served
only from threads/, with known suffixes and a size cap, never through a symlink that leaves the campaign."""
from __future__ import annotations
from pathlib import Path

MAX_BYTES = 8 * 1024 * 1024
SUFFIXES = {".pdf", ".tex", ".bib", ".md", ".txt", ".json", ".jsonl", ".log"}
PAGE_POLICY = ("default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; "
               "frame-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")


class Refused(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


def refusal(headers, port: int) -> str | None:
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    if headers.get("Host") not in hosts:
        return "local host required"
    origin = headers.get("Origin")
    if origin and origin not in {"http://" + h for h in hosts}:
        return "same origin required"
    return None


def headers(kind: str, filename: str | None = None) -> dict:
    out = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"}
    if kind == "pdf":
        out.update({"X-Frame-Options": "SAMEORIGIN", "Content-Security-Policy": "frame-ancestors 'self'",
                    "Content-Disposition": f'inline; filename="{filename or "document.pdf"}"'})
    else:
        out.update({"X-Frame-Options": "DENY", "Content-Security-Policy": PAGE_POLICY})
    return out


def resolve(root: Path, relative: str) -> Path:
    root = Path(root).resolve()
    threads = root / "threads"
    candidate = root / relative
    try:
        target = candidate.resolve(strict=True)
    except (FileNotFoundError, RuntimeError, OSError):
        raise Refused(404, "document not found")
    if not target.is_relative_to(threads) or not target.is_file() or target.suffix not in SUFFIXES:
        raise Refused(404, "document not found")
    if target.stat().st_size > MAX_BYTES:
        raise Refused(413, "document too large for this viewer")
    return target
