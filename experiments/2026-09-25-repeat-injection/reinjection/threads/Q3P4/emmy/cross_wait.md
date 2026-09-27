# Fixed-batch CVaR at a double-auction crossing decision

## Sources and sharpened question

Q is the supplied *Competitive Market Behavior of LLMs*. Its order book selects an untraded agent uniformly
each iteration, executes a crossing order at the resting quote, admits a spread-improving order without
execution, and ends after 300 iterations ([Q, lines 239–259](../inputs/Q.tex)). Profit is zero when an agent
does not trade ([Q, lines 261–278](../inputs/Q.tex)). Q reports that GPT Large agents often improve quotes by
one cent rather than crossing, with 2.2–3.8 trades per round and low efficiency
([Q, lines 359–360](../inputs/Q.tex)).

P is the supplied *Fixed-Batch CVaR and Participation in a Quadratic Resource-Allocation Mechanism*. Its
one-sample construction separates an expected empirical CVaR objective from true CVaR
([P, lines 28–54](../inputs/P.tex)); its value bound applies to the expected surrogate, not to a particular
batch ([P, lines 56–64](../inputs/P.tex)). P calls other cited papers “Q” and “P” internally; those names do
not refer to the assigned pair here.

I sharpen the joint question to a single action: when a buyer can secure a small positive profit by crossing
now or seek a larger profit by posting an improved bid near the iteration cap, can an exact fixed-batch
empirical-CVaR decision choose the action rejected by true CVaR? This is a constructed decision under Q's
rules. Q instructs agents to maximize profit, without a CVaR objective, so the calculation does not explain
their observed behavior. In fact, the one-sample surrogate wait choice is also the expected-profit choice in
the example. CVaR is a proposed intervention and evaluation lens, not an inferred LLM preference. Unlike P's
participation example, waiting here has true-risk utility zero relative to no trade; the failure is an action
ranking, not a negative participation payoff.

## General calculation

Let crossing yield certain profit \(g>0\). Let posting a noncrossing bid yield profit \(h>g\) with conditional
probability \(p\) and zero otherwise. Write \(f=1-p\) and use upper-tail CVaR of loss \(L=-\pi\), with tail
mass \(\beta\in(0,1)\). Define risk-adjusted utility as \(R=-\operatorname{CVaR}_{\beta}(L)\). Directly
filling the worst \(\beta\) fraction of the two-point loss distribution gives

\[
R_{\rm cross}=g,\qquad
R_{\rm wait}=h\left(1-\frac{f}{\beta}\right)_{+}.
\]

For a fresh batch of \(s\) independent continuation draws, let \(M\sim\operatorname{Binomial}(s,f)\) count
failures. The empirical CVaR includes zero-loss failures first and gives empirical risk utility

\[
\widehat R_{\rm wait}(M)=h\left(1-\frac{M}{\beta s}\right)_{+},\qquad
\widetilde R_{\rm wait}(s)=h\sum_{m=0}^{s}\binom{s}{m}f^m p^{s-m}
\left(1-\frac{m}{\beta s}\right)_{+}.
\]

Here \(\widetilde R\) is the negative *expected empirical* CVaR, the same type of surrogate distinguished in
P. By convexity of the positive-part function,

\[
\widetilde R_{\rm wait}(s)\geq R_{\rm wait}.
\]

The direction of this bias is general for independent samples and an integrable loss: writing empirical CVaR
as an infimum over its threshold,
\(\mathbb E[\inf_{\eta}F_s(\eta)]\leq\inf_{\eta}\mathbb E[F_s(\eta)]=\operatorname{CVaR}_{\beta}(L)\). Thus
expected empirical CVaR of loss is optimistic. The two-point calculation gives its exact size at this crossing
decision. For \(s=1\), \(\widetilde R_{\rm wait}(1)=ph\), so it coincides with expected profit regardless of
\(\beta\). When \(\beta=1/2\), \(\widetilde R_{\rm wait}(2)=p^2h\). A ranking reversal at \(s=1\) occurs
whenever

\[
h\left(1-\frac{f}{\beta}\right)_{+}<g<ph.
\]

In particular, any \(f\geq\beta\) and \(ph>g\) suffice. This is a strict comparison of *expected empirical
objectives*, not a guarantee about the choice induced by one realised batch.

## A state permitted by Q's rules

Consider the penultimate iteration of a round with all 22 agents still untraded. Set a selected buyer's
reservation value to \(v=3.25\), a resting ask to \(a=3.00\), and suppose the standing bid is below
\(b=2.25\). These prices and the seven seller reservation values at most \(2.25\) occur on Q's specified grid
([Q, lines 210–219](../inputs/Q.tex)). The buyer can cross at \(a\), earning \(g=v-a=1/4\), or post the
improving noncrossing bid \(b\), earning \(h=v-b=1\) if matched on the final iteration. The buyer is not told
the other sellers' costs in Q; the count of seven is analyst knowledge used to construct the counterfactual,
not an estimate available to the prompted trader ([Q, lines 261–278](../inputs/Q.tex)).

