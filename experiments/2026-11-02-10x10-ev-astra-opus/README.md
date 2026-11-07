# EV rerun of the original 14 pairs

Hypothesis: the current EV pipeline produces higher ex post contribution ratings than the original campaign.
The original shortlist is fixed. Scan scores are ex ante and are not the outcome measure.

## Research

- One peer, Astra-high; consolidation by Astra-high; independent verification by Opus 5.5-high.
- Six research rounds, two repairs; initially two concurrent slots, increased to four at 16:06 CET after a graceful drain.
  Shared subscription seat pools remain six Codex and two Claude slots.
- Token ceiling: 1 billion input and 14 million output tokens, following the Atlas pilot ceiling.
- Fresh ledgers; original Q/P corpora, shortlist and scan record copied without changes.
- Original full-text sources are staged locally; no proactive bibliography expansion (`prefetch_limit=0`).
  Researchers can retrieve additional literature during their calls.
- Current Nobel verification policy, with venue examples adapted to mechanism design and multi-agent research.
- Engine frozen at the revision in `engine-ref`; no automatic fallback to another research model.
- Research-only run: no new paper-writing stage is commissioned for this note-level comparison.

This compares complete pipeline configurations. Models, prompts and allowances differ from the historical run;
it does not isolate the causal effect of removing branches or changing the peer count.
The root historical configuration has two peers and no explicit composable three-branch setting.

## Historical ratings

`operator/historical-paper-ratings.jsonl` preserves the ten ratings retrieved from
`../nobel/data/paper_significance_pf10x10_main.jsonl`. All five accepted papers received 2/10 in both readings:
Q1P2, Q1P6, Q4P6, Q7P1 and Q7P7. The rater was Opus 5.5 using the mechanisms-agents rubric.
Every rated paper's recorded hash matches the retained original paper.
The remaining nine pairs have no historical paper rating in that file.

## Paired ex post comparison

The driver rates all 14 original final research notes and all 14 new final research notes after research ends,
including PAUSE outcomes. Each note receives two independent Opus 5.5 readings with the same frozen rubric.
The historical paper ratings stay separate from this freshly measured note baseline.

The rater receives only the note and rubric, no verifier verdict, pipeline label, hypothesis or earlier ratings.
Numerical verifier scores quoted inside notes are masked using the retained Atlas masking implementation.
Job identities are opaque; tools and search are disabled. Jobs are shuffled with seed 20261102.
The original note may still contain prose about its research history; this is not guaranteed textual anonymity.
The rubric and masking code are retained under `operator/`, together with original note snapshots and hashes.

Primary outcome: mean paired difference across all 14 pairs, using the mean of two readings per note.
Also report each pair's difference and counts of improved, tied and declined pairs. No outcome-based exclusions.
Missing or invalid ratings stop completion rather than being filled with zero.
Using Opus for verification and rating is held fixed across the new note ratings, but the rater is not
independent of the new verifier's model family; this comparison cannot establish human-assessed quality.

Outputs: `operator/note-ratings.jsonl`, `operator/comparison.csv`, `operator/comparison.json`.
The driver resumes completed research and skips rating jobs already recorded.

## Operation and validation

`run_experiment.py` runs the frozen engine, then ratings, and records its phase in
`operator/experiment-status.json`. A stopped process requires diagnosis before resumption.
`operator/validation.json` records the stub research and rating-orchestration checks.
The stub run exercises all 14 pairs; the 56 rating responses are simulated for orchestration validation.
Resuming either stage made no additional calls in validation.

See the repository [experiment ledger](../../EXPERIMENTS.md) for related repeat and recursion experiments.

## Concurrency amendment, 2 November

The user authorized increasing concurrency to four if active work could finish undisturbed.
`operator/increase_seats.py` waits for the two-seat runner to drain, changes only the campaign seat count,
and restarts with explicit provenance acceptance. It preserves the old configuration and manifest,
checks the new heartbeat after one minute, and records the result in `operator/seat-change.json`.
The model routes, per-pair allowances, shortlist and rating rubric stay fixed.

## Paper follow-up, 6 November

After the comparison was complete, Q1P1 and Q7P1 went on to the paper stage on the same frozen runtime
(`run.json`, runtime sha256 `19d166f0`), after a primary-source recovery
(`operator/primary-recovery-20261106/recovery.md`). Both papers were accepted by the reviewer at round 5.
Both presentation passes then stopped at PAUSE-ON-PRESENT: the guard refused a correction that changed
accepted wording, and escalations remain open (`threads/<pair>/paper/presentation/state.json`).
Neither paper is cleared or released. Two standalone editorial runs
(`operator/q1p1-editorial-20261106`, `operator/q7p1-editorial-20261106`) failed: the Q1P1 editor stopped,
and the Q7P1 notation checker had a transport failure. These papers are outside the note-level comparison above.

## What git keeps

Thread folders, transport evidence and `receipts.jsonl` stay on the operator's machine (see `.gitignore`).
Git keeps the configuration, prompts, frozen engine, run and event records, ratings and operator scripts.
