# A wall gate with strategically selected reports

## Source interface and sharpened question

Q defines a direct mechanism in which an agent reports \(\hat t\in C(t)\),
then takes an action. Incentive compatibility must deter a joint deviation
in report and action [Q, lines 348-396](../inputs/Q.tex). Q also models
enforceable permissions through a reward of \(-\infty\) for a prohibited
action [Q, lines 319-345](../inputs/Q.tex). P calibrates a Hausdorff error
radius for one frozen wall fitter and certifies every non-abstained point
at its first wall-distance gate [P, lines 71-108](../inputs/P.tex).
The sharpened question is whether the first gate stays correct when an
agent chooses both a report-contingent wall model and a scan point.

## Menu-wide certificate

Let \(J\) be a finite menu of wall fitters \(F_j\), fixed before calibration.
For calibration episodes \(Z_i=(X_i,W_i^*)\), where \(i=1,\ldots,n\), define

\[
R_i=\max_{j\in J}d_H(F_j(X_i),W_i^*),\qquad
k=\left\lceil(n+1)(1-\alpha)\right\rceil.
\]

Let \(\varepsilon\) be the \(k\)th order statistic of
\(R_1,\ldots,R_n\), or \(+\infty\) when \(k>n\).
Assume that the complete episodes \(Z_1,\ldots,Z_n,Z_{n+1}\) are
exchangeable, that the fitters are fixed independently of these episodes,
and that estimated and reference wall sets are nonempty compact sets with
a common frame and wall convention. Then P's rank argument gives

\[
\Pr\left\{\max_{j\in J}d_H(F_j(X_{n+1}),W_{n+1}^*)\leq\varepsilon\right\}\geq 1-\alpha.
\]

On this single event, P's distance-to-set inequality holds for every
\(j\in J\) and every point \(p\). Thus a gate that accepts only if
\(\operatorname{dist}(p,F_j(X_{n+1}))+\varepsilon\leq\delta\), rejects
only if \(\operatorname{dist}(p,F_j(X_{n+1}))-\varepsilon>\delta\), and
abstains otherwise agrees with the reference-wall gate for every
non-abstained decision. The choice of \(j\) and \(p\) may depend
arbitrarily on the new room, the agent's private information, and earlier
decisions in that room. This is a gate-level guarantee about decisions
actually passed through the enforcement wrapper. It does not require
truthful reporting or obedience to a recommended point. It does not cover
an agent that can bypass the gate or submit an uncalibrated wall set.

## Why separate certificates are insufficient

Let \(U\) be uniform on \(\{1,\ldots,m\}\) and visible in the new
room's features before reporting. Let \(W^*\) be the vertical segment at
horizontal coordinate \(0\) with height \(1\). Fitter \(j\) returns
the parallel segment at coordinate \(0.4\) when \(U=j\), and otherwise
returns \(W^*\). Each fixed fitter has \(d_H(F_j(X),W^*)=0\) with
probability \(1-1/m\). Hence each has a valid population-level radius
\(0\) at miscoverage \(\alpha=1/m\). An agent that reports \(j=U\) and
submits \(p=(0.4,0.5)\) causes its chosen fitted-wall gate with radius
\(0\) to accept, while the reference-wall gate at P's
\(\delta=0.15\,\mathrm m\) rejects, with probability \(1\). This
refutes adaptive-report validity from separate marginal coverage
statements. It does not claim that every finite-sample split-conformal
realization uses radius \(0\).

The menu score fixes that failure, but it can be expensive: in this
example \(\max_j d_H(F_j(X),W^*)=0.4\) in every room, so the resulting
certificate abstains at the displayed point. A useful paper would need
an efficiency result or an experiment showing that menu-wide calibration
leaves a meaningful accepted region for realistic reports.

## A tighter certificate for an enforced scan menu

Suppose the wrapper also restricts report \(j\) to a nonempty finite set
\(C_j(X)\) of points computed from the observed episode by a rule frozen
before calibration. The sets must include every point the agent can submit
under that report. Calibrate the episode score

\[
T_i=\max_{j\in J}\max_{p\in C_j(X_i)}
\left|\operatorname{dist}(p,F_j(X_i))
-\operatorname{dist}(p,W_i^*)\right|.
\]

Using the same split-conformal order statistic and exchangeable complete
episodes yields a radius \(\eta\) for which
\[
\Pr\left\{\forall j\in J,\ \forall p\in C_j(X_{n+1}),\
\left|\operatorname{dist}(p,F_j(X_{n+1}))
-\operatorname{dist}(p,W_{n+1}^*)\right|\leq\eta\right\}
\geq1-\alpha.
\]
Replacing \(\varepsilon\) by \(\eta\) in the gate inequalities therefore
protects every submitted point under any report and later action choice.
The calibration and new episode must use the same candidate-generation
rule; the agent cannot add points outside its enforced set. P's distance
inequality gives \(T_i\leq R_i\) for each calibration episode, so the
scan-menu radius \(\eta\leq\varepsilon\) on the same data, including the
infinity convention. It can be strictly smaller when large wall errors
occur away from every eligible scan point. This improves the certificate
for a limited action interface, while giving up P's guarantee over all
possible points. The construction and dominance proof remain direct
conformal corollaries; usefulness requires measuring the eligible scan
sets and fallback rate.

## Research status

The max-score construction is a direct conformal simultaneous-coverage
argument, not a new general conformal theorem. Existing work studies
[post-selection of the miscoverage level](https://arxiv.org/abs/2304.06158),
[data-dependent model selection](https://arxiv.org/abs/2408.07066), and
[online choice among multiple conformal models](https://arxiv.org/abs/2411.03678).
The potential contribution here is a precise report-and-action interface
for Q's strategic mechanisms using P's geometry, plus a measured
comparison of menu-wide coverage, abstention, and incentive-compatible
menu design. Neither Q nor P supplies the ground-truthed rooms or a
strategic deployment experiment needed to establish operational value.
