# Peer scores under a shared observation error

## Question and scope

The useful joint question is narrower than whether peer scoring is robust to correlated noise: **which object is identified by repeated agreement, and which behavior is induced by payment?** Q supplies an incentive theorem for reports and actions. P supplies a statistical model that aggregates pairwise comparisons into a latent comparator score. Neither link alone certifies that the recovered or truthfully reported quantity equals a desired state or contribution.

Q's peer-discipline example assumes a known conditional distribution of co-player types for each reported type. Its separation condition is \(\beta_i[t_i]\ne\beta_i[\hat t_i]\); its quadratic score creates expected truthful-report advantage \(\Lambda\|\beta_i[t_i]-\beta_i[\hat t_i]\|_2^2\). The action result also uses utility cancellation and an off-support penalty, not the peer score alone (Q, lines 1647-1740, condition (S), reward (PR), and Proposition "Support-wise implementability of every feasible rule"). Q explicitly lets the designer know the type-dependent belief map (lines 1789-1794). These are mechanism assumptions, not estimates of how reports relate to the principal's objective.

P compares egocentric images with an LMM, fits a Bradley–Terry likelihood, and uses its scores as potentials (P, lines 281-349). Its convergence proposition targets a postulated stable LMM preference vector, while its Shapley proposition assumes that this vector equals true Shapley values and expressly avoids claiming practical Shapley recovery (P, lines 351-389). P's benchmark has separate dense per-agent rewards for analysis, so its reported pairwise accuracy is agreement with that benchmark proxy (P, lines 427-428, 550-551, 665-667, 1072-1074). The proxy is not established as a Shapley value.

There is a timing mismatch before either theorem can be transferred. Q's agents report their types before interim signals arrive (Q, lines 1542-1567); P's LMM compares current images after observation (P, lines 285-312). A peer mechanism for P's agent-supplied images or judgments requires a new post-observation reporting game and its own separation and deviation conditions. If agents cannot alter what the LMM sees, strategic reporting is absent from P's current pipeline, while calibration remains relevant.

## A separating counterexample

Let the desired binary state be \(T\sim\operatorname{Bernoulli}(1/2)\), let a task-level visual error be \(N\sim\operatorname{Bernoulli}(p)\), independent of \(T\), and let every peer observe \(X_i=T\oplus N\). The peers share one error realization per task. For every \(i\ne j\), \(\Pr(X_j=x\mid X_i=x)=1\), so Q's peer-type separation holds: the two conditional distributions are point masses at different reports, with squared distance \(2\). Truthful reporting is an equilibrium of Q's quadratic peer score in the trivial zero-utility, one-action instance.

Nevertheless, \(\Pr(X_1=\cdots=X_n=0)=\Pr(X_1=\cdots=X_n=1)=1/2\) for every \(p\in[0,1]\). Thus any number of peer reports, even over arbitrarily many tasks, has the same law when \(p=0\), \(p=1/2\), or \(p=1\). Those cases respectively make a truthful report correct, uninformative, or exactly reversed relative to \(T\). For a known \(0<p<1/2\), unlimited peers still leave task-level Bayes error \(p\): they all reveal the same \(X\). Q's result remains valid **within each fully specified model**, where the designer knows the belief map and can use its information about \(T\). The example blocks learning that map or certifying target accuracy from peer agreement alone.

The same model separates truthfulness from equilibrium selection. With two agents, Q's score reduces to \(q(r_i,r_j)=1\) for a match and \(-1\) otherwise. Both agents reporting \(X_i\) is a strict Bayesian equilibrium. Both reporting \(1-X_i\) is also a strict Bayesian equilibrium, since each agent then predicts the other's flipped report perfectly. The two report profiles have the same observable law when \(T\) is uniform. Q proves implementation by a truthful equilibrium under its assumptions; it does not assert that peer reports alone select or certify that equilibrium.

## Why more comparisons do not remove a shared error

For a contribution difference \(d\), suppose one visual scene induces a common comparator shift \(B\), and repeated LMM calls satisfy \(Y_k\mid B\sim\operatorname{Bernoulli}(\sigma(d+B))\). Even if calls are conditionally independent, the two-item Bradley–Terry fit obeys \(\hat d_K=\operatorname{logit}(K^{-1}\sum_k Y_k)\to d+B\), not \(d\). Larger \(K\) learns the scene-conditioned preference more precisely. Without a restriction fixing the location of \(B\), the transformations \(d'=d+a\) and \(B'=B-a\) yield the same observations. Position-swapped queries can address position bias but need not remove a common scene shift. P's own observations that comparison errors cluster when all cameras lack useful visual cues motivate checking this dependence (P, lines 550-551 and 1074).

