# When a room prior changes a door graph

## Source-grounded question

Can a robot retain the search savings of a room-guided door detector while giving an explicit certificate
for each claimed room-to-door dependency and paying for additional observations only where the certificate
fails? This sharpens the initial question about whether Q and P combine. It asks for a theorem about the
interface between their methods, not a general theorem about semantic mapping.

Q gives a conditional error-propagation proposition: an edge transfers a smoothness bound only after its
metric, output sensitivity, and additive perturbation model are stated ([Q, lines 1083-1110](../inputs/Q.tex)).
Q also says that component guarantees alone do not compose across changed
instances and benchmarks ([Q, lines 1023-1082](../inputs/Q.tex)); prediction calls can be charged explicitly
([Q, lines 1242-1258](../inputs/Q.tex)). P supplies a concrete edge. A room model defines walls, and its
door detector first keeps LiDAR points satisfying \(\operatorname{dist}(p,W)\leq\delta\), with
\(\delta=0.15\,\mathrm m\). It then thresholds scan derivatives and candidate widths
([P, lines 352-391](../inputs/P.tex)). Doors are considered only after a room is accepted, and a provisional door
triggers an active visit ([P, lines 394-427](../inputs/P.tex)).

P reports topology correct in its simplified tests ([P, lines 527-562](../inputs/P.tex)), but also
identifies accepted false room models and later invalidation, with revision currently absent
([P, lines 259-261 and 613-632](../inputs/P.tex)). Its thresholds were tuned empirically for its setup
([P, lines 481-489](../inputs/P.tex)). These observations motivate a conditional formal result, not a claim that P
fails on its reported experiments.

## Gate-level statement

Fix the finite scan \(S\) presented to the first door gate and an estimated, nonempty closed wall set
\(\widehat W\). Let \(W^\star\) be the corresponding true wall set, under a fixed coordinate registration.
Define

\[
m_{\rm wall}=\min_{p\in S}\left|\operatorname{dist}(p,\widehat W)-\delta\right|.
\]

If \(d_H(W^\star,\widehat W)\leq\varepsilon\) and \(m_{\rm wall}>\varepsilon\), the first gate makes exactly
the same pass or fail decision for every \(p\in S\) using \(W^\star\) and \(\widehat W\). Indeed, for any
closed sets with finite Hausdorff distance,

\[
\left|\operatorname{dist}(p,W^\star)-\operatorname{dist}(p,\widehat W)\right|
\leq d_H(W^\star,\widehat W)\leq\varepsilon.
\]

Thus no signed threshold comparison can change when its estimated distance lies more than \(\varepsilon\)
from \(\delta\). The statement is conditional on a valid error bound and fixed observations. A covariance or
a Mahalanobis association threshold in P is not itself such a deterministic bound ([P, lines 459-480](../inputs/P.tex)).

The restriction is necessary for this gate. Consider one fixed observation \(p\) and parallel wall segments
\(W_t^-\) and \(W_t^+\) at distances \(\delta-t\) and \(\delta+t\) from \(p\), with common finite length and
\(t>0\). Their Hausdorff distance is \(2t\), while the binary first-gate outputs differ by one. As \(t\)
tends to zero, no finite global Lipschitz constant maps Hausdorff wall error to this binary gate output. If
a pivotal edge pair passes every other door test, the graph may differ by a door node and connectivity edge.
This counterexample alone does not establish that every P output changes or that every error-dependent
guarantee is impossible: Q explicitly permits discontinuous smoothness envelopes ([Q, lines 325-336](../inputs/Q.tex)).

For a *complete* detector certificate, each additional discrete decision needs its own bound. If the two
measured anchor points each move by at most \(\varepsilon_a\), their estimated width moves by at most
\(2\varepsilon_a\), so its distance to each width threshold must exceed \(2\varepsilon_a\). The derivative
peak gate needs an error bound for the derivative, not merely raw range noise. Candidate pairing and
landmark association need uniqueness gaps. P's condition that a candidate segment lie within a wall has no
numerical tolerance in the printed algorithm, so it cannot be certified from the stated model. Optimizer
stability after the graph structure is fixed needs a separate conditioning argument. No full graph theorem
follows from the first-gate lemma alone.

## Provenance of positive topology

P promotes a provisional door to a nominal door after a visit and then offers a cross action
([P, lines 416-427](../inputs/P.tex)). That door is an observed candidate, not yet a witnessed
connection. For a first-time destination room, LTSM waits for the crossing and the new room's
initialisation before storing the dual-coordinate connection ([P, lines 429-436 and
495-497](../inputs/P.tex)). A successful crossing witnesses a traversable physical passage at that
time, conditional on reliable action and transition sensing. Attaching names of two rooms still
requires correct room recognition and door association.

The crossing witness is not available for every edge P displays. Its loop-closure example connects
previously known rooms through an uncrossed door, using robot-pose projection as the robot
approaches ([P, lines 440-445](../inputs/P.tex)); the scene graph also has a door-to-door match
edge for loop closure ([P, line 187](../inputs/P.tex)). Such an edge needs its own association
certificate or must remain a hypothesis. Therefore a proposed graph should record door detection,
door-to-door matching, crossing, and endpoint-room identity as distinct evidence fields. A wall
margin addresses stability of the initial detection gate; it does not certify the later match or
crossing. The negative case still needs coverage evidence, since no crossing event can witness an
absent opening.

## Research design and failure test

An implementable extension would attach a wall error bound and margin to every room-derived door decision.
When a bound is unavailable or a margin is too small, the robot may request a new viewpoint, perform a
broader scan, or leave the edge unverified. A negative door claim also requires spatial coverage: an unseen
opening can have no residual to monitor. [Emmy's audit-only lower bound](../emmy/verification_cost.md)
formalizes this separate coverage cost. Its coupling proof is sound under independent, unit-cost audits, but
P's LiDAR may cover many regions in one view. The proposed output would distinguish a verified edge, a
verified absence within a covered wall interval, and an unresolved interval. The intended cost is travel and
sensing effort plus penalties for incorrect topology. Q's \(\kappa\) definition prices predictor calls, not
physical sensing, so a new objective is required before using consistency or robustness language.

Useful experiments would perturb room pose, dimensions, and LiDAR points independently around the
\(0.15\,\mathrm m\) gate; include occluded and nonrectangular rooms; and record structural edits, missed
doors, false doors, unresolved wall length, and observation cost. Compare P's fixed gate with
margin-triggered remeasurement and a broad-coverage baseline. A formal result needs explicit coverage,
error-bound calibration, and revision semantics for asynchronous graph updates. Otherwise the strongest
justified claim is the local gate theorem above.

Prior-work search used `site:arxiv.org scene graph construction uncertainty topology guarantees active
perception room door detection robustness`, `site:arxiv.org semantic SLAM scene graph topology stability
perturbation margin certificate`, and `site:arxiv.org topological map room door active exploration missed
doors uncertainty verification`. [Active Semantic Perception](https://arxiv.org/abs/2510.05430) and
[SCOUT](https://arxiv.org/abs/2606.06721) already use scene uncertainty to guide traversal. The proposed
contribution must therefore exceed uncertainty-guided revisit alone. These searches do not establish
novelty.
