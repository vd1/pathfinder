# Contract representation as a test of mechanism equivalence

## Paired observation

Q models a mechanism by its messages, contingent recommendations, and reward schedule. Its multi-agent revelation principle identifies the outcomes achievable by indirect and incentive-compatible direct mechanisms, while preserving agents' ability to deviate in both reporting and action (`inputs/Q.tex`, lines 1510-1643). Q also states that a reward can depend only on the action and state distinctions the evaluator can identify (`inputs/Q.tex`, lines 917-947). These are benchmarks for asking what a contract actually makes observable and enforceable.

P's programmatic tile contract converts a negotiated agreement into a tile-indexed transfer map accepted by both players. Its natural-language tile contract retains the negotiation transcript and asks a judge whether each attempted move is covered (`inputs/P.tex`, lines 248-290). The paper reports both players finishing on \(79\%\) of mutually dependent boards with the programmatic contract and \(46\%\) with the natural-language contract. It reports similar mean numbers of covered tiles, about \(2.60\), but fewer later Pay-for-Partner proposals and acceptances under the natural-language condition (`inputs/P.tex`, lines 403-410).

The judge audit reports three errors among \(1{,}155\) *approved* contract moves, all false positives (`inputs/P.tex`, lines 1422-1427). This is an estimate of errors conditional on approval. It cannot estimate false negatives, because rejected moves are absent from that denominator. It also does not establish that the two conditions negotiated the same tiles, that agents believed coverage was equally reliable, or that the judge would decide identically at histories the agents considered but did not reach.

## Conditional equivalence

Fix a board and an accepted agreement \(C\). Let \(h\) be any reachable history and \(a\) any legal next action. Write \(T_C(h,a)\) for the chip transfer, enforcement penalty, and next state, including the insufficient-inventory case. Suppose the programmatic and natural-language versions give both players the same information about \(C\), have identical legal actions and timing, and satisfy \(T_C^{\mathrm{prog}}(h,a)=T_C^{\mathrm{lang}}(h,a)\) for every \((h,a)\), including histories outside the realized path. Assume players understand these maps and have the same terminal score preferences. Then the two induced extensive-form games are isomorphic: every strategy profile has the same distribution of action histories and payoffs in each version. Their equilibrium *outcome sets* coincide. This does not assert that a particular language-model run will select the same equilibrium, or that language models satisfy the assumptions.

This gives a precise interpretation of a remaining performance difference after transfer maps and contract terms are held fixed. It would be evidence about comprehension, beliefs, computation, or equilibrium selection induced by presentation. Without those controls, an outcome gap can also come from different negotiated terms or different enforcement decisions. Q's general implementability propositions cannot be applied directly to P's bounded chip and point transfers: Q permits reward schedules and prohibitions unavailable in CT-Bench (`inputs/Q.tex`, lines 1697-1715; `inputs/P.tex`, lines 248-305).

## Decisive experiment

Start from each board and a fixed, independently validated tile agreement. Randomly assign the *display* of the same obligations as a JSON map or a faithful natural-language statement. Independently assign the *executor* as exact code or the judge. Hold the game rules, penalties, counterpart, and agreement fixed. Audit the judge on all attempted moves against the validated map, reporting false positives and false negatives. Sample feasible but unplayed moves too, since agents may anticipate off-path coverage. Measure agreement acceptance, Pay-for-Partner proposals and acceptances, covered-move attempts, realized transfers, and Both Finished.

A display effect with exact execution would isolate a representation or belief channel. An executor effect with fixed display would identify enforcement differences. If both disappear after fixing the agreement, contract selection is a better explanation for the original gap. The paper's observed trade-volume association is a useful hypothesis about behavioral crowding-out, but the existing comparison does not identify it as a causal mediator.

## Limits

This note proves only the conditional equivalence statement, not that P's two implementations satisfy its assumptions. The audit denominator problem is a measurement limitation, not evidence that false negatives occurred. A paired experiment is needed for a publication-level causal claim.
