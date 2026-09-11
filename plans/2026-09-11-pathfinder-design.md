# Pathfinder: design

Status: draft for review, 11 September 2026. Written from a conversation with
the operator; the agQSL campaigns (Pathfinder3, Julien edition, E-prime) are
the prior instance this design is extracted from.

## Purpose

Given two corpora of papers, Q and P, find the pairs (q, p) about which there
is something interesting to say, and for each such pair produce a developed
research thread: a visible trace, a verdict, and a LaTeX note.

The campaign has two phases. The scan scores every pair cheaply. The research
develops each shortlisted pair with two peer agents and an independent
verifier. A monitor and a budget guard sit alongside.

This repository is a minimal reference implementation. Its second purpose is
to be read: a colleague, or an agent working for one, should be able to
rebuild it for their own corpora from the README and the prompts. Zero
bureaucracy: no database, no daemon, no queue, standard-library Python, state
in plain files.

## Inputs

Two corpora, each a JSONL file with one paper per line:

    {"id": "2409.01234", "title": "...", "abstract": "...",
     "authors": [...], "date": "2024-09-03", "text": null}

`pathfinder fetch --q QUERY --p QUERY --n N` fills them from the arXiv API,
most recent first. `pathfinder fetch --sources` downloads each paper's e-print
source, flattens it with `latexpand` into one file under
`sources/<id>.tex`, and sets `text` to that path. A paper with only a PDF is
converted with `pdftotext` to `sources/<id>.txt`. Missing tools fail loudly.
Hand-written corpus files are equally valid; the fetcher is a convenience.

Pair ids are positional: `Q2P3` is row 2 of Q against column 3 of P.

## Phase A: scan

`pathfinder scan` walks Q row by row and P within each row. Each pair is one
independent model call with no tools. The context is `prompts/scan.md`, then
Q's title and body, then P's, in that order so the prompt and the Q side form
a cacheable prefix across a row. The body is the abstract, or the flattened
full text when `text` is set and `scan.fulltext` names that side. The Julien
variant is full text on Q and abstract on P.

Each result appends one line to `scan.jsonl`: pair id, feasibility, gain,
connexion, rationale, backend, model, seconds, tokens, cost. Pairs already
present are skipped, so a killed scan resumes where it stopped. A call that
returns no parseable JSON is retried once, then recorded with null scores and
an error field so the gap is visible.

## Selection

`pathfinder select --cut PERCENT` ranks scored pairs by feasibility times
gain, ties broken by the smaller of the two then by pair id, and keeps the
top `ceil(N * cut / 100)` with no expansion at ties. It writes
`shortlist.json`: the ordered pair list, the parameters, and a digest of
`scan.jsonl`. It refuses an incomplete scan unless `--force`. The cut is a
cost-versus-recall parameter; 1 percent is the default and the 5 by 5 test
uses 12 so three pairs reach research.

## Phase E-prime: research

One thread per shortlisted pair under `threads/<pair_id>/`:

    inputs/Q.tex  inputs/P.tex      flattened sources (or .txt)
    ledger.jsonl                    shared append-only ledger
    ada/  emmy/                     each peer's scratch directory
    <pair_id>.tex                   the consolidated note
    <pair_id>.verdict.json          verdict history, one entry per round
    status.json                     stage, round, status, reason
    receipts are campaign-wide, see below

Ledger entries are `{seq, at, actor, kind, text, supersedes}` with kinds
idea, finding, objection, correction, intention, ready, and review. The
runner writes review entries; peers write the rest through a helper command.
Readiness names the latest entry seen; a later substantive entry reopens it.

Stages of a thread:

1. Peers. Ada and Emmy start together as concurrent CLI calls confined to
   the thread directory. Tools: file reading under `inputs/` and their own
   scratch directory, the ledger helper, and web search when
   `peer_search` is on. A peer that returns without readiness is relaunched
   on the same ledger while allowance remains. The stage ends when both
   are ready against the latest substantive entry or the allowance is spent.
