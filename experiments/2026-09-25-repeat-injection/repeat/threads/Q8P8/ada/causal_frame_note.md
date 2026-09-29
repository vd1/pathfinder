# When a precise frame does not identify who moves whom

## Question and source passages

The question has changed from whether P can be transferred directly to Q's hand to whether P's precision rule identifies the direction of hand-object influence. P models absolute end-effector poses and sets gripper actions aside (`inputs/P.tex:412-418`). It interprets a frame-conditioned pose density as an interventional distribution (`inputs/P.tex:535-543`), then masks an object frame when its local stream spread falls below a threshold (`inputs/P.tex:597-612`, `inputs/P.tex:660-668`). Q supplies a contrasting contact regime: a seven-motor, sixteen-joint hand with only motor-encoder sensing (`inputs/Q.tex:226-230`, `inputs/Q.tex:282`) that rotates a cube continuously while holding it (`inputs/Q.tex:642-649`, `inputs/Q.tex:757-784`). Its CAD and identified actuation map connect joint motion, tendon lengths, and motor commands (`inputs/Q.tex:379-489`).

## Exact ambiguity in the observational criterion

Consider one scalar coordinate of end-effector pose \(E\) and object pose \(F\) at a fixed skill phase. Let \(0<\varepsilon<1\). The following two structural models differ in causal direction:

\[
\begin{aligned}
\text{external object: }&F\sim\mathcal N(0,1),\quad E=(1-\varepsilon)F+\eta_E,\\
\text{robot-driven object: }&E\sim\mathcal N(0,1),\quad F=(1-\varepsilon)E+\eta_F,
\end{aligned}
\]

where either independent noise has variance \(2\varepsilon-\varepsilon^2\). Both models generate the same joint Gaussian: \(\operatorname{Var}(E)=\operatorname{Var}(F)=1\) and \(\operatorname{Cov}(E,F)=1-\varepsilon\). In particular, \(\operatorname{Var}(E-F)=2\varepsilon\) in both. Repeating this construction over six independent local pose coordinates makes P's geometric mean standard deviation \(M=\sqrt{2\varepsilon}\) in both models. It can be arbitrarily small even though only the second model has robot-to-object influence.

The difference appears under intervention. In the first model \(\mathbb E[F\mid\operatorname{do}(E=e)]=0\); in the second it equals \((1-\varepsilon)e\). Thus no threshold on the observational stream covariance alone can distinguish a tightly tracking robot from a tightly carried object. This is an identifiability result about the criterion, not a measured failure of DynaMAC.

## Contact-rich extension and test

Q's cube can rotate relative to a stationary palm while remaining under finger influence. This does not by itself defeat P's rule: if demonstrations align closely at each phase, their stream covariance may still be small. Variable rotation phase, speed, or contact mode can make the covariance large even while the hand causes the cube's motion. The corresponding false-negative rate needs measurement. P's brief pre-grasp false positives (`inputs/P.tex:615-624`) do not address sustained tracking or variable-phase in-hand motion.

A controlled test would compare P's mask with an action-response estimate. At selected phases, apply small independent perturbations \(\delta a_t\) to Q's seven motor targets through its identified actuation map, record the actual encoder response and externally observed cube pose, and estimate a short-horizon sensitivity \(B(\tau)=\partial\mathbb E[\Delta x_{F,t+\tau}\mid\operatorname{do}(a_t)]/\partial a_t\). The baseline should include (1) an exogenously moved object that the robot tracks without contact, (2) a rigid held object, (3) varied in-hand rotation, and (4) an object driven by an external agent while touched by the hand. Independent randomization and matched initial states distinguish the motor perturbation's effect from spontaneous object motion. A nonzero response supports robot-to-object influence, though a zero response on one channel does not prove exogeneity because that motor direction may be ineffective at the current contact.

The decisive measurements are precision-rule link classification, intervention-rule classification, object motion after masking, and task success. Q's released simulator can provide contact and cube-pose ground truth for the first experiment. A hardware test needs an external object tracker: Q states that its deployment does not log cube pose (`inputs/Q.tex:781-784`), while P's simulation evaluation uses ground-truth object poses and its physical experiments use RGB-D task-parameter estimates (`inputs/P.tex:864`, `inputs/P.tex:1048-1055`). Q's encoder-only policy is therefore not a direct implementation of P, and P's end-effector pose action streams would need an explicit extension to tendon commands for a full combined controller.

