"""pathfinder: scan every pair of two corpora, research the shortlist."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from . import config, corpus, edit, health, monitor, paper, reconcile, research, runner, scan, select, transport


def main(argv=None):
    """@planks("When the operator runs the research command")
    @planks("When the operator applies reconciliation to the shortlist")
    """
    if hasattr(sys.stdout, "reconfigure"):         # a detached run's log fills as it runs, not in 8 KB blocks
        sys.stdout.reconfigure(line_buffering=True)
    ap = argparse.ArgumentParser(prog="pathfinder"); ap.add_argument("--root", default=".")
    ap.add_argument("--accept-change", metavar="REASON",
                    help="dispatch although the run record changed since the previous run; the reason is recorded")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("collection-check", help="read-only validation of a restricted collection and shared budget")
    f = sub.add_parser("fetch", help="fill Q.jsonl and P.jsonl from the arXiv API, or append older papers with --more")
    f.add_argument("--q"); f.add_argument("--p"); f.add_argument("--n", type=int, default=5)
    f.add_argument("--more", type=int, metavar="N", help="append the next N older papers per side using the saved queries")
    x = sub.add_parser("explore", help="open-ended: fetch older papers, flatten, scan the new pairs, grow the shortlist; repeat")
    x.add_argument("--min-score", type=float, required=True, help="a pair joins the shortlist at or above this score")
    x.add_argument("--page", type=int, default=5, help="papers to add per side per pass")
    x.add_argument("--passes", type=int, default=1, help="how many passes; 0 means until stopped")
    so = sub.add_parser("sources", help="the full text of every corpus paper through the source cache, or, with a pair, of one thread's papers")
    so.add_argument("pair", nargs="?", help="an existing thread: fetch its papers and library into the cache")
    so.add_argument("--into-inputs", action="store_true", help="also add them to the thread's inputs/, beside its files (recorded in inputs/added.json)")
    so.add_argument("--side", choices=["Q", "P", "both"], default="both")
    pf = sub.add_parser("prefetch", help="before research: the sources of each shortlisted pair's papers, their references and the papers citing both, into the cache")
    pf.add_argument("pairs", nargs="*", help="default: every shortlisted pair")
    sub.add_parser("scan", help="phase A: score every pair").add_argument(
        "--rescan", nargs="+", metavar="PAIR", help="score these pairs again against scan-context.json, appending their rows")
    s = sub.add_parser("select", help="freeze the top cut, or every pair at or above --min-score, as shortlist.json")
    s.add_argument("--cut", type=float); s.add_argument("--min-score", type=float); s.add_argument("--force", action="store_true")
    s.add_argument("--per-paper", type=int, help="at most this many pairs per paper; the next best pairs take the places")
    rs = sub.add_parser("research", help="run the shortlisted threads")
    rs.add_argument("--research-only", action="store_true", help="stop at terminal research; do not run editorial stages")
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
    w.add_argument("--amend", metavar="FINDINGS.json", help="an author round answering outside findings (review.json's findings schema), then a reviewer round")
    am = sub.add_parser("account-amend", help="review a fixed bounded account candidate without changing historical acceptance")
    am.add_argument("pair")
    am.add_argument("--id", required=True, help="immutable amendment identity")
    am.add_argument("--packet", type=Path, required=True, help="directory containing candidate, changes and evidence JSON")
    am.add_argument("--evidence-root", type=Path, required=True, help="base for packet evidence paths")
    am.add_argument("--reason", required=True, help="recorded owner authority and scope")
    am.add_argument("--apply", action="store_true", help="run one fresh PCE review and install only if accepted; default prepares without calls")
    av = sub.add_parser("account-amend-revise", help="review a bounded revised candidate under the existing amendment identity")
    av.add_argument("pair")
    av.add_argument("--id", required=True)
    av.add_argument("--revision", required=True)
    av.add_argument("--packet", type=Path, required=True)
    av.add_argument("--reason", required=True)
    av.add_argument("--apply", action="store_true")
    av.add_argument("--approval", type=Path, help="owner approval for an exact pending-successor history exception")
    successor = sub.add_parser("account-amend-successor", help="review an explicit successor to an accepted account returned by presentation")
    successor.add_argument("pair")
    successor.add_argument("--id", required=True)
    successor.add_argument("--packet", type=Path, required=True)
    successor.add_argument("--reason", required=True)
    successor.add_argument("--apply", action="store_true")
    successor.add_argument("--approval", type=Path,
                           help="explicit owner approval artifact for an exact bound history exception")
    ar = sub.add_parser("account-amend-review", help="grant one evidence-repaired review of an unchanged account amendment")
    ar.add_argument("pair")
    ar.add_argument("--id", required=True, help="existing amendment identity")
    ar.add_argument("--grant", required=True, help="immutable bounded review grant ID")
    ar.add_argument("--inputs", type=Path, required=True, help="retained historical scientific inputs JSON")
    ar.add_argument("--inputs-sha256", required=True, help="explicitly approved packet SHA256")
    ar.add_argument("--reason", required=True, help="authority and reason for this additional review")
    ar.add_argument("--apply", action="store_true", help="run this same prepared review; default makes no calls")
    ar.add_argument("--before-first-call", action="store_true", help="isolate approved evidence before any role has run")
    br = sub.add_parser("account-bibliography", help="build and select a metadata-only bibliography revision without scientific review calls")
    br.add_argument("pair")
    br.add_argument("--id", required=True)
    br.add_argument("--packet", type=Path, required=True)
    br.add_argument("--reason", required=True)
    br.add_argument("--apply", action="store_true")
    wr = sub.add_parser("account-wire-review", help="one immutable whole-body readability repair of a failed raw-literal review")
    wr.add_argument("pair")
    wr.add_argument("--id", required=True)
    wr.add_argument("--grant", required=True)
    wr.add_argument("--failed-round-sha256", required=True)
    wr.add_argument("--reason", required=True)
    wr.add_argument("--apply", action="store_true")
    rr = sub.add_parser("account-register-review", help="repair superseded mandatory claims in a fresh immutable round of the same candidate")
    rr.add_argument("pair")
    rr.add_argument("--id", required=True)
    rr.add_argument("--revision", required=True)
    rr.add_argument("--grant", default="final-candidate-register-v1")
    rr.add_argument("--reason", required=True)
    rr.add_argument("--apply", action="store_true")
    pc = sub.add_parser("account-present-continue", help="grant one guarded clarity correction cycle on a paused account")
    pc.add_argument("pair")
    pc.add_argument("--id", required=True)
    pc.add_argument("--context", type=Path, required=True, help="JSON with source, exact quote and finding location")
    pc.add_argument("--reason", required=True)
    pc.add_argument("--apply", action="store_true", help="run this continuation; default prepares without calls")
    pr = sub.add_parser("present", help="the presentation pass on an accepted paper: editor, lookup, fresh check, corrections; ends CLEARED")
    pr.add_argument("pair", nargs="?", help="default: every accepted paper whose pass has not ended")
    pr.add_argument("--edited", action="store_true", help="finish a PCE-accepted account without commissioning a paper")
    pr.add_argument("--restart", action="store_true", help="start the pass afresh, discarding an earlier one")
    rt = sub.add_parser("rate-release", help="prepare or resume one Sol and one Astra significance rating of a dated release")
    rt.add_argument("pair")
    rt.add_argument("--edited", action="store_true", help="rate the final released account")
    rt.add_argument("--apply", action="store_true", help="dispatch missing ratings once each; otherwise prepare only")
    rl = sub.add_parser("release", help="export a CLEARED paper as a clean article in paper/release/ with a leak check; ends RELEASED")
    rl.add_argument("pair")
    rl.add_argument("--timestamp", help="fixed release UTC timestamp, YYYYMMDDTHHMMSSZ; retries reuse it")
    rl.add_argument("--edited", action="store_true", help="release the cleared PCE account")
    vr = sub.add_parser("verify-replay", help="reassess a classic verifier on an exact follow-up copy, preserving the original")
    vr.add_argument("pair")
    vr.add_argument("--origin", type=Path, help="original campaign root; preparation requires an exact copied thread")
    vr.add_argument("--reason", help="owner authority and purpose of the replay")
    vr.add_argument("--receipt", help="restore a completed verifier erased by an empty trailing event; no new call")
    vr.add_argument("--apply", action="store_true", help="apply the verifier replay or selected receipt restoration, then stop before further work")
    ro = sub.add_parser("reopen", help="give a finished thread one more step: a repair (PAUSE-ON-REVISE), a peer round "
                        "(PAUSE-ON-ITERATE, PAUSE) or an extend round toward a target (DRAFT); the next verdict ends it")
    ro.add_argument("pair"); ro.add_argument("--grant", choices=("repair", "round", "extend"), required=True)
    ro.add_argument("--reason", required=True, help="why the operator grants it, kept in the thread's record")
    ro.add_argument("--note", help="added to the ledger as an operator entry (required to reopen a PAUSE, and an extend's target)")
    e = sub.add_parser("edit", help="after a terminal verdict: rewrite the note as a readable short paper with references")
    e.add_argument("pair", nargs="?", help="default: every terminal thread without an edited note")
    e.add_argument("--recheck", action="store_true", help="run the edited note's reference checks again, no model call")
    xp = sub.add_parser("export", help="write a self-contained snapshot of the monitor page and every thread's documents")
    xp.add_argument("dir"); xp.add_argument("--with-sources", action="store_true", help="include the copied arXiv sources under inputs/")
    xp.add_argument("--zip", action="store_true", help="also zip the directory")
    sub.add_parser("restyle", help="rebuild every note, readable note and paper PDF with the current styles; sources untouched")
    r = sub.add_parser("reconcile", help="inspect a thread and name or apply the one safe action")
    r.add_argument("pair", nargs="?"); r.add_argument("--apply", action="store_true")
    r.add_argument("--repair-only", action="store_true",
                   help="make the action's state repair and call no model; the deployment's own command resumes")
    r.add_argument("--pce-evidence", help="approved hash-bound retained evidence projection JSON; requires --pce-grant")
    r.add_argument("--pce-grant", help="unique ID for an explicit bounded editorial continuation")
    r.add_argument("--passes", type=int)
    r.add_argument("--fact-checks", type=int)
    r.add_argument("--reason")
    r.add_argument("--retire-orphans", action="store_true",
                   help="only retire call records whose runner and child are dead; no thread is touched")
    sub.add_parser("repair-verdict", help="explicitly repair escaping in a saved terminal verifier reply; no model call").add_argument("pair")
    life = sub.add_parser("lifecycle", help="file custody inventory, dry-run cleanup and verified archive/restore")
    life.add_argument("action", choices=("inventory", "ignores", "cleanup", "archive", "verify", "restore"))
    life.add_argument("--archive", type=Path)
    life.add_argument("--dest", type=Path)
    life.add_argument("--sha256", help="required external archive digest for restore")
    ns = ap.parse_args(argv)
    if ns.cmd == "lifecycle":
        from . import lifecycle
        root = Path(ns.root)
        try:
            if ns.action == "inventory":
                result = lifecycle.inventory(root)
            elif ns.action == "ignores":
                archived = lifecycle.verify_archive(ns.archive) if ns.archive else None
                print(lifecycle.ignore_rules(lifecycle.inventory(root), archived), end=""); return 0
            elif ns.action == "cleanup":
                result = lifecycle.cleanup_plan(root)
            elif ns.action == "archive":
                if not ns.dest:
                    raise ValueError("archive requires --dest outside the source tree")
                result = lifecycle.archive(root, ns.dest)
            elif ns.action == "verify":
                if not ns.archive:
                    raise ValueError("verify requires --archive")
                result = lifecycle.verify_archive(ns.archive)
            else:
                if not (ns.archive and ns.dest and ns.sha256):
                    raise ValueError("restore requires --archive, --dest and --sha256")
                result = lifecycle.restore(ns.archive, ns.dest, ns.sha256)
            print(json.dumps(result, indent=1)); return 0
        except (ValueError, RuntimeError, OSError) as error:
            print(f"lifecycle refused: {error}", file=sys.stderr); return 1
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
    from . import collection
    if ns.cmd == "collection-check":
        result = collection.inspect(c)
        print(json.dumps(result, indent=1))
        return 0 if result["status"] == "verified" else 1
    if collection.enabled(c) and ns.cmd not in (
            "research", "state", "health", "stop", "playbook", "economy", "serve", "view"):
        raise collection.Refused("restricted collection permits research and read-only operational commands only")
    if ns.cmd in ("present", "release") and ns.edited:
        from . import pce_recovery
        if not ns.pair:
            raise SystemExit("--edited requires one explicit pair")
        pce_recovery.preflight(c, presentation=True)
    if ns.cmd in DISPATCHING and ns.cmd != "research":       # research opens its own run inside runner.run
        from . import provenance
        try:
            with provenance.run_context(c, ns.accept_change):
                return _dispatch(ns, c)
        except provenance.ChangeRefused as refused:
            print(f"refusing to dispatch: {refused}"); return 1
    return _dispatch(ns, c)


DISPATCHING = {"scan", "explore", "research", "paper", "edit", "present"}


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
    elif ns.cmd == "sources" and ns.pair:
        from . import library
        if ns.into_inputs:
            out = library.add_to_inputs(c, ns.pair)
            print(f"{ns.pair}: added {', '.join(out['added']) or 'nothing'}; read from {out['inputs'] or 'the files it had'}")
        else:
            library.prefetch(c, [ns.pair])
    elif ns.cmd == "prefetch":
        from . import library
        pairs = ns.pairs or [p["pair_id"] for p in json.loads(c.path("shortlist.json").read_text())["pairs"]]
        t = library.prefetch(c, pairs)
        print(f"{t['pairs']} pairs, {t['papers']} papers in the cache {library.cache(c)}, {t['failed']} without a source")
    elif ns.cmd == "sources":
        for side in (["Q", "P"] if ns.side == "both" else [ns.side]):
            corpus.sources(c, side)
    elif ns.cmd == "scan":
        if ns.rescan:
            scan.rescan(c, ns.rescan, stop=lambda: runner.stopped(c))
        else:
            scan.run(c, stop=lambda: runner.stopped(c))
    elif ns.cmd == "select":
        out = select.run(c, ns.cut, ns.force, ns.min_score, ns.per_paper)
        print(f"selected {out['n_selected']} of {out['n_scored']} " + (f"at {out['cut']}%" if out["cut"] is not None else f"at score >= {out['min_score']}")
              + (f", at most {out['per_paper']} per paper" if out["per_paper"] else ""))
        if out.get("weights"):
            print(f"weighted by {out['weights']['path']} (revision {out['weights']['revision']})")
        for p in out["pairs"]:
            weighted = f"  weighted {p['weighted']:g} (x {p['weight']:g})" if "weighted" in p else ""
            print(f"  {p['pair_id']}  score {p['score']}  ({p['feasibility']} x {p['gain']}){weighted}")
    elif ns.cmd == "research":
        return runner.run(c, pairs=ns.pairs, accept_change=ns.accept_change, research_only=ns.research_only)
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
        from . import economy
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
    elif ns.cmd == "paper" and ns.amend:
        if not ns.pair:
            raise SystemExit("--amend needs a pair")
        try:
            print(f"{ns.pair}: {paper.amend(c, ns.pair, ns.amend)}")
        except transport.TransportFailed:
            print(f"{ns.pair}: transport failure; run `pathfinder paper {ns.pair}` later to resume the amend")
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
                                           and paper_due(c, p["pair_id"])]
        for pid, result in paper.run_many(c, pairs, stop=lambda: runner.stopped(c)).items():
            print(f"{pid}: {result}")
    elif ns.cmd == "account-bibliography":
        from . import account_bibliography
        print(account_bibliography.run(c, ns.pair, identity=ns.id, packet=ns.packet, reason=ns.reason, apply=ns.apply))
    elif ns.cmd == "account-wire-review":
        from . import account_wire
        print(account_wire.repair(c, ns.pair, identity=ns.id, grant_id=ns.grant,
              failed_round_sha256=ns.failed_round_sha256, reason=ns.reason,
              apply=ns.apply, accept_change=ns.accept_change))
    elif ns.cmd == "account-register-review":
        from . import account_register
        print(account_register.repair(c, ns.pair, identity=ns.id, revision=ns.revision,
              grant_id=ns.grant, reason=ns.reason, apply=ns.apply, accept_change=ns.accept_change))
    elif ns.cmd == "account-amend-successor":
        from . import account_successor
        print(account_successor.run(c, ns.pair, identity=ns.id, packet=ns.packet,
                                    reason=ns.reason, approval=ns.approval,
                                    apply=ns.apply, accept_change=ns.accept_change))
    elif ns.cmd == "account-amend-revise":
        from . import account_revision
        print(account_revision.run(c, ns.pair, identity=ns.id, revision=ns.revision, packet=ns.packet,
                                   reason=ns.reason, approval=ns.approval, apply=ns.apply, accept_change=ns.accept_change))
    elif ns.cmd == "account-present-continue":
        from . import account_present
        print(account_present.apply(c, ns.pair, identity=ns.id, context_path=ns.context,
                                    reason=ns.reason, resume=ns.apply, accept_change=ns.accept_change))
    elif ns.cmd == "account-amend-review":
        from . import account_review
        print(account_review.apply(c, ns.pair, identity=ns.id, grant_id=ns.grant,
                                   inputs=ns.inputs, inputs_sha256=ns.inputs_sha256, reason=ns.reason,
                                   resume=ns.apply, accept_change=ns.accept_change,
                                   before_first_call=ns.before_first_call))
    elif ns.cmd == "account-amend":
        from . import account_amend
        print(account_amend.apply(c, ns.pair, identity=ns.id, packet=ns.packet,
                                 evidence_root=ns.evidence_root, reason=ns.reason,
                                 resume=ns.apply, accept_change=ns.accept_change))
    elif ns.cmd == "present":
        if ns.edited:
            from . import account_release
            print(f"{ns.pair}: {account_release.present(c, ns.pair, restart=ns.restart)}")
            return
        from . import presentation
        pairs = [ns.pair] if ns.pair else [p["pair_id"] for p in json.loads(c.path("shortlist.json").read_text())["pairs"]
                                           if research.status(c, p["pair_id"]).get("status") == "DRAFT"
                                           and paper.status(c, p["pair_id"]).get("status") == "ACCEPTED"
                                           and presentation.state(c, p["pair_id"]).get("state") not in presentation.TERMINAL]
        for pid in pairs:
            try:
                print(f"{pid}: {presentation.run(c, pid, restart=ns.restart)}")
            except transport.TransportFailed:
                print(f"{pid}: transport failure; run again later to resume")
            reason = presentation.state(c, pid).get("reason")
            if reason:
                print(f"  {reason}")
    elif ns.cmd == "rate-release":
        from . import significance
        print(json.dumps(significance.run(c, ns.pair, edited=ns.edited, apply=ns.apply,
                                         accept_change=ns.accept_change), indent=2))
    elif ns.cmd == "release":
        if ns.edited:
            from . import account_release
            print(json.dumps(account_release.release(c, ns.pair, timestamp=ns.timestamp)))
            return
        from . import release
        out = release.run(c, ns.pair, timestamp=ns.timestamp)
        print(f"{ns.pair}: {out['status']}: {out['path']} ({out['keys']} keys renamed, {out['pointers']} ledger pointers kept in paper/provenance.json)")
    elif ns.cmd == "verify-replay":
        from . import verify_replay
        print(json.dumps(verify_replay.run(c, ns.pair, origin=ns.origin, reason=ns.reason,
                                          apply=ns.apply, accept_change=ns.accept_change, receipt=ns.receipt), indent=2))
    elif ns.cmd == "reopen":
        from . import reopen
        try:
            entry = reopen.reopen(c, ns.pair, ns.grant, ns.reason, ns.note)
        except (ValueError, RuntimeError) as error:
            raise SystemExit(f"reopen refused: {error}")
        print(f"{ns.pair}: reopen {entry['n']} from {entry['from']['status']} with {'an' if ns.grant == 'extend' else 'a'} {ns.grant} grant"
              + (f"; archived {', '.join(entry['archived'])}" if entry["archived"] else "")
              + f"\nthe runner reaches it on its next pass; on its own: pathfinder research --pairs {ns.pair}")
    elif ns.cmd == "edit" and ns.recheck:
        if not ns.pair:
            raise SystemExit("--recheck needs a pair")
        checks = edit.recheck(c, ns.pair)
        print(f"{ns.pair}: references rechecked: " + ("; ".join(checks) or "no findings"))
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
        if ns.pce_evidence and not ns.pce_grant:
            raise SystemExit("--pce-evidence requires --pce-grant")
        if ns.pce_grant:
            from . import pce_recovery
            if not ns.pair or not (ns.apply or ns.repair_only) or ns.retire_orphans:
                raise SystemExit("PCE grant requires one pair and --apply or --repair-only")
            print(pce_recovery.apply(c, ns.pair, identity=ns.pce_grant, passes=ns.passes,
                                    fact_checks=ns.fact_checks, reason=ns.reason, evidence=ns.pce_evidence, resume=not ns.repair_only, accept_change=ns.accept_change))
            return
        pairs = [ns.pair] if ns.pair else [p["pair_id"] for p in json.loads(c.path("shortlist.json").read_text())["pairs"]]
        for path, call in health.orphans(c, None if not ns.pair else set(pairs)):
            print(f"orphaned call record {call.get('attempt_id')} ({call.get('thread')}/{call.get('stage')}/{call.get('actor')}): "
                  "its runner and child are dead" + ("" if ns.apply or ns.repair_only or ns.retire_orphans
                                                        else "; --retire-orphans retires it"))
        if ns.apply or ns.repair_only or ns.retire_orphans:
            for call in health.retire_orphans(c, None if not ns.pair else set(pairs)):
                print(f"  -> retired orphaned call record {call.get('attempt_id')} (event call_abandoned)")
        for pid in [] if ns.retire_orphans else pairs:
            info = reconcile.inspect(c, pid); print(f"{pid}: {info['status']} at {info['stage']} round {info['round']}: {info['action']}")
            if (ns.apply or ns.repair_only) and not info["action"].startswith("nothing"):
                print(f"  -> {reconcile.apply(c, pid, resume=not ns.repair_only, accept_change=ns.accept_change)}")


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


def paper_due(c, pair_id) -> bool:
    """`pathfinder paper` with no pair: a paper not yet accepted, or, with "presentation": true, an accepted one
    whose presentation pass has not ended."""
    from . import paper, presentation
    s = paper.status(c, pair_id).get("status")
    if s not in paper.ACCEPTED_STATES:
        return True
    return (s == "ACCEPTED" and presentation.enabled(c)
            and presentation.state(c, pair_id).get("state") not in presentation.TERMINAL)


if __name__ == "__main__":
    sys.exit(main())

