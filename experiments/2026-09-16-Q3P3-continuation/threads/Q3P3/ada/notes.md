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

## Continuation round (owner entry #40), 2026-09-16

### Access check
- arXiv abstract page https://arxiv.org/abs/2608.18167 (v1, 16 Aug 2026) links no code or data.
  P App. A says the prompts "will be released alongside the implementation upon acceptance".
- Web query run: "Adversarial Review" reviewer critic "false consensus" SWE-PRBench LiveCodeBench code github.
  The GitHub repositories named adversarial-review that it returns are unrelated projects.
- P does not list its 105 LCB stdin tasks, per-task outcomes, the LCB outer cap, or critic
  disagreement rates, and it uses a paid model (Sonnet 4.5). An exact reproduction or a matched
  ablation on P's own tasks is therefore still not possible. No paid calls were made.

### New controlled experiment (not a reproduction)
Files: `stop_signal_exp.py` (runner), `stop_signal_analyse.py` (analysis),
`stop_signal_calls.jsonl` (all model outputs), `stop_signal_run.log`.

- Model: local gemma4:26b through ollama, thinking off, temperature 0.7, no paid API.
- Tasks: HumanEvalPack python (https://huggingface.co/datasets/bigcode/humanevalpack), a seeded
  random 40 of the 164 problems. Each problem has a canonical and a human-injected buggy
  solution. Ground truth comes from the hidden tests: all 40 canonical solutions pass and
  all 40 buggy ones fail (checked by the runner).
- Prompts: P App. A "reviewer prompt (LCB)" and "AR: critic prompt (LCB)", verbatim.
  One deviation, made for local throughput: a system line asks for responses under 200 words
  that end with the required verdict line. The one verbose call made before this change
  (about 1000 tokens, roughly 25 to 60 s) is kept in `stop_signal_calls_verbose_pilot.jsonl`
  and left out of the analysis. Brevity may move R's operating point. It does not change the
  logic of the test.
- Design, review only: R reviews each artifact once. If R approves, C critiques that review
  once, and an independent second reviewer R2 reviews the artifact once.

What it isolates. P's AR stops the outer loop only when R approves and C agrees in the first
round (first-pass termination). Write \( \mathrm{TPR} = P(\text{approve} \mid \text{correct}) \)
and \( \mathrm{FPR} = P(\text{approve} \mid \text{buggy}) \). Take a content-free critic that
disagrees with probability \( d \), independently of correctness. It gives
\[ \mathrm{TPR}_{\mathrm{ZI}} = (1-d)\,\mathrm{TPR}_R, \qquad \mathrm{FPR}_{\mathrm{ZI}} = (1-d)\,\mathrm{FPR}_R, \]
so the share of shipped artifacts that are buggy is unchanged. It only sends more artifacts,
correct ones included, back for editing. The real critic adds stopping information only if
\[ P(\text{C agrees} \mid \text{R approves, correct}) \ne P(\text{C agrees} \mid \text{R approves, buggy}). \]
The experiment estimates both conditional rates, and does the same for R2, which gives
information without interaction. It does not measure whether the critic's text improves M's
edits. Emmy's generation ablation (#43) covers that part.
