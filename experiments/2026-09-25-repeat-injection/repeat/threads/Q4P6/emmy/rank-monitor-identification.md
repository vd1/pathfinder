# Rank monitoring and strategic teammates

## Question and scope

The sharpened question is whether P's visual pairwise comparisons can serve as a reward instrument for Q's strategically acting agents, and what extra observation is needed when agents can coordinate. This changes the initial, broader question about using P's credit assignment in Q's mechanism.

Q requires a reward schedule to deter both false reports and action deviations (Q.tex, "Mechanisms and revelation," lines 315-405; "Multi-agent mechanisms," lines 1508-1616). Its own taxonomy says a coarse action measure leaves payoff-relevant distinctions outside the reward schedule (Q.tex, lines 917-965). Q explicitly leaves collusion and full implementation for future work (Q.tex, line 426). P obtains pairwise judgments from egocentric images, fits a Bradley-Terry score, and feeds its softmax through terminal-zero potential shaping (P.tex, lines 281-350). P reports comparator errors when all agents face a wall (P.tex, line 550). Its score convergence is to the LMM's latent preference, while the Shapley interpretation assumes that this latent preference already equals true Shapley values (P.tex, lines 358-390).

## Two boundaries

First, P's potential shaping cannot change a rational agent's completed-episode action incentives if the initial potential is fixed before the strategic choice. For each agent and realized history, its shaping contribution telescopes:

\[
\sum_{t=0}^{T-1}\gamma^t\bigl(\gamma\psi_{i,t+1}-\psi_{i,t}\bigr)
=-\psi_{i,0}+\gamma^T\psi_{i,T}=-\psi_{i,0}.
\]

