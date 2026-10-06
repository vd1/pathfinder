"""pathfinder: scan every pair of two corpora, research the shortlist."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from . import config, corpus, edit, health, monitor, paper, reconcile, research, runner, scan, select, transport


def main(argv=None):
    """@planks("When the operator runs the research command")
    @planks("When the operator applies reconciliation to the shortlist")
    """
    ap = argparse.ArgumentParser(prog="pathfinder"); ap.add_argument("--root", default=".")
    ap.add_argument("--accept-change", metavar="REASON",
                    help="dispatch although the run record changed since the previous run; the reason is recorded")
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
    rs = sub.add_parser("research", help="run the shortlisted threads")
    rs.add_argument("--pairs", nargs="+", help="a bounded run over exactly these shortlisted pairs")
    co = sub.add_parser("coordinate", help="run a schedule of (arm, pair) entries across child campaigns, one pair at a time")
    co.add_argument("schedule"); co.add_argument("--status", action="store_true", help="print the aggregated snapshot instead")
    fz = sub.add_parser("freeze", help="write the engine's runtime files at a commit into a new directory")
    fz.add_argument("dest"); fz.add_argument("--ref", required=True); fz.add_argument("--repo")
    vf = sub.add_parser("verify-frozen", help="compare a frozen copy with its commit: verified, modified or unverifiable")
    vf.add_argument("dest"); vf.add_argument("--repo")
    sub.add_parser("stop", help="ask a running scan or research to drain and exit").add_argument("--clear", action="store_true", help="remove the stop marker instead")
    la = sub.add_parser("launch", help="start a long command detached and confirm it is alive: pathfinder launch -- research")
    la.add_argument("--settle", type=float, default=20.0, help="seconds to wait before checking the process")
    la.add_argument("args", nargs=argparse.REMAINDER, help="the pathfinder subcommand and its arguments, after --")
    sub.add_parser("playbook", help="the next actions for the operator or the supervising agent, with commands").add_argument("--json", action="store_true")
    sub.add_parser("economy", help="input tokens by stage and by pair, and the cached share").add_argument("--json", action="store_true")
    ie = sub.add_parser("import-eva2", help="a julien-2 eva2 experiment as a canonical composable campaign")
    ie.add_argument("experiment"); ie.add_argument("--out", required=True)
    pv = sub.add_parser("probe-vera", help="sound and planted-flaw copies of finished pairs, one direct-EVA review each")
    pv.add_argument("--pairs", nargs="+", required=True); pv.add_argument("--out", required=True)
    pz = sub.add_parser("pauses", help="provider subscriptions recorded as exhausted, which every campaign waits for")
    pz.add_argument("--clear", metavar="BACKEND", help="remove a provider's pause (codex or claude)")
    sub.add_parser("gc", help="remove what finished threads' records do not need, and compact old receipts").add_argument("--dry-run", action="store_true")
    sub.add_parser("status", help="print campaign and shortlist state")
    ev = sub.add_parser("evidence", help="a pair's evidence manifest: cited files, resolutions, errors and proposed declarations")
    ev.add_argument("pair"); ev.add_argument("--json", action="store_true")
    ev.add_argument("--apply", metavar="FILE", help="a JSON list of declarations to validate and commit atomically")
    sub.add_parser("state", help="the campaign state document: unit states, stage counts, blocks, token budget").add_argument("--json", action="store_true")
    sub.add_parser("health", help="read-only operational snapshot for the supervising agent").add_argument("--json", action="store_true")
    sub.add_parser("serve", help="serve the live monitor page").add_argument("--port", type=int, default=8790)
    vw = sub.add_parser("view", help="serve the operator view: state, pipeline, units and documents")
    vw.add_argument("--port", type=int, default=8791)
    vw.add_argument("--schedule", help="a coordination's schedule.json: one view over all its arms")
    w = sub.add_parser("paper", help="after DRAFT: write a paper with references and have it reviewed")
    w.add_argument("pair", nargs="?", help="default: every DRAFT thread without an accepted paper")
    w.add_argument("--review", action="store_true", help="one reviewer round on the paper as it stands, no author call (for a hand-edited paper)")
    e = sub.add_parser("edit", help="after a terminal verdict: rewrite the note as a readable short paper with references")
    e.add_argument("pair", nargs="?", help="default: every terminal thread without an edited note")
    xp = sub.add_parser("export", help="write a self-contained snapshot of the monitor page and every thread's documents")
    xp.add_argument("dir"); xp.add_argument("--with-sources", action="store_true", help="include the copied arXiv sources under inputs/")
    xp.add_argument("--zip", action="store_true", help="also zip the directory")
    sub.add_parser("restyle", help="rebuild every note, readable note and paper PDF with the current styles; sources untouched")
    r = sub.add_parser("reconcile", help="inspect a thread and name or apply the one safe action")
    r.add_argument("pair", nargs="?"); r.add_argument("--apply", action="store_true")
    sub.add_parser("repair-verdict", help="explicitly repair escaping in a saved terminal verifier reply; no model call").add_argument("pair")
    ns = ap.parse_args(argv)
    if ns.cmd == "coordinate":
        from . import coordinator
        if ns.status:
            print(json.dumps(coordinator.snapshot(Path(ns.schedule)), indent=1, default=str)); return 0
        try:
            state = coordinator.run(Path(ns.schedule), accept_change=ns.accept_change)
        except coordinator.ScheduleChanged as refused:
            print(f"refusing to coordinate: {refused}"); return 1
        print(json.dumps(state, indent=1, default=str))
        return 0 if state["status"] in ("complete", "censored") else 1
    if ns.cmd in ("freeze", "verify-frozen"):
        from . import freeze
        repo = Path(ns.repo) if ns.repo else Path(__file__).resolve().parent.parent
        if ns.cmd == "freeze":
            print(json.dumps({k: v for k, v in freeze.freeze(repo, ns.ref, Path(ns.dest)).items() if k != "files"}, indent=1))
            return 0
        result = freeze.verify(Path(ns.dest), repo); print(json.dumps(result, indent=1))
        return 0 if result["status"] == "verified" else 1
    if ns.cmd == "view" and ns.schedule:         # a coordination: its parent need not be a campaign
        from . import coordinator, view
        _, arms, _ = coordinator.load(Path(ns.schedule))
        view.serve(arms, ns.port); return 0
    if ns.cmd == "launch":                       # before loading: the launched command loads the campaign itself
        from . import launch
        args = ns.args[1:] if ns.args[:1] == ["--"] else ns.args
        try:
            print(json.dumps(launch.run(Path(ns.root), args, ns.settle), indent=1))
        except RuntimeError as error:
            print(f"launched command exited: {error}"); return 1
        return 0
    if ns.cmd == "import-eva2":                  # makes a campaign: none to load first
        from . import import_eva2
        print(import_eva2.run(Path(ns.experiment), Path(ns.out))); return 0
    c = config.load(Path(ns.root))
    if ns.cmd in DISPATCHING and ns.cmd != "research":       # research opens its own run inside runner.run
        from . import provenance
        try:
            with provenance.run_context(c, ns.accept_change):
                return _dispatch(ns, c)
        except provenance.ChangeRefused as refused:
            print(f"refusing to dispatch: {refused}"); return 1
    return _dispatch(ns, c)


DISPATCHING = {"scan", "explore", "research", "paper", "edit"}


def _dispatch(ns, c):
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
        return runner.run(c, pairs=ns.pairs, accept_change=ns.accept_change)
    elif ns.cmd == "repair-verdict":
        from . import recovery
        print(json.dumps(recovery.repair_verdict(c, ns.pair), indent=2))
    elif ns.cmd == "stop":
        if ns.clear:
            c.path("stop.json").unlink(missing_ok=True); print("stop marker cleared")
        else:
            runner.request_stop(c, "operator"); print("stop requested; running commands will drain and exit")
    elif ns.cmd == "evidence":
        from . import composable, evidence
        c = composable.resolve(c, ns.pair)           # a composable pair: the branch or joint thread that owns the evidence
        if not (c.thread_dir(ns.pair) / "status.json").exists():
            print(f"no thread for {ns.pair}"); return 1
        if ns.apply:
            print(json.dumps(evidence.apply_declarations(c, ns.pair, json.loads(Path(ns.apply).read_text())), indent=1))
            return 0
        m = evidence.manifest(c, ns.pair)
        proposed = evidence.proposals(m, c.thread_dir(ns.pair))
        print(json.dumps({**m, "proposals": proposed}, indent=1) if ns.json else evidence.text(m, proposed))
    elif ns.cmd == "playbook":
        from . import playbook
        actions = playbook.next_actions(c)
        print(json.dumps(actions, indent=1) if ns.json else playbook.text(actions))
    elif ns.cmd == "probe-vera":
        from . import probe
        report = probe.run(c, ns.pairs, Path(ns.out))
        print(json.dumps({k: v for k, v in report.items() if k != "units"}, indent=1))
    elif ns.cmd == "economy":
        from . import economy, transport
        summary = economy.summary(transport.receipts(c))
        print(json.dumps(summary, indent=1) if ns.json else economy.text(summary))
    elif ns.cmd == "pauses":
        from . import exhaustion
        if ns.clear:
            print(f"cleared the {ns.clear} pause" if exhaustion.clear(ns.clear) else f"no {ns.clear} pause")
        else:
            print("\n".join(exhaustion.describe(p) for p in exhaustion.all_active()) or "no provider is paused")
    elif ns.cmd == "gc":
        from . import gc
        report = gc.collect(c, dry_run=ns.dry_run)
        print(("would collect" if ns.dry_run else "collected") + f" {report['files']} files and {report['stripped']} prompt copies "
              f"in {report['threads']} finished threads, {(report['bytes'] + report['receipt_bytes']) / 1e6:.1f} MB "
              f"(receipts {report['receipt_bytes'] / 1e6:.1f} MB)")
    elif ns.cmd == "status":
        print(monitor.status_text(c))
    elif ns.cmd == "state":
        from . import campaign_state
        doc = campaign_state.build(c)
        print(json.dumps(doc, indent=1, default=str) if ns.json else campaign_state.text(doc))
    elif ns.cmd == "health":
        print(json.dumps(health.snapshot(c), indent=2) if ns.json else health.text(c))
    elif ns.cmd == "view":
        from . import view
        view.serve(c, ns.port)
    elif ns.cmd == "serve":
        monitor.serve(c, ns.port)
    elif ns.cmd == "paper" and ns.review:
        if not ns.pair:
            raise SystemExit("--review needs a pair")
        try:
            print(f"{ns.pair}: {paper.review(c, ns.pair)}")
        except transport.TransportFailed:
            print(f"{ns.pair}: transport failure; run again later")
    elif ns.cmd == "paper":
        pairs = [ns.pair] if ns.pair else [p["pair_id"] for p in json.loads(c.path("shortlist.json").read_text())["pairs"]
                                           if research.status(c, p["pair_id"]).get("status") == "DRAFT"
                                           and paper.status(c, p["pair_id"]).get("status") != "ACCEPTED"]
        for pid in pairs:
            try:
                print(f"{pid}: {paper.run(c, pid, stop=lambda: runner.stopped(c))}")
            except transport.TransportFailed:
                print(f"{pid}: transport failure; run again later")
    elif ns.cmd == "edit":
        pairs = [ns.pair] if ns.pair else [p["pair_id"] for p in json.loads(c.path("shortlist.json").read_text())["pairs"]
                                           if research.status(c, p["pair_id"]).get("status") in research.TERMINAL
                                           and edit.status(c, p["pair_id"]).get("status") != "done"]
        for pid in pairs:
            try:
                print(f"{pid}: {edit.run(c, pid, stop=lambda: runner.stopped(c))}")
            except transport.TransportFailed:
                print(f"{pid}: transport failure; run again later")
    elif ns.cmd == "export":
        print(monitor.export(c, Path(ns.dir), ns.with_sources, ns.zip))
    elif ns.cmd == "restyle":
        from . import restyle
        res = restyle.regenerate(c)
        print(f"rebuilt {res['rebuilt']}, failed {len(res['failed'])}")
        for name, tail in res["failed"]:
            print(f"--- {name}\n{tail[-800:]}")
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
