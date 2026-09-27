# A revealed-price test for token-charged auction agents

## Sources and question

The assigned Q is Bergemann, Koh, and Morris, *Mechanism Design for Alignment and Control*. Its action
space can contain a complete trajectory ([Q.tex, lines 278–294](../inputs/Q.tex)), and its mechanism adds
a reward schedule to an agent's utility ([Q.tex, lines 319–343](../inputs/Q.tex)). It requires the
recommended action to beat feasible deviations after information arrives ([Q.tex, lines
348–404](../inputs/Q.tex)). The discussion explicitly permits path-dependent rewards while warning that
dynamic analysis is hard ([Q.tex, lines 2450–2453](../inputs/Q.tex)).

The assigned P is *The Cost of Price Discovery in an LLM Double Auction*. It proposes a disclosed
per-token charge in an otherwise matched auction arm ([P.tex, lines 37–47](../inputs/P.tex)); it reports
no charged-auction run ([P.tex, lines 9–10](../inputs/P.tex)). P asks whether charging causes earlier
crossing and improved net welfare, but neither crossing nor aggregate token use has a general directional
prediction because the order book and future calls change.

I sharpen the question: **Before interpreting any auction-level treatment effect as a price response,
does an individual trader's demand for metered tokens satisfy the necessary incentive restriction at a
fixed decision problem?** This is a new diagnostic for P's proposal, not an empirical finding or a direct
corollary of Q's cycle characterization.

## Two-price restriction

Fix a trader's type, reservation value, book state, available response policies, model version, and the
behavior of other traders. Let \(A\) be the common set of feasible response policies or complete
trajectories. Let \(U(a)\) be that trader's expected payoff before the experimental token charge, and let
\(T(a)\) be its expected metered token use. Both must be defined on the same action space at both prices.
The Q-style additive reward is \(r_{\tau}(a)=-\tau T(a)\). If \(a_0\) and \(a_1\) maximize
\(U(a)-\tau_jT(a)\) at \(0\leq\tau_0<\tau_1\), respectively, their incentive inequalities are

\[
U(a_0)-\tau_0T(a_0)\geq U(a_1)-\tau_0T(a_1),
\qquad
U(a_1)-\tau_1T(a_1)\geq U(a_0)-\tau_1T(a_0).
\]

Adding them yields

\[
(\tau_1-\tau_0)\bigl(T(a_0)-T(a_1)\bigr)\geq0,
\qquad\text{hence}\qquad T(a_1)\leq T(a_0).
\]

The same argument applies to optimal lotteries, with \(U\) and \(T\) replaced by expectations. It also
applies to a stochastic response policy if the policy itself is the chosen action and its expected payoff
and token count are stable across prices. It is a necessary condition only. A higher price can still
increase or decrease spread crossing, withdrawals, gross surplus, or total tokens in a live auction.
Those outcomes depend on how the changed response alters the subsequent state and the other agents'
behavior.

If both actions are observed, the same inequalities bound their pre-charge payoff difference:

\[
\tau_0\bigl(T(a_0)-T(a_1)\bigr)
\leq U(a_0)-U(a_1)
\leq \tau_1\bigl(T(a_0)-T(a_1)\bigr).
\]

This provides a partial revealed-preference estimate without observing \(U\). With more than two prices,
every pair supplies a restriction; inconsistent choices can be analyzed using the same
incentive-inequality logic rather than inferred from auction totals.

## A local limit of an own-token tariff

The monotonicity test checks whether the additive-charge model describes choices. Even when it does, an
own-token tariff can fail to induce the welfare-best quote. Consider a standing seller ask \(p\), a buyer
with \(v>p\), and a seller with \(c<p-\delta\), where \(\delta>0\). The buyer can cross the ask now or
post a bid \(p-\delta\). Assume the buyer's two initial replies consume the same metered tokens. If it
bids, the scheduler imposes one later seller call that consumes \(K_S>0\) additional tokens. Assume the
seller's metered cost for that call is the same whether it accepts or declines, and no other continuation
changes the match. Once called, the seller accepts because \(p-\delta-c>0\); its call cost is sunk for
this choice.

For any own-token price \(\tau\geq0\), the buyer gains \(\delta\) by bidding and pays the same token
charge under either initial reply. Yet both paths produce the same gross gain \(v-c\), while crossing
now avoids the seller's later tokens. At any social conversion \(\lambda>0\), crossing therefore raises
\(W_{\lambda}\) by \(\lambda K_S\). This is a conditional counterexample to implementation by a
uniform tariff on each trader's own tokens. It does not predict the outcome in P's full auction, where
the next call is random, a bid may fail to trade, and the seller's reply length can vary. It also shows
why passing the fixed-state monotonicity test would not establish an efficient tariff.

