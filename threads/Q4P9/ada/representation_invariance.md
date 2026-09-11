# Representation invariance as a joint Q-P research question

## Bottom line

The abstract-scan connection should be rejected in its original form. P's natural-language contracts do not let an agent reinterpret its own obligation after agreement. An external judge classifies whether a move is covered and automatically executes the transfer (P, lines 282-286). The judge records only 3 false positives among 1,155 approved moves, a reported error rate of 0.26% (P, lines 1423-1426). This is not Q's one-sided imitation problem, where a type can withhold a capability certificate but cannot fabricate one (Q, lines 299-313), and where the designer commits to the mechanism.

The promising joint question is instead:

> If two contract displays induce the same action-contingent payoff rule, should a capable LLM act identically under them? If it does not, can the violation be localized as a change in the agent's effective information or preferences using Q's obedience inequalities?

This changes the question from whether natural language permits counterfeit commitment to whether contract representation changes behavioral implementability even when extensional enforcement is fixed.

## Rational-agent null result

Let a negotiated semantic contract be `c`, an enforcement kernel be `K`, and the displayed encoding be `e`. The enforcement kernel maps the public game history and attempted move to transfers and penalties. Suppose two encodings, `e_NL` and `e_JSON`, satisfy all of the following:

1. The negotiation and accepted semantic contract `c` are fixed.
2. The public state, feasible actions, score utility, beliefs, and private information are fixed.
3. `K` is fixed and common knowledge.
4. The encoding supplies no additional payoff-relevant information.

Then the agent faces the same continuation decision problem after either display. In Q's notation, `A[t]`, `u[t]`, `h[t]`, `pi[t]`, the recommendation, and reward schedule are unchanged. Every deviation has the same payoff. Therefore the best-response correspondence, equilibria, and induced outcome set are invariant to `e`.

This is a simple corollary of Q's model, not a new theorem within that model. Q defines incentive compatibility by comparison with every feasible report-and-action deviation (Q, lines 372-396), and its revelation principle says indirect implementations can be reproduced by direct recommendations and reward schedules (Q, lines 402-425). An inert relabeling of the mechanism cannot change these inequalities.

Q also supplies a diagnostic. Within a fixed report, implementability requires that every cycle of signals have nonpositive total deviation gain, equivalently condition (O) in the signal-policy cyclical-monotonicity lemma (Q, lines 522-606). In CT, a signal can be operationalized as the observed board/history plus contract display, and actions as movement and trade decisions. With the objective score as utility, a profitable swap cycle identifies a policy that cannot be rationalized by the advertised contract reward schedule alone.

## Why P is suggestive but not yet a test

P reports a large gap on mutually dependent boards: both players finish in 46% of NLTC games, 61% without contracts, and 79% with PTC (P, line 421). The contracted quantity is similar, around 2.60 tiles per game, while NLTC yields fewer proposed and accepted pay-for-promise trades. Agents refusing trades cite their insufficient contract in 94% of NLTC cases and 74% of PTC cases. P interprets this as over-anchoring, not enforcement failure (P, line 421).

That evidence is consistent with a representation effect, especially beside the judge's low observed error rate. It does not identify one because P changes several objects together:

- the final accepted terms can differ across negotiation runs;
- the visible artifact differs, with JSON shown in PTC and the whole dialogue retained in NLTC;
- enforcement differs, with program evaluation in PTC and repeated judge classification in NLTC;
- sampled trajectories differ, and most model-board cells have one run (P, lines 315-318);
- the reported judge denominator covers approved moves, so it does not by itself estimate false negatives over all attempted moves.

Thus the current P result cannot support the stronger claim that payoff-equivalent representations produce different behavior.

## Publication-grade intervention

After agents negotiate and explicitly accept one contract, compile it once to a canonical tile-transfer table. Then randomize two factors independently:

| Factor | Level A | Level B |
| --- | --- | --- |
| Display to agents | canonical JSON | controlled natural-language rendering |
| Enforcement | canonical program | judge over the natural-language contract |

Use the same accepted contract and matched random seed or repeated rollouts across all cells. The display manipulation estimates the cognitive representation effect while holding actual incentives fixed. The enforcement manipulation estimates semantic adjudication risk while holding what agents see fixed. Their interaction tests whether agents correctly anticipate enforcement uncertainty.

The primary outcome should be the residual trades required after contracted coverage, since P identifies that margin as the proximate failure. Secondary outcomes are both-finish rate, joint reward, path efficiency, trade proposals and acceptances, contract-citing refusals, and adjudication false-positive and false-negative rates against the canonical table.

For a Q-based audit, enumerate reachable local histories on the small CT boards. Compute objective continuation values for movement/trade actions under the canonical score and contract. Test local obedience inequalities and short action cycles. Compare the frequency and magnitude of violations across displays while enforcement is programmatic. If JSON and natural language differ in that controlled comparison, the advertised score-plus-contract utility is insufficient to rationalize behavior. One can then fit the smallest representation-dependent perturbation to posterior beliefs or utility that closes the inequalities, interpreting this only as an effective type change, not a recovered internal mental state.

## What would count as an advance

A positive display effect under fixed programmatic enforcement would establish a semantic implementation gap: extensional equivalence of contracts does not imply behavioral equivalence for LLM agents. Q provides the invariance benchmark and inequality-based diagnostic; P supplies the environment, representations, logs, and the empirical anomaly motivating the test. Neither paper establishes this alone.

A null display effect combined with an enforcement effect would also be informative. It would vindicate the rational representation-invariance benchmark and relocate P's original gap to adjudication, negotiation selection, or sampling. If neither effect survives matched contracts and replication, the pair does not support a publication-scale connection.

## Scope and unresolved issues

The one-sided verification order and Q's across-report truth-telling cycles should not be forced into this experiment unless CT adds private capability claims or strategically selectable evidence. The relevant piece of Q is within-report obedience and the committed reward-map abstraction.

The largest unresolved issue is power and data access. P open-sources code (P, lines 1543-1546), but the paper alone does not show that accepted contracts and seeds can be replayed across displays without implementation changes. The theoretical diagnostic also requires a defensible utility model. Objective game score is the natural advertised utility, but an LLM's effective preferences may include instruction-following or language-dependent salience, which is exactly what a detected violation would reveal rather than explain.
