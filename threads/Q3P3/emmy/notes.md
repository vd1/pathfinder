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