2. Consolidate. Ada writes `<pair_id>.tex` from the ledger as it stands,
   whether or not readiness was reached. A thin note that says what stayed
   open is valid. An empty ledger skips consolidation and verification and
   ends the thread as PAUSE with reason `empty ledger`.
3. Verify. A fresh tool-less call reads the inputs, the ledger and the note
   and returns DRAFT, ITERATE or PAUSE with a reason and, for ITERATE, one
   action. ITERATE appends a review entry, clears readiness and returns to
   stage 1 with the round counter incremented. At the round cap, three by
   default, ITERATE becomes PAUSE-ON-ITERATE.

Terminal statuses: DRAFT, PAUSE, PAUSE-ON-ITERATE. Those are the only
outcomes a human is asked to look at. BLOCKED is a machinery state for the
reconcile command and never a scientific decision.

Allowances are per stage and per round: peer seconds in aggregate, peer
calls each, consolidate seconds, verify seconds.

## Runner

`pathfinder research` is a loop in one terminal. It holds `seats` threads,
four by default, admits the next shortlisted pair whenever a seat frees, and
skips threads already terminal, so restarting is idempotent. One lock file
per thread prevents two runners or a reconcile call from double-working a
pair.

Every model call appends to `receipts.jsonl`: thread, stage, actor, backend,
model, seconds, input tokens, output tokens, cost. Cost is the CLI's reported
figure where it gives one, else tokens times the list price table in
`campaign.json`. Spend is always the sum of receipts.

Budget guard: before each admission and each call, the runner adds receipts
to the allowance of calls in flight. Over the cap, it writes `stop.json` and
refuses. Overshoot is bounded by what is already running. `pathfinder stop`
writes the same file.

Every stop is a drain. On `stop.json` or Ctrl-C the runner admits nothing
new, lets in-flight calls finish and write their receipts and ledger
entries, records each thread's status, then exits. Removing `stop.json` and
rerunning resumes.

Transport failure: a call with no session id after 60 seconds is killed,
recorded as `transport_failed` at zero cost outside the thread's call count,
and retried once after 30 seconds. Two in a row set `health.json` and pause
admissions until a probe call succeeds.

Stage failure: a consolidate or verify that times out or returns nothing
readable reruns once within its allowance; a second failure sets BLOCKED
with the reason in `status.json`.

`pathfinder reconcile [PAIR] [--apply]` inspects a thread (process alive or
gone, ledger, note, verdict) and reports the one safe action: resume peers,
run consolidate, run verify, record terminal, or nothing. `--apply` does it.
No per-incident flags.

## Transport

`transport.call(prompt, *, backend, model, tools, cwd, timeout)` returns
text, session id, seconds, tokens and cost. Two backends: the Claude Code CLI
(`claude -p`, JSON output) and the Codex CLI (`codex exec --json`). The
subprocess environment is scrubbed of API keys; the backends use the user's
CLI login. No model or backend fallback: a capacity or auth failure stops
admissions rather than substituting.

## Monitor

`pathfinder serve` runs a standard-library HTTP server on localhost. `/`
serves one page; `/state` recomputes a JSON document from the campaign
files on each request and the page polls it. The monitor writes nothing and
the runner does not know it exists. Panels:

- Campaign: phase, spend against cap, wall time, seats, stop and health
  flags, threads by status.
- Scan: Q by P heat map of the score product, row and column summaries,
  score distribution, the cut line; coverage and cost per row while running.
- Shortlist: one line per pair with status, round, stage, calls, seconds,
  spend, and links to its ledger, note and verdict.
- Thread: the ledger in order with actor and kind, counts by kind and actor,
  gaps between entries, verdicts by round.

`pathfinder status` prints the campaign and shortlist panels as text from
the same state function.

## Configuration

