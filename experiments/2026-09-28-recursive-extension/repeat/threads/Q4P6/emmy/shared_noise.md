# What peer agreement can certify under shared noise

## A joint counterexample

Let the desired binary state be \(\theta\sim\operatorname{Bernoulli}(1/2)\). A single nuisance bit \(Z\sim\operatorname{Bernoulli}(1/2)\), independent of \(\theta\), corrupts every observer of one scene. Two agents observe the same bit

\[
S_1=S_2=S=\theta\oplus Z.
\]

Treat \(S_i\) as an ex ante type in a one-stage peer-reporting game. Each type predicts the other perfectly: \(\beta_i[s](S_j=s)=1\), so Q's separation condition (S) holds maximally. The quadratic score in Q's (PR) is \(q(r_i,r_j)=2\mathbf 1\{r_i=r_j\}-1\). If the other agent reports truthfully, reporting \(S_i\) yields score \(1\), while reporting its opposite yields \(-1\). Thus strategic truthful reporting is a strict best response. Yet \(S\) is independent of \(\theta\), so no statistic of the reports predicts the desired state better than chance. Peer agreement identifies the common observed bit, including its shared error.

For the P-side comparison, let \(\theta=1\) mean agent 1 truly contributed more than agent 2. Given the shared observed bit \(S\), suppose each repeated LMM query independently says that agent 1 wins with probability \(p_S=\sigma(a(2S-1))\), for \(a>0\) and logistic link \(\sigma\). The two-agent Bradley--Terry estimate of the score difference converges to \(a(2S-1)\), an LMM preference of the observed scene. Because \(S\) is independent of \(\theta\), its sign has probability \(1/2\) of matching the true ordering, for arbitrarily many queries. This counterexample grants conditional independence of LMM queries, so it does not depend on a failure of conditional maximum-likelihood estimation.

Unconditionally on the shared nuisance, the repeated judgments are correlated. If \(\bar Y_K\) is their mean and \(p=\sigma(a)\), then

\[
\operatorname{Var}(\bar Y_K\mid\theta)
= (p-1/2)^2 + p(1-p)/K.
\]

The first term is an error floor. P's concentration argument in its Convergence and Robustness proposition and appendix requires a stable target and independent or suitable martingale increments. Repeating calls on the same corrupted observation only concentrates around a nuisance-dependent preference. This does not contradict Q: Q guarantees a truthful equilibrium relative to a specified conditional peer-type law and uses an additional utility cancellation and off-support penalty for obedience.

The counterexample also distinguishes two other issues. Q's direct mechanism draws interim signals after type reports (Q, Definition of Multi-agent direct mechanism, lines 1542-1567). P's LMM compares current egocentric images (P, LMM-based Pairwise Comparison, lines 281-312). A literal use of Q's theorem for P requires redefining the images or judgments as reportable types, with the corresponding conditional peer law. Also, Q proves existence of a truthful-report equilibrium, not that the mechanism selects it. In the symmetric example, both reporters flipping their bits is another equilibrium of the peer score.

## A sharp restricted recovery statement

For each of \(G\) independent observation groups of the same fixed \(\theta\), let \(Z_g\sim\operatorname{Bernoulli}(q)\), independently across groups, where \(q<1/2\), and let the two observers in group \(g\) see \(S_{g1}=S_{g2}=\theta\oplus Z_g\). Within each group, the peer-score argument still makes a truthful report a strict best response when its peer reports truthfully. If those truthful reports are selected, a majority vote over one bit from each group gives

\[
\Pr(\widehat\theta\ne\theta)
\le \exp\{-2G(1/2-q)^2\}.
\]

The independent unit is a group, not a repeated query. With one group, the best possible error is \(q\), even if it contains arbitrarily many observers. If \(q=1/2\), no number of groups identifies \(\theta\). If the orientation restriction \(q<1/2\) is absent, the laws under \((\theta,q)\) and \((1-\theta,1-q)\) are observationally equivalent. An audited label, known direction of accuracy, or a calibrated independent channel must orient the reports. Cardinal Shapley recovery requires a stronger calibrated relation between the comparison probabilities and Shapley differences, plus adequate comparisons. The majority bound concerns a binary ordering only.

This is a possible research line: characterize target identification separately from peer-type separation, then estimate contribution rankings with uncertainty calibrated to independent scenes and audits. A full contribution claim would require a model tying scene-level preferences to causal contribution; P's Interpretability via Shapley Values proposition explicitly assumes that tie (P, lines 380-389). The remaining open strategic step is selecting truthful reports when peers can coordinate on a common relabeling.

## Sources and scope

Q, Peer discipline, lines 1649-1718, supplies separation (S), score (PR), and the support-wise implementation result. Q's multi-agent timing appears at lines 1542-1567. P, Pairwise Comparison and Rank Aggregation, lines 281-329, supplies the image-to-comparison and Bradley--Terry steps. P, Convergence and Robustness and Interpretability via Shapley Values, lines 351-389, identifies the LMM preference target and states the additional Shapley assumption.

Prior peer-prediction work already studies truthful equilibria and signal relabeling. [Kong and Schoenebeck, *Equilibrium Selection in Information Elicitation without Verification via Information Monotonicity*](https://arxiv.org/abs/1603.07751) explicitly discusses relabeling equilibria. [Shnayder et al., *Informed Truthfulness in Multi-Task Peer Prediction*](https://arxiv.org/abs/1603.03151) studies multi-task informed truthfulness. Those papers limit any novelty claim for the peer-score observation alone; the potential contribution here would need to join target calibration, clustered embodied comparisons, and strategic reporting in a useful theorem or experiment.