## What would make this publishable

The pair supports a falsifiable methods paper if the observational mask produces sustained false positives or false negatives in these controlled cases, and a direction-sensitive replacement improves object-frame selection or manipulation success under the same demonstrations and sensing budget. The Gaussian counterexample establishes a limitation of the statistic, while the empirical comparison must establish that it matters in practice. I have not shown that the current DynaMAC implementation fails on Aero Hand Open.

Related prior work includes active tactile inference of grasped-object dynamics ([Sundaralingam and Hermans, 2020](https://arxiv.org/abs/2003.13165)) and pose tracking through contact feedback and simulation ([Liang et al., 2020](https://arxiv.org/abs/2002.12160)). These make contact inference an established topic; the proposed contribution would need to be specific to causal frame selection in dynamic multi-stream policies. Search queries used: `robot manipulation causal contact inference action interventions object motion affordance grasp moving within hand`; `site:arxiv.org robot manipulation distinguish object follows robot robot follows object intervention causal influence contact`; `site:arxiv.org causal contact graph robot manipulation action perturbation object pose kinematic link`.

## Anisotropic contact and the limits of a scalar gate

Emmy identified a second, independent diagnostic. Suppose the local pose covariance at one skill phase has five tightly constrained directions and one variable yaw direction:

\[
\Sigma=\operatorname{diag}(\epsilon^2,\epsilon^2,\epsilon^2,\epsilon^2,\epsilon^2,s^2),
\qquad M=(\det\Sigma)^{1/12}=(\epsilon^5s)^{1/6}.
\]

For example, \(\epsilon=10^{-4}\) and \(s=10^{-1}\) yield \(M\approx 3.16\times10^{-4}\), below P's reported threshold \(\tau_M=10^{-3}\) (`inputs/P.tex:597-612`), despite substantial spread in yaw. This is a constructed local-coordinate example, not a measurement of Q's cube rotation. It proves that the scalar threshold cannot certify precision in every direction. The example assumes a positive definite covariance and that the five small eigenvalues are not raised by regularization.

P suggests a diagonal weight matrix \(W\) for finer control (`inputs/P.tex:611`). If \(W\) is fixed and nonsingular, however,

\[
\det(W\Lambda W)=\det(W)^2\det\Lambda,
\qquad M_W=|\det W|^{-1/6}M.
\]

Thus weighting the determinant changes its scale but does not reveal which direction has high spread. A direction-specific test must inspect eigenvalues or specified task coordinates before masking. Whether P's fitted covariances actually have this pattern is open.

Covariance eigenspaces and subspace models for task-parameterized robot movement already appear in
[Calinon's tutorial, Section 4](https://calinon.ch/papers/Calinon-JIST2015.pdf).
The generic use of eigenvalues is therefore not a novelty claim. The open pair-specific question is whether
P's binary dynamic frame gate makes consequential errors at Q's changing hand contacts.

## Frame reference versus object-state feedback

P's streams generate absolute end-effector pose targets from object frames and omit gripper actions (`inputs/P.tex:412-480`). Q's fixed-base hand rotates the cube through seven tendon targets (`inputs/Q.tex:644-669`). Retaining cube yaw in P's pose-frame fusion would not by itself create finger commands. An object yaw can be endogenous under motor intervention and still be useful as feedback for orientation targeting or disturbance recovery. A causal frame gate and a state-feedback controller therefore answer different questions.

A stronger follow-up would build a tendon-command controller with the same externally tracked cube pose in every condition. Test targeted yaw and recovery after a controlled yaw disturbance. Compare P's whole-frame precision mask, a direction-sensitive frame mask, and a controller that models cube yaw as feedback state rather than as an exogenous reference. Report frame decisions, yaw error, retention, and perturbation response. This requires a new action model and physical cube tracking; Q's published encoder-only policy does not supply either. The available papers support the diagnostic and experimental question, not an observed gain from partial masking.
