"""pathfinder: scan every pair of two corpora, research the shortlist."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from . import config, corpus, monitor, reconcile, runner, scan, select


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pathfinder"); ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="fill Q.jsonl and P.jsonl from the arXiv API")
    f.add_argument("--q", required=True); f.add_argument("--p", required=True); f.add_argument("--n", type=int, default=5)
    sub.add_parser("sources", help="download and flatten e-print sources for both sides").add_argument("--side", choices=["Q", "P", "both"], default="both")
    sub.add_parser("scan", help="phase A: score every pair")
    s = sub.add_parser("select", help="freeze the top cut as shortlist.json"); s.add_argument("--cut", type=float); s.add_argument("--force", action="store_true")
    sub.add_parser("research", help="run the shortlisted threads")
    sub.add_parser("stop", help="ask a running scan or research to drain and exit").add_argument("--clear", action="store_true", help="remove the stop marker instead")
    sub.add_parser("status", help="print campaign and shortlist state")
    sub.add_parser("serve", help="serve the live monitor page").add_argument("--port", type=int, default=8765)
    r = sub.add_parser("reconcile", help="inspect a thread and name or apply the one safe action")
    r.add_argument("pair", nargs="?"); r.add_argument("--apply", action="store_true")
    ns = ap.parse_args(argv); c = config.load(Path(ns.root))
    if ns.cmd == "fetch":
        for side, query in (("Q", ns.q), ("P", ns.p)):
            rows = corpus.fetch(query, ns.n); corpus.write(rows, c.path(f"{side}.jsonl"))
            print(f"{side}: {len(rows)} papers for {query!r}")
            for row in rows:
                print(f"  {row['id']}  {row['date']}  {row['title']}")
    elif ns.cmd == "sources":
        for side in (["Q", "P"] if ns.side == "both" else [ns.side]):
            corpus.sources(c, side)
    elif ns.cmd == "scan":
        scan.run(c, stop=lambda: runner.stopped(c))
    elif ns.cmd == "select":
        out = select.run(c, ns.cut, ns.force); print(f"selected {out['n_selected']} of {out['n_scored']} at {out['cut']}%")
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
    elif ns.cmd == "reconcile":
        pairs = [ns.pair] if ns.pair else [p["pair_id"] for p in json.loads(c.path("shortlist.json").read_text())["pairs"]]
        for pid in pairs:
            info = reconcile.inspect(c, pid); print(f"{pid}: {info['status']} at {info['stage']} round {info['round']}: {info['action']}")
            if ns.apply and not info["action"].startswith("nothing"):
                print(f"  -> {reconcile.apply(c, pid)}")


if __name__ == "__main__":
    sys.exit(main())
