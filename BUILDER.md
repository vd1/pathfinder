# Building your own Pathfinder

Two ways to run this on your own corpora.

**Route A, use this repository.** Clone it, follow the README, point
`fetch` at your two queries or drop your own `Q.jsonl` and `P.jsonl` in a
campaign directory. Nothing below is needed.

**Route B, have an agent build one for you.** Paste the prompt below into
Claude Code or Codex in an empty directory, fill in the bracketed parts, and
let it work. It describes what to build, the decisions that matter and the
things the pilot taught, and it points at this repository for the prompts
and the spec. The agent may build in any language and tooling you prefer.

---

## The prompt

I want a small pipeline that looks for research connexions between two
corpora of papers. Build it here, in [language and tooling, e.g. Python 3.12
with uv, standard library only], for me to run from a terminal with my
[Claude Code | Codex] subscription. Keep it simple: plain files for all
state, one process per command, no services, no database, no framework.
Read the design and the prompts at https://github.com/vd1/pathfinder: the
state machine in `plans/2026-09-12-state-machine.md` is the shape to
build, with every state, transition, agent, prompt, what each agent sees
and writes, and the budget of each loop; the spec in
`plans/2026-09-11-pathfinder-design.md` and the pilot report in
`plans/2026-09-11-pilot-report.md` carry the reasons; the seven prompts in
`prompts/` may be copied verbatim. Do not copy the code; write yours.

### What it does

Two corpora, Q and P, each a list of papers with id, title, abstract and,
where available, the full text. Mine are: [two arXiv queries, or two files
you already have, or a description of where the papers come from].

1. **Scan.** Score every pair (q, p) with a strong model from titles and
   abstracts, one call per pair, no tools, using the scan prompt: two axes,
   feasibility and gain, each 0 to 100, score is their product. Enumerate
   Q rows in order so the prompt prefix caches. Append every result to one
   JSONL file so the scan can stop and resume. Keep the top cut (a
   percentage) or every pair above a threshold as the shortlist, frozen
   with a digest of the scan file.

2. **Research.** For each shortlisted pair, a thread directory with the two
   full texts, an append-only ledger, and two peer agents with tools and web
   search running concurrently on the peer prompt. Peers write ideas,
   findings, objections, corrections and intentions to the ledger through a
   small helper command, and declare ready naming the latest entry they
   read; a new substantive entry reopens readiness. When both are ready or
   the allowance runs out, the first peer consolidates the ledger into a
   LaTeX note named after the pair. An independent tool-less verifier reads
   everything and returns one of four words: DRAFT; REVISE when the ledger
   supports the result but the note misstates it, which sends the note back
   to the consolidating peer for one repair without a peer round; ITERATE
   when a specific gap stands in the way and the peers can close it with
   what they have, which loops back to the peers automatically up to a cap
   of four rounds; PAUSE otherwise, including when the gap needs data or
   experiments the peers do not have, with the missing input named, and
   when a previous ITERATE asked for the same thing and it was not
   supplied. At the round cap the thread ends as PAUSE-ON-ITERATE, at the
   repair cap as PAUSE-ON-REVISE. An empty ledger ends the thread as
   PAUSE. The terminal statuses are exactly DRAFT, PAUSE, PAUSE-ON-ITERATE
   and PAUSE-ON-REVISE; every PAUSE-ON-X means the loop named X ran out of
   its budget with the judge still asking, and a human can raise the
   budget and resume. The peers receive the scan judge's
   connexion sentence and rationale as a first hypothesis; a consolidation
   after ITERATE keeps the prior note's results and appends; every verdict
   records the digest of the note it judged.

   After any terminal verdict, an editor call rewrites the consolidated
   note as a short readable paper with BibTeX for a reader without the
   ledger: title, abstract, the two papers in plain words, what was done,
   results, what did not hold, why the thread stopped, references limited
   to Q, P and the sources the ledger cites. The pipeline builds it and
   refuses a wrong reference title, telling the editor the right one.

3. **Paper.** On a DRAFT thread, an author agent with tools and web search
   writes a short paper with BibTeX references from the note and ledger,
   searches for prior work on the specific result, records its queries,
   verifies every reference against arXiv or a DOI, and builds with
   latexmk. The pipeline rebuilds, checks that every citation exists and is
   used and that arXiv titles match the API, and an independent reviewer,
   shown the author's search record, returns ACCEPT or AMEND with findings
   by id, up to three rounds; the paper ends ACCEPTED or PAUSE-ON-AMEND,
   mirroring the thread's endings; every review records the paper's
   digest.

4. **Open-ended mode.** Instead of a fixed grid and a percentage cut, the
   campaign can grow: page the same queries backwards in time appending
   older papers without reordering (so positional pair ids stay valid),
   flatten and scan only the new pairs, and rewrite the shortlist as every
   pair at or above a score threshold, keeping any pair whose thread has
   started. One `explore` command does a pass; the runner in another
   terminal admits as the shortlist grows.

