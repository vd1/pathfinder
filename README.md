# Pathfinder

Pathfinder takes two corpora of papers, Q and P, and looks for pairs (q, p) that
have something to say to each other. It runs in two phases:

1. **Scan.** A strong model scores every pair of the grid from titles and
   abstracts, on two axes (feasibility, gain). The top cut of the ranking is
   frozen as the shortlist.
2. **Research.** For each shortlisted pair, two peer agents with the full
   sources and a shared append-only ledger look for a publishable connexion.
   The first peer consolidates the ledger into a LaTeX note, an independent
   verifier returns DRAFT, REVISE, ITERATE or PAUSE; REVISE sends the note
   back to the consolidating peer for one repair without new research, and
   ITERATE loops back to the peers up to a cap.

Every thread ends with a ledger, a note named after the pair (for example
`Q2P3.tex`), a verdict history and a terminal status: `DRAFT`, `PAUSE`,
`PAUSE-ON-ITERATE` or `PAUSE-ON-REVISE`. The whole pipeline as a state
machine, with every transition's agent, prompt, visibility and budget, is
in `notes/pathfinder-engine.pdf`.

3. **Paper.** On a DRAFT thread, an author agent writes a short paper with
   BibTeX references, searching for prior work and verifying every
   reference; the pipeline builds it and checks the citations; an
   independent reviewer answers ACCEPT or AMEND, and AMEND sends it back to
   the author, up to a round cap. ACCEPT may carry minor findings, the kind
   an author applies while formatting; AMEND is for a finding that changes
   a claim, its scope, its attribution or its correctness. The paper ends
   ACCEPTED, or PAUSE-ON-AMEND when the cap is reached with amendments still
   asked for, the same shape as the thread's PAUSE-ON-ITERATE. A paper the
   owner has edited by hand gets one reviewer round without an author call
   through `pathfinder paper PAIR --review`; it counts as the next round and
   is not budgeted.

On every terminal thread an editor also rewrites the consolidated note as
a short readable paper with references, for a reader without the ledger
(`pathfinder edit`, or automatically from the runner).

## Requirements

