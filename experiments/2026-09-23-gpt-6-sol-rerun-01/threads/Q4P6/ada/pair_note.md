# Rank shaping, strategic incentives, and open teams

## Claim and scope

The abstract-level claim that Q certifies strategic robustness of P is unsupported.
Q's multi-agent incentive compatibility condition compares truthful, obedient play
against a feasible false report followed by an arbitrary action deviation
(Q, lines 1568-1618). P instead obtains pairwise judgments from an external LMM
applied to agents' egocentric images, fits Bradley--Terry scores for active agents,
and uses those scores as a potential in training (P, lines 285-349).
P's convergence proposition assumes a connected comparison graph and a stable
Bradley--Terry latent preference (P, lines 356-379). It addresses statistical
error relative to that latent preference, not strategic manipulation of the inputs
or the latent preference itself.

The sharpened question is: **When do rank-derived potentials preserve incentives across entry and exit, and what deviations become possible if reward delivery omits inactive transitions?** Q supplies the right notion of deviation and actual reward mechanisms. P supplies the active-set comparisons and an open-team benchmark with battery-driven removal and respawn (P, lines 263, 397, 427).

## Pathwise calculation

For a fixed agent, suppose P's displayed formula is applied on every transition, including those on which the agent is inactive. Let \(\psi_t^i\) denote the *same cached potential* when it appears in adjacent rewards. Then

\[
\sum_{t=0}^{T-1}\gamma^t\left(\gamma\psi_{t+1}^i-\psi_t^i\right)
=-\psi_0^i+\gamma^T\psi_T^i=-\psi_0^i,
\]

since P defines terminal potential as zero (P, lines 331-349). If \(\psi_0^i\) is fixed before the agent can deviate, this is an action-independent offset. An agent's choice to improve its camera view or rank can change intermediate shaping rewards but not its exact discounted episode payoff. Therefore, this potential cannot itself implement Q's truthful-reporting or obedience constraints. This is a statement about fully evaluated returns; P's observed faster learning can still arise from altered feedback to a finite training algorithm.

For possible selective reward delivery, let \(m_t^i\in\{0,1\}\) indicate whether the agent is credited with shaping on transition \(t\). Expanding the sum gives

\[
\sum_{t=0}^{T-1}\gamma^t m_t^i
\left(\gamma\psi_{t+1}^i-\psi_t^i\right)
=-m_0^i\psi_0^i
+\sum_{t=1}^{T-1}\gamma^t(m_{t-1}^i-m_t^i)\psi_t^i
+\gamma^T m_{T-1}^i\psi_T^i.
\]

The middle term is zero for continuous reward delivery and otherwise depends on active-set boundaries. This is a conditional implementation risk, not a finding that P actually skips rewards: P states that comparisons are limited to active agents and skipped with fewer than two active agents (P, lines 285-305), but its text does not specify a fixed-agent potential extension, reward delivery during inactivity, or caching of repeated stochastic LMM evaluations. The paper's mathematical formula alone supports the first calculation if those conventions are supplied. Softmax over a score vector whose dimension is \(|I^t|\) needs a per-agent extension at participation changes.

A boundary witness consistent with the natural extension \(\psi_t^i=0\) while inactive is an entry at \(t=1\) in a two-transition episode: set \(m_0^i=0\), \(m_1^i=1\), \(\psi_0^i=\psi_2^i=0\), and \(\psi_1^i=q>0\). The entering transition would contribute \(\gamma q\), but is masked; the active transition contributes \(-q\). Discounted shaping is therefore \(-\gamma q\). This illustrates that a higher entry rank can lower, rather than raise, exact shaped return under this convention. Whether the agent can control entry rank independently of useful task work is unknown. The formula, rather than a generic claim that rank inflation is always profitable, is the testable prediction.

## Distinctive research test

Implement P's rank potential with two explicit conventions: (A) a fixed-dimension, cached potential for every agent and every transition, with terminal zero; (B) shaping only on active transitions, matching a plausible but unconfirmed implementation. Introduce a strategic deviation opportunity in MARS-Bench: an agent can choose a camera-facing or battery-expending action that changes its LMM ranking or active status while sacrificing task progress. Measure (i) discounted per-agent return after a complete episode, (ii) observed rank and shaping reward, (iii) task success, and (iv) learned behavior with a finite training budget. The exact-return prediction is zero incentive effect in A, conditional on fixed initial potential, while B can show boundary incentives. A control with direct rank payout or Q-style report-contingent scoring should alter exact-return incentives, making the mechanism distinction observable.

Q's peer-scoring result does not transfer for free. It needs distinct beliefs over co-player types, scored co-player reports, utility cancellation, and sufficiently large or unbounded rewards (Q, lines 1645-1735). P establishes none of these. If strategic elicitation is the objective, one must specify an actual non-potential transfer and verify Q's separation and double-deviation inequalities in the embodied setting.

## Limitations

This note proves only a conditional arithmetic result and identifies an implementation ambiguity. It does not establish a bug in P's code, a profitable physical manipulation in MARS-Bench, or novelty against outside literature. A publication case would require implementation inspection, a concrete deviation that changes boundary payoffs or finite-training behavior, and a comparison with a mechanism satisfying a stated incentive constraint.
