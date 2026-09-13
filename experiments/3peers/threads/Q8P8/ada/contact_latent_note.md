# From rigid linkage to latent compliant contact

## Changed question

The original hardware-port question is too generic. The sharper question is:

> Does DynaMAC's zero-shot static-to-dynamic transfer fail when causal coupling is mediated by underactuated compliant contact, because low relative-pose variance no longer identifies endogeneity? Can a contact-belief stream restore transfer while retaining five-demonstration learning?

## Mechanism

P treats a frame (f) as linked when

\[
M_t^{(f)} = \left|\det\left(\boldsymbol{\Lambda}_t^{(f)}\right)\right|^{-1/(2d)} < \tau_M.
\]

Its motivating grasp is rigid: after grasping, the mug pose is dictated by the end effector, its conditional spatial variance approaches zero, and the endogenous mug stream is masked (P, *Manipulation in Dynamic Environments*, especially the causal-assumption and kinematic-link-analysis paragraphs). P then represents bimanual influence with streams such as (p(\hat p_{\mathrm{right}}\mid\hat p_{\mathrm{left}})), using the opposite end-effector pose as a candidate frame (P, *Bimanual Manipulation as Multi-Agent Cooperation*).

Q supplies a direct counter-regime. Aero Hand has (16) joints, (7) motors, and only (7) motor encoders. One cable drives three finger joints, and "which joint moves at any instant is set by the mechanics rather than commanded directly." Silicone pads provide compliant contact (Q, *Design overview* and *Kinematics and transmission*).

Let (w_t\in SE(3)) be wrist pose, (f_t\in SE(3)) object pose, and (z_t) an unobserved contact mode containing passive joint configuration, contact locations, stick or slip state, and deformation. A compliant grasp has the form

\[
f_t = w_t\,h(z_t), \qquad z_{t+1}\sim p(z_{t+1}\mid z_t,a_t,\xi_t).
\]

The intervention (\operatorname{do}(w_t)) can change (f_t), so the object is endogenous, while

\[
H(f_t\mid w_t)>0
\]

because (z_t) varies. Causal endogeneity therefore does not imply the near-zero conditional variance used by P. In-hand reorientation is the extreme counterexample: the wrist can remain fixed while the hand deliberately changes (f_t). The seven encoder readings need not fix (z_t), since tendon length does not uniquely specify the passive joint and contact configuration under obstruction.

## Decisive study

Use Q's tendon-level MuJoCo model first, with two hands mounted on simulated arms, on a segmented handover or joint-carry task that requires regrasping or allows controlled microslip. Train only on static demonstrations, as in P. Sweep return-spring stiffness, fingertip and joint friction, object seating or geometry, grasp type, and imposed arm perturbation. These interventions vary contact-mode aliasing while preserving the arm-level task and policy data. Pad compliance and cable slack would require additional system identification before they could be treated as validated physical sweep axes.

Measure:

1. Original DynaMAC success under zero-shot perturbations.
2. Link-detector false negatives against a simulator interventional-influence oracle, rather than raw binary contact. For example, under matched latent state and low-level commands, estimate

\[
I_{w\to f}(t)=\frac{\mathbb{E}_{\delta w}\!\left[d\!\left(f_{t+\Delta}^{\operatorname{do}(w+\delta w)},f_{t+\Delta}\right)^2\right]}{\mathbb{E}_{\delta w}\!\left[\lVert\delta w\rVert^2\right]}.
\]

Then test whether \(M_t^{(f)}\) classifies high \(I_{w\to f}(t)\). The intervention horizon and feedback policy must be fixed because they change the measured influence.
Estimate dispersion from phase-matched relative transforms \(w_t^{-1}f_t\), with segmentation and demonstrations held fixed. P computes \(M_t^{(f)}\) from phase-indexed demonstration covariance, so pooling different phases would introduce variation unrelated to contact-mode aliasing.
3. The relationship among (M_t^{(f)}), compliance, and task success.
4. Demonstration count needed to recover a fixed success target.

Compare original wrist-pose streams with an oracle contact-mode stream and a realizable belief stream inferred from histories of wrist pose, object pose, motor encoders, and commands. A current-motor-state baseline is important but should not be presumed sufficient. Vision-only object pose is already consistent with P's external perception assumption. Hardware validation can then use Q's identified actuation map and the same seven available encoder channels.

The strongest result need not be a new policy. A systematic divergence between true causal coupling and P's variance detector, plus recovery by an oracle contact variable, establishes the representation failure. Recovery by the history-based belief makes the contribution constructive. If that belief requires dynamic demonstrations, however, it repairs robustness but does not retain P's zero-shot static-to-dynamic claim.

## Controls and failure conditions

- Include rigid parallel grippers and an artificially rigid Aero grasp. Otherwise failures may be ordinary integration errors.
- Match arm trajectories, perception, demonstrations, and policy class across the compliance sweep.
- Separate frame-selection failure from low-level grasp failure by replaying identical high-level references with an oracle link mask.
- Compare original frame selection, forced wrist-only conditioning, forced retention of the tracked-object stream, and substitution of the oracle causal mask. Detector error should precede and predict policy error; oracle-mask rescue is the key identification test because another retained stream may otherwise hide the defect.
- Test tasks with and without in-hand motion. A result limited to deliberate reorientation should not be generalized to every compliant grasp.
- If original DynaMAC remains strong and its detector still separates links over the full sweep, this pair offers mainly a robustness validation, with limited novelty.

## Feasibility boundary

Q releases a stationary unimanual RL environment, not bimanual arms, demonstrations, cameras, or an RLBench adapter. P uses dense (6)-DoF arm trajectories learned from five demonstrations. A full physical port is therefore substantial work. The publishable unit should begin as a controlled simulator study of the causal criterion, followed by a narrow physical handover, rather than a broad DynaBench replacement.
