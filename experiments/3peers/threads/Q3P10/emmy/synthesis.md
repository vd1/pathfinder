# Compute-inclusive market alignment

## Finding

There is a publishable connection, but I would change the selected question. The sharper question is:

> Does a double auction that looks allocatively efficient when inference is free remain efficient once the agents must pay for the reasoning and repeated quoting needed to reach the allocation?

This is stronger than asking whether survival stakes amplify Q's urgency vocabulary. Q's lexical evidence is explicitly associational and comes from only Gemini Large: it says that its analysis identifies terms separating crossing from incrementing, "not what causes an agent to switch," and that reasoning traces may be unfaithful (Q, lines 405--442). P also breaks the monotone-amplification premise: halving jobs sometimes improves small agents' efficiency while reducing decision cost (P, lines 691--703). Survival pressure may accelerate, degrade, or nonmonotonically change trading.

The joint advance is a resource-rational definition of market-institution alignment. Q supplies an institution with an exact welfare benchmark, but its efficiency numerator counts trading surplus and omits the inference used to obtain it (Q, lines 294--300). This matters because GPT Large can consume the finite horizon with repeated \(\$0.01\) improvements (Q, lines 359--360). P supplies the missing endogenous cost: every reasoning and output token consumes energy, with

\[
C_{i,t}=kT_{i,t}S_i^{\alpha},
\]

and energy depletion can deactivate an agent (P, lines 101--106, 148--170, 301--305). P, however, lacks a theoretical maximum-surplus allocation against which to judge whether cognition bought good coordination. Putting P's accounting into Q's controlled market yields a claim neither paper can make alone: apparent allocative alignment can differ from compute-inclusive alignment.

Define conventional realized surplus as \(G\), the equilibrium maximum as \(G^{\star}\), and inference cost in the same induced-value units as \(C=\sum_{i,t}C_{i,t}\). Report both

\[
\eta_{\mathrm{alloc}}=\frac{G}{G^{\star}}
\qquad\text{and}\qquad
\eta_{\mathrm{net}}=\frac{G-C}{G^{\star}}.
\]

If the outside option also consumes computation, subtract the preregistered baseline cost from \(C\). The scale conversion from tokens or energy to induced dollars must be fixed ex ante; otherwise \(\eta_{\mathrm{net}}\) is arbitrary. A useful primary endpoint that avoids this conversion is the Pareto frontier of \(G/G^{\star}\) against tokens, API cost, or joules.

## Minimal experiment

Keep Q's reservation schedules, persistent order book, random activation, and human benchmark. Do not auction P's MMLU jobs: that would change private values, add task-accuracy heterogeneity, and make failures impossible to attribute to the market mechanism. Instead, add only P's energy ledger to every market call and convert realized trading profit into replenishing energy.

The main causal experiment should use a randomized consequential (2\times2) tariff within each model and seed:

\[
C=fN+\lambda T,
\]

where \(N\) is the number of quote actions, \(T\) is token use, \(f\in\{0,f_1\}\), and \(\lambda\in\{0,\lambda_1\}\). Every cell displays an accumulating ledger and debits the market endowment only after the round. This keeps the active supply and demand schedules fixed within a round. For any outcome \(Y\), the contrasts \(E[Y\mid f,\lambda_1]-E[Y\mid f,0]\) at each \(f\) identify the token-price effect conditional on quote price, while \(E[Y\mid f_1,\lambda]-E[Y\mid0,\lambda]\) at each \(\lambda\) identify the quote-price effect conditional on token price. Their difference-in-differences identifies whether the two prices are complements or substitutes. If the interaction is nonzero, report these simple effects rather than only averaged main effects. Realized charges are post-treatment mediators, so equalizing them ex post would destroy these causal contrasts; pilot calibration should set and then freeze \(f_1\) and \(\lambda_1\).

Add a no-ledger baseline and an identically displayed, nonbinding ledger at \((f_1,\lambda_1)\). Their contrast estimates combined ledger salience, while the consequential \((f_1,\lambda_1)\) cell versus its nonbinding counterpart estimates the additional effect of consequence, subject to the ledger being believed. A single nonbinding cell does not identify separate salience effects for quote and token prices. That requires mirroring the full \(2\times2\) factorial with nonbinding ledgers. Keep the iteration cap fixed and visible. A secondary extension can permit within-round deactivation to study selection under survival pressure. A further horizon treatment is useful only after this core design, because Q already notes that a longer horizon may rescue trade volume (Q, lines 359--360).

Q's symmetric schedule offers a natural calibration. Its six equilibrium gains are \(2.50,2.00,1.50,1.00,0.50,0\), so \(G^{\star}=7.50\) per round. Preregister fee levels as fractions of \(G^{\star}\), rather than directly importing P's environment-specific \(k=0.015\).

Primary outcomes are \(\eta_{\mathrm{alloc}}\), the surplus-cost frontier, trades, price dispersion, tokens per realized unit of surplus, quote improvement size, spread at crossing, time to trade, and deactivation by private-value rank. Analyze behavioral traces only as secondary diagnostics. A direct causal test is whether randomized \(f\), \(\lambda\), or their interaction changes crossing hazards or quote increments; urgency-word shifts cannot establish that.

The most interesting result need not be amplification. Moderate inference cost could suppress wasteful penny improvements and raise \(\eta_{\mathrm{alloc}}\), while high cost could induce premature crossing or abstention and lower it. That predicts an inverted-U response. In the secondary survival arm, high-cost models or agents with marginal reservation values may deactivate first, changing the active supply and demand schedules rather than merely making all traders more urgent.

## Support and cautions

Q reports conventional efficiency between \(0.36\) and \(0.91\), with the smallest model closest to equilibrium (Q, lines 310--356). P separately reports that larger models use more tokens and are less energy-efficient even with a uniform per-token price (P, lines 484--492, 834--843). This convergence motivates, but does not establish, a model-scale claim because the papers use different models, prompts, tasks, and experimental populations. The new study should run the same model families under the same auction conditions and treat model as a blocked factor.

The original transplant has another identification problem: P's "survival" is a constructed deactivation rule, not literal survival, and P warns against anthropomorphic interpretation (P, lines 893--910). The defensible claim concerns budget exhaustion in deployed agent systems. Likewise, a binding energy balance changes the set of active traders, so conventional efficiency should be computed against both the original full-market optimum and the contemporaneous active-agent optimum. The gap between them separates selection loss from poor allocation among survivors.

## What remains unresolved

The key unresolved design choice is the common unit for inference cost and induced trading surplus. A physical or monetary conversion supports net welfare; otherwise the cost-efficiency frontier should be primary. Statistical power and exact tariff calibration require a pilot because P uses only five seeds and reports substantial variability (P, lines 893--904). The factorial may be costly to power, especially for model interactions. The nonbinding ledger must also be believable enough to match salience without creating a different demand effect. Hidden reasoning-token observability and controllability may differ across model APIs. No external prior-art search was performed, so this is a pair-level opportunity, not a novelty claim.
