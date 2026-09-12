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
`Q2P3.tex`), a verdict history and a terminal status: `DRAFT`, `PAUSE` or
`PAUSE-ON-ITERATE`.

3. **Paper.** On a DRAFT thread, an author agent writes a short paper with
   BibTeX references, searching for prior work and verifying every
   reference; the pipeline builds it and checks the citations; an
   independent reviewer accepts or returns it, up to a round cap.

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
receipts.jsonl     one line per model call; the only source of spend figures
stop.json          present while a stop is requested
health.json        present while admissions are paused after transport failures
threads/<pair>/    inputs/, ledger.jsonl, ada/, emmy/, <pair>.tex,
                   <pair>.verdict.json, status.json, lock
threads/<pair>/paper/   paper.tex, references.bib, paper.pdf, search.md,
                   review.json, paper.json (accepted, returned, blocked)
threads/<pair>/edited/  note.tex, references.bib, note.pdf, edit.json
```

## campaign.json

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
- `budget_usd`: hard cap on receipts plus in-flight estimate.
- `call_estimate_usd`: what one in-flight call is assumed to cost by the guard.
- `prices`: per-model prices used when the CLI reports no cost.
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
- The budget guard runs before every admission: receipts plus in-flight calls
  times `call_estimate_usd` must stay under `budget_usd`, otherwise it writes
  the stop marker itself.
- A call that produces no session within 60 seconds, plus a second per
  5 KB of prompt, is a transport failure:
  no receipt, the thread is marked stopped. Two in a row set `health.json`;
  admissions pause until a probe call succeeds.
- Threads are locked by a pid file. `pathfinder reconcile [pair]` names the
  one safe action for a thread (start, resume peers, run consolidate, run
  verify, or nothing) and `--apply` performs it.

## Prompts

The seven prompts in `prompts/` are the place to tune behaviour: `scan.md`
(the two-axis judge), `peer.md` (the creative brief), `consolidate.md`,
`verify.md`, `author.md`, `review.md` and `editor.md`. A campaign directory may carry its own `prompts/` to override
them.

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
