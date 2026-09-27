# Fixed-batch CVaR can reverse action-policy implementability

## Source check and modeling choice

The supplied Q is Bergemann, Koh, and Morris, *Mechanism Design for Alignment and Control*, not the
quadratic resource-allocation mechanism called "Q" in P's setting and proof. Q defines a type as a
preference, feasible-action set, belief, and information experiment (Q.tex, lines 278-314). Its
state-independent reward result tests an action policy with signal cycles (Q.tex, lines 522-665). P
studies expected empirical CVaR and gives a one-sample failure of true-risk participation in a different
tax game (P.tex, lines 28-54), along with a conditional value-error bound (P.tex, lines 56-84).

The connection below makes an explicit additional assumption: after observing signal \(s\), an agent
ranks actions by the negative conditional CVaR of an auxiliary loss shock. This risk-adjusted value is
used as Q's reduced-form utility \(u(a,s)\). It is not a claim that Q already models CVaR or that P's
quadratic tax appears in the supplied Q.
Because the action reward is deterministic conditional on the action and report, CVaR cash translation
makes the payoff equal to this reduced-form utility plus the reward (P.tex, lines 19-22).

## Exact finite-batch reversal

Let there be two equally likely states \(s_0,s_1\), perfectly revealed to the agent, and two actions
\(a,b\). Fix any finite batch size \(m\geq1\) and \(h>0\). In state \(s_0\), action \(a\) is risky and
\(b\) is safe; in state \(s_1\), reverse the roles. Risky loss is \(0\) or \(2h\), each with probability
\(1/2\), and safe loss is the constant
\[
c_m=2h-h2^{-m}.
\]
Use upper-tail mass \(1/2\). The true conditional CVaR of the risky action is \(2h\). Write \(q_m\) for
the expectation over a fresh \(m\)-observation batch of its empirical CVaR. The all-zero batch has
probability \(2^{-m}\); empirical CVaR is zero there and never exceeds \(2h\). Hence
\[
q_m\leq2h(1-2^{-m})<c_m<2h.
\]

Consider the policy \(a(s_0)=a\), \(a(s_1)=b\), which prescribes the risky action in each state. Under
expected empirical CVaR, zero rewards make the policy strictly optimal at both signals, since
\(q_m<c_m\). Under true conditional CVaR, a state-independent action reward cannot support it. Let
\(r_a,r_b\) be the two rewards. Obedience at \(s_0\) requires
\[
r_a-r_b\geq 2h-c_m=h2^{-m},
\]
while obedience at \(s_1\) requires
\[
r_b-r_a\geq h2^{-m}.
\]
The requirements contradict each other. Equivalently, Q's signal-cycle sum, condition (O), is
\(2(c_m-2h)=-2h2^{-m}<0\) for the true utility. The surrogate cycle sum is \(2(c_m-q_m)>0\).

This shows an exact reversal of implementability in Q's state-independent reward class for every finite
fixed batch. The primitives depend on \(m\); the example does not claim persistent failure for one fixed
instance as \(m\) grows. Q's fully state-contingent rewards could resolve these two local incentives.

For the one-sample case, take \(h=1\): true risky CVaR is \(2\), expected empirical CVaR is \(1\), and
safe loss is \(3/2\). This uses the same one-sample downward-bias mechanism as P's example, while Q's
cycle test turns the bias into an implementability failure.

## A useful robust certificate

For a fixed policy and signal set, suppose estimated values obey \(|\widetilde U(a,s)-U(a,s)|\leq e\)
for every compared action and signal. Each edge of a signal cycle changes by at most \(2e\), so a
length-\(K\) cycle with estimated sum at least \(2Ke\) has nonnegative true sum. By Q's signal-cycle
lemma, if every simple signal cycle meets that margin, the policy is implementable under the true values
by some state-independent schedule. Conversely, a true negative cycle rules out every such schedule. P's
value-level bound suggests how a CVaR oracle could supply \(e\) under its own boundedness and
valid-query assumptions (P.tex, lines 56-84); it is a bound on the expected empirical surrogate, not on
each realized batch.

A publication question is whether this cycle-margin certificate can be extended to Q's nested signal and
type-report conditions, including double deviations and a statistically valid finite-batch guarantee.
The example above gives a precise failure mode and shows why a strict margin is necessary for uniform
exact-implementability claims.

## Timing caveat

If the agent instead ranks an entire signal-contingent plan by *ex-ante* CVaR of the joint signal and
loss distribution, Q's continuation value \(G_t(\widehat t)\) cannot generally be obtained by averaging
conditional CVaRs. For \(0\leq J\leq U\) and tail mass \(\beta\),
\[
0\leq\operatorname{CVaR}_{\beta}(J)
-\mathbb E[\operatorname{CVaR}_{\beta}(J\mid S)]
\leq(1-\beta)U.
\]
The first inequality follows because a conditional CVaR threshold can vary with \(S\), while ex-ante
CVaR uses one threshold. The upper bound follows from
\(\mathbb E[\operatorname{CVaR}_{\beta}(J\mid S)]\geq\mathbb E[J]\) and
\(\operatorname{CVaR}_{\beta}(J)\leq\min\{U,\mathbb E[J]/\beta\}\). It is sharp when a signal reveals
loss \(U\) with probability \(\beta\) and loss \(0\) otherwise. This modeling distinction survives
infinite data and must be settled before extending Q's outer report-cycle test. CVaR time inconsistency
itself is established in prior work, including [Miller and Yang](https://arxiv.org/abs/1512.05015) and
[Rudloff, Street, and Valladão](https://optimization-online.org/2010/12/2860/).

I searched for prior work with the queries "CVaR cyclic monotonicity mechanism", "sample CVaR
implementability mechanism design", and "CVaR sequential mechanism design incentive compatibility
private signal". These searches did not establish novelty. The mechanism-specific cycle reversal and a
full nested robust certificate require a dedicated literature check and a formal theorem.
