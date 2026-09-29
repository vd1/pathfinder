# Energy-conserving assignment and the limit of peer scores

## Sources and sharpened question

Q defines incentive compatibility as truthful reporting followed by obedience to a
signal-contingent recommendation (Q, Section 4, Definition "Honesty, obedience,
and action feasibility," lines 1568-1616). Its peer-discipline theorem
implements any feasible target under separated beliefs by scaling a co-player
score and prohibiting off-path actions (Q, Section 5, Proposition "Support-wise
implementability of every feasible rule," lines 1653-1736). Q explicitly
treats rewards as free and unbounded (Q, introduction, line 267).

P has finite energy, token-dependent reasoning costs, nonbinding recommendations,
and a job reward split among successful agents who attempt the same job
(P, Section 3, lines 147-169 and 199-238). P's competitive and cooperative
conditions change the agents' prompted objectives, while the job payout rule
stays the same (P, Section 4, lines 264-276). P reports more collisions without
discussion (P, Section 5, lines 569-629), but the no-discussion runs also have
more active agents and job attempts (P, Tables in lines 357-429 and 569-629).

I sharpen the question to: **Can P's fixed job payout be reallocated so that an
efficient assignment is stable under selfish objectives, and when does the
benefit repay the cost of communicating it?** The first part has a one-round,
known-type answer below. The communication comparison, private-type problem,
and dynamic-survival problem remain open.

## Collision value and the incentive wedge

Fix one job \(j\) with reward \(R_j\). Two agents try it. Write \(S_i\)
for the event that agent \(i\) succeeds, \(p_i=\Pr(S_i)\), and
\(q=\Pr(S_1\cap S_2)\). P pays a total of \(R_j\) whenever at least
one agent succeeds. Thus expected group payout is

\[
R_j\Pr(S_1\cup S_2)=R_j(p_1+p_2-q).
\]

The marginal group payout from the second attempt is
\(R_j(p_2-q)=R_j\Pr(S_2\cap S_1^c)\). P's equal split instead gives
agent \(2\) expected private payout \(R_j(p_2-q/2)\). The private value
of entering an occupied job exceeds its marginal group payout by
\(R_jq/2\). This identity allows arbitrary dependence between the agents'
successes. Conditional independence gives the special case \(q=p_1p_2\).

If agent \(2\) can instead attempt an unoccupied job \(k\), with success
probability \(p_{2k}\) and expected attempt costs \(c_{2j}\) and
\(c_{2k}\), moving to \(k\) increases expected group energy by

\[
R_kp_{2k}-R_j(p_2-q)-(c_{2k}-c_{2j}).
\]

The collision can therefore be efficient. For example, with equal costs,
\(R_j=800\), \(p_1=0.1\), \(p_2=0.9\), independence, and an empty job
worth \(R_kp_{2k}=10\), the second attempt's marginal expected payout is
\(648\). Reassigning it loses expected energy. Collision counts alone have
no fixed welfare sign.

## A bounded payout construction

Consider a one-round game with a fixed active set, job-or-idle actions,
risk-neutral agents maximizing expected own energy, known success laws and
expected token costs, and no continuation value. A coordinator selects a
global maximizer of expected total energy over all job-or-idle profiles.
Collisions are allowed. For each job, rank assigned agents above visitors,
with a fixed order within each class. Give the whole \(R_j\) to the
highest-priority successful solver, or zero if none succeeds. The total
realized payout remains P's original payout. Each agent's potential
correctness and expected token cost on a given job are assumed stable when
the other agents change jobs.

If \(x_i^{\mathrm{priority}}\) and \(x_i^{\mathrm{split}}\) are the two
realized payouts, the required reward adjustment is
\(r_i=x_i^{\mathrm{priority}}-x_i^{\mathrm{split}}\). For each job,
\(\sum_i r_i=0\) and \(|r_i|\leq R_j\). The adjustment is funded entirely
by reallocating that job's existing prize.

At the target profile, a unilateral deviation to another job \(k\) pays
the entrant \(R_k\) exactly when it succeeds and all agents assigned
to \(k\) fail. This is its marginal contribution to expected group payout
at \(k\). At its original job \(j\), agent \(i\)'s expected priority
payout is at least its marginal contribution, since it can win whenever
all higher-priority incumbents fail, even if a lower-priority incumbent
also succeeds. Thus, for every unilateral job or idle deviation,

\[
\Delta\mathbb E[\text{own energy}]
\leq\Delta\mathbb E[\text{group energy}].
\]

The inequality includes the change in the deviator's own token or idle cost,
which equals its contribution to group cost. Since a global group-energy
optimum has no profitable unilateral group-energy change, the target is a
Nash equilibrium. Ties, other equilibria, and imperfect optimization remain
possible. The mechanism changes only who receives an existing payout. It
needs no new energy, negative balance, or independence assumption. In Q's
notation it is an action-dependent reward adjustment that offsets P's
original split rule (Q, multi-agent reward schedule at lines 1510-1542).

This construction does not elicit private success probabilities. It also
excludes donations. A donation changes the donor's own balance while
conserving current group energy, and it can change future survival, so the
one-round payoff inequality does not cover it. P's reactivation findings
show why this is material (P, baseline results, lines 419-430; discussion,
lines 845-849).

Even without donations, priority can change future survival. In a stylized
two-agent example, each begins with \(15\) energy, spends \(10\) to solve
the same job, and succeeds; the job pays \(20\). P's split leaves balances
\((15,15)\), while priority leaves \((25,5)\). A later call costing
\(10\) with no reward leaves both split-rule agents active, but depletes
the priority loser. The one-round theorem therefore does not imply an
improvement in multi-round welfare.

## Why Q's peer score cannot be imported without a budget condition

Q's score scale is chosen large enough that its truth-telling gain exceeds
any payoff gain from lying. The proof requires \(\Lambda\delta\geq M\),
where \(\delta\) is the smallest squared distance between co-player belief
distributions and \(M\) bounds a non-score gain from misreporting
(Q, lines 1704-1734). If scores must be paid in P's survival energy, a
bound on available transfers matters.

A simple bound makes this precise. Let two private types induce co-player
outcomes with laws \(P_0\) and \(P_1\). A report score \(z_r(y)\) lies in
\([0,B]\). Suppose each type would gain at least \(M\) from falsely
reporting if scores were absent. Truthfulness for both types requires

\[
\mathbb E_{P_0}[z_0-z_1]\geq M,\qquad
\mathbb E_{P_1}[z_1-z_0]\geq M.
\]

Adding the inequalities and using \(|z_0(y)-z_1(y)|\leq B\) yields

\[
2M\leq\sum_y(P_0(y)-P_1(y))(z_0(y)-z_1(y))
\leq 2B\operatorname{TV}(P_0,P_1).
\]

Consequently \(B\geq M/\operatorname{TV}(P_0,P_1)\). For
\(P_0=\operatorname{Bernoulli}(1/2-\varepsilon)\) and
\(P_1=\operatorname{Bernoulli}(1/2+\varepsilon)\), the necessary range is
\(B\geq M/(2\varepsilon)\). This is a narrow impossibility for bounded
scores of this form, not a theorem against every possible allocation
mechanism. It also does not apply when Q's reward is an unconstrained
change in utility rather than a transfer of P-energy.

## Empirical test and unresolved issues

An informative test would hold seeded jobs, models, objectives, and
communication length fixed while randomizing the split rule against
assignment priority. It should record joint correctness on shared jobs,
counterfactual success on other jobs through held-out evaluations, token
costs by phase and job, group energy, deactivation, and donations. The main
outcome should be net group energy and survival, with collisions reported
as a mechanism variable. P's five-seed aggregates and collision counts do
not identify the welfare effect or the private success laws (P, Section 7,
lines 892-912).

The theoretical next step is to combine private capability reports, a finite
scoring budget, and a continuation value for survival. The main identification
hurdle is that P observes success only on attempted jobs. The main design
hurdle is that an energy transfer can change both current incentives and the
set of agents that remain active later.
