# From commitment to semantic compression

## Assessment

The proposed concealment/counterfeiting link does not fit the implemented game. Q's hard-evidence order restricts which *types* can be reported: a certificate may be withheld but not fabricated (Q, lines 299-303). In P's NLTC, a separate judge interprets the retained negotiation and automatically executes covered transfers (P, lines 282-286). Its reported adjudication error is 3 false positives among 1,155 approved moves (P, lines 1422-1428), but that denominator cannot reveal false-negative denials. The contracting agent neither chooses the interpretation nor counterfeits a capability certificate.

P's own evidence locates the failure after contracting. On mutually dependent boards, P reports similar use of contract-covered tiles in PTC and NLTC, but fewer residual P4P proposals and acceptances under NLTC. When declining a trade, agents cite an insufficient contract more often under NLTC (94%) than PTC (74%); both-finish rates are 46% and 79%, respectively (P, lines 410-420). This is an attention or policy-response effect, not established enforcement failure.

## Sharpened question

When identical obligations and enforcement are presented as a compiled contract or as the richer negotiation transcript, does semantic compilation improve decisions by changing the agent's effective information capability?

This replaces the scan's question. It uses Q's definition of type, especially the information experiment π[t] alongside utility and feasible actions (Q, lines 276-297), but does not invoke Q's one-sided verification order.

## Benchmark and diagnostic

Let T be a complete negotiation transcript and J = c(T) its faithful compiled JSON. Hold fixed the board, contract obligations, automatic enforcement, feasible actions, scoring utility, and residual-trade menu. An ideal agent that observes T can reproduce any policy available after observing J by computing c and then following the J-policy. Thus the transcript experiment weakly Blackwell-dominates the compiled display, and its maximum expected score cannot be lower. This orders attainable value, not individual trajectories: multiple best responses and stochastic decoding can produce different behavior at equal value. If representation is absent from the primitives and both displays induce the same information, mechanism, type, and equilibrium selection, behavior is invariant.

A robust performance advantage for J after these controls is therefore a *semantic-compression reversal*: the nominally less informative display performs better. It rejects the joint maintained model of costless information processing, stable instructed utility, and faithful compilation. It does not by itself identify whether compression changes effective π[t], effective utility through salience, or optimization error.

Q's within-report obedience condition offers a secondary diagnostic. Treat board and public history as signals, and trajectory or trade/move choices as actions, as Q explicitly permits complete trajectories as actions (Q, lines 276-280). Preregister the advertised score-plus-transfer utility and use repeated matched rollouts to estimate choice probabilities. Positive revealed-preference cycles would show failure to rationalize this maintained utility, not uniquely identify an internal type change, because Q's condition assumes deterministic policy and known posterior utility.

## Decisive CT experiment

Create one human-validated or independently dual-validated canonical contract for each negotiated transcript, rather than reusing PTC's own judge-generated JSON. Require identical explicit acceptance. First use the same deterministic compiled enforcement engine in every display arm, then cross display with programmatic versus judge enforcement to estimate adjudication risk separately. Randomize what each agent sees among:

- canonical JSON;
- a controlled natural-language rendering of that same JSON;
- the full negotiation transcript;
- JSON plus the full transcript.

Replay the same boards, models, contract terms, seeds where supported, and residual-trading opportunities. Measure own score, both-finish, residual-trade proposal and acceptance, contract-citing refusals, coverage-comprehension probes, and choice-cycle violations. The controlled prose arm separates syntax from transcript length and negotiation-history salience. JSON plus transcript tests whether an explicit compiled core repairs the richer display.

The central prediction is not merely that JSON wins. If semantic compression is the mechanism, performance and coverage comprehension should order with decision-relevant compression, and JSON plus transcript should resemble JSON. If controlled prose matches JSON while the full transcript fails, the culprit is context and salience rather than formality. If matched display arms converge but judge enforcement differs, adjudication explains the gap. If both factors converge, unmatched terms, acceptance, or sampling in P's original comparison are responsible.

## Publication value and limit

The publishable contribution would be a theory-guided benchmark for *representation-dependent effective capability*: compilation can increase realized value even though it discards information. P supplies the environment, exact payoff, contract variants, and observed reversal candidate; Q supplies the information-capability primitive and obedience-cycle implementation test. Neither paper isolates semantic compression or states the Blackwell reversal.

The main unresolved issue is identification. Q assumes coherent expected-utility types and does not model computational costs, prompt-dependent preferences, or limited attention. A reversal is a rejection and measurement result, not an explanation, unless comprehension probes and the factorial arms distinguish information extraction from salience and enforcement.
