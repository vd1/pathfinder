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
  Leave it out to use the ChatGPT login. `"search": "config"` passes web
  search as `web_search` configuration instead of the `--search` flag;
  `"search": "always"` lets a tool-less call search too. `"config"`: a list
  of further Codex settings, each passed with `-c`.
- `stage_attempts`: attempts for consolidation and verification (default 2);
  a value that is not a positive integer fails before any call.
- `strict_evidence`: `false` by default; only for composable schemes
  (`research_scheme`, `research_bundles`), whose review stages inline every
  file in the peers' directories and every file the ledger cites. A cited
  path that leaves the thread, uses `..` or goes through a symlink always
  blocks the thread. Otherwise a missing file is named as missing and a
  binary or oversized file (`evidence_max_bytes`, default 300000) is listed
  with its size and digest; with `strict_evidence` both block the thread.
- `research_scheme`: absent for the classic single-engine EVA thread;
  `direct_eva` (formerly `eva_minus`, still read with a warning: the peers research, Vera reviews the
  ledger directly and issues requests, no synthesis; the thread ends HANDOFF);
  `eva` with `research_bundles` for a joint thread over frozen bundles; or
  `composable`: each pair runs as `branches` direct-EVA branches (default 3,
  in `threads/<pair>/branch-runs/<label>/`), each handoff is frozen read-only
  into `threads/<pair>/branches/<label>/` with a `bundle.json` inventory, and a
  joint EVA thread then researches over the bundles in the pair's directory,
  followed by the usual edit and paper. Optional `branch` and `joint` blocks
  override any campaign key (typically `rounds`, `ledger_reviews`) for the
  branches or the joint thread. `branches/metrics.json` records Vera's
  rejection rate and the divergence between branches.
- `parent`, `extensions`, `deployment`, `stub`: see "One engine, many
  deployments" below.

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

### Local failure alerts and supervision handoff

Runner failures, blocked research, and supervision ending with `needs_operator`
write `alert.json` and append `alerts.jsonl`, print a terminal alert, and attempt
a macOS desktop notification without calling a model. Thus failed model
authentication does not prevent the timer from alerting. Desktop delivery is
best effort: macOS notification permissions and Focus settings may hide it.
`submitted` means the notification command succeeded, not that the user saw it.
Other platforms retain the terminal and file alerts. Disable desktop attempts
with `"notifications": {"desktop": false}` in `campaign.json`.

This is not an independent watchdog for a killed timer or a sleeping host.
Notification failures are recorded and do not mask the original pipeline error.
No email, network notification service, or background system service is installed.

Extend an active watch without relaunching research:

```sh
uv run python -m pathfinder.supervise --root CAMPAIGN --extend-hours 6
```

The request targets the current session only. Check `extension_id` and
`deadline_at` in `supervision/latest-session.json` to confirm it was applied.
The timer checks between audits and at most five seconds apart while waiting;
an ongoing audit must finish first. Request extensions before the deadline.
An expired or failed watch requires a new session, not an extension request.

If research is still running after its watch ends, inspect its recorded PID and
process identity, then attach a new watch without starting another runner:

```sh
uv run python -m pathfinder.supervise --root CAMPAIGN --attach-pid PID \
  --hours 6 --scope 'Research and editing for this campaign' \
  --resume-command 'uv run pathfinder --root CAMPAIGN research'
```

Attachment requires a PID matching campaign evidence and available process
identity information. It pins that identity while watching, refuses an active
timer or stop marker, and does not signal or launch the attached runner.
The explicit PID still needs operator inspection, especially for legacy records
or possible PID reuse before attachment. For an exited runner, use the normal
start/resume command instead. Include author/reviewer stages in scope and the
resume command when the campaign runs a full pipeline.

### Saved verdict repair

An explicitly authorized supervisor can use `--allow-verdict-repair`, or an
operator can run:

```sh
uv run pathfinder --root CAMPAIGN repair-verdict Q1P1
```

This repairs only illegal JSON string escapes in an existing completed PAUSE
or DRAFT verifier reply with a reason and null action. It matches the saved
reply to its receipt, preserves the raw reply and research note, records
before-state and hashes under `supervision/repairs/`, and logs the intervention.
It makes no model call, changes no judgment, and leaves editing/paper work for
the normal resume path. Live owners, active calls, stops, duplicate round
verdicts, ambiguous content and unsupported verdict transitions are refused.
Inspect descendants before repair. If interrupted between checkpoint writes,
use the preserved before-state for explicit reconciliation rather than bypassing
the duplicate-round guard.

Accepted papers and completed edits may still carry unresolved reference checks.
These remain visible in `health --json` and its text warnings; acceptance does
not silently certify a failed external lookup.

### Shared engine used by statarb

The sibling statarb adapter, `arxiv_drip/research_protocol.py`, freezes this
repository's `pathfinder/` package and prompts into each new investigation by
default (or uses its configured `pathfinder_root`). No second maintained engine
needs copying. New jobs therefore inherit these fixes; existing frozen jobs do
not. Its paper-to-strategy dossier, subscription accounting, persisted sessions,
data contracts and trading controls remain statarb-specific. Merely inheriting
supervision commands does not enable an Astra timer in statarb's worker.

The local transport now distinguishes recoverable reconnect events from terminal
failure: a successfully completed turn and successful process exit can clear a
transient error, while raw events remain in the receipt. A terminal failure,
nonzero exit, timeout, or absent completion event still fails the call. This
adopts statarb's final-outcome discipline without importing trading behavior.

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

## One engine, many deployments

statarb, in-repository experiments and other campaigns run this engine
rather than editing copies of it (see
[the plan](plans/2026-09-27-1809-single-engine-deployments.md)). A deployment
adjusts it only through:

