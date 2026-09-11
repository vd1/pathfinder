# Pathfinder pilot report

Date: 11 September 2026. Campaign: the repository root, as recorded in the
"Reference run" section of `2026-09-11-pathfinder-design.md`, which holds the
exact figures. This note holds the lessons: first about the harness, then
about the quality of what it produced.

## What was run

Two corpora of five arXiv papers each, fetched by the loose queries
"mechanism design" and "agentic cooperation". All 25 pairs scanned with
claude-sonnet-5 from abstracts. Cut at 12%, three threads on claude-opus-5
with tools and web search. A fourth pair, Q1P2, added afterwards by widening
the cut to 16%, run on gpt-5.6-sol through the Codex CLI and the ELM proxy.

| thread | backend | status | rounds | ledger | calls | USD |
| --- | --- | --- | --- | --- | --- | --- |
| Q4P3 | claude, opus | PAUSE | 2 | 27 | 15 | 29.73 |
| Q1P1 | claude, opus | PAUSE | 1 | 28 | 8 | 27.16 |
| Q3P3 | opus round 1, then codex via ELM | PAUSE-ON-ITERATE | 3 | 39 | 19 | 8.88 + 5.14 |
| Q1P2 | codex, gpt-5.6-sol via ELM | DRAFT | 2 | 36 | 12 | 7.43 |

Scan: 25 pairs, 0.82 USD. Claude total: 66.58 USD API-equivalent; Codex 20.0 USD from the price table (two threads and the paper stage). Campaign total 87.53 USD over 92 calls.

## Harness lessons

1. **Plain files were enough.** State in a campaign directory, one pid lock
   per thread, one receipt line per call, one stop marker, one health marker.
   Every recovery path that could be reached was reached, without a
   supervisor: a drain with six calls in flight, a resume at the recorded
   stage, a runner killed during a stage, a stage timeout, refused API
   calls, the budget guard. `reconcile` named the right action every time.

2. **Peers are the cost, and one peer call is about five dollars.** Opus
   with tools reads two full TeX sources, runs simulations and writes
   derivations, so a call runs 5 to 12 minutes and costs 3.5 to 5.4 USD. A
   thread costs 25 to 30 USD; the scan of the whole grid cost less than one
   peer call. At a 1% cut on a 10,000 grid that is about 3,000 USD of
   research against about 330 USD of scan. The levers, in order: the cut or
   threshold, the peer allowance, the model.

3. **Costs are API-equivalent, not billed.** The Claude CLI reports a cost
   at API rates for every call, and the pilot ran on a subscription, so the
   dollars are what a metered user would pay. On a subscription the binding
   limit is the plan's quota, which the pipeline does not see; a rate-limit
   refusal would arrive as an ordinary error in a receipt. Codex reports
   tokens only, priced from the campaign's table.

4. **Control of the budget is soft, by design and by decision.** The guard
   runs at admission, so the last admitted thread finished 6.58 USD over
   the cap. A drain takes as long as the longest call in flight, twenty
   minutes here. Both were judged acceptable for an experiment: "stop"
   means "within one call" and "budget" means "budget plus one thread".

5. **Allowances that looked generous were not.** Consolidation took 895
   and 1344 seconds; the first attempt timed out at 600 with no note.
   Consolidate now allows 1800 seconds, verify 900. A killed call reports
   no usage, so timed-out calls are charged at the call estimate.

6. **The API refuses some prompts, intermittently.** Three resumed peer
   calls were rejected by a safeguard classifier in two to three seconds
   each. The receipt recorded the error, the thread carried on with the
   other peer, and the same prompt went through minutes later. A pipeline
   must treat this as weather, and this one did.

7. **Readiness is worth a small protocol.** A peer whose ready declaration
   is current now waits for its partner instead of spending a call; on
   Q1P1 that saved one five-dollar call per resume. The allowance still
   resets per runner invocation rather than per round; left as is.

8. **The monitor as a local server was the right call.** One page polling
   one state document, thread files served from the campaign directory,
   nothing rebuilt on a schedule. Not visually checked in this session.

