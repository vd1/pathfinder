"""pathfinder: scan every pair of two corpora, research the shortlist."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from . import config, corpus, monitor, paper, reconcile, research, runner, scan, select


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pathfinder"); ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="fill Q.jsonl and P.jsonl from the arXiv API, or append older papers with --more")
    f.add_argument("--q"); f.add_argument("--p"); f.add_argument("--n", type=int, default=5)
    f.add_argument("--more", type=int, metavar="N", help="append the next N older papers per side using the saved queries")
    x = sub.add_parser("explore", help="open-ended: fetch older papers, flatten, scan the new pairs, grow the shortlist; repeat")
    x.add_argument("--min-score", type=float, required=True, help="a pair joins the shortlist at or above this score")
    x.add_argument("--page", type=int, default=5, help="papers to add per side per pass")
    x.add_argument("--passes", type=int, default=1, help="how many passes; 0 means until stopped")
    sub.add_parser("sources", help="download and flatten e-print sources for both sides").add_argument("--side", choices=["Q", "P", "both"], default="both")
    sub.add_parser("scan", help="phase A: score every pair")
    s = sub.add_parser("select", help="freeze the top cut, or every pair at or above --min-score, as shortlist.json")
    s.add_argument("--cut", type=float); s.add_argument("--min-score", type=float); s.add_argument("--force", action="store_true")
    sub.add_parser("research", help="run the shortlisted threads")
    sub.add_parser("stop", help="ask a running scan or research to drain and exit").add_argument("--clear", action="store_true", help="remove the stop marker instead")
    sub.add_parser("status", help="print campaign and shortlist state")
    sub.add_parser("serve", help="serve the live monitor page").add_argument("--port", type=int, default=8790)
    w = sub.add_parser("paper", help="after DRAFT: write a paper with references and have it reviewed")
    w.add_argument("pair", nargs="?", help="default: every DRAFT thread without an accepted paper")
    r = sub.add_parser("reconcile", help="inspect a thread and name or apply the one safe action")
    r.add_argument("pair", nargs="?"); r.add_argument("--apply", action="store_true")
    ns = ap.parse_args(argv); c = config.load(Path(ns.root))
    if ns.cmd == "fetch" and ns.more:
        for side in ("Q", "P"):
            for row in corpus.more(c, side, ns.more):
                print(f"  {side} + {row['id']}  {row['date']}  {row['title']}")
    elif ns.cmd == "fetch":
        if not (ns.q and ns.p):
            raise SystemExit("fetch needs --q and --p, or --more N after a first fetch")
        c.path("fetch.json").write_text(json.dumps({"q": ns.q, "p": ns.p, "n": ns.n, "q_start": ns.n, "p_start": ns.n}, indent=1))
        for side, query in (("Q", ns.q), ("P", ns.p)):
            rows = corpus.fetch(query, ns.n); corpus.write(rows, c.path(f"{side}.jsonl"))
            print(f"{side}: {len(rows)} papers for {query!r}")
            for row in rows:
                print(f"  {row['id']}  {row['date']}  {row['title']}")
    elif ns.cmd == "explore":
        explore(c, ns.min_score, ns.page, ns.passes)
    elif ns.cmd == "sources":
        for side in (["Q", "P"] if ns.side == "both" else [ns.side]):
            corpus.sources(c, side)
    elif ns.cmd == "scan":
        scan.run(c, stop=lambda: runner.stopped(c))
    elif ns.cmd == "select":
        out = select.run(c, ns.cut, ns.force, ns.min_score)
        print(f"selected {out['n_selected']} of {out['n_scored']} " + (f"at {out['cut']}%" if out["cut"] is not None else f"at score >= {out['min_score']}"))
        for p in out["pairs"]:
            print(f"  {p['pair_id']}  score {p['score']}  ({p['feasibility']} x {p['gain']})")
    elif ns.cmd == "research":
        runner.run(c)
    elif ns.cmd == "stop":
        if ns.clear:
            c.path("stop.json").unlink(missing_ok=True); print("stop marker cleared")
        else:
            runner.request_stop(c, "operator"); print("stop requested; running commands will drain and exit")
    elif ns.cmd == "status":
        print(monitor.status_text(c))
    elif ns.cmd == "serve":
        monitor.serve(c, ns.port)
    elif ns.cmd == "paper":
        pairs = [ns.pair] if ns.pair else [p["pair_id"] for p in json.loads(c.path("shortlist.json").read_text())["pairs"]
                                           if research.status(c, p["pair_id"]).get("status") == "DRAFT"
                                           and paper.status(c, p["pair_id"]).get("status") != "accepted"]
        for pid in pairs:
            print(f"{pid}: {paper.run(c, pid, stop=lambda: runner.stopped(c))}")
    elif ns.cmd == "reconcile":
        pairs = [ns.pair] if ns.pair else [p["pair_id"] for p in json.loads(c.path("shortlist.json").read_text())["pairs"]]
        for pid in pairs:
            info = reconcile.inspect(c, pid); print(f"{pid}: {info['status']} at {info['stage']} round {info['round']}: {info['action']}")
            if ns.apply and not info["action"].startswith("nothing"):
                print(f"  -> {reconcile.apply(c, pid)}")


def explore(c, min_score: float, page: int, passes: int):
    """One pass: append older papers on both sides, flatten them, scan the new pairs, regrow the shortlist."""
    done = 0
    while not runner.stopped(c) and (passes == 0 or done < passes):
        if not runner.guard_ok(c, inflight=0):
            print("budget guard stopped exploration"); return
        added = sum(len(corpus.more(c, side, page)) for side in ("Q", "P"))
        print(f"pass {done + 1}: {added} papers added")
        if not added:
            print("nothing more to fetch"); return
        for side in ("Q", "P"):
            corpus.sources(c, side)
        scan.run(c, stop=lambda: runner.stopped(c))
        out = select.run(c, min_score=min_score)
        print(f"shortlist: {out['n_selected']} pairs at score >= {min_score}")
        done += 1


if __name__ == "__main__":
    sys.exit(main())
