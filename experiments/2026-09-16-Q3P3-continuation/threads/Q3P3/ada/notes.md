# ada notes on Q3P3 (Q: LLM double auction; P: Adversarial Review)

## Line pursued
Zero-intelligence (ZI) baselines separate what an institution delivers from what agent
intelligence adds. Neither paper has one. Q compares LLM markets only with Smith's humans.
P compares its protocol only with other LLM protocols.

## Q side (simulations of Q's stated mechanism, Sec 3.2)
- ZI-C (Gode and Sunder 1993) in Q's mechanism: efficiency 0.956 to 0.961, 5.8 to 5.9
  trades per round, alpha 19 to 21 (cda_sim_out.txt). This does not depend on the quote range
  (0.943 to 0.957; cda_robust_out.txt). Emmy got 0.959 independently.
- Every LLM cell in Q Table 1 (max 0.91) is below ZI-C. LLMs lose surplus by omission
  (too few trades); ZI-C loses a little by commission (extramarginal trades).
- ZI-equivalent horizon (cda_tick_out.txt): ZI-C matches GPT Large's five-round mean
  efficiency (0.53) at T of about 53, Gemini's (0.70) at about 80, and GPT Small's (0.87)
  at about 131, against Q's T of 300.
- Tick size as a lever: for creeper agents (one-tick steps) at T=300, efficiency is 0.19 at
  $0.01, 0.74 at $0.05 and 0.95 at $0.10. ZI-C is tick-insensitive. This gives a falsifiable
  prediction for Q's released framework.
- Prompt detail: Q's system prompt says a round ends "once no one can post an improving
  order, or once a cap on orders is reached". The mechanism ends at T=300 regardless.

## P side
- The move to the methods that beat the 77% cluster also adds re-review after edits. The
  once-edit methods (Single-reviewer, Two-reviewers) sit at 75 to 77%. The re-reviewing ones
  are MARS (up to 2 rounds, 82%) and AR (until first-pass clean, 87%).
- Proposed control: a ZI critic, meaning random verdicts at the LLM critic's disagreement
  rate, plus an R-only outer loop.
- Toy model (review_loop_toy_out.txt), calibrated so that one review-edit cycle has zero net
  effect: iterating until approval adds +0.3 to +9.1pp (median +2.6pp). A random critic
  lowers pass rates.
- P's "structural, not individual" claim rests on a single model. Q shows that model identity
  moves efficiency from about 0.5 to about 0.9 under a fixed institution.

## Status of evidence
The Q-side numbers are simulations of the stated mechanism. Emmy reports that the authors'
own ZI-C runs show 6.4 to 6.9 trades and alpha 27.6 to 31.1, with a different value grid and
a deadlock exit. The P side is a design argument plus a toy model; it has no P per-task data.

## Qualifications after emmy's #7 and #9
- The direction of failure depends on the model. GPT Large and Gemini Large lose surplus
  by omission. GPT Small in round 5 (6.2 trades) and the unreported Gemini Flash runs in
  the authors' notebook (6.7 to 8.4 trades) also show commission.
- Q enforces no tick for LLM agents (emmy's code reading, verified by ada: apply_order.py
  lines 69 and 107 compare floats strictly; PRICE_INCREMENT is used only in the ZI deadlock
  check in control.py; nothing is rounded). So the tick result applies only to
  agents on an enforced grid. Testing it in Q needs an enforced tick and a tick stated in
  the prompt. It is then the same kind of intervention as emmy's ACCEPT menu: both change
  the admissible message set, which is what P did in Sec 4.4.

## Prior work checked (queries recorded, no novelty claim)
- "zero-intelligence traders baseline LLM agents continuous double auction efficiency Gode Sunder comparison"
- "LLM agents double auction zero-intelligence benchmark allocative efficiency large language model traders"
- "multi-agent LLM critic ablation random verdict reviewer critic false consensus code review extra revision rounds"
- "tick size minimum price increment LLM trading agents order book experiment effect on convergence"
- Nearest hit: BAZAAR, https://github.com/lechmazur/bazaar. It is a sealed-bid double auction
  with 4 buyers and 4 sellers. ZI-family baselines rank near the bottom on individual
  profit. It reports no market efficiency, so it is a different comparison.
- Background: Gode and Sunder (1993), https://www.journals.uchicago.edu/doi/10.1086/261868 ;
  Jia and Yuan, https://arxiv.org/abs/2409.08357 (cited by Q).