- settings in `campaign.json`;
- prompt overlays and a `styles/` directory, as above;
- extensions named in `campaign.json` and loaded from the deployment's own code:
  `"extensions": {"path": "deploy", "admission": "mypolicies:budget",
  "snapshot_extra": "mymonitor:extra", "transport": "mydispatch:execute"}`.
  A `transport` extension is a deployment's own dispatcher: the engine still
  admits each call, records it and writes the receipt. A `panels` extension,
  `panels(campaign)`, returns the deployment's own boxes for the operator
  page, drawn in the page's designs by `kind`: `"table"` (`columns`, `rows`),
  `"cards"` (`cards` of `status`, `badge`, `meta`, `title`, `summary`, `issue`,
  `actions`; `"grid": true` for a card grid), `"metrics"` (`items` of `label`,
  `value`, `small`) or `"pipeline"` (`stages` of `title` and `states` of `key`,
  `label`, `count`). Cells and actions are text, numbers, `{"text", "href"}`
  with an `https` link, or `{"text", "pdf"}` with a PDF's path, which the page
  opens in the operator's own viewer (as it does a unit's PDF). Every box on
  the page can be collapsed; the browser remembers which. `consumer` and `failure_rules` are
  described above. Extension code is trusted; the engine validates what it
  returns. Each deployment's modules need unique names.

**Admission.** Every model call is admitted inside an engine-owned
reservation. Under one lock the engine checks the campaign's stop marker and
its parent's (`"parent": ".."` in a child campaign), asks the admission policy,
and reserves. A policy returns admit, defer or stop;
`pathfinder.admission:budget_per_call` is built in. A refused call gets a
receipt with outcome `refused` and no cost, and is a stop, never a failure.

**Bounded runs.** `pathfinder research --pairs Q1P1 Q2P3` runs exactly those
pairs. `runner.run_pair` takes one pair through research, edit and, for a
DRAFT, the paper, resuming where it stands. `pathfinder coordinate
schedule.json` runs a fixed schedule of (arm, pair) entries across child
campaigns one pair at a time; the schedule is recorded in
`coordination.json`, and a changed schedule needs `--accept-change`. A
`"batch"` block (`deadline`, `max_units`, `max_consecutive_failures`) bounds
it. With `"next_unit": "module:callable"` (and `"path"`, relative to the
schedule, put on `sys.path` with the same safeguards as extensions), the
coordinator asks the deployment for each unit after the fixed schedule:
`next_unit(arms, progress)` returns `{"arm", "pair"}` or `None`;
`progress["done"]` lists the units run or found finished in this run.

**Shared seats.** Campaigns on one subscription name it:
`"account": {"name": "codex-main", "seats": 6}`. A call then holds one seat
of the account, across every process, from admission to its end; the pool
lives in `$PATHFINDER_ACCOUNTS` (default `~/.pathfinder/accounts`), one
reservation file per call, reaped when its process is gone. One account has
one seat count: a campaign naming it with another count is refused. A call
waiting for a seat emits `admission_deferred`.

**Sources that throttle agents.** Every receipt counts the rate-limit answers
the agents met in their own tool calls (`source_limits`, arXiv for now);
`pathfinder health` warns about the last 50 calls and the playbook gives the
apex agent an action.

**Run records.** Every command that calls a model takes campaign ownership
and writes `run.json` (appended to `runs.jsonl`): engine commit and a digest
of the files it loaded, deployment files and lock, extension code, resolved
settings, composed prompts, styles, TeX and corpus. Receipts name the run.
When any of these changed since the previous run the command refuses until
rerun with `pathfinder --accept-change REASON ...`; code edited on disk after
the process loaded it requires a restart.

**Frozen copies.** `pathfinder freeze DIR --ref engine-vX.Y` writes the
engine's runtime files at that commit; `pathfinder verify-frozen DIR`
compares a copy with the commit's own tree and reports verified, modified
or unverifiable.

**Model-free runs.** `"backend": "stub"` drives every stage with
deterministic replies and real builds, for contract tests.

**Releases.** `deployments.toml` lists every live deployment, pinned, as
supported or not yet supported. `uv run python scripts/release_check.py`
runs the suite with `PATHFINDER_RELEASE=1` and fails on any failure, skip,
missing or mispinned supported deployment, or change to the candidate
during the run.

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

The prompts in `prompts/` are the place to tune behaviour: `scan.md`
(the two-axis judge), `peer.md` (the creative brief), `consolidate.md`,
`verify.md`, `author.md`, `review.md`, `editor.md` and `supervisor.md`. An
installed engine carries them inside the package. A campaign adjusts them
one file at a time: for role R, the campaign's `prompts/R.md` replaces the
engine's prompt, `prompts/R.append.md` is appended to whichever prompt
applies, and placeholders such as `{{ACTOR}}` are filled in last. Roles
without a campaign file use the engine's prompt.

## The thread's context

Every stage of a thread runs with file tools in the thread's directory.
The researchers get links: the paths of the two papers and the ledger,
which they read as much as they need. The consolidator and the verifier
get the two papers, the ledger and the current account inline, in that
order, with the instruction last, and are pointed at the peers'
directories and the files the ledger cites, which they read themselves.
The consolidator returns the account in its response. The two papers and
the ledger entries already present are the same bytes for both and from
one round to the next, so a prompt cache can serve that leading part;
nothing depends on a cache hit.

Two switches in `campaign.json`, both off by default, put material in
front of the researchers' calls, with their brief
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
a `\title`, and no other package. A campaign's own `styles/` directory is
searched first, by every build (edit, paper, restyle, the monitor) and by the
agents, so a deployment can replace `pathfinder-common.sty` or add a kind.

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

- One package, standard library only, with a terminal runner, optional
  bounded supervision, and local failure notifications; no required service.
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