Q permits rewards to depend on the joint action profile ([Q.tex, lines 1508–1525](../inputs/Q.tex))
and treats full trajectories as actions ([Q.tex, lines 2450–2453](../inputs/Q.tex)). These features
suggest a restricted repair. On trajectories where the same buyer and seller certainly trade, suppose
the buyer's charged payoff is \(v-p(a)-\tau C_B(a)\), where \(p(a)\) is the execution price and
\(C_B(a),C_S(a)\) are verifiable total tokens. Offer the trajectory-contingent reward

\[
R_B(a)=p(a)-\lambda C_S(a)-(\lambda-\tau)C_B(a).
\]

The buyer's total payoff is then \(v-\lambda[C_B(a)+C_S(a)]\), so it chooses the lower-token path
within this fixed-match comparison. Charging it for both agents' tokens without the \(p(a)\) term can
still fail: the private price gain \(\delta\) favors waiting whenever \(\delta>\lambda K_S\).
The proposed correction therefore addresses both the delay externality and the price-transfer motive.
It requires observed prices and token counts, a credible and potentially funded reward, and a fixed
match. With changing matches, seller costs, outside options, and private values also matter. Q's
coupled-reward example does not prove implementation in P's standing-book auction. P already notes
that an own-call charge omits possible savings to the counterparty
([P.tex, lines 37–39](../inputs/P.tex)); the construction makes the required local correction explicit.

## Executable empirical design

Use a one-call book snapshot or a controlled replay with one trader charged and the other traders'
continuation policies held fixed. Randomly assign several disclosed prices across fresh, independent
instances of the same model and state. Keep the task text and parameters fixed apart from the price, and
use a non-binding budget so the feasible action set does not change. Meter every generated token covered
by the stated charge, including reasoning tokens if those are billed. Estimate the conditional mean of
metered tokens at each price with repeated runs; compare those means against the nonincreasing
restriction. Then report crossing and withdrawal rates separately. Finally run P's full auction
comparison and report its \(G\), \(C\), and \(W_{\lambda}=G-\lambda C\) separately ([P.tex, lines
29–35](../inputs/P.tex)).

A statistically clear increase in conditional token demand rejects the **joint** assumptions of a stable
price-independent payoff, a common feasible set, and maximization of the stated additive charge. It does
not alone show which assumption failed. In particular, Q says measured preferences can depend on the
prompt ([Q.tex, lines 2446–2448](../inputs/Q.tex)); changing a displayed number could change behavior
through language effects rather than a stable economic reward. P itself lists charge comprehension and
token-record reliability as unresolved ([P.tex, lines 53–54](../inputs/P.tex)). Conversely, monotone
token demand is consistent with the model but does not prove it. A treatment that changes every trader's
price at once does not satisfy the fixed-opponents condition, and aggregate run-level token counts need
not be monotone.

## Other bridge considered

Q's peer-scoring construction can elicit types when different types imply different conditional
distributions over peers ([Q.tex, lines 1650–1699](../inputs/Q.tex)). P lists eleven distinct reservation
values on each side ([P.tex, lines 22–27](../inputs/P.tex)). **If** the values are assigned as a uniform
random permutation within each side, a fixed same-side peer has conditional probability \(0\) of the
trader's own value and \(1/10\) of each other value. Two distinct own values therefore induce the
*single-peer marginal* distributions separated by squared Euclidean distance \(2/10^2=1/50\). Q's score
instead uses the entire co-player profile, so applying this smaller distance requires a modified score
against one peer. P does not state the permutation assumption; Q's implementation also uses unrestricted
rewards and hard action prohibitions, and a direct-report mechanism would replace P's standing-book
market. I therefore regard this as a conditional benchmark, not the main claim.

## Publication threshold

The two-price inequality and local counterexample are elementary, so neither is a standalone theoretical
contribution. A paper would need a credible metered intervention, the fixed-state diagnostic, full-auction
outcome estimates, and a test of whether a verifiable trajectory-contingent incentive improves net welfare over the
uniform tariff. The current pair supplies the mechanism model and the unrun test setting, but no
empirical result. A targeted search for prior work used the
queries “arxiv LLM agents inference token cost price demand revealed preference experiment tokens”,
“arxiv large language models price sensitivity token usage revealed preference”, and “site:arxiv.org/abs
token price revealed preference LLM agents”. The search found work on token budgets ([Token-Budget-Aware
LLM Reasoning](https://arxiv.org/abs/2412.18547)) and LLM preference tests ([The Innate Economic
Preferences of Language Models](https://arxiv.org/abs/2607.26288)); it does not establish novelty.
