"""Read-only view of a campaign: a state document, a text status, a local server with one live page."""
from __future__ import annotations
import json, mimetypes, re, shutil, subprocess, tempfile, time
from collections import Counter
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from . import corpus, edit, paper, reconcile, research, transport


def _jsonl(p: Path):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def _jsonl_one(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def state(campaign) -> dict:
    Q = corpus.read(campaign.path("Q.jsonl")) if campaign.path("Q.jsonl").exists() else []
    P = corpus.read(campaign.path("P.jsonl")) if campaign.path("P.jsonl").exists() else []
    scan = _jsonl(campaign.path("scan.jsonl")); by_id = {r["pair_id"]: r for r in scan}
    grid = [[(by_id.get(corpus.pair_id(i, j), {}).get("feasibility") or 0) * (by_id.get(corpus.pair_id(i, j), {}).get("gain") or 0)
             if corpus.pair_id(i, j) in by_id else None for j in range(1, len(P) + 1)] for i in range(1, len(Q) + 1)]
    receipts = transport.receipts(campaign); rc, stages = {}, {}
    for r in receipts:
        if r.get("stage") == "scan":
            continue
        t = rc.setdefault(r.get("thread"), {"spend": 0.0, "seconds": 0.0, "calls": 0})
        t["spend"] += r.get("cost") or 0; t["seconds"] += r.get("seconds") or 0; t["calls"] += 1
        st = stages.setdefault(r.get("thread"), {}).setdefault(r.get("stage"), {"calls": 0, "seconds": 0.0, "spend": 0.0, "errors": 0})
        st["calls"] += 1; st["seconds"] += r.get("seconds") or 0; st["spend"] += r.get("cost") or 0; st["errors"] += bool(r.get("error"))
    sl = json.loads(campaign.path("shortlist.json").read_text()) if campaign.path("shortlist.json").exists() else {"pairs": []}
    threads, shortlist = {}, []
    for p in sl["pairs"]:
        pid = p["pair_id"]; s = research.status(campaign, pid); d = campaign.thread_dir(pid)
        led = _jsonl(d / "ledger.jsonl")
        verd = json.loads((d / f"{pid}.verdict.json").read_text()) if (d / f"{pid}.verdict.json").exists() else []
        noise = {".aux", ".log", ".out", ".fls", ".fdb_latexmk", ".blg", ".bbl", ".pdf", ".synctex.gz", ".toc"}
        files = sorted(str(x.relative_to(d)) for x in d.rglob("*") if x.is_file() and "__pycache__" not in x.parts
                       and ".build" not in x.parts and x.suffix not in noise and x.name not in ("lock", "ledger.lock")) if d.exists() else []
        threads[pid] = {"status": s, "entries": len(led), "by_kind": dict(Counter(e["kind"] for e in led)),
                        "by_actor": dict(Counter(e["actor"] for e in led)), "ledger": led, "verdicts": verd,
                        "note": f"{pid}.tex" if (d / f"{pid}.tex").exists() else None, "files": files,
                        "by_stage": stages.get(pid, {}), "connexion": by_id.get(pid, {}).get("connexion"),
                        "paper": paper.status(campaign, pid) if (d / "paper").exists() else None,
                        "edited": edit.status(campaign, pid) if (d / "edited").exists() else None,
                        "q_title": Q[int(pid[1:].split("P")[0]) - 1].get("title") if Q else None,
                        "p_title": P[int(pid.split("P")[1]) - 1].get("title") if P else None,
                        "q_abstract": Q[int(pid[1:].split("P")[0]) - 1].get("abstract") if Q else None,
                        "p_abstract": P[int(pid.split("P")[1]) - 1].get("abstract") if P else None}
        shortlist.append({**p, "status": s.get("status"), "round": s.get("round"), "stage": s.get("stage"),
                          **rc.get(pid, {"spend": 0.0, "seconds": 0.0, "calls": 0})})
    statuses = Counter(t["status"].get("status", "new") for t in threads.values())
    attention = []                                   # what an owner would act on: reason, age, the one safe action
    for p in sl["pairs"]:
        pid = p["pair_id"]; s = threads[pid]["status"]; st = s.get("status", "new")
        if st not in research.TERMINAL and st not in ("running",) and st != "new":
            info = reconcile.inspect(campaign, pid)
            words = {"start": "Start the thread.", "resume peers": "Resume the peers where they stopped.", "run consolidate": "Run the consolidation again.",
                     "run verify": "Run the verification again."}
            attention.append({"pair": pid, "kind": st, "reason": s.get("reason"), "since": s.get("updated"),
                              "action": words.get(info["action"], info["action"]) + " Reconcile does this."})
        pp = threads[pid].get("paper")
        if pp and pp.get("status") in ("PAUSE-ON-AMEND", "blocked", "stopped"):
            attention.append({"pair": pid, "kind": f"paper {pp['status']}", "reason": pp.get("reason"), "since": pp.get("updated"),
                              "action": "The reviewer still asked for amendments when the round cap was reached. Read the paper and its last review; to try another round, raise paper_rounds in campaign.json and run the paper stage for this pair again, or leave it."})
        ee = threads[pid].get("edited")
        if ee and ee.get("status") in ("blocked", "stopped"):
            attention.append({"pair": pid, "kind": f"edit {ee['status']}", "reason": ee.get("reason"), "since": ee.get("updated"), "action": "Run the editor for this pair again."})
    waiting = [p["pair_id"] for p in sl["pairs"] if threads[p["pair_id"]]["status"].get("status", "new") == "new"]
    if waiting and _jsonl_one(campaign.path("stop.json")):
        attention.append({"pair": ", ".join(waiting), "kind": "held by the stop marker", "reason": _jsonl_one(campaign.path("stop.json")).get("reason"),
                          "since": _jsonl_one(campaign.path("stop.json")).get("at"), "action": "Clear the stop marker and start the runner again; raise budget_usd first if the guard wrote the marker."})
    phase = ("research" if sl["pairs"] else "select" if scan and len(scan) >= len(Q) * len(P) and Q else "scan" if Q else "fetch")
    return {"generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "campaign": {"name": campaign.root.name, "phase": phase, "spend": round(sum(r.get("cost") or 0 for r in receipts), 4), "budget": campaign.budget_usd,
                         "calls": len(receipts), "seconds": round(sum(r.get("seconds") or 0 for r in receipts)),
                         "first_call": receipts[0].get("at") if receipts else None, "last_call": receipts[-1].get("at") if receipts else None,
                         "errors": sum(bool(r.get("error")) for r in receipts),
                         "seats": campaign.seats, "stop": _jsonl_one(campaign.path("stop.json")),
                         "health": _jsonl_one(campaign.path("health.json")), "by_status": dict(statuses), "backend": campaign.backend,
                         "model": campaign.model},
            "scan": {"done": len(scan), "total": len(Q) * len(P), "grid": grid, "q": [q.get("title") for q in Q],
                     "p": [p.get("title") for p in P], "q_ids": [q.get("id") for q in Q], "p_ids": [p.get("id") for p in P], "cost": round(sum(r.get("cost") or 0 for r in scan), 4),
                     "scores": sorted((r["feasibility"] * r["gain"] for r in scan if r.get("feasibility") is not None), reverse=True),
                     "cut": sl.get("cut"), "min_score": sl.get("min_score"), "n_selected": len(sl["pairs"])},
            "shortlist": shortlist, "threads": threads, "attention": attention}


