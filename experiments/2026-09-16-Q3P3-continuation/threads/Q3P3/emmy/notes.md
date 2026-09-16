# emmy notes on Q (Struski et al., LLM double auction) and P (Qiu and Gill, Adversarial Review)

## Line pursued

Both papers treat convergence of interacting LLM agents as the object. Q wants
convergence (to p* = 2.00, q* = 6) and does not get enough of it. P wants the
reviewer and critic to converge on a correct review and gets too much of it
("false consensus", P Sec 4.3). The shared variable is how the protocol prices
the terminal action relative to the agent's default move:

* Q: a trade needs a jump across the spread; the default is a $0.01 own-side
  improvement (Q Sec 4.2). The prompt (Q App. B; same text in
  configs_final/smith1_*.yaml) offers no explicit "accept the standing quote"
  action, frames each move against the own-side quote only, says a resting
  quote "may transact later", and never states the cap (300 ticks).
* P: the inner loop ends on AGREE, which is the cheap default for the critic.
  The fix (P Sec 4.4) gates the terminal action on code evidence.

## Evidence produced here

1. ZI-C benchmark in Q's own mechanism (emmy/sim_cda.py): efficiency 0.959,
   5.9 trades per round, alpha 19. Every LLM condition in Q Table 1 (0.36 to
   0.91) is below it on efficiency.
2. Q's repository contains ZI-C and ZI-U configs, and
   notebooks/results_analysis_multiple_cda.ipynb shows two ZI-C runs that the
   paper does not report: 20 sims (6.5 to 6.9 trades per round, alpha 27.6 to
   31.1) and 10 sims (6.4 to 6.6 trades, alpha 20.0 to 21.5, close to my
   sim). LLM alpha in Q Table 1 (11.7 to 28.1) is inside or below that range,
   so on price dispersion the LLMs are no worse than random traders; on
   efficiency they are worse.
2b. The same notebook has unreported Gemini runs (smith1_flash_t1, 5 sims;
   smith1_pro_t1, 3 sims; Feb 2026) with 6.7 to 8.4 trades per round, above
   q* = 6. Submarginal traders who transacted per round: Flash 1.0 to 2.4
   buyers and 1.2 to 2.4 sellers; ZI-C 0.5 to 1.4 buyers and 0.6 to 1.2
   sellers. So real LLM markets in Q's framework show the commission failure
   (above the ZI-C rate) as well as the omission failure of GPT Large.
3. Exact loss decomposition (emmy/sim_decomp.py): loss = omission
   (intramarginal traders left out) + commission (extramarginal traders in).
   Pure creep: omission 0.82, commission 0.00. Accept-default agents:
   commission 0.10 to 0.17, alpha 35 to 41, efficiency 0.71 to 0.79. Making
   the terminal action cheap converts omission into commission.
4. Mapping to P: omission corresponds to recall loss (Case B), commission to
   precision loss (Case A). P reports F1 only, on 100 PRs, without intervals.

## Proposed experiment (not run)

Two by two on Q's framework: action menu {improve only (Q as is), typed menu
ACCEPT / IMPROVE / PASS modelled on P's AGREE / DISAGREE_EVIDENCE /
DISAGREE_CONCERN} crossed with horizon {hidden, remaining ticks shown}. Score
omission and commission separately against the ZI-C benchmark. Prediction from
P: a cheap ACCEPT raises volume but moves the loss into commission; a gated
ACCEPT (justify against own value and remaining ticks) is the market analogue
of P's text constraint.

## Limits

* The creeper and acceptor agents are stylised; only the ZI-C benchmark and the
  decomposition identity are robust.
* The terminal-action account of P rests on two case studies and one F1 delta.
* Prior work on conformity in multi-agent debate exists (searched: "multi-agent
  LLM debate conformity sycophancy false consensus critic yields confident
  rebuttal 2025"); I make no novelty claim for the P side.

## Continuation iteration (2026-09-16, owner entry #40)

### Access check

* arXiv 2608.18167 is v1 only (16 Aug 2026), "Accepted to ICML 2026 Workshop
  on DL4C", no code or data link. P App. A: prompts "will be released alongside
  the implementation upon acceptance". Searches for an author repository found
  only unrelated projects named adversarial-review.
* P does not list its 105 LCB stdin tasks. LCB release v6 (test6.jsonl) has 112
  stdin AtCoder tasks (60 hard, 2025-01-04 to 2025-04-06); no contest-date
  window of it gives 105 tasks with 57 hard, so P's set is not identified.
* P's model is Claude Sonnet 4.5 (paid; excluded by #40). A reproduction or a
  matched ablation on P's own tasks, model and harness is not possible.

### What P's aggregates identify (p_aggregate.py)

Rounded percentages fix the counts: ZS 81, Self-Refine 81, SR 81, TwoR 79,
MARS 86, AR 91 of 105. Exact McNemar p over all pairings compatible with the
marginals: AR vs MARS in [0.0625, 0.49]; MARS vs SR in [0.0625, 0.54]; AR vs SR
in [0.002, 0.14]. Neither "MARS clearly higher" nor "AR over MARS" can reach
p < 0.05 with any pairing. Prose errors: MARS "85%" (Table: 82%) and MARS
"43/57" hard (Table: 39/57; 43 is AR).

### New controlled experiment (ar_ablation.py; not a reproduction)

Local gemma4:26b (Ollama, no thinking, T = 0.7), 40 medium/hard LCB v6 stdin
tasks (seeded shuffle), P App. A LCB prompts adapted to stdin programs, hidden
tests from the dataset. Arms share their prefix per task (same v0, same first
review): ZS, SR (edit once), RO (R-only iterate-to-clean), AR (inner cap 5,
first-pass termination), ARZ (content-free critic, DISAGREE rate matched to the
realized AR rate in inner round 1 and later rounds). Outer cap 3 edits for RO,
AR, ARZ. Analysis fixed in ar_ablation_analyse.py before results:
AR - SR = (RO - SR) + (ARZ - RO) + (AR - ARZ), plus the stop signal on v0
(accept given v0 correct, accept given v0 wrong), the market omission and
commission split read on the reviewer's terminal decision.

### What P's token medians imply (p_token_bound.py; ledger #53)

P Fig. 5a: LCB median tokens ZS 8000, SR 22000, TwoR 28000, AR 30000,
"estimated from per-method call counts". Solving gives review r = 6000 and
edit e = 8000. Any edited AR task needs at least six calls (generate, review,
critique, edit, review, critique), costing 28000 + 2c. If the critic call costs
more than 1000 tokens, the median AR task (the 53rd of 105) was not edited, so
at least 53 AR tasks shipped v0 at first pass. AR fails 14 tasks, so at most 14
failing v0 were accepted. The +10 over ZS/SR comes from at most 52 edited
tasks. With the ZS failure count (24) as a proxy for AR v0 failures, a stop
rule that ignores correctness and accepts a tasks is compatible (hypergeometric
p >= 0.05) only for a <= 77. More than about 78 first-pass accepts would
therefore prove the stop decision carries correctness information. P does not
report the count, so this reduces one part of the causal question to one
number in P's logs.

### Status at the end of the continuation

The local ablation (ar_ablation.py) and ada's stop-signal run were still in
progress when this call ended. Per-call timings (43 to 131 s) put the planned
40 tasks at about 10 h. Nothing from those runs is reported as a result here.
