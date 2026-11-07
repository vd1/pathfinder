"""The engine's own downloads (arXiv metadata, sources, PDFs).

They go through an opener that takes proxies from the environment only. urllib's default opener asks the
macOS system configuration for proxies, which initializes system frameworks in this process; after that,
children forked by the engine (the Codex CLI) died with signal 11 before their session, so a paper or
edit stage that had just checked references on arXiv could never call a model (agQSL, 2 October)."""
from __future__ import annotations
import urllib.request


def opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(urllib.request.ProxyHandler(urllib.request.getproxies_environment()))


def urlopen(url, timeout: float):
    return opener().open(url, timeout=timeout)