P sets terminal potential to zero. Thus every strategy has the same total payoff shift, even if the intermediate potential depends on actions, comparisons, or time. The result applies to action-stage obedience and to report-stage truthfulness only when the initial potential is independent of the report. It is a known property of potential shaping, already cited by P; the multi-agent result is documented by [Devlin and Kudenko (2012)](https://www.ifaamas.org/Proceedings/aamas2012/papers/2C_3.pdf). P's contribution is to learning speed in cooperative training, not to a change in strategic equilibrium.

Second, Bradley-Terry observations cannot identify common changes in all latent scores. With conditional comparison probability

\[
\Pr(i\succ j\mid c)=\sigma(c_i-c_j),
\qquad \sigma(x)=\frac{1}{1+e^{-x}},
\]

the full comparison data have the same law at \(c\) and \(c+z\mathbf 1\), assuming the comparison selection rule itself provides no absolute information. Any estimator or payment measurable only from these data also has the same law at these two profiles. This is an identification statement, irrespective of query count or estimation accuracy.

## A minimal example

Two agents choose effort \(e_i\in\{0,1\}\). Agent \(i\)'s intrinsic payoff is \(\beta(e_1+e_2)-k e_i\), and the designer values \(e_1+e_2\). Let their pairwise comparison be \(Y_i\in\{0,1\}\), with one winner and

\[
\Pr(Y_i=1\mid e)=\sigma\bigl(\eta(e_i-e_j)\bigr),
\qquad \eta>0.
\]

The distribution of \(Y\) is identical at \((1,1)\) and \((0,0)\). If each agent receives any payment \(r_i(Y)\), both agents gain \(k-2\beta\) by jointly moving from \((1,1)\) to \((0,0)\). Thus, when \(k>2\beta\), no comparison-only payment makes \((1,1)\) resistant to this coalition deviation. A rank prize can still make \((1,1)\) a Nash equilibrium because one agent's unilateral reduction does change the comparison law. This distinction matters because Q's incentive compatibility is unilateral.

The issue is familiar in relative performance evaluation; [Gibbons and Murphy (1989)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=461382) discuss collusion and shirking under relative pay. The pair-specific research opportunity would be to measure and control this common-mode blind spot for visual LMM monitors with strategically chosen views, not to claim that relative-performance collusion itself is new.

## Absolute anchor and a testable threshold

Give the monitor an additional binary outcome \(Z\), with \(\Pr(Z=1\mid e)=q_{e_1+e_2}\), where \(q_m=m/2\). Pay \(r_i=wY_i+bZ\), with \(w,b\geq0\). Put \(d=\sigma(\eta)-1/2\). For either fixed action of the other agent, raising one's effort changes expected utility by

\[
\Delta_i^{\mathrm{unilateral}}=\beta-k+wd+b/2.
\]

Hence high effort is strictly dominant if \(wd+b/2>k-\beta\). At the joint shift \((1,1)\to(0,0)\), the rank component stays constant, while the anchor payment falls by \(b\) per agent. The joint deviation is unprofitable for both if \(b\geq k-2\beta\). For \(\beta=0\), an anchor alone needs \(b>2k\) for strict unilateral obedience; rank plus anchor can instead use \(b\geq k\) and \(wd+b/2>k\). This is a stochastic episode-success example where the two signals distinguish different deviations. It does not establish lower total payments or that P's tasks have this success law.

More generally, if the entire observable monitor output has laws \(P_H\) and \(P_L\) under target and common-shirk profiles, and a payment is constrained to \([0,B]\), then

\[
\sup_{0\leq r\leq B}\bigl(\mathbb E_{P_H}r-\mathbb E_{P_L}r\bigr)
=B\,\operatorname{TV}(P_H,P_L).
\]

Thus a deviation saving more than \(B\operatorname{TV}(P_H,P_L)\) cannot be deterred for that agent by any bounded monitor-contingent reward. Pure pairwise Bradley-Terry observations have total variation zero for a common score shift. A binary anchor with success probabilities \(p_H,p_L\) supplies total variation \(|p_H-p_L|\). Q permits unbounded rewards, so the finite \(B\) constraint is an added deployment assumption; when total variation is zero, even unbounded finite payments cannot separate the profiles. This is an observability and budget bound, not a general sufficiency result for all Q incentive constraints. False-report and action double deviations require additional inequalities.

## Statistical caveat

P's Proposition 1 assumes that a connected comparison graph suffices for its unregularized
Bradley-Terry estimate to have a finite error bound (P.tex, lines 313-327 and 363-378).
For two agents and one decisive comparison, the queried graph is connected, but the
likelihood increases as \(c_1-c_2\to\infty\); there is no finite MLE. The same happens
after any number of wins in one direction. This is the standard [strong-connection
condition](https://arxiv.org/abs/1411.1168) for existence, not a new statistical finding.
A separate translation ambiguity means that \(c\) and \(c+z\mathbf1\) fit the same
data, so a Euclidean score-error bound requires a normalization. P acknowledges this
in its Shapley proposition, and its softmax potential does not depend on that translation.
A monitor used for incentive guarantees needs explicit regularization or a bounded score
space, followed by an error bound appropriate to strategic observations.

## Strategic views and a monitor-law test

The rank-prize threshold above assumes that the comparison law continues to track
effort after an agent changes its view. P does not test that assumption: its
comparison accuracy is averaged over training observations, and it reports frequent
errors when all egocentric views face walls (P.tex, lines 550 and 1072-1074).
The following is a stress-test model, not a finding about P's environment.

Take the target effort profile \((1,1)\) and a binary rank outcome
\(Y_i\sim\operatorname{Bernoulli}(1/2)\). Suppose a unilateral shirker has a
clear-view law \(\operatorname{Bernoulli}(1/2-d)\), but can choose an
uninformative view that makes its comparison law
\(\operatorname{Bernoulli}(1/2)\). If shirking saves a positive amount and
the reward uses only \(Y_i\), the latter deviation has exactly the target
monitor law. No finite comparison-contingent transfer deters it. An absolute
outcome signal or a separately scored view-quality signal is then necessary.
P's raw images could potentially support the latter, even though its specified
credit pipeline reduces them to comparisons.

There is a subtler failure even when each deviation is individually visible.
For one agent, let the target monitor law be
\(P_0=\operatorname{Bernoulli}(1/2)\) and two equally attractive camera-action
deviations yield \(P_1=\operatorname{Bernoulli}(1/2-d)\) and
\(P_2=\operatorname{Bernoulli}(1/2+d)\), with \(d>0\). Each law is separated
from \(P_0\), but \((P_1+P_2)/2=P_0\). Any one payment \(r(Y_i)\) has zero
average expected payment difference across these two deviations, so it cannot
make both costly when each saves a positive amount. This instantiates the
finite-monitor convex-hull criterion in [Ada's derivation](../ada/monitor-obedience.md).
The issue is simultaneous deterrence, not estimator accuracy.

The criterion also suggests an empirical certificate. Fix a finite monitor
alphabet of size \(m\), a specified target and \(J\) specified deviations,
and a common payment \(r\in[0,B]\). Estimate each monitor law from \(N\)
independent samples. By a coordinatewise Hoeffding bound and a union bound,
with probability at least \(1-\alpha\), every estimated law is within

\[
\delta=\frac{m}{2}\sqrt{\frac{\log(2m(J+1)/\alpha)}{2N}}
\]

in total variation of its true law. For any fixed payment in \([0,B]\),
the estimated target-versus-deviation reward difference then differs from
the true difference by at most \(2B\delta\). Consequently, a payment found
from the sampled laws with estimated obedience slack greater than
\(2B\delta\) for every listed deviation is strictly obedient for those
deviations with the stated probability. The bound is loose and does not
certify unlisted adaptive deviations, false reports, or a changing active
coalition. It states what a strategic-monitor experiment would need to sample.

## Publication test and unresolved assumptions

A useful paper would combine a constrained version of Q's verification-order mechanism with P-style visual monitoring: characterize which unilateral and coalition deviations the comparison kernel separates; choose the cheapest absolute anchor that restores separation; then test the inequalities under strategically selected camera views and changing active coalitions. P's passive average comparison accuracy does not establish the relevant worst-case separation. Important unresolved points are whether the visual comparator follows a Bradley-Terry law after strategic view choices, whether the sparse team outcome distinguishes the common shift, the cost and error of observing that outcome, and whether coalition-proofness is the desired solution concept. The bare two-agent threshold above is a benchmark, not a publication claim by itself.