def status_text(campaign) -> str:
    s = state(campaign); c = s["campaign"]
    lines = [f"phase {c['phase']}  spend {c['spend']:.2f}/{c['budget']:.2f} USD  calls {c['calls']}  "
             f"stop {'yes' if c['stop'] else 'no'}  health {'flag' if c['health'] else 'ok'}",
             f"scan {s['scan']['done']}/{s['scan']['total']}  shortlist {s['scan']['n_selected']}  threads {c['by_status']}"]
    for p in s["shortlist"]:
        lines.append(f"{p['pair_id']:>8} {str(p['status']):>17} round {p['round'] or 0} {str(p['stage']):>11} "
                     f"calls {p['calls']:>3} {p['seconds']:>6.0f}s {p['spend']:>7.2f} USD")
    return "\n".join(lines)


PAGE = Path(__file__).parent / "monitor.html"
TEXT = {".jsonl", ".json", ".md", ".py", ".tex", ".bib", ".txt", ".out", ".log", ".csv"}
_pdf_cache: dict = {}


def pdf(tex: Path) -> tuple[bytes, str]:
    """Compile a note with pdflatex in a scratch directory; cached by mtime. Returns (pdf bytes, log)."""
    key, mtime = str(tex), tex.stat().st_mtime
    if key in _pdf_cache and _pdf_cache[key][0] == mtime:
        return _pdf_cache[key][1], _pdf_cache[key][2]
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(tex, tmp)
        for _ in range(2):
            subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex.name], cwd=tmp,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        out, log = Path(tmp) / tex.with_suffix(".pdf").name, Path(tmp) / tex.with_suffix(".log").name
        data = out.read_bytes() if out.exists() else b""
        text = log.read_text(errors="replace") if log.exists() else "pdflatex produced no log"
    _pdf_cache[key] = (mtime, data, text)
    return data, text