`campaign.json` at the campaign root:

    backend, model, peer_search, seats, cut, rounds,
    allowances {peer_seconds, peer_calls, consolidate_seconds, verify_seconds},
    budget_usd, prices {model: {input_per_m, output_per_m}},
    scan {fulltext: null | "q" | "p" | "both"}

## Layout

    pathfinder/
      README.md
      pyproject.toml         uv, Python 3.12, no third-party dependencies
      pathfinder/
        corpus.py  transport.py  scan.py  select.py  ledger.py
        research.py  runner.py  reconcile.py  monitor.py  cli.py
      prompts/
        scan.md  peer.md  consolidate.md  verify.md
      tests/                 offline, with a fake CLI binary
      campaign.json          the reference campaign lives at the repo root

## Test campaign

Q: the five most recent arXiv papers on mechanism design. P: the five most
recent on agentic cooperation. Cut 12 percent, so three threads. The aim is
functionality, not science: every stage runs, a stop drains, a killed peer
reconciles, the monitor shows all of it.

## Prompts

The four prompts are the scientific content of the template and are kept
as separate files so they can be reviewed and retuned without touching
code. The versions agreed on 11 September 2026 are the initial contents of
`prompts/`; the scan prompt scores two independent axes as in the agQSL v7
judge, the peer prompt is a domain-neutral cut of the E-prime researcher
prompt with web search allowed, the verify prompt returns one of three words.

## Departures from the agQSL instance, recorded for the design rationale

- Phases B, C, D and E are gone. The scan hands directly to peer research,
  as the Julien campaign already does.
- ITERATE loops automatically up to a cap instead of asking an owner.
- Peers may search the web, with a citation rule.
- One transport adapter with two CLI backends; no proxy route.
- No document store, no pane titles, no cross-campaign coordination
  registry. One campaign per directory.

## Out of scope for step 1

Mixed corpora (patents, reports), row synthesis, publishing state to a
remote page, multiple campaigns per checkout, the builder prompt (step 2).

## Reference run, 11 September 2026

Campaign: `backend` claude, `model` claude-opus-5, `scan_model`
claude-sonnet-5, `cut` 12, `rounds` 3, `budget_usd` 60. Corpora fetched
with `pathfinder fetch --q "mechanism design" --p "agentic cooperation" --n 5`;
the arXiv `all:` query is loose, so both sides are a mixed bag, which is what
the functionality test wanted.

Q: 2609.04787, 2609.02872, 2609.02580, 2609.01595, 2608.30499.
P: 2609.04460, 2608.23650, 2608.18167, 2608.08330, 2607.28002.
All ten e-prints were TeX and flattened with `latexpand`; none needed
`pdftotext`.

Scan: 25 pairs, 27 calls (two replies were unparseable and retried), 0.82
USD, 256 model seconds. Scores (feasibility times gain) ranged from 0 to
2100; the cut at 12% took three pairs:

| pair | Q | P | feasibility | gain | score |
| --- | --- | --- | --- | --- | --- |
| Q4P3 | 2609.01595 Mechanism Design for Alignment and Control | 2608.18167 Adversarial Review | 60 | 35 | 2100 |
| Q1P1 | 2609.04787 Learning-Augmented Algorithms | 2609.04460 Distributed risk-averse optimization via CVaR | 55 | 35 | 1925 |
| Q3P3 | 2609.02580 Competitive Market Behavior of LLMs | 2608.18167 Adversarial Review | 55 | 35 | 1925 |

Research, as it ended:

| pair | status | rounds | ledger entries | calls | model minutes | USD |
| --- | --- | --- | --- | --- | --- | --- |
| Q4P3 | PAUSE | 2 | 27 | 15 | 112 | 29.73 |
| Q1P1 | PAUSE | 1 | 28 | 8 | 88 | 27.16 |
| Q3P3 | PAUSE-ON-ITERATE (Opus round 1, then Codex via ELM) | 3 | 39 | 19 | 47 | 14.02 |
| Q1P2 | DRAFT (Codex, gpt-5.6-sol via ELM, added later at cut 16) | 2 | 36 | 12 | 13 | 7.43 |