- Python 3.12 and [uv](https://docs.astral.sh/uv/).
- One of the two agent CLIs, logged in: `claude` (Claude Code) or `codex`.
- `latexpand` (ships with TeX Live) to flatten arXiv sources, and `pdftotext`
  for the rare PDF-only e-print.

## Quick start

```bash
uv sync
uv run pathfinder fetch --q "mechanism design" --p "agentic cooperation" --n 5
uv run pathfinder sources
uv run pathfinder scan
uv run pathfinder select --cut 12
uv run pathfinder serve      # in a second terminal: http://localhost:8790/
uv run pathfinder research
uv run pathfinder status
uv run pathfinder paper         # for every DRAFT thread
uv run pathfinder paper Q1P6 --review   # one reviewer round on a paper you edited by hand
uv run pathfinder export report --zip   # a self-contained snapshot of the page and every document
```

Every command takes `--root DIR`; the default is the current directory, which
is the campaign directory. The repository root is itself a campaign, the
reference run described in `plans/`.

## Open-ended mode

Instead of a fixed grid and a percentage cut, a campaign can grow: page the
same arXiv queries backwards in time, scan only the new pairs, and admit a
pair to the shortlist when its score crosses a threshold.

```bash
uv run pathfinder fetch --q "..." --p "..." --n 5      # the first page, as above
uv run pathfinder explore --min-score 1500 --page 5 --passes 3
uv run pathfinder research                             # in another terminal, admits as the shortlist grows
```

Each pass appends the next `--page` older papers per side (never reordering
what is there, so pair ids stay valid), flattens them, scans the new pairs
and rewrites `shortlist.json` with every pair at or above `--min-score`.
`--passes 0` runs until `pathfinder stop`. `fetch --more N` and
`select --min-score T` are the two steps on their own. In the pilot, scores
of 1925 and above gave the threads that ran and 600 was the next; the scan
costs about three cents a pair.

## Campaign directory

```
campaign.json      configuration (see below)
fetch.json         the two queries and how far each side has been paged
Q.jsonl  P.jsonl   one paper per line: id, title, abstract, authors, date, text
sources/           flattened e-prints, <id>.tex or <id>.txt (ignored by git)
scan.jsonl         one row per scored pair, appended as the scan runs
shortlist.json     the frozen cut, with a digest of scan.jsonl
receipts.jsonl     one line per attempted model call, failures included; the only
                   source of spend figures (see Receipts below)
stop.json          present while a stop is requested
health.json        first operational failure of the latest research run
runner.json        run identity, PID, scheduler heartbeat, last completed investigation
runner.lock        OS-held research-runner lock; file existence is not ownership
active-calls/      per-attempt identity, owner/child PIDs, start time and nominal deadline
failures.jsonl     append-only runner failure records, retained across restarts
threads/<pair>/    inputs/, ledger.jsonl, ada/, emmy/, <pair>.tex,
                   <pair>.verdict.json, status.json, lock
threads/<pair>/paper/   paper.tex, references.bib, paper.pdf, search.md,
                   review.json, paper.json (ACCEPTED, PAUSE-ON-AMEND, blocked)
threads/<pair>/edited/  note.tex, references.bib, note.pdf, edit.json
```

The repository root is the reference campaign (Q "mechanism design", P
"agentic cooperation"). `experiments/3peers/` is a second campaign
directory of the same shape: the eight explore pairs run again with three
peers, compared against two in the pilot report. Point any command at it
with `--root experiments/3peers`; its `sources` is a link to the root's.

## campaign.json

`campaign.example.json` in the repository root is a working starting point
with no path leaving the campaign directory: copy it to `campaign.json` in
your own campaign directory and edit the models and the budget.

- `backend`: `claude` or `codex`. No fallback between them.
- `model`: model for peers, consolidation and verification.
- `scan_model`: model for the scan; defaults to `model`.
- `peer_search`: whether peers may use web search.
- `seats`: how many threads run at once.
- `cut`: percentage of scored pairs that make the shortlist.
- `rounds`: cap on verifier ITERATE loops per thread.
- `repairs`: cap on REVISE repair passes per thread (default 1).
- `paper_rounds`: cap on author and review rounds in the paper stage.
- `allowances`: `peer_seconds` (shared by both peers per round), `peer_calls`
  (per peer per round), `consolidate_seconds`, `verify_seconds`,
  `paper_seconds`, `review_seconds`, `edit_seconds`.
- `budget_usd`: cap on known cost, plus `call_estimate_usd` for every call in
  flight and every call that opened a session and whose cost is unknown.
- `call_estimate_usd`: what one in-flight call is assumed to cost by the guard.
- `prices`: per-model prices, in USD, used when the CLI reports no cost. A
  model missing from the table has unknown cost, not zero: the guard then
  counts each of its calls at `call_estimate_usd`, so price the models you use.
  An entry may also give `cached_input_per_m`: Codex counts cached tokens
  inside its input total, and with that rate they are priced apart. In the
  recorded Astra experiments nine input tokens in ten were cached, and flat
  pricing overstated the cost 4.5 times. The shipped table prices
  `gpt-6-astra` at OpenAI's published standard rates of 16 September 2026: 10,
  1 and 50 USD per million uncached input, cached input and output tokens.
  Those rates double for a request above 272,000 input tokens. Nothing is
  done about that tier, for two reasons: a receipt sums the requests of a
  call, so its input total can pass the threshold without any single request
  doing so, and the Codex CLI's context window, 258,000 tokens at that date,
  keeps a single request below it.
- `scan.fulltext`: `null`, `"q"`, `"p"` or `"both"` to scan with flattened
  sources instead of abstracts on that side.
- `codex`: optional, for the Codex backend through a custom OpenAI-compatible
  provider such as a university proxy: `name`, `base_url`, `env_key` (the
  variable Codex reads the key from), `key_file` (a dotenv file holding
  `env_key=value`, read into the child environment only) and `wire_api`.
  Leave it out to use the ChatGPT login.

## Stops, guard, failures, reconcile

- `pathfinder stop` writes `stop.json`. A running scan finishes its current
  call and exits; a running research loop stops admitting, lets calls in
  flight land, writes their checkpoints and exits. `stop --clear` removes the
  marker; the next `research` resumes every thread at its recorded stage.
- The budget guard runs before every admission: known cost, plus
  `call_estimate_usd` for each call in flight and each call that opened a
  session and whose cost is unknown, must stay under `budget_usd`, otherwise it writes the stop marker itself.
- A call that produces no session within 60 seconds, plus a second per
  5 KB of prompt, is a transport failure, and so is an agent CLI that cannot
  be launched: a receipt with no usage and no cost, the thread is marked stopped.
  Session-started timeouts also count as operational failures. The first failure
  observed by the research scheduler sets `health.json`, stops admissions, and
  drains active work before exiting nonzero. There are no automatic health probes.
  Editor failures propagate too; terminal research with unfinished editing stays
  pending. An explicit `research` invocation resumes it without repeating research.
  The previous failure remains in `failures.jsonl` and the new run's metadata.
- Threads are locked by a pid file. `pathfinder reconcile [pair]` names the
  one safe action for a thread (start, resume peers, run consolidate, run
  verify, or nothing) and `--apply` performs it.

### Five-minute supervising-agent audit

Run `uv run pathfinder --root CAMPAIGN health --json` at each audit, or omit
`--json` for a short human-readable view. This command is read-only. It exposes
the research runner's identity and heartbeat, active model calls with exact
pair/stage/actor and child PID, nominal deadlines, last successful call,
completed-investigation progress, unfinished editing, and recent errors with
paths to the evidence. Compare snapshots: a heartbeat or a completed model call
does not establish scientific progress. Repeated calls on the same stage can
still indicate a livelock. Old campaigns without instrumentation report unknown
runner liveness rather than healthy status.

The supervising Astra agent owns diagnosis, intervention, and the incident
ledger. The optional session-local timer below supplies its clock; nothing is
installed as a permanent service. At each
audit, inspect warnings and changes since the previous snapshot. A missing PID,
heartbeat older than five minutes, or overdue call is evidence for investigation,
not an instruction to kill a process. PID reuse, slow tools, and host suspension
can complicate interpretation. The deadline is the requested call allowance;
the existing transport's startup and cleanup can overrun it. The audit exposes
that overrun rather than promising a hard termination bound.

After a confirmed crash, inspect orphaned calls and any surviving child processes
before restarting. The research runner uses an exclusive OS lock, released on
process death, and refuses restart while recorded call owner or child PIDs remain
alive. Do not remove an active-call record to bypass this check. Descendants and
PID identity still require operator inspection before termination or restart.
Standalone `edit`, `paper`, and `reconcile --apply` commands retain their existing
coordination rules; do not run them concurrently with a research runner.

Record each intervention in the supervising agent's incident ledger: campaign
and run ID, detection time, evidence paths, observed versus suspected cause,
action taken, and the later evidence that progress resumed. `failures.jsonl`
records runtime errors, not the agent's diagnosis. Clear an operator stop with
`stop --clear` only when resumption is intended, then run `research` explicitly.
No five-minute audit schedule is enabled merely by adding this command.

### Campaign-scoped supervision session

From this checkout, launch the runner and its timer together:

```sh
uv run python -m pathfinder.supervise \
  --root /absolute/path/to/campaign \
  --scope 'Research and readable editing for the selected pairs' \
  --resume-command 'uv run pathfinder --root /absolute/path/to/campaign research' \
  -- uv run pathfinder --root /absolute/path/to/campaign research
```

The start command follows `--`. The resume command is parsed as arguments and
executed without a shell. For a campaign that includes author/reviewer stages,
supply its full pipeline launcher and resume command and name those stages in
`--scope`; research completion alone is not full pipeline completion. Preserve
a frozen experiment's launcher and engine rather than substituting this example.

The timer is a foreground process for this campaign session, not a desktop task,
cron job, or installed service. It launches GPT-6 Astra through
[Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
at five-minute intervals, with an earlier audit when its original runner exits.
Each audit receives saved snapshots and process evidence; the incident ledger
carries context between audit invocations. Audits are serial, missed ticks are
skipped, and the timer ends when Astra reports completion or needs operator input.
It refuses a completion report that conflicts with a recorded live runner/call.

Keep the terminal session and Mac available. `--interval` defaults to 300 seconds,
`--audit-timeout` to 240 seconds, and `--hours` to a six-hour session ceiling.
These limits bound the timer's activity, not model billing. A timed-out or failed
audit ends supervision visibly; it does not kill the campaign runner. Ctrl-C
requests a campaign stop and ends the timer; active work may still be draining.
A killed timer or sleeping host does not provide an independent watchdog.

Evidence lives under `supervision/`: `latest-session.json`, a session directory
with runner logs and state, per-audit before/after snapshots, filtered process
evidence, agent event logs and structured results, and `incidents.jsonl` written
by Astra. A campaign-level timer lock prevents overlapping supervision sessions.
The audit stays sandboxed. If the timer cannot obtain process evidence, or the
audit lacks permission to perform a safe recovery, it must ask the operator.

The reusable audit instructions are in [prompts/supervisor.md](prompts/supervisor.md).
Assign the campaign directory and its documented resume command when creating
the task. The [scheduled-task documentation](https://learn.chatgpt.com/docs/automations?surface=app)
places task management in the desktop app or web, not the Codex CLI. A task
auditing local campaign files needs access to this checkout and those files.

For an isolated recovery drill, `tests/supervision_trial.py` accepts `prepare`,
`crash`, or `resume`, followed by an empty test directory for preparation or the
prepared directory thereafter. The drill runs the real research scheduler with
a deterministic editor double: `crash` exits the runner with code 23 during
editing, and `resume` finishes only that fixture stage. It produces no scientific
result or model calls. An agent audit can diagnose the failure and record an
incident before invoking resume. This proves neither recurring task delivery
nor recovery of an arbitrary infrastructure fault.

## Receipts

Every call the transport attempts appends one line to `receipts.jsonl`,
including a CLI that cannot be launched, a call that never opens a session
and a call killed at its deadline. A receipt holds `v` (2), `at`, `thread`,
`stage`, `actor`, `backend`, `model`, `seconds`, `outcome` (`completed`,
`error`, `timeout`, `no session`, `launch failed`), `error`, and:

- `usage`: the provider's usage counters exactly as it reported them, or
  null when none arrived. On a call that did not complete they may be
  partial. The two CLIs count differently (Codex's `input_tokens` includes
  its cached tokens, Claude's does not), which is why the raw object is kept.
- `input_tokens`, `output_tokens`, `cache_write`, `cache_read`,
  `prefix_read`: the same counters under common names for the monitor. A
  counter that was not reported is null, never zero.
- `cost` in USD and `cost_basis`: `reported` by the CLI, or `priced` from the
  reported counters with the campaign's table, in which case `rates` holds
  the rates applied. A priced amount is an approximation: it ignores cache
  writes and any long-context tier. When neither is possible both are null.

Nothing in a receipt is an estimate. The guard's caution about calls of
unknown cost lives in the guard, which does not charge a call that never
reached a session. The monitor shows known cost and, beside
it, how many calls have unknown cost. Receipts without `v` predate this
format; in them a zero may mean unknown.

## Prompts

The seven prompts in `prompts/` are the place to tune behaviour: `scan.md`
(the two-axis judge), `peer.md` (the creative brief), `consolidate.md`,
`verify.md`, `author.md`, `review.md` and `editor.md`. A campaign directory may carry its own `prompts/` to override
them.

## The thread's context

The researchers and the consolidator get links: the paths of the two
papers and the ledger, which they read through their tools, as much as
they need. The two judges get their material inline, in the same order,
the two papers, the ledger, the note, then for the reviewer the search
record, the paper and the checks, and the instruction last. The two papers
and the ledger entries already present are the same bytes for both judges
and from one round to the next, so a prompt cache can serve that leading
part; what follows it, the new entries, the note and the instruction,
changes. Nothing depends on a cache hit.

Two switches in `campaign.json`, both off by default, put material in
front of the researchers' and the consolidator's calls, with their brief
after it: `inline_papers` for the two papers, `inline_ledger` for the
ledger as it stood when the call began (the read command then starts
from its last entry). They are separate so that either effect can be
tested alone. Off by default because a researcher given the whole of both papers
reads all of it and tends to audit the papers rather than work the pair,
and on a long tool-using session the head is re-read on every turn, which
a cache makes cheaper but not free. Receipts record `cache_write`,
`cache_read` and `prefix_read` (the first turn's cache hit) so the effect
can be measured rather than assumed.

## Styles

The three LaTeX documents each load one style from `pathfinder/styles/`:
`pathfinder-note` for the consolidated note, `pathfinder-readable` for the
readable note, `pathfinder-paper` for the paper. Each loads the maths,
hyperref and url packages, opens the document with the pair, the two
papers' titles linked to their arXiv abstracts, the date of production and
the thread's state (its ending or round, and how many ITERATE and REVISE
so far), prints a running header with the kind, the pair and the date, and
provides the theorem
environments the prompts allow; the note style also has `\ledger{12, 15}`
for citing ledger entries. The opening block comes from
`pathfinder-meta.tex`, which the pipeline writes beside each document
before the agent is called and again after every verdict, so no agent
types a title-block value; the style reads it if present. The pipeline
puts the styles directory on `TEXINPUTS` for its own builds and for the
agents' shells, so a document only needs `\usepackage{pathfinder-paper}`,
a `\title`, and no other package.

`pathfinder restyle` rebuilds every note, readable note and paper PDF of a
campaign with the current styles. Documents written before the styles
existed are built from a restyled copy in the scratch directory: the
packages and theorem environments the style provides are dropped, the
author and date are left to the style, and the plain bibliography style
becomes plainurl. The sources themselves are never rewritten, because every
verdict and review records the digest of the text it judged. The metadata
file carries each document's own production date, taken from the last
verdict, the editor's status and the paper's status. The monitor builds
notes the same way on demand.

## Departures from the agQSL instance

- One package, standard library only, one loop in one terminal; no
  supervisors, services or notification files.
- Receipts are the only spend figure; there is no separate cost model.
- Stops are always drains; there is no forced kill short of a second Ctrl-C.
- ITERATE loops automatically up to `rounds`; nothing waits for a human.
- The monitor is a live page served from the campaign directory, not a
  static HTML rebuilt on a schedule; `export` writes the same page with
  the state inline and every thread's documents beside it, so a campaign
  can be handed over as one zip. A "decision queue" table at the top
  lists every thread or stage waiting on a person, with reason, age and
  the one safe action. It renders TeX mathematics in ledger
  entries and verdicts written with `\(...\)`, `\[...\]` or `$$...$$`
  through KaTeX from a CDN when online; plain text otherwise.

## Building your own

`BUILDER.md` holds a prompt a colleague can paste into Claude Code or Codex
to have an agent build a pipeline like this one in their own stack, with the
decisions that matter and what the pilot taught written in.

Licence: MIT.

## Built with Shipshape

This repository uses [Shipshape](https://github.com/dmytri/shipshape), a context-isolated spec-driven workflow for coding agents. Install with `npx skills add dmytri/shipshape --skill '*'`, or the experimental open-plugin build with `npx plugins add dmytri/shipshape`.
