# Verification cost for concept-first room graphs

## Pair-specific question

Can a robot use a predicted room and door graph to save sensing work while still certifying the room
connectivity it reports? This sharpens the broad question of whether Q's learning-augmented
guarantees transfer to P's architecture. The target is topological correctness and the price of
observations, rather than geometric pose error alone.

Q explicitly notes that actions can censor the target needed to measure prediction error (Q, lines
973-980), that downstream error transfer needs a proved metric and sensitivity bound (Q, lines
1095-1105), and that predictor calls can be included in an objective (Q, lines 1242-1258).
Physical sensing has a separate cost here. P supplies a concrete loop: room instantiation triggers a visit toward the
estimated centre and validation from accumulated views (P, lines 341-350); the door agent runs only
after a current room appears and filters points by distance to the room-derived walls (P, lines
352-380, 416-427). P reports that partial occlusion can let an incorrect room be accepted and that
later unseen features can invalidate it; revision is proposed, not implemented (P, lines 613-633).

## An information lower bound

Consider a deliberately simple sensing abstraction. There are \(n\) independently
inspectable wall regions. The true connectivity state is a bit vector \(x\in\{0,1\}^n\), where
\(x_j=1\) means a doorway exists in region \(j\). Initial observations and a
prediction \(\hat x\) are identical across the states considered. An audit of region
\(j\) costs one unit and reveals \(x_j\) without error; no other action reveals
it. The output must equal \(x\). This models occluded candidate regions after the passive
views are exhausted, not P's complete sensor physics. It requires that each region can eventually be
inspected; permanent occlusion makes certification impossible.

**Claim.** If a possibly randomized algorithm outputs the exact topology with probability at least
\(1-\delta\) for every \(x\) and every \(\hat x\), where \(\delta<1/2\), then on
the no-door state \(x=0^n\) it audits at least \(n(1-2\delta)\) distinct regions in
expectation. At \(\delta=0\), it audits all \(n\), even when \(\hat x=0^n\) is exact.

**Proof.** Couple runs on \(0^n\) and on \(e_j\), with the same prediction, internal
random coins, and all observations until region \(j\) is audited. Let \(E_j\) be
the event that the run on \(0^n\) never audits \(j\), and let \(C_0\) be
the event that its output is correct. On \(E_j\cap C_0\), the coupled run on \(e_j\) sees
the same transcript and outputs \(0^n\), so it is wrong. Thus \(\Pr(E_j\cap C_0)\leq\delta\) and
\(\Pr(E_j)\leq\Pr(C_0^c)+\delta\leq2\delta\). Summing \(\Pr(E_j^c)\) over regions yields the bound. The argument makes no
assumption about the quality of \(\hat x\).

The claim is a verification cost, not a competitive-ratio theorem. Q assumes a positive offline
optimum when defining a multiplicative ratio (Q, lines 257-265); the no-door instance may have zero
offline sensing cost. An additive cost or a benchmark that also requires certification is
appropriate. It also does not say that P currently incurs \(n\) physical visits: a wide
LiDAR view can inspect several regions at once. With actions that certify subsets of regions, the
analogous covering problem depends on their reachable views and travel costs.

## Research path

The useful interface would tag each graph edge or absent edge with its evidence provenance and the
wall region actually observed. A room-to-door geometric margin, as in ada's ledger finding #4, can
certify that a *measured* point stays on the same side of P's wall-distance gate under a bounded
wall perturbation. It cannot certify an occluded region. An active auditor would use cheap passive
coverage first, then visit only uncertified regions or retain their topology as unknown. A revised
room hypothesis must invalidate descendant door certificates whose wall or pose assumptions changed.

Positive and negative topology have different witnesses. P promotes a detected door to nominal status
after a visit, before crossing (P, lines 416-427). Its long-term memory records a room connection as the
robot crosses and initialises the destination room (P, lines 429-436). Successful crossing witnesses a
traversable physical passage, subject to valid transition sensing; the claim that two *named rooms* are
connected also needs correct room identity and association. P's acknowledged false room acceptance
(P, lines 613-619) leaves that claim conditional. A nominal door awaiting crossing should be a candidate,
not a certified connection. For an absent door there is no corresponding action witness: certification
requires coverage and a sensor model that distinguishes an opening from an intact wall. The audit bound
above says how expensive this can be in its independent-region abstraction.

The publishable result would need a realistic observation model and a nontrivial cost bound, such as
an approximation to minimum travel-weighted views needed to certify all currently reachable door
regions, plus an explicit error/coverage tradeoff when certification is deferred. On P's four-room
and ten-room scenarios (P, lines 481-526), inject occlusions and false early room fits; compare
graph-edit errors, missed doors, travel, inference cost, and revision latency against P's current
validation, a fitness-monitoring variant, and a broad-coverage baseline. The current note proves only the abstraction above. Whether a
useful certificate is computable from P's LiDAR and whether its extra exploration cost is acceptable
remain unresolved.

## Nearby work checked

[Active Semantic Perception](https://arxiv.org/abs/2510.05430) samples scene graphs for unobserved regions and chooses waypoints by information
gain. [SCOUT](https://arxiv.org/abs/2606.06721) couples uncertainty-aware scene graphs to semantic coverage. These are
adjacent active perception approaches; their abstracts do not establish the particular all-topology
verification guarantee above. Search queries: `site:arxiv.org active semantic exploration scene graph prediction verification occlusion topological completeness`, `site:arxiv.org robot exploration learned predictions competitive ratio verification hidden doors`, and `site:arxiv.org "robot exploration" "predictions" "competitive"`.
This is a bounded search, not a novelty claim.

Ada also located [Estimating Map Completeness in Robot Exploration](https://arxiv.org/abs/2406.13482), which learns a stopping estimate from partial grid maps, and
[Landmark-based Distributed Topological Mapping and Navigation](https://arxiv.org/abs/2103.03741), which uses designed landmark coverage conditions for topological exploration. I
checked their abstracts. The proposed door certificate would need to distinguish its assumptions and
result from both.
