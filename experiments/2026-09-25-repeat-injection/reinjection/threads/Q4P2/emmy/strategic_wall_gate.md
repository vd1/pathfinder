# Strategic selection and calibrated wall gates

## Source interfaces

Q makes the agent's report select a continuation plan, then gives the agent a private signal before its action. Incentive compatibility must deter a joint report and action deviation ([Q, lines 348-396](../inputs/Q.tex)). Q's verification order treats capability evidence as impossible to counterfeit ([Q, lines 299-303](../inputs/Q.tex)). Its signal-policy cycle condition characterizes obedience under a state-independent reward ([Q, lines 522-564](../inputs/Q.tex)).

P freezes one wall fitter, calibrates its room-level Hausdorff error on exchangeable episodes, and obtains marginal simultaneous correctness of every non-abstained first wall-distance gate decision ([P, lines 71-108](../inputs/P.tex)). Its certificate covers this first gate only; it supplies neither conditional coverage nor a validated fallback ([P, lines 108-114 and 135-149](../inputs/P.tex)).

The joint question is sharper than whether a single calibrated gate is correct: **can a gate certificate survive a privately informed agent's choice of perception regime and whether to act?** This is a hypothetical extension of P's pipeline. P does not claim that its room fitter is a strategic agent.

## A deviation-robust first-gate certificate

Let \(J\) be a finite, fixed menu of wall fitters. Each \(F_j\) is frozen independently of calibration. An episode \(Z=(X,W^*)\) contains the scan input and a compact reference wall set in a common frame. All candidate outputs \(F_j(X)\) are nonempty compact wall sets using the same wall convention. Calibration episodes \(Z_1,\ldots,Z_n\) and a new episode are exchangeable. In Q's timing, a type or pre-report room feature can select \(j\), and a later private signal can select whether and where to use the gate. The simultaneous result below even allows \(j\) to be chosen after that signal. The menu, calibration data, and conformal quantile must be fixed before selection.

Set

\[
R_i=\max_{j\in J}d_H(F_j(X_i),W_i^*),\qquad
k=\lceil(n+1)(1-\alpha)\rceil.
\]

Let \(\varepsilon\) be the \(k\)-th order statistic of \(R_1,\ldots,R_n\), or \(+\infty\) if \(k>n\). The exchangeable-rank argument in P gives

\[
\Pr\!\left\{\forall j\in J:\ d_H(F_j(X_{\rm new}),W_{\rm new}^*)\le\varepsilon\right\}\ge 1-\alpha.
\]

On this one event, P's distance-to-set inequality holds for every \(j\) and every point \(p\). For the chosen \(j\), accept only when \(\operatorname{dist}(p,F_j(X))+\varepsilon\le\delta\); reject only when \(\operatorname{dist}(p,F_j(X))-\varepsilon>\delta\); abstain otherwise. Every such non-abstained decision agrees with the reference-wall gate, regardless of how the agent selects \(j\) and \(p\). The probability is marginal over episodes and calibration. This result says nothing about the agent's incentive to obey the protocol or about downstream doors and motion.

This calibration can be vacuous. A single poor menu item can inflate \(\varepsilon\) for all items, and \(\varepsilon\ge\delta\) may eliminate certified acceptances. The finite menu must contain every wall estimate the agent can actually submit; if it can synthesize arbitrary new estimates after calibration, the argument does not apply.

The statistical certificate is not Q's hard evidence. Q's verification order assumes a capability claim cannot be counterfeited at all; the conformal event still fails with probability up to \(\alpha\). The menu-wide result is a chance constraint on a separately enforced gate, not a proof of truthfulness or of an exact verification relation.

## Why separate certificates and conditional deployment fail

Suppose each fitter has an individual failure event \(E_j\) with \(\Pr(E_j)\le\alpha\). If a privately informed agent chooses \(j\), its selected failure event lies in \(\bigcup_jE_j\), so the only generic bound is \(\Pr(E_{j_{\rm chosen}})\le\min(1,|J|\alpha)\). This factor can be attained by disjoint failure events and a signal revealing which fitter fails. The geometry can realize the example: in one dimension take \(W^*=\{0\}\), \(\delta>0\), and zero nominal radius. On event \(E_j\), fitter \(j\) returns \(\{2\delta\}\), while the other fitter returns \(\{0\}\). Selecting \(j\) and point \(p=2\delta\) certifies acceptance against its estimate although the reference gate rejects. These fixed zero radii illustrate non-composition of marginal events; this example does not assert that a particular finite calibration sample will output zero.

Even the joint certificate does not imply a useful error rate conditional on deployment. Let \(D\) mean that the agent uses a non-abstained gate decision, \(q=\Pr(D)>0\), and \(B\) mean that this decision is wrong. The joint event gives

\[
\Pr(B\mid D)=\frac{\Pr(B\cap D)}{q}\le\min\{1,\alpha/q\}.
\]

If the agent has a private signal revealing exactly the exceptional rooms and acts only there, the conditional error can be one. The unconditional error bound still holds. This distinction matters if performance is reported per deployment or if the agent can choose which rooms to enter. P does not calibrate an agent-selected trajectory distribution.

## Obedience is a separate constraint

Consider a single type with two private signals \(g,b\) that indicate low and high gate risk, respectively, and two feasible actions: use \(U\) and fallback \(F\). Let \(U_t(a,s)\) be Q's posterior utility and define \(\Delta(s)=U_t(U,s)-U_t(F,s)\). A state-independent reward \(r\) supports the desired contingent policy \(a(g)=U\), \(a(b)=F\) only if

\[
\Delta(g)\ge r(F)-r(U)\ge\Delta(b).
\]

Thus \(\Delta(g)\ge\Delta(b)\) is necessary and sufficient for weak obedience with an unrestricted action reward, exactly Q's two-signal cycle inequality. When the agent values gate use more in high-risk rooms, \(\Delta(g)<\Delta(b)\), no such reward can induce the desired selective fallback. Equal values permit only indifference, which is weak implementation. Report incentives add Q's separate type-cycle constraints. State-contingent rewards or enforceable permissions may change this conclusion, but P provides no runtime ground-truth wall to score the hidden risk state.

## Publication test and limits

A focused paper could characterize the feasible safety-throughput frontier for a finite report menu: simultaneous calibration over all report-contingent fitters, followed by Q's obedience and truthfulness conditions for use versus fallback. A useful result would quantify how much simultaneous calibration enlarges abstention and identify when the desired fallback policy is implementable with the state measures actually available. An experiment would require ground-truthed, episode-level wall sets, a fixed menu, an independently defined fallback, and an agent or policy with measurable report and action choices. Neither Q nor P supplies those data or an implemented strategic wall estimator. The max-score lemma and two-action inequality alone are short corollaries, so they are a research starting point rather than a standalone publication claim.

Related statistical problems are already studied. [Sarkar and Kuchibhotla](https://arxiv.org/abs/2304.06158) give simultaneous conformal inference after a data-dependent choice of miscoverage level. [Liang, Zhu, and Barber](https://arxiv.org/abs/2408.07066) study conformal prediction after model selection using holdout data. [Bao and colleagues](https://jmlr.org/papers/volume26/24-0452/24-0452.pdf) give selection-conditional coverage for online selected predictions. None of these abstracts establishes the Q/P wall-gate mechanism considered here, but they reinforce that a generic post-selection or conditional-coverage observation is insufficient as a novelty claim.