Total spend 66.58 USD over 52 receipts; wall time from the first scan call
to the last verify call 2 h 38 min, of which about 1 h was the operator
drain and restarts described below. Both notes compile clean under
`pdflatex` with article class and amsmath only (11 and 13 pages). The
verifier's reasons are in each `<pair>.verdict.json`; both PAUSE verdicts
say the same thing in different words: the peers proved things about one
paper and connected them to the other by analogy, so the pair itself does
not yet carry a result.

What the run exercised, in order:

1. Three threads admitted at once on four seats; six peer calls in flight.
2. `pathfinder stop` after 25 seconds: no new admission, all six calls
   landed over the next 19 minutes (each 5 to 12 minutes, 3.5 to 5.4 USD),
   every thread checkpointed as `stopped` at the peers stage, locks
   released, runner exited.
3. `stop --clear` and `research` again: `reconcile` named `resume peers` for
   all three; the runner resumed Q4P3 at its recorded stage.
4. The first consolidation of Q4P3 timed out at 600 seconds with no note.
   The runner was then killed by hand (SIGKILL, plus its model process)
   during the retry. `reconcile` saw the dead lock and named
   `run consolidate`; `reconcile Q4P3 --apply` finished the thread through
   ITERATE, a second peer round, a second consolidation and a PAUSE.
5. `research` again admitted Q1P1, which ended PAUSE in one round, then
   refused Q3P3: spend 66.58 plus one call estimate of 5 projected 71.58
   against the cap of 60, so the guard wrote `stop.json` and the runner
   exited. Q3P3 stays at `stopped at peers` until someone raises the budget
   and runs `research` or `reconcile Q3P3 --apply`.

What had to change on the way:

- Port 8765 was taken on this machine; the monitor default moved to 8790.
- Peer calls cost about 5 USD, not 2: `call_estimate_usd` went to 5,
  `peer_calls` to 2 and `seats` to 1 for the resume so the guard could bite
  between threads. The guard is admission-time only, by design, which is
  why the total overshot the cap by 6.58 within the last admitted thread.
- `consolidate_seconds` went from 600 to 1800 and `verify_seconds` from
  600 to 900: consolidations took 895 and 1344 seconds.
- A timed-out call reports no usage; it is now charged at
  `call_estimate_usd` so the guard does not undercount.
- A consolidation that timed out after writing its note is no longer rerun.
- A peer whose ready declaration stands now waits for its partner instead
  of spending a call.
- `reconcile --apply` now consults the budget guard.
- Three resumed peer calls were refused by an API safeguard
  (`reasoning_extraction`), each in 2 to 3 seconds for 0.05 USD; the
  refusals were intermittent and the threads carried on with the other
  peer. The one sentence those calls add, the resume line, was reworded.
- The peer allowance is per runner invocation, not per round: a resumed
  thread starts its peers with a fresh `peer_calls` and `peer_seconds`. Left
  as is; it is simple and the guard bounds it.
- Scan receipts are excluded from the per-thread spend shown by the
  monitor.

Added afterwards: the cut widened to 16% to admit Q1P2, run on the Codex
backend through the ELM proxy; it ended DRAFT after two rounds in six
minutes of wall time, and its paper stage reached ACCEPT in three rounds
for 8.36 USD. Q3P3 resumed on Codex from its Opus ledger and ended
PAUSE-ON-ITERATE after three rounds. One explore pass then grew the grid
to 10 by 10 and a threshold of 1500 admitted nine more pairs, of which
Q4P10 and Q3P9 ran on Codex to PAUSE before the guard stopped admissions
at the 100 USD cap. The health flag, the interrupt drain, both BLOCKED
paths and prompt override are covered by tests with the fake CLI. Not
exercised: `scan.fulltext` and the PDF-only path. The pilot report,
`2026-09-11-pilot-report.md`, holds the lessons.
