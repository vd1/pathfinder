# Costed inference in Q's double auction

## Joint question

Can making LLM traders bear the cost of their own inference reduce the repeated one-cent quote improvements in Q enough to increase realized gains from trade before the market closes? Can any gain exceed the added computation cost? This is a hypothesis for a controlled experiment, not a result of either paper.

Q's **Trading Mechanism** samples an untraded agent for up to \(300\) iterations per round. In **Individual Behavior**, most quote improvements are \(\$0.01\); in **Aggressive Rent-Seeking Suppresses Trade Volume**, GPT Large makes only \(2.2\) to \(3.8\) trades per round and realizes efficiency between \(0.36\) and \(0.67\). P's **Small vs. large models** defines generated-token cost \(C=kTS^{\alpha}\), with \(k=0.015\) and usually \(\alpha=0.5\). P's **No Discussion Phase** shows that removing a call phase reduces expenditure and improves survival while increasing job collisions. Thus P supplies a cost-accounting intervention and a warning that fewer calls may impair allocation; it does not supply evidence about double auctions.

## Payoff mechanism and its limits

Suppose a buyer with value \(v\) can cross the standing ask \(a\) now, or post a smaller bid \(b<a\) that fills later with probability \(q\) at price \(b\). If the current decision call costs the same under both actions and waiting requires expected additional inference cost \(c\), crossing is privately favored in this simplified one-step model exactly when

\[
v-a \geq q(v-b)-c.
\]

This is an illustration, not a claim about Q's agents: a real continuation can yield other prices, multiple calls, and no fill. The inequality shows why a future inference cost can favor crossing, but its effect depends on expected fill and price improvement. A token-metered current call may also have action-dependent cost, so the common-current-cost cancellation need not hold. Higher cost can instead induce early exit or prevent a profitable match.

Q's **Market Environment** gives 11 buyers and 11 sellers with values and costs from \(0.75\) to \(3.25\) in \(0.25\) steps. Sorting buyers high to low and sellers low to high, the gross gain from matched pair \(j\) is

\[
\Delta_j = \bigl(3.25-0.25(j-1)\bigr)-\bigl(0.75+0.25(j-1)\bigr)
=2.5-0.5(j-1).
\]

The first five pairs yield \(2.5,2,1.5,1,0.5\), whose sum is \(G^\star=7.5\). The sixth pair has zero gross gain. Q's equilibrium quantity \(q^\star=6\) is therefore not a strict welfare target when computation is costly: five correctly matched positive-gain trades already exhaust the gross surplus. Report realized gross surplus \(G\), its ratio \(G/7.5\), generated tokens and calls, and operational net value separately. If \(\rho\) converts P's synthetic energy units into Q's price units, one explicit accounting metric is

\[
N_{\rho}=G-\rho\sum_{i,t} kT_{i,t}S_i^{\alpha}.
\]

The value of \(\rho\) needs sensitivity analysis. P knows the parameter sizes of its open models, whereas Q reports proprietary GPT and Gemini models without their sizes. Thus \(S_i^{\alpha}\) cannot be populated from Q for a mixed-model market. In a homogeneous-model arm, absorb this constant into \(\rho\) and use metered generated tokens; for cross-model comparisons, use an observable cost schedule rather than assert parameter counts. Report calls, generated and input tokens, and any separately measured compute or API expenditure. P's formula counts generated tokens only, so it is a behavioral accounting rule, not a complete measure of provider cost. A billed fee and P's synthetic energy are not automatically real social resource costs, so \(N_{\rho}\) should not be called social welfare without an additional cost interpretation.

## Discriminating experiment

Keep Q's private values, order book, model, random selection procedure, and horizon fixed within each comparison. Give **all** treatment arms an irrevocable exit action and a rule that ends a round when no active trader remains on either side. Randomize a disclosed inference charge, including zero, and debit every decision call, including a decision to post no quote. A fixed-per-call treatment isolates the value of ending future calls; a generated-token treatment adapts P's accounting and also permits response-length changes. Use matched seeds with repeated independent runs and record both prices and actions. Start with one model, so model-size differences do not confound the cost response.

Primary endpoints are \(G\), \(N_{\rho}\), total calls, total generated tokens, the fraction of one-cent improvements, the probability of crossing conditional on spread and remaining time, and exits before profitable matches. Q's price-dispersion statistic is secondary because tightly grouped prices do not prove that valuable pairs traded. A positive result requires an improvement over the zero-charge arm at a stated \(\rho\), not merely fewer quotes. A negative result is informative if charges instead reduce participation or increase net cost.

Q's stated \(300\)-iteration cap alone may leave aggregate call counts unchanged after an early trade because remaining agents keep being sampled. Its **System Prompt** also mentions stopping when no one can post an improving order, a rule that is absent from the method description. The [released round-control implementation](https://raw.githubusercontent.com/jswistak/competitive-market-simulation/master/src/market_simulation/graph/nodes/control.py) checks the cap, the number of active agents, and deadlock, but treats any active LLM as capable of further action for the deadlock check. Consequently, with at least two untraded LLM agents, ordinary rounds reach the cap. The exit and stopping rule above must be identical across arms.

## Prior work and novelty boundary

Charging for double-auction offers is established: [Jamison and Plott's costly-offer experiment](https://authors.library.caltech.edu/records/fnhzb-n0e58) reported slower equilibration and reduced efficiency, and [Noussair and coauthors' transaction-cost experiment](https://www.sciencedirect.com/science/article/abs/pii/S0167268198000638) reported lower quantity and efficiency. The proposed contribution is a test of inference costs in LLM traders with Q's documented one-cent loops, including the distinction between cost per decision call and cost per submitted offer. Whether the effect reverses the older human-market result remains open.

Search queries used: `continuous double auction costly bid revision computational costs market efficiency experiment paper`; `LLM traders continuous double auction inference budget token cost paper`; `per bid cost continuous double auction quote revisions welfare laboratory experiment`.

## Alternative checked

P's **Introducing Scarcity** reduces the number of jobs from \(12\) to \(6\) and reports lower decision energy for some agents. This suggests testing whether a coarser price grid makes Q's choices easier, but it also changes which prices agents can offer and the rent split at a trade. P changes both opportunity count and competition, rather than quote precision. The inference-charge experiment therefore makes a more direct use of the pair; the grid test can be a later factorial control, not evidence that coarsening improves Q's market.
