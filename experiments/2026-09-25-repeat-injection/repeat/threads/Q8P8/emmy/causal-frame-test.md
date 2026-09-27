# Causal frame selection at changing hand contacts

## Question

Can action-conditioned evidence distinguish an object that the hand moves from an independently moving object when their relative pose is not rigid? This sharpens the pair question to a testable limit of P's frame gate on Q's dexterous hand. It does not assume that either method can be transferred to the other's action space as written.

## What the papers establish

- P, [Multi-Stream Policy Learning](../inputs/P.tex) (lines 412-489), defines object-frame Gaussian streams for absolute end-effector poses and fuses them by a product of experts. In "Manipulation in Dynamic Environments" (lines 490-672), it treats a low spread in the end-effector pose relative to an object as evidence of a kinematic link and removes that object's frame. Its geometric mean standard deviation is \(M_t^{(f)}=|\det(\Lambda_t^{(f)})|^{-1/(2d)}\), with \(d=6\).
- Q, [Hand Design](../inputs/Q.tex) (lines 205-330) and "Learning In-Hand Cube Rotation" (lines 642-798), supplies a tendon-driven hand with seven motor channels, changing finger contacts, and sustained rotation of a grasped cube. Q's simulator exposes the cube pose and supports command changes. Its deployed policy observes only the seven encoder-derived channels and its previous action. The hardware experiment did not log cube pose.
- Q, "The joint-to-actuation model" (lines 392-486), gives a rank-seven map from sixteen joint angles to seven motor-side variables. Motor readings therefore do not uniquely specify all joint angles or the contact state.

## The identification problem

P's precision is a spread at a given skill or trajectory phase, not the rate at which the relative pose changes during a rollout. For a repeatable object-relative rotation, let \(T_{HO}(t)=T_0R_z(\omega t)\). If local pose error at each phase has covariance \(\Sigma_t=\epsilon^2I_6\), then \(\Lambda_t=\epsilon^{-2}I_6\) and \(M_t=\epsilon\). For any \(\epsilon<\tau_M\), the gate reports a link even though \(T_{HO}(t)\) changes with time. This construction shows that low spread does not prove a rigid grasp. It does not by itself show a control failure: an endogenous object frame might still be correctly excluded from P's product of experts.

The converse is relevant to Q. During variable-speed rotation, slip, or finger gaiting, a cube may be action-caused while its relative pose varies across demonstrations at the same phase. The resulting spread can exceed \(\tau_M\), leaving an endogenous frame active. Whether this happens under P's fitted Gaussian streams is an empirical question.

There is also a partial-constraint problem even if the rotation varies widely.
For diagonal local pose covariance with five standard deviations
\(\epsilon\) and one free yaw standard deviation \(s\), P's scalar becomes
\(M=(\epsilon^5s)^{1/6}\). Small spread in the five constrained
directions can force \(M<\tau_M\) for any finite \(s\), so a single low
determinant does not imply all six pose coordinates are rigidly linked.
Q's cube rotation is a natural case to test: the cube can remain retained
spatially while yawing relative to the palm. P's whole-frame mask would
remove the cube pose from end-effector expert fusion. This does not imply
that an object-yaw feedback controller should lose the measurement.
It is a mathematical possibility, not a measured control failure.
P's suggested fixed diagonal weighting cannot recover the missing
directional information: for nonsingular \(W\),
\(\det(W\Lambda W)=\det(W)^2\det(\Lambda)\), which only rescales \(M\).

More generally, observations alone cannot identify the direction of coupling. The same joint law of end-effector pose \(E\) and object pose \(F\) admits both \(p(F)p(E\mid F)\) and \(p(E)p(F\mid E)\). A robot tracking an externally moved object and a robot driving a grasped object can therefore present the same observational covariance. This is a standard causal-identification issue, not a new theorem. A controlled motor intervention separates the cases if the object response is observable.

## Smallest decisive experiment

1. In Q's released simulator, collect matched short rollouts with fixed initial hand and cube state. Apply randomized small perturbations to one of the seven motor targets, keeping external object forcing fixed. Record the cube pose, motor commands, motor readings, and contact events. Repeat for free motion, rigidly held objects, controlled rotation, and slip or regrasp.
2. Fit P's phase-conditioned pose streams and report its \(M_t^{(f)}\) classification against an interventional label. Define the label by whether changing the motor command changes the cube's future pose under matched exogenous conditions. Evaluate false positives and false negatives by contact regime, not only overall accuracy.
3. Compare P's precision gate with an action-response score, for example the norm of the change in the cube's future pose under paired motor perturbations. Use the same thresholds selected on separate rollouts. A useful result would show improved classification in nonrigid contact while preserving P's detection of exogenous moving objects.

For the partial-constraint question, also report the six covariance
eigenvalues. A control comparison needs separate roles for object pose:
an exogenous task frame for P's end-effector expert fusion, or an
endogenous feedback state for a tendon-command controller. An
orientation-target or external yaw-perturbation task could compare
whole-frame masking, a direction-sensitive gate, and a controller using
cube yaw as feedback. The tendon-command adapter, pose tracking, and
matched policy architecture would have to be built for that test.

The physical extension needs external cube tracking, such as P's visual pose input. Q reports no physical cube-pose log. Also, Q validates motor/cable behavior much more directly than contact-conditioned cube dynamics: its thumb has the largest model mismatch ("Kinematic validation" and "Dynamic validation", lines 584-641). Simulation classification alone would not establish real-world gains.

## Scope and prior-work caution

This experiment diagnoses P's causal reading; it is not yet a complete seven-motor manipulation policy. A control result would need an explicit mapping from object-frame goals or feedback to Q's cable commands and a comparison with matched policy architectures. Generic visual in-hand pose feedback is already studied, for example [Visual Dexterity](https://arxiv.org/abs/2211.11744) and [Learning Haptic-based Object Pose Estimation for In-hand Manipulation Control with Underactuated Robotic Hands](https://arxiv.org/abs/2207.02843). The possible contribution is the tested causal-frame criterion under underactuated, changing contact, not adding vision by itself.

Covariance eigenspaces and subspace models for task-parameterized robot
skills are established in [Calinon's tutorial][subspace], Section 4.
Inspecting eigenvalues alone is not a stand-alone novelty claim. The
pair-specific question is whether P's binary dynamic frame mask
misclassifies Q's changing contact and whether an action-response
estimate assigns cube yaw to an appropriate feedback role in a matched
tendon-action controller.

[subspace]: https://calinon.ch/papers/Calinon-JIST2015.pdf