Stipulate a continuation policy under which each of the seven eligible sellers crosses \(b\) if selected next
and every other selected agent takes no action that trades this buyer. Uniform selection among the 22 untraded
agents then gives \(p=7/22\). The action and continuation choices obey Q's order processing rules. They are
assumptions, not observed policies or equilibrium claims. With \(\beta=1/2\),

\[
R_{\rm wait}=0<\frac14=R_{\rm cross},\qquad
\widetilde R_{\rm wait}(1)=\frac7{22}>\frac14,
\qquad
\widetilde R_{\rm wait}(2)=\frac{49}{484}<\frac14.
\]

Thus an exact maximizer of the expected one-sample empirical CVaR waits, while an exact maximizer of true CVaR
crosses. Increasing the batch to two reverses the surrogate ranking. The wait action completes this buyer's
trade with probability \(7/22\), versus certainty for crossing. The true-risk action margin is \(1/4\); the
exact surrogate value error for waiting is \(7/22\) at one sample and \(49/484\) at two samples. The same
two-sided value-error argument as in P's conditional guarantee says a margin larger than twice the maximum
error protects an action ranking; that sufficient condition holds at two samples here
([P, lines 66–75](../inputs/P.tex)). This is a fresh two-action calculation, not an application of P's
equilibrium proposition.

If the standing ask belongs to the seller with cost \(1.00\), and other next actors generate no trade,
crossing yields welfare \(3.25-1.00=9/4\), while waiting yields expected welfare
\(\sum_{c\in\{0.75,1.00,\ldots,2.25\}}(3.25-c)/22=49/88\). This welfare comparison depends on that further
continuation assumption. In other states, more crossing can displace a higher-value buyer and reduce total
surplus, as Ada notes in the ledger; the action-level risk result does not imply a market-efficiency theorem.

## What would make this a paper

The mathematical ranking reversal is a tractable mechanism-specific example, but its empirical relevance is
untested. A follow-up could branch Q's released order-book simulator at matched late-round states, hold
other-agent policies fixed, and estimate each candidate action's conditional distribution of fill and profit
from many continuations. From that distribution, calculate the *expected* empirical-CVaR oracle for each fixed
batch size and compare its crossing recommendation with true CVaR. This first phase tests whether the ranking
reversal occurs in states produced by Q-style agents. The first empirical gate is the frequency of reachable
late states satisfying the reversal inequalities. If such states are rare, this example gives little
publication case by itself.

A separate intervention would supply agents with averaged outputs from repeated fresh batches of the same
fixed size and ask them to act on those values. A single realised batch does not instantiate P's expected
surrogate; its action can differ from the ranking calculated above. One arm should supply an oracle based on
hidden costs and policies; another should estimate fill probabilities using only the trader's public history,
to isolate the information advantage. Full-market rollouts would then measure trade completion, allocative
surplus, and CVaR of aggregate efficiency loss. P shows that local CVaR and CVaR of aggregate loss can select
different allocations ([P, lines 86–94](../inputs/P.tex)). The existing Q experiments alone cannot identify a
CVaR cause: they report actions and market outcomes but no CVaR objective or elicited fill probability. Q's
ten evaluation runs are not the trader's oracle batch size \(s\).

P's uniform value-error result and quadratic-mechanism equilibrium proposition are not applied here: the
action set is discrete, the continuation distribution depends on other traders, and Q's CDA is not P's
quadratic allocation mechanism. The transferable object is P's distinction between true CVaR and a repeatedly
sampled expected empirical surrogate.

Prior work already considers risk-based bidding in continuous double auctions
([Vytelingum et al., 2004](https://eprints.soton.ac.uk/259567/)) and bias in sampling-based CVaR optimization
([Tamar et al., 2015](https://doi.org/10.1609/aaai.v29i1.9561)). Hence neither risk-aware bidding nor
finite-sample CVaR bias is a novelty claim. Searches run:
`continuous double auction CVaR bidding risk aversion agent empirical conditional value at risk`;
`empirical CVaR finite sample optimistic bias stochastic optimization expected empirical CVaR`;
`finite horizon double auction order crossing execution risk conditional value at risk`;
`large language model agent continuous double auction CVaR risk aversion execution probability`;
`conditional value at risk limit order execution probability sample size bias auction`;
`LLM trading agents finite horizon double auction risk preference quote crossing`. The defensible research
contribution would require new evidence that this specific sampling failure affects Q-style LLM trading, or a
remedy with verified market outcomes.