def serve(campaign, port: int = 8790):
    root = campaign.root

    class H(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(root), **k)

        def _send(self, body: bytes, ctype: str, code: int = 200):
            self.send_response(code); self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body)

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                return self._send(PAGE.read_bytes(), "text/html; charset=utf-8")
            if path == "/state":
                return self._send(json.dumps(state(campaign)).encode(), "application/json")
            m = re.fullmatch(r"/threads/(Q\d+P\d+)/\1\.pdf", path)
            if m:
                tex = campaign.thread_dir(m.group(1)) / f"{m.group(1)}.tex"
                if not tex.exists():
                    return self._send(b"no note yet", "text/plain; charset=utf-8", 404)
                data, log = pdf(tex)
                return self._send(data, "application/pdf") if data else self._send(log.encode(), "text/plain; charset=utf-8", 500)
            if Path(path).suffix in TEXT:
                f = root / path.lstrip("/")
                if f.is_file() and root in f.resolve().parents:
                    return self._send(f.read_bytes(), "text/plain; charset=utf-8")
            return super().do_GET()

        def log_message(self, *a):
            pass

    print(f"monitor at http://localhost:{port}/  (state at /state, thread files under /threads/)")
    HTTPServer(("127.0.0.1", port), H).serve_forever()


KEEP = {".tex", ".bib", ".pdf", ".json", ".jsonl", ".md", ".txt", ".py", ".out", ".csv"}


def export(campaign, out: Path, with_sources: bool = False, zip_it: bool = False) -> Path:
    """Write a self-contained snapshot of the campaign page: index.html with the state inline, and every
    thread's documents (notes compiled to PDF). Returns the directory, or the zip when asked."""
    out = Path(out); shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True)
    st = state(campaign)
    page = PAGE.read_text()
    page = page.replace("<script>\nlet selected", "<script>window.STATIC = true; window.STATE = " + json.dumps(st) + ";</script>\n<script>\nlet selected", 1)
    (out / "index.html").write_text(page)
    for name in ("campaign.json", "Q.jsonl", "P.jsonl", "scan.jsonl", "shortlist.json", "receipts.jsonl"):
        if campaign.path(name).exists():
            shutil.copy(campaign.path(name), out / name)
    for p in st["shortlist"]:
        pid = p["pair_id"]; src = campaign.thread_dir(pid); dst = out / "threads" / pid
        if not src.exists():
            continue
        for f in src.rglob("*"):
            rel = f.relative_to(src)
            if not f.is_file() or "__pycache__" in rel.parts or ".build" in rel.parts or f.suffix not in KEEP:
                continue
            if rel.parts[0] == "inputs" and f.suffix != ".json" and not with_sources:
                continue
            (dst / rel).parent.mkdir(parents=True, exist_ok=True); shutil.copy(f, dst / rel)
        tex = src / f"{pid}.tex"
        if tex.exists():
            data, _ = pdf(tex)
            if data:
                (dst / f"{pid}.pdf").write_bytes(data)
    if zip_it:
        return Path(shutil.make_archive(str(out), "zip", root_dir=out.parent, base_dir=out.name))
    return out
