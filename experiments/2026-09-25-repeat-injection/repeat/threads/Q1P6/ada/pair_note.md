# Q and P: the prediction target for rank-based reward shaping

## Paper evidence

Q defines prediction error against a task-specific target and asks for a downstream cost guarantee in its Evaluation Criteria (Q, lines 257-339). Its Semantic Predictions section requires an adapter and a task-defined error before a model output can enter an algorithmic guarantee (Q, lines 1169-1198). Its Pricing the Prediction section charges predictor calls explicitly (Q, lines 1242-1258).

P queries every ordered pair of active agents, fits Bradley-Terry scores, and applies their softmax as a vector potential (P, lines 283-349). P's Proposition 1 controls error relative to the LMM's latent preference under a connected comparison graph, while Proposition 2 identifies that preference with Shapley values only under an extra assumption (P, lines 358-390). P evaluates pairwise accuracy against dense task rewards and varies the number of queries (P, lines 540-548 and 939-1075). Its MAPPO experiments train for a finite number of environment steps (P, lines 450-525).

## Exact objective and changing teams

Embed the potential in a fixed population of agents: \(\psi_{i,t}=0\) when agent \(i\) is absent or the episode is terminal. If every agent receives the shaping transition on every step, including exit and reentry steps, then

\[
\sum_{t=0}^{T-1}\gamma^t(\gamma\psi_{i,t+1}-\psi_{i,t})
=-\psi_{i,0}+\gamma^T\psi_{i,T}=-\psi_{i,0}.
\]

The same realized \(\psi_{i,t}\) must appear in both adjacent terms. The initial potential must be fixed before the policy's first action. Under these conditions, any LMM output preserves each agent's exact policy ordering. The comparison quality can affect finite-training behavior, not the exact objective. P gives potentials with dimension \(|I^t|\), but does not state the cross-coalition embedding or reward-credit convention needed to check this boundary.

For example, suppose shaping is credited only when an agent is active. Write \(a_{i,t}=1_{\{i\in I^t\}}\). Even with zero potential while absent and at episode termination, the masked sum is

\[
\sum_{t=0}^{T-1}\gamma^t a_{i,t}(\gamma\psi_{i,t+1}-\psi_{i,t})
=-a_{i,0}\psi_{i,0}
+\sum_{t=1}^{T-1}\gamma^t(a_{i,t-1}-a_{i,t})\psi_{i,t}.
\]

At reentry the summand is \(-\gamma^t\psi_{i,t}\). The positive term on the preceding transition was omitted. This is a conditional implementation counterexample, not evidence that P's implementation actually uses this mask.

For nonterminal, nonempty coalitions, P's softmax has \(\sum_i\psi_{i,t}=1\). Therefore, if the team pools every agent's shaped reward by summation, its total potential is independent of the rank scores. This does not prevent different per-agent allocations from changing a finite-training update.

P defines a scalar team reward in its open Dec-POMDP (P, line 263) and a vector shaped reward in its potential construction (P, lines 337-349). It does not specify how MAPPO routes that vector into advantages. This distinction gives a direct implementation audit. Let \(u_t=\sum_{i\in\mathcal N}\psi_{i,t}\), using zero coordinates for absent agents. Pooling over the fixed population gives

\[
\sum_{i\in\mathcal N}F_{i,t}=\gamma u_{t+1}-u_t.
\]

For every nonterminal state with a nonempty coalition, \(u_t=1\), independent of rank. Thus a common advantage built solely from fully pooled shaped rewards cannot carry P's pairwise ranking signal. Coalition changes do not alter this conclusion if the full population is pooled at both endpoints.

If instead the implementation pools only rewards for agents active at the start of a transition, then for nonterminal steps with nonempty coalitions,

\[
\sum_{i\in I^t}F_{i,t}
=\gamma\sum_{i\in I^t\cap I^{t+1}}\psi_{i,t+1}-1
=\gamma\left(1-\sum_{i\in I^{t+1}\setminus I^t}\psi_{i,t+1}\right)-1.
\]