9. **Long prompts need a longer opening.** The verify and review prompts
   inline both sources, the ledger and the note, 280 KB on Q1P2. Through
   Codex that sometimes takes more than a minute before the first event,
   which the fixed 60-second grace read as a dead transport. The grace now
   scales with prompt size. The Claude CLI never showed the delay.

10. **Test coverage after the pilot.** Exercised for real: fetch, flatten,
   scan with retry, select, concurrent and sequential admission, peers,
   consolidate, verify, ITERATE into a second round, PAUSE, operator drain,
   resume, killed runner and reconcile, budget guard, stage timeout, API
   refusal, the Codex backend through a custom provider. Covered only by
   tests with a fake CLI: DRAFT, PAUSE-ON-ITERATE, empty ledger, transport
   failure and the health flag, the interrupt drain, both BLOCKED paths,
   prompt override. Untested: full-text scanning, the PDF-only e-print
   path.

## Quality of outcomes

1. **The scan did what the rubric asked, on corpora that gave it little.**
   Scores ranged from 0 to 2100 of a possible 10,000. Three pairs sat at
   1925 to 2100 and the fourth at 600. Loose arXiv queries produce mostly
   unrelated pairs, and the judge said so. The shortlist mechanism worked;
   recall could not be tested because there was little to recall.

2. **The peers behaved like researchers.** Across the three Claude threads
   they wrote 19 Python scripts, re-implemented each other's simulations,
   filed nine objections and corrections, cited sixteen outside sources by
   URL, and declared ready with the entry number they had read. The
   ledgers read as lab notebooks. Concrete results came out: Q1P1 found and
   fixed a loose inequality in P's proof; Q4P3 proved a converse to an
   example in Q's model.

3. **But the depth went into one paper and the bridge was thin.** Both
   verifiers rejected the notes on the same ground: the peers proved things
   about one paper and reached the other by analogy. Q1P1's note says
   itself that Q "contributes vocabulary and proof obligations, not a
   theorem". The peer prompt asks the pair-level question in its first
   sentence, so this is a model tendency rather than a prompt defect, and
   the prompt stays as it is. Two threads on loose corpora are not enough
   to say how often it happens.

4. **The verifier was the strongest component.** Both verdicts were
   specific, traced claims to ledger entries, checked the algebra, and
   named the missing anchor. ITERATE on Q4P3 produced a real second round;
   the round narrowed the connexion rather than anchoring it, and the
   second verdict said so. The verifier's reasons are the most useful text
   in the run for a human deciding what to do next.

5. **The notes are usable artefacts.** Both compile clean under pdflatex
   with article class and amsmath only, 11 and 13 pages, attribute claims
   to ledger entries by number, and state plainly where the material is
   thin. Nothing in them was invented outside the ledger, as far as the
   verifier could tell.

6. **One DRAFT, from the weakest pair on the cheapest model.** Q1P2 scored
   600 in the scan, a third of the three Opus pairs, and reached DRAFT on
   gpt-5.6-sol in two rounds by narrowing the claim until the verifier
   accepted it. Whether that says more about the pair, the model or the
   verifier is open; see the Codex section. The next test of outcome
   quality is the same pipeline on corpora curated to contain pairs a
   human already suspects, with both backends on the same pairs.

## Codex through ELM

The fourth pair, Q1P2 (learning-augmented algorithms against concept-guided
scene graphs, scan score 600), ran on gpt-5.6-sol through the Codex CLI
with ELM as a custom model provider. The transport gained an optional
`codex` block in `campaign.json` for that: provider name, base URL, the
environment variable carrying the key and the dotenv file it is read from.
A tool-less probe answered in 4 seconds; Codex's own system prompt costs
about 12,800 input tokens per call.

The thread ended DRAFT after two rounds: 12 calls, 773 model seconds, 6
minutes of wall time, 7.43 USD at the table price. Peer calls took 30 to
140 seconds and cost 0.3 to 1.5 USD, consolidation 49 and 77 seconds, and
each verification 12 seconds. The ledger has 36 entries, with 7 objections
and 5 corrections, five markdown notes in the peer directories, no scripts
and no outside citations. The note is 3 pages and compiles clean.

Three things to weigh before reading the DRAFT as a win:

