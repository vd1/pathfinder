# Finite-batch CVaR can reverse a signal-cycle test

## Question and scope

Can an expected empirical CVaR oracle make a policy appear implementable
under a state-independent reward when no such reward implements it under
the true risk values? Yes, for every finite batch size. The question is
sharper than whether a particular learned action has low true-risk utility.

Q means the supplied `inputs/Q.tex`, *Mechanism Design for Alignment and
Control*. Its signal-cycle characterization in lines 522–665 concerns
state-independent reward schedules. P means the supplied `inputs/P.tex`,
*Fixed-Batch CVaR and Participation in a Quadratic Resource-Allocation
Mechanism*. Its one-sample construction is in lines 28–54, and its
expected-empirical value-error statement is in lines 56–84. P's references
to a paper called Q concern a different paper and do not establish this
connection.

The construction uses a reduced-form conditional risk preference. Let
\(\Theta=S=\{0,1\}\), with both states assigned positive prior probability,
and let the signal reveal the state exactly. For each action and state,
an auxiliary shock generates a loss. Define Q's primitive payoff as
\(u(a,\theta)=-\operatorname{CVaR}_{1/2}(L(a,\theta,\xi))\), and define
the surrogate payoff as the negative expectation of empirical CVaR from
a fresh batch of size \(m\). The agent evaluates its plan by averaging
these conditional risk values across states, as Q's expected-utility
model requires. This is not ex-ante CVaR of the mixed signal-outcome law.

## Construction

Choose \(h>0\). A risky action loses \(0\) or \(2h\), each with
probability \(1/2\). A safe action loses a constant \(c_m\). At state
\(0\), action \(a\) is risky and \(b\) is safe. At state \(1\), action
\(b\) is risky and \(a\) is safe. Let
\[
q_m=\mathbb E_{\rm batch}
\left[\widehat{\operatorname{CVaR}}_{1/2,m}
(\text{risky loss})\right].
\]
Every empirical CVaR in this expression lies in \([0,2h]\). It is zero
on the all-zero batch, an event of probability \(2^{-m}>0\). Thus
\(q_m<2h\) for every finite \(m\). Choose
\(q_m<c_m<2h\). One explicit choice is
\(c_m=2h-h2^{-m}\): the all-zero event also gives
\(q_m\leq2h(1-2^{-m})\), so this safe loss lies strictly above
\(q_m\).

Consider the policy \(a(0)=a\) and \(a(1)=b\), which recommends the
risky action in either state. Its expected empirical surrogate prefers
the recommended action by \(c_m-q_m>0\) after each signal. Zero reward
therefore supports truthful obedience in the one-type surrogate model.
For \(m=1\), \(q_1=h\); choosing \(h=1\) and \(c_1=1+\varepsilon\)
recovers the one-sample numbers \(0,2,1+\varepsilon\), with
\(0<\varepsilon<1\).

The true upper-half CVaR of the risky loss is \(2h\), while that of the
safe loss is \(c_m\). The two-signal cycle in Q's condition (O) is
\[
\begin{aligned}
&U(a,0)-U(b,0)+U(b,1)-U(a,1)\\
&\qquad=2(c_m-2h)<0.
\end{aligned}
\]
Q's signal-cycle lemma therefore rules out every state-independent
supporting reward for this same policy under true risk utility. Directly,
obedience at state \(0\) requires
\(r(a)-r(b)\geq 2h-c_m\), while obedience at state \(1\) requires
\(r(b)-r(a)\geq 2h-c_m\). Both cannot hold.
For the explicit choice above, the surrogate cycle is at least
\(2h2^{-m}>0\), and the true cycle is exactly
\(-2h2^{-m}<0\).

This is an exact-implementability failure for a policy selected from an
expected empirical objective, not a claim about a particular realised
batch or about strategic learning. The general Q mechanism allows
state-dependent rewards; the impossibility applies to its explicit
state-independent subclass. For each fixed safe cost \(c<2h\), increasing the
batch size eventually corrects the surrogate ordering. The claim is
that no finite batch size gives a uniform exact guarantee over instances
without a positive margin.

## Margin certificate

Suppose a finite-signal, one-type model has a uniform posterior utility
error \(|U(a,s)-\widetilde U(a,s)|\leq e\) for every action and signal.
For a signal cycle of length \(K\), the true and surrogate values of
condition (O) differ by at most \(2Ke\). Consequently, if every simple
signal cycle involving at least two distinct prescribed actions has
surrogate value at least \(2Ke\), the true policy passes Q's necessary
and sufficient signal-cycle test. Cycles with a single assigned action
have value zero under both models. Q's lemma then constructs a true
state-independent supporting reward; the surrogate reward itself need
not remain valid.

There is also an exact criterion for one reward that works for every
utility array in a rectangular error set. Let \(B\) be the distinct
actions prescribed by the policy, and suppose every entry
\(U(a,s)\) may vary independently within
\([\widetilde U(a,s)-e,\widetilde U(a,s)+e]\). For distinct
\(a,b\in B\), put
\[
w(a,b)=\max_{s:a(s)=a}
\bigl[\widetilde U(b,s)-\widetilde U(a,s)+2e\bigr].
\]
A common state-independent reward supports the policy throughout this
box exactly when every directed cycle on \(B\) has total weight at
most zero. Indeed, robust obedience is equivalent to the finite
difference constraints \(r(a)-r(b)\geq w(a,b)\). Summing them proves
necessity, and Q's path-potential construction proves sufficiency when
there is no positive cycle. Unprescribed actions can receive
\(-\infty\). This is an exact test for the rectangular uncertainty
model and a sufficient certificate when P supplies only an error bound
for the actual CVaR utilities.

For a fixed Q direct mechanism, a uniform primitive payoff error
\(|u-\widetilde u|\leq e\) also implies a \(2e\) bound on any true
joint report-and-action deviation gain when the mechanism is incentive
compatible for the surrogate: each side of Q's incentive inequality
changes by at most \(e\). This extends the value-error logic in P's
conditional proposition to Q's double deviations, but it does not
restore exact incentive compatibility without slack. Applying P's
numerical value bound requires its bounded-loss and valid-query
assumptions uniformly in every state and action considered here.

## Limits and publication test

The example isolates a structural change: sampling bias can cross Q's
cycle boundary, after which no state-independent reward can repair the
policy. It does not establish a new general CVaR estimator bound or a
strategic learning theorem. The most useful next step is to formulate
and compare robust cycle margins for finite samples in richer signal
structures, with prior-work checking before claiming novelty. Emmy's
separate concern about ex-ante CVaR across signals remains distinct:
Q's expectation across signals cannot simply be replaced by a global
CVaR without rederiving its obedience criterion.