### The decisions that matter

- **Receipts are the only spend figure.** Every model call appends one line
  with stage, actor, model, seconds, tokens, cost and error. Spend is the
  sum. Costs from the CLI are API-equivalent even on a subscription.
- **A budget guard, soft by design.** Before admitting a thread, spend plus
  calls in flight times a per-call estimate must stay under the cap;
  otherwise write a stop marker. It does not interrupt a running thread.
- **Every stop is a drain.** A stop marker (written by the operator, the
  guard, or the first Ctrl-C) stops admissions; calls in flight land and
  write their checkpoints; the runner exits. A second Ctrl-C aborts.
  Restarting resumes every thread at its recorded stage.
- **Transport.** One adapter over the agent CLI: prompt on stdin, streaming
  JSON out, session id parsed from the first event. No session within 60
  seconds plus a second per 5 KB of prompt is a transport failure: no
  receipt, thread marked stopped, no retry inside the thread. Two in a row
  set a health flag; admissions pause until a probe call succeeds. Never
  fall back to another model or backend.
- **Stage failures.** A consolidation or verification that times out or
  returns nothing is rerun once, unless its output already exists. An
  unreadable verdict blocks the thread. One `reconcile` command inspects a
  thread and names the one safe action (start, resume peers, run
  consolidate, run verify, or nothing), and applies it on request.
- **Locks.** One pid file per thread directory; a dead pid is not a lock.
- **Monitor.** A local HTTP server on 127.0.0.1 serving one page that polls
  a state document every few seconds. A pipeline strip (pairs scanned,
  shortlisted, threads finished, drafts, papers accepted) and a budget bar;
  the scan as a heat map with the shortlist outlined and labels linking to
  arXiv; a shortlist table with status pills and buttons for the readable
  note, the paper and the verified note as PDFs; an outputs grid of the
  finished threads; and a thread panel, addressable by URL hash, with the
  ledger rendered in the page and filterable by actor, verdict cards, the
  paper review, calls by stage and every file. Notes compile to PDF on
  demand; text files are served as text, not downloads. Nothing about
  monitoring replays a ledger: the server derives the state document from
  the files the pipeline already writes.
- **Prompts are files** in `prompts/`, overridable per campaign. They are
  the place to tune behaviour; the code should not need to change for that.

### What the pilot taught, so build it in

- Peer calls with a strong model cost 3 to 5 USD and 5 to 12 minutes; a
  thread costs 25 to 30 USD. Consolidation needs up to 25 minutes.
  Defaults: 1800 seconds shared by the peers per round, 2 calls per peer,
  1800 for consolidation, 900 for verification, cap 60 USD.
- The Codex workspace sandbox has no network unless you pass
  `sandbox_workspace_write.network_access=true`; peers and authors need it
  for search. Codex reports tokens, not cost; keep a price table.
- APIs refuse some prompts intermittently. Record the error in the receipt
  and carry on; do not retry in a loop.
- A peer whose ready declaration stands should wait for its partner, not
  spend a call.
- The reviewer of a paper must be shown the author's search record, or it
  will flag the search as unsupported.
- The arXiv API rate-limits; back off and retry once or twice.
- `latexpand` can crash on some templates; fall back to the PDF text and
  never let one bad e-print stop the side.
- Long inline prompts through Codex can take more than a minute to open a
  session; scale the transport grace with prompt size.
- A verifier asked the same unmeetable ITERATE three times before the
  PAUSE rule existed; three of four capped threads on the sister campaign
  needed a note repair, not research, which is why REVISE exists.
- Two editor runs started by hand on the same threads raced on a
  directory; give every stage the same per-thread lock the runner uses.
- A loop over threads (edit, paper) must continue past one transport
  failure and report it, not abort.

### How to test it

Write a fake CLI binary driven by environment variables (what to reply,
how long to wait before the session line, whether to hang, a shell command
to run in the working directory before replying) and test every path with
it: scan resume and retry, the cut, a thread reaching each terminal status,
the iterate cap, REVISE repairing once then capping, the empty ledger, a
stop draining a call in flight, the budget guard writing the marker, two
transport failures setting the health flag and a probe clearing it, both
BLOCKED paths and reconcile clearing them, a killed runner leaving a dead
lock, threshold selection keeping started threads, append-only paging,
the paper and editor round trips with a real latexmk. Make the fake write
every file a real call writes, or a branch real calls never take will
pass. Then run a real pilot on two corpora of five papers each with the
cut at 12 percent and the budget at [60] USD, exercise stop, resume and
reconcile by hand while it runs, and write a short report of what happened
and what it cost. Show me the report before running anything larger.

### What I will decide

Backend and models: [claude with claude-opus-5 for research and
claude-sonnet-5 for the scan | codex with gpt-5.6-sol, through
[ChatGPT login | a custom provider at URL with key in file]]. Budget: [60]
USD. Seats: [4]. Ask me anything else you need before you start; do not
assume.