Here rank can affect the pooled reward through entrants, but the missing credit on the preceding transition also prevents the fixed-coordinate PBRS telescoping identity. The actual reward routing in P's implementation remains unknown. Separate per-agent rewards and approximate critics give another possible channel; with a critic matched to the potential, temporal-difference and GAE residuals cancel exactly. A useful replication should record the actual pooled and per-agent reward tensors, the inactive-agent mask, and the critic targets at entry and exit.

## A rank-perfect predictor can increase gradient variance

Consider a one-step cooperative game with two active agents. Agent 2 is inert. Agent 1 takes \(a\in\{0,1\}\), with \(\pi_\theta(a=1)=1/2\) at the parameter of interest, and the team return is \(G=a\). Define coalition values \(v(\varnothing)=0\), \(v(\{1\})=v(\{1,2\})=1/2\), and \(v(\{2\})=0\). The true Shapley scores are \((1/2,0)\), so P's ideal softmax gives \(b=\psi_1=e^{1/2}/(e^{1/2}+1)>1/2\) when \(\rho=1\).

For raw REINFORCE with a pre-action baseline \(b\), let \(z=\nabla_\theta\log\pi_\theta(a)\) and \(g_b=z(G-b)\). At \(\pi_\theta(a=1)=1/2\), \(z=1/2\) for \(a=1\) and \(z=-1/2\) for \(a=0\). Hence

\[
g_b=\begin{cases}(1-b)/2,&a=1,\\b/2,&a=0,\end{cases}
\qquad
\mathbb E[g_b]=1/4,
\qquad
\operatorname{Var}(g_b)=(b/2-1/4)^2.
\]

The neutral baseline \(b=1/2\) has zero variance; the ideal Shapley-derived softmax has positive variance. This is a counterexample to using ordinal credit accuracy as a sufficient proxy for finite-sample gradient quality. It is not a prediction of MAPPO behavior. With an exact critic adjusted for the potential, the shaped temporal-difference residual equals the unshaped residual, so any observed MAPPO benefit needs an analysis of approximation, optimization, or credit routing.

For a frozen policy and pre-action history \(h\), the raw gradient's conditional second moment is minimized by

\[
b^*(h)=\frac{\mathbb E[\|z\|^2G\mid h]}{\mathbb E[\|z\|^2\mid h]},
\qquad
M_h(b)-M_h(b^*)=\mathbb E[\|z\|^2\mid h](b-b^*)^2.
\]

This suggests a task-aligned error for P's predictor: the weighted squared gap between \(\rho\psi_i\) and \(b_i^*\), evaluated alongside final success at a fixed training and inference budget. It does not establish that this error alone predicts MAPPO learning speed.

## Estimator and query cost

P's connected-graph premise does not ensure an unregularized Bradley-Terry MLE. With two agents, two comparisons, and true tie probability \(1/2\), both outcomes favor the same agent with probability \(1/2\). On either event the graph is connected but the likelihood supremum occurs at an infinite score difference. The reported probability \(1-n^{-2}=3/4\) for a finite estimation error cannot hold in this case. Finite MLE existence requires strong connectivity of the observed win graph, not just connectivity of the undirected query graph; see [Rinaldo, Petrović, and Fienberg, Section 6.3](https://stat.cmu.edu/~arinaldo/papers/Rinaldo_Petrovic_Fienberg.pdf).

P's stated every-ordered-pair protocol uses \(|I^t|(|I^t|-1)\) comparisons per queried step. A comparison budget, regularized estimator, and a query rule based on expected learning benefit per call form a concrete study. The reward and compute conversion needs an explicit price \(\kappa\), as Q emphasizes. Repeated calls cannot be assumed independent when a fixed LMM produces correlated or deterministic answers.

Prior work already proves [dynamic potential-shaping invariance](https://eprints.whiterose.ac.uk/id/eprint/75121/), shows that [potential shaping can increase policy-gradient variance](https://proceedings.neurips.cc/paper_files/paper/2023/file/a5357781c204d4412e44ed9cbcdb08d5-Paper-Conference.pdf), and identifies [query-policy misalignment in preference-based RL](https://proceedings.iclr.cc/paper_files/paper/2024/hash/c703e3320a0d0f1ed2e2b95964249c17-Abstract-Conference.html). A publication would need to go beyond those results by treating P's changing coalitions and pairwise LMM calls jointly, then showing a finite-training benefit under charged queries.