There is also a finite-sample issue in P's printed guarantee. The method defines an unregularized MLE (P, lines 326-329), although the proof sketch invokes regularized-MLE analysis (P, lines 367-374). For two compared agents, if all \(K\) observations favor one agent, the graph is connected but the likelihood \(\sigma(d)^K\) has no finite maximizer. Connectivity alone therefore does not imply that the stated estimator or error bound exists. A repeated common judgment can create this case. Regularization, a compact score range, or a suitable bidirectional-win condition repairs existence; target calibration remains a separate requirement.

## A minimal repair and its limits

Suppose an independently generated anchor label \(A=T\oplus E\) is observed on random audited tasks, where \(E\sim\operatorname{Bernoulli}(q)\), \(q<1/2\), is independent of \((T,N)\), and its error rate is known. Under truthful reporting,

\[
\Pr(A=X)= (1-p)(1-q)+pq = 1-q-p(1-2q),
\qquad
p=\frac{1-q-\Pr(A=X)}{1-2q}.
\]

Thus audited tasks identify the report-to-target error rate \(p\), and an assumption \(p<1/2\) or an anchor orients the meaning of the binary labels. They still do not reveal an unaudited task's individual error realization \(N\). Alternatively, \(m\) independent observation groups with independent errors of known rate \(p<1/2\) permit majority recovery of \(T\), with error at most \(\exp[-2m(1/2-p)^2]\); duplicating peers inside one group does not change \(m\).

An anchor can also address the separate strategic problem if it enters the *actual* payment. Assume \(p<1/2\), known or bounded above from independent calibration, and positive coefficients \(\lambda,w\). Let a report earn the peer score with coefficient \(\lambda\), and on an independently selected audit with probability \(\alpha\), a matching-anchor bonus with coefficient \(w\). For either observed \(X_i=x\), truthful reporting has expected audit advantage \(\alpha w(1-2p)(1-2q)\) over flipping. The peer-score disadvantage from truth versus any peer strategy is at most \(2\lambda\). Hence \(\alpha w(1-2p)(1-2q)>2\lambda\) makes reporting \(X_i\) a strict best response regardless of peer strategy in this binary zero-utility game. This is an illustrative sufficient condition, not a result for Q's full model: nonzero utility and action deviations require additional bounds and an obedience instrument. An anchor used only for evaluation identifies a statistical link but supplies no reporting incentive.

P's potential reward cannot simply replace that reporting payment. For a fixed initial state and terminal potential \(0\), its per-agent shaped return telescopes:

\[
\sum_{t=0}^{H-1}\gamma^t\bigl(\gamma\psi_i(s_{t+1},t+1)-\psi_i(s_t,t)\bigr)=-\psi_i(s_0,0).
\]

Under those conditions it changes learning feedback but not the exact payoff ranking over policies. This agrees with P's statement that potential shaping preserves equilibria (P, lines 331-349), and with the prior [policy-invariance theorem](https://arxiv.org/abs/1401.3907). A Q-style reporting or obedience guarantee needs a payment or verification rule with a nonconstant total payoff effect. Whether the initial potential depends on a strategic report or whether a dynamic learning rule violates the telescoping assumptions must be modeled separately.

## Research assessment

A defensible project is an **audit and dependence-aware certificate for peer-derived contribution scores**: distinguish independent view groups from repeated calls to one scene, estimate the remaining target error against a defined contribution proxy, and state a separate equilibrium condition for reports and actions. The toy counterexample and audit calculation are elementary, so a publication would need a general theorem or a compelling evaluation on P's dynamic-team setting. P already supplies dense analytic rewards for a test bed. The test should stratify scenes by shared visual failure, vary independent camera diversity versus repeated queries, and report both comparator calibration and strategic vulnerability. This proposal does not claim that its benchmark proxy equals Shapley contribution.

Prior work already treats [measurement integrity in peer prediction](https://arxiv.org/abs/2108.05521), [conditional independence in peer elicitation games](https://arxiv.org/abs/2505.13636), and [random effects in Bradley–Terry comparisons](https://doi.org/10.1111/rssa.12959). Those results limit any novelty claim for the general warning. The potentially new part lies in a unified certificate and its empirical test for open-team multimodal credit assignment, if such a certificate can be proved and validated. The precise target definition, availability and quality of independent anchors, and an implementable action-incentive layer remain unresolved.
