# Wrist-frame substitution as a decision problem

## Source connection

Input P states \(T_o=T_wG\), where \(G\) is the object pose relative to the donor wrist, and gives a conditional two-trial impossibility when identical wrist, encoder, and action histories require different receiving approaches ([P.tex](../inputs/P.tex), lines 45-70). It explicitly lacks measured physical pose traces and matched histories, and proposes measuring \(G\) at fixed wrist pose (lines 92-109).

Input Q defines predictions from information observable at prediction time, separates consistency, robustness, and error-dependent guarantees ([Q.tex](../inputs/Q.tex), lines 257-340), and requires an edge metric and sensitivity condition before prediction error propagates to a downstream guarantee (lines 1097-1109). It also prices prediction calls in objective units (lines 1242-1258). These are analysis tools, not guarantees for handover.

## Exact feasibility condition

Let \(z\) contain all receiver-visible wrist, motor-encoder, and action history at the commitment time. Let \(\Gamma(z)\) be the set of object-to-wrist transforms compatible with that history. For a fixed object, donor state, receiver, and task, let \(S(G)\) be the set of receiving actions that succeed at transform \(G\). Assume success is deterministic once the full relevant physical state and action are fixed; otherwise extend \(G\) to include the other hidden variables.

A deterministic receiver restricted to \(z\) can guarantee success for all compatible states exactly when

\[
\bigcap_{G\in\Gamma(z)} S(G)\ne\varnothing .
\]

The forward direction picks an action in the intersection. For the reverse direction, every action outside it fails in at least one compatible state. The same criterion holds for a randomized receiver when \(\Gamma(z)\) is finite and success probability one is required in each state. For an infinite state set, different actions can fail on different measure-zero sets, so the randomized statement needs care. In a two-state subproblem with disjoint success sets and an equal prior, the average success probability of any randomized receiver is at most \(1/2\). This is a numerical version of P's conditional proposition, not evidence that such states occur on the reported hand.

The criterion uses *task feasibility*. Large geometric orientation variation can be harmless if one receiver action works throughout \(\Gamma(z)\); small variation can matter near a grasp or collision boundary. A symmetric cube also creates task-dependent pose equivalences, so an angular error alone need not measure receiving difficulty.

This does not make Q's formal consistency definition empty. That definition is conditional on a supplied prediction being exact for an individual instance. What fails on two matched states with distinct poses is the stronger claim that a single deployed predictor using only \(z\) can be exact on both.

For long continuous histories, exact duplicate \(z\) values may never occur in finite data. With binary loss
\(\ell(a,G)=\mathbf{1}\{a\notin S(G)\}\), the decision-relevant conditional quantity is

\[
R^*(z)=\min_a\mathbb E[\ell(a,G)\mid Z=z]
=1-\max_a\Pr\{a\in S(G)\mid Z=z\}.
\]

In the two-state disjoint-action case with conditional state probabilities \(p\) and \(1-p\), this equals
\(\min\{p,1-p\}\). Approximate history matching therefore needs a justified tolerance or a controlled
reseating protocol. Pose dispersion alone does not determine \(R^*(z)\).

## A conditional prediction-set reduction

Suppose a set predictor \(C(z)\) has marginal pose coverage under a declared test distribution:

\[
\Pr\{G\in C(Z)\}\ge 1-\alpha .
\]

If the receiver finds \(a(z)\in\bigcap_{g\in C(z)}S(g)\) for every acted-on case, then its marginal failure probability is at most \(\alpha\), since failure implies the true transform lies outside the covered set. If failure loss is at most \(M\), expected failure loss is at most \(\alpha M\). With \(q\) sensing calls costing \(\kappa\) each, the corresponding accounting is

\[
\mathbb E[\mathrm{loss}+\kappa q]\le \alpha M+\kappa\mathbb E[q].
\]

This requires a valid coverage statement for the deployed distribution, a sound success set, and an action in the intersection. Marginal coverage gives a marginal failure statement, not a per-history or adversarial guarantee. An empty intersection requires an explicitly analyzed query, abstention, or different grasp. This reduction is elementary and should not be advertised as a new general theorem.

Q's multiplicative competitive ratio also needs care here. With binary failure loss and a successful clairvoyant grasp at each pose, \(\mathrm{OPT}(G)=0\); the ratio is undefined under Q's own positive-optimum convention. A handover study should instead report failure probability and additive expected loss with sensing and latency costs, or define a positive-cost objective and a benchmark that states which observations it can use. Q's priced-call benchmark leaves the offline optimum uncharged, which is a deliberate modeling choice rather than a neutral transfer to handover.

For the two equally likely hidden states, suppose a state-preserving sensor returns \(W\) with state-conditional
laws \(K_0,K_1\). The optimal failure probability after sensing is
\((1-\operatorname{TV}(K_0,K_1))/2\). If the only other charges are failure penalty \(M\) and sensor
price \(\kappa\), sensing lowers expected additive cost exactly when
\(\kappa<M\operatorname{TV}(K_0,K_1)/2\). This is a standard binary testing identity. Calling the same
predictor again on unchanged \(z\) gives no new state information; the query must obtain a genuinely
state-dependent measurement. Sensor contact that changes \(G\) requires a transition model and invalidates
this fixed-state calculation.

For a candidate object pose \(\hat G=(\hat R,\hat t)\), true pose \(G=(R,t)\), point \(x\) with \(\|x\|\le\rho\), and relative rotation angle \(\theta\), a fixed wrist gives

\[
\|T_wGx-T_w\hat Gx\|
\le \|t-\hat t\|+2\rho\sin(\theta/2).
\]

A verified geometric clearance margin exceeding this bound can certify the corresponding point constraint. Certifying the whole receiving trajectory and grasp also needs orientation, contact, friction, donor collision, and actuation margins. This is the missing task-sensitivity step before Q's error-propagation rule can be used.

## Publication test and limits

The most concrete experiment is to hold the donor wrist fixed, externally record marked-object \(G\) during in-hand rotation or controlled reseating, and group trials by receiver-visible histories. For each group, measure the spread of \(G\), the successful receiver-action sets, and whether their intersection is empty. Then compare wrist-only, encoder-history, last-seen-pose, fresh-view, and robust-grasp receivers on the same orientation-sensitive handover task. Record success, collision, latency, and sensing cost. A rigid grasp control distinguishes internal object motion from other handover error. This sharpens P's proposed experiment by making *decision disagreement*, rather than pose variance alone, the key outcome.

Theoretical ingredients alone are unlikely to support a paper. [Hsiao et al. (2011)](https://dspace.mit.edu/entities/publication/6e875648-ad9a-438b-9c77-ad779b82610c) already study grasping under object-pose uncertainty with information-gathering trajectories; [Yang et al. (2023)](https://arxiv.org/abs/2303.12246) give covered pose-uncertainty sets from vision; and a [2025 robot-to-robot handover study](https://link.springer.com/article/10.1007/s10514-025-10201-y) reports relative object motion as a common handover failure because it misaligns a precomputed receiver grasp. None of these sources establishes the proposed matched-history phenomenon for P's wrist-frame substitution on the hand discussed in P.

The current pair therefore supports a focused empirical question, not a demonstrated performance failure or a new general guarantee: **under what measured in-hand pose variation and receiving tolerances does the donor wrist cease to be a sufficient handover frame, and what added observation is worth its cost?**
