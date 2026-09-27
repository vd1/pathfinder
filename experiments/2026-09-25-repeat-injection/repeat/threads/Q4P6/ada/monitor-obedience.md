# Monitor laws and obedience

## Question

Can the visual comparison monitor in P support the action incentives required by Q? This is a narrowed question about rewards paid from observable monitor outputs. Q itself permits richer action and state contingent rewards, so the restrictions below are added for this bridge (Q.tex, lines 1542-1604). P supplies the candidate monitor: LMM judgments of agents' egocentric images, followed by Bradley-Terry aggregation (P.tex, lines 281-329). Its implemented score is used through potential shaping (P.tex, lines 331-349), which cannot change completed-episode incentives when initial potential is fixed and terminal potential is zero.

## Exact finite-monitor test

Fix an agent, a target action profile, and a finite monitor output space \(\mathcal M\). Let \(P_0\) be the law of the output on the target path and \(P_j\) its law after profitable unilateral deviation \(j\). Let \(g_j>0\) be the deviation's gain in intrinsic expected utility. The designer commits to one monitor-contingent payment \(r:\mathcal M\to[0,B]\), with \(B>0\). Q-style obedience for this fixed target requires all the inequalities

\[
\mathbb E_{P_0}r-\mathbb E_{P_j}r\ge g_j.
\]

For a probability vector \(\lambda\) over deviations, write \(P_\lambda=\sum_j\lambda_jP_j\) and \(g_\lambda=\sum_j\lambda_jg_j\). A single feasible payment exists **if and only if**

\[
B\operatorname{TV}(P_0,P_\lambda)\ge g_\lambda
\qquad\text{for every probability vector }\lambda.
\]

Indeed, with \(D_j(r)=\mathbb E_{P_0}r-\mathbb E_{P_j}r-g_j\), feasibility is \(\max_{0\le r\le B}\min_jD_j(r)\ge0\). The minimum over \(j\) equals the minimum over their probability mixtures. Finite-dimensional minimax interchanges the maximum and minimum because both domains are compact and convex and the expression is bilinear. For fixed \(\lambda\), the best payment is \(B\) on outputs where \(P_0(m)>P_\lambda(m)\) and zero elsewhere, so

\[
\max_{0\le r\le B}\bigl(\mathbb E_{P_0}r-\mathbb E_{P_\lambda}r\bigr)
=B\operatorname{TV}(P_0,P_\lambda).
\]

The criterion covers every unilateral deviation in the chosen finite model with one reward schedule. It is stronger than checking \(B\operatorname{TV}(P_0,P_j)\ge g_j\) for each deviation separately. For example, let the monitor be binary, \(P_0=\operatorname{Bernoulli}(1/2)\), \(P_1=\operatorname{Bernoulli}(0)\), and \(P_2=\operatorname{Bernoulli}(1)\), with \(g_1=g_2>0\). Each deviation is individually distinguishable from the target, but \((P_1+P_2)/2=P_0\). No common monitor payment deters both. This is a mathematical counterexample, not an empirical assertion about P's comparator.

Q notes that finite-policy implementability can be checked by a linear feasibility program (Q.tex, line 915); the condition above is its monitor-law dual for one agent and a fixed target. It does not cover false-report and action double deviations, other agents' incentives, or coalitional deviations unless their distinct constraints are included. Nor is it a new general mechanism-design theorem. The bridge to test is whether a P-like comparison monitor plus an absolute task-outcome signal has enough separation, uniformly over strategic camera and action choices, to satisfy the relevant constraints with an affordable \(B\). P's average passive comparison accuracy and its Bradley-Terry latent-score proposition do not answer that question (P.tex, lines 358-376 and 540-552).

## Statistical prerequisite

P defines an unregularized Bradley-Terry maximum likelihood estimate on all real score vectors (P.tex, lines 316-327), then claims a finite score-error bound from an undirected connected comparison graph (P.tex, lines 363-373). With two agents and all decisive judgments favoring one, the graph is connected but the likelihood increases as the winning score difference tends to infinity, so no finite maximum exists. Scores are also identified only up to a common translation, while the displayed bound compares uncentered vectors. P acknowledges translation ambiguity in its Shapley interpretation (P.tex, lines 385-386), and its softmax shaping is translation invariant. The point for this proposed bridge is narrower: score-error bounds cannot be imported into a strategic incentive margin without a specified gauge, estimator regularization or bounded score set, and a guarantee under the monitor laws induced by deviations.