- The first verdict was ITERATE with a precise action (establish a
  calibrated Hausdorff coverage bound on P's wall estimates), the peers did
  that in round 2 by restricting the claim to a first-gate, split-conformal
  setting, and the second verdict accepted the restricted theorem. That is
  the loop working as designed.
- The same model verified in 12 seconds what Opus took 3 to 8 minutes to
  verify, on a note a third the length. A quicker, more lenient verifier
  and a narrower claim both make DRAFT easier to reach. The two verifiers
  have not been compared on the same note.
- The thread cost a quarter of an Opus thread and ran in a tenth of the
  time. For a campaign of a hundred threads the difference is a day and a
  few hundred dollars against a week and a few thousand.

Q3P3 then ran on Codex from its Opus round 1 ledger, the mixed case: 17
calls, 13 minutes, 5.14 USD, and PAUSE-ON-ITERATE after three rounds. The
verifier returned the same ITERATE three times, asking for a test on P's
data that the peers do not have. Two rounds were spent on an action the
peers could not take. The verify prompt now says that a gap needing data,
experiments or access the peers do not have is a PAUSE with the missing
input named, and that a repeated unmet ITERATE is not asked again.

The mechanics were identical on both backends: same files, same stages,
same reconcile behaviour. One operator error on the way: the stop marker
left by the budget guard made the first `reconcile --apply` end as
`stopped` at once; `stop --clear` fixed it. A stale stop marker is easy to
leave behind and the CLI could say so when a command starts.

## Paper stage

Added after the pilot on request, from the Julien edition's author-note and
final-review prompts with the packaging left out. On a DRAFT thread,
`pathfinder paper` runs an author agent with tools and web search that
writes `paper/paper.tex` and `paper/references.bib`, searches for prior
work on the specific result, verifies every reference against arXiv or a
DOI, and builds with latexmk. The pipeline rebuilds in a scratch copy and
checks citations, uncited entries, missing identifiers and arXiv titles
against the API, then an independent tool-less reviewer returns ACCEPT or
REVISE with findings by id, up to `paper_rounds`.

On Q1P2 through Codex and ELM, the paper reached ACCEPT in round 3: six
pages, five references with verified metadata, 8.36 USD over the stage's
runs. What the first attempts taught:

- The Codex workspace sandbox has no network unless asked. The first
  author could not reach arXiv, wrote a search record saying so, and cited
  only Q and P. The transport now opens network access when search is on.
  The second author ran six queries over OpenAlex and the arXiv API, read
  three related papers and cited them.
- The reviewer must see the search record. The first reviewer flagged as
  unsupported a record it had never been shown. It is now in the prompt.
- Two review calls on a 280 KB prompt produced no session within 60
  seconds through Codex; the session grace now grows with prompt size,
  and the stage resumes at the review rather than paying for the author
  again.
- The reviewer's findings went from "search record unsupported, symbols
  undefined" to "n is not declared a positive integer" over three rounds,
  which is the shape of a review converging. The arXiv API rate-limited
  the pipeline's own title check once; it now backs off and retries.

## Open-ended mode, first pass

`explore --min-score 1500 --page 5 --passes 1` appended five older papers
per side (one e-print crashed latexpand; the PDF text was used), scanned
the 75 new pairs for 2.52 USD and rewrote the shortlist at the threshold:
thirteen pairs, nine of them new, four above 3000 where the first page had
none above 2100. The second page of "agentic cooperation" was closer to
the query's meaning (commitment to cooperation with self-negotiated
contracts, an energy-society simulation, dynamic multi-agent oversight,
rank aggregation for credit assignment), which is the corpus effect the
pilot report predicted. The runner admitted the top new pair, Q4P10
(alignment mechanism design against dynamic multi-agent oversight), on
Codex under the remaining budget; the guard holds the other eight.

## Conversation with the E-prime agent

At V's request Scout (this session) compared notes with the Fable session
running the agQSL E-prime campaigns unattended (29 of 59 Julien pairs
closed at the time). Their side, condensed:

- **Monitoring.** E-prime has no live monitor: a static watchboard is
  regenerated every ten minutes by replaying both campaign ledgers (17 s
  and 7 s), pgrep for liveness and list prices; the ELM counter lags by an
  hour. A polling watcher bolted on for unattended running woke them four
  times on stale reports before its rules were right. Their first change:
  the coordinator writes one state document from the state it holds and
  the page polls it; nothing about monitoring replays a ledger. Second: an
  owner-event queue (grant wanted, cap reached, parked, refusal, note
  ready, closed) the coordinator appends to, with wanted options, evidence
  and a resolution that is also written to the pair's ledger. Fields their
  campaigns would need beyond Pathfinder's state: an owner stage beside the
  runtime status, checkpoint id and imported flag, waiting and held
  reasons, per-call failure kind and retry allowance, per-peer attempts and
  seconds used, per-service last tick and last import.
- **Failure recovery.** Nine distinct failure kinds in two days on 90
  threads is why they have a reconcile command; four threads in a pilot do
  not meet them. What they have that Pathfinder lacks: collecting a review
  never applied, retrying a refused call once the capacity retries are
  spent, acknowledging a peer excluded by the content filter so the other
  peer's ledger still becomes a note, numbered checkpoints, an explicit
  repair pass. What Pathfinder has that they lack and are taking: fail-fast
  transport with the prompt-size term (their refused calls burnt the full
  600 or 900 s allowance), a graceful stop (a restart orphaned two
  workers), a single ledger per pair (most of their stale-report incidents
  come from an owner ledger and a runtime ledger joined by checkpoint
  import), receipts as the only spend figure, the served state page.
- **Allowances and rounds after 59 pairs.** Research calls take 200 to
  450 s, consolidation 100 to 300 s, review 70 to 140 s on their models;
  they would cut research to 600 s per peer and give consolidation more.
  Every pair that reached round three asked for a fourth, and three of
  four asks were repairs of the note, not research; a repair pass
  (consolidate against the review, then review, a tenth of a round) took
  all three to PAUSE or DRAFT. Their recommendation: a fourth verdict
  word, REVISE, routed to consolidation only, research rounds capped at
  three and repairs at one. Continuation notes kept dropping accepted
  results; the continuation should append to the prior note.
- **What is wrong rather than lean, in their words.** No idea artefact
  between scan and research: asking the peers to discover the link inside
  the most expensive stage puts the hardest step in the wrong place; on
  the vanilla side a Phase B judge with full text on both sides produced a
  300-word derived idea with line locators into the sources, and it was
  the one input reviewers cited. Automatic rounds with no owner veto are
  where the budget goes. Web search for peers should be an explicit,
  per-thread, logged policy: source-only authority is what lets a reviewer
  check every claim against a fixed corpus; with search, novelty claims
  become claims about the open literature.
- **Their worst bug today** was a repaired note inheriting the review of
  the version it replaced; it passed 69 tests because the fake calls did
  not write the files real calls write. Their fix, both layers: record the
  note's digest in every review and refuse to apply a review whose digest
  is not the current note's; and fakes must produce a call directory that
  the collector cannot tell from a real one.

What Pathfinder took from it today:

- The peer prompt now carries what the scan saw: the connexion sentence,
  the rationale and the two scores, as a first hypothesis to confirm,
  sharpen or replace.
- A consolidation after ITERATE is told to keep the prior note's results
  that still stand and append, not rewrite.
- Every verdict records the note's digest and every paper review records
  the paper's digest.

Left for V, because they decided the opposite today: automatic ITERATE
rounds without an owner veto, and web search for peers as the default.
Recommended outright: REVISE as a fourth verdict word routed to
consolidation only, capped at one repair. Noted for the test suite: the
fake CLI should write everything a real call writes.

## Decisions taken on the way

- Soft budget control stays; no per-stage in-flight estimate.
- The peer prompt stays; the first sentence already asks the right question.
- The per-invocation peer allowance stays.
- Monitor default port moved to 8790.
- The reference campaign file goes back to the Claude backend after the
  Codex thread; the `codex` block stays in it as a worked example.

## What would come next

- Curated corpora, to test recall and to look for a DRAFT.
- An open-ended mode: page arXiv backwards in time, scan new pairs as they
  arrive, admit a thread when a score crosses a threshold. Most pieces
  exist; pair ids should become arXiv-id based first.
- The builder prompt for colleagues, once the code has been read for
  leanness.
