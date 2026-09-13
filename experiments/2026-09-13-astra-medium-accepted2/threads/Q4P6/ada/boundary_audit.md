# When rank-based shaping becomes an unintended mechanism

## Assessment and changed question

The abstract-level proposal does not survive the papers' definitions. P's comparisons are external LMM
judgments of egocentric observations, not peer reports. Its consistency claim estimates the judge's latent
preferences, not truthful capabilities. Q's revelation principle characterizes outcomes already supported by
incentives; it does not certify an arbitrary scoring pipeline.

The sharper question is: **when does the accounting of comparison-derived shaping preserve incentives, and
when do report or participation boundaries turn it into an unintended transfer?** The potentially publishable
line is an audit and repair for open-team learning, with a strategic concealment stress test. The algebra
below is established PBRS reasoning applied to P's particular design, not a claim of a new general invariance
theorem. An implementation audit and substantive experiment remain necessary.

## Source anchors

- Q, single-agent environment, `inputs/Q.tex:280`, explicitly permits an action to be a complete trajectory.
  Its IC definition and explanation at lines 372-396 require joint report and action deviations to be
  unprofitable.
- Q, peer discipline, lines 1664-1734: distinct conditional co-player beliefs, proper scoring,
  reported-utility cancellation, and off-target prohibitions jointly support implementation. Scoring alone is
  not the result.
- Q, scalable oversight, lines 2105-2110: the affine reward changes the actor's marginal incentives. This
  differs from a trajectory-constant transfer.
- P, pairwise comparison and rank aggregation, lines 283-328: the judge receives paired egocentric images,
  compares active agents, and estimates Bradley-Terry scores. Singleton comparisons are skipped.
- P, potential function, lines 330-350: softmax scores define a vector potential, terminal potential is zero,
  and discounted potential differences augment the environment reward.
- P, robustness and Shapley discussion, lines 361-404: the target is the LMM's latent preference; equality
  with Shapley values is an additional assumption.
- P, MARS-Bench, line 427, and appendix lines 665-675: action-dependent battery depletion removes agents,
  followed by random-delay respawn. P does not specify persistent per-agent potential coordinates and return
  accounting through absences.
- P, appendix line 1122: comparisons are used during training only. A deployment-time reporting mechanism
  would be an extension.

## Exact invariance and its limits

Fix a finite-horizon game, a persistent agent identity, the same information and feasible-strategy spaces, and
the same initial history before any strategic choice. Let the base discounted payoff include whatever
intrinsic preferences or costs are being modeled. Add

\[
F_{i,t}=\gamma\Phi_{i,t+1}-\Phi_{i,t},
\qquad
\widetilde r_{i,t}=r_{i,t}+\rho F_{i,t}.
\]

Potentials may depend on history, coalition, reports, and realized judge randomness. The same realized value
must appear in the adjacent increments. With terminal potential zero,

\[
\sum_{t=0}^{T-1}\gamma^t F_{i,t}=-\Phi_{i,0}.
\]

If the initial value is fixed under deviations, every strategy's expected payoff changes by the same constant.
Therefore every unilateral deviation gain, including a joint report/action deviation, is unchanged. Strictly
profitable deviations remain profitable. Exact PBRS cannot newly establish Q's honesty or obedience
constraints. It can accelerate learning or select among existing equilibria, so this does not refute P's
empirical learning gains.

This comparison must hold information fixed. If shaped rewards disclose previously inaccessible peer
information, the agent may have a larger strategy space. Such disclosure is a separate mechanism effect.
Likewise, finite-horizon learning with an approximate critic need not behave like exact optimization. Neither
qualification is a proof of IC.

If the first report determines the initial potential, the residual is instead a report-dependent transfer:

\[
\widetilde U_i(\hat t_i)-U_i(\hat t_i)
=-\rho\,\mathbb E[\Phi_{i,0}(\hat t_i)].
\]

Lowering the initial score is rewarded. The remedy is to include the report transition from a fixed pre-report
potential, or explicitly refund the initial potential. P has no such explicit report stage; this is a warning
against the proposed strategic extension.

## Entry and exit identity

Let \(m_{i,t}\in\{0,1\}\) indicate whether agent \(i\)'s return includes the shaping reward on transition
\(t\). Suppress \(i\). Direct index shifting gives

\[
\begin{aligned}
\sum_{t=0}^{T-1}\gamma^t m_t
(\gamma\Phi_{t+1}-\Phi_t)
={}&-m_0\Phi_0
+\sum_{t=1}^{T-1}\gamma^t(m_{t-1}-m_t)\Phi_t\\
&+\gamma^T m_{T-1}\Phi_T.
\end{aligned}
\]

The interior terms are an exact description of the incentive changes due to masking. Coalition changes alone
do not invalidate PBRS: full persistent accounting still telescopes. Zero terminal potential alone is
insufficient if other increments are dropped.

For the natural extension \(\Phi_t=0\) while inactive, exits contribute zero but every re-entry contributes a
negative debit. If \(E\) is the set of re-entry times and terminal potential is zero,

\[
\sum_t\gamma^t m_t F_t
=-m_0\Phi_0-\sum_{e\in E}\gamma^e\Phi_e.
\]

A participant can then benefit from lowering its score on re-entry, conditional on having a feasible
manipulation that does not offset the gain through task payoff or manipulation cost. This incentive is present
even with an exact comparator. It concerns the sign and accounting of the potential, not statistical ranking
error.

Conversely, retaining nonzero inactive potentials can produce exit credits as well. The general identity
covers both conventions; an audit must establish which is implemented. Actor-loss masking, reward masking,
critic bootstrapping, and treating a disappearance as a terminal event are distinct operations and must not be
conflated.

## Exact concealment example

Use a three-transition horizon with \(\gamma=0.99\), \(\rho=1\), fixed zero base rewards, mask \((1,0,1)\),
and potentials

\[
(\Phi_0,\Phi_1,\Phi_2,\Phi_3)
=(1/2,0,p,0).
\]

The returning agent can expose evidence yielding \(p=1/2\), or conceal evidence yielding \(p=1/10\), with
unchanged physical trajectory. This manipulable evidence channel is an explicit new assumption. Both values
are possible two-agent softmax scores: score differences are respectively zero and \(\log(1/9)\).

Full accounting gives \(-1/2\) for either choice. Masked accounting gives

\[
G_{\rm mask}(p)=-1/2-(0.99)^2p.
\]

The exposed-evidence return is \(-0.99005\); the concealed-evidence return is \(-0.59801\). Concealment gains
\(0.39204\), before any cost. A concealment cost below this amount makes concealment strictly preferable. This
is a counterexample to applying a blanket invariance assertion to the masked extension, not evidence that P's
robots actually exploit it.

## Repair and a diagnostic

Maintain persistent agent identities and recorded potentials. Either include all shaping increments in the
same agent's return across absences, or settle the omitted boundary increments. Under zero inactive
potentials, adding \(\Phi_t\) to the first active reward at every re-entry exactly cancels the re-entry debit.
The remaining total is the fixed initial constant. A controllable initial report needs its own initialization
correction as above.

For a general mask, the boundary settlement at time \(t\geq1\) is \((m_t-m_{t-1})\Phi_t\); nonzero inactive
potentials may require settling a payment outside active transitions. These statements concern discounted
return accounting, not a complete implementation prescription for recurrent PPO.

An independent diagnostic uses the exact critic transformation. If

\[
\widetilde V_t=V_t-\rho\Phi_t,
\]

then, with consistent transitions and terminal handling,

\[
\widetilde r_t+\gamma\widetilde V_{t+1}-\widetilde V_t
=r_t+\gamma V_{t+1}-V_t.
\]

Thus exact TD residuals, and their consistently bootstrapped GAE sums, agree. Differences caused by
approximate critics can improve learning without implementing new strategic preferences. This is also a useful
way to localize terminal-mask errors.

## Concrete research protocol and stopping criterion

First reproduce the exact example and the mask identity; `check_boundaries.py` does so using rational
arithmetic. Then inspect a runnable MARS-RA implementation for inactive coordinates, reward and loss masks,
singleton conventions, stored versus resampled potentials, respawn identity, and terminal/truncation
bootstrapping. No implementation is included in the supplied inputs, so that audit has not been performed.

Next use a small finite open-team task with enumerated policies and an explicit evidence-withholding action.
Measure actual discounted deviation gains for the original accounting, complete persistent accounting, and the
boundary settlement. Hold comparator probabilities fixed initially; then vary query count. The predicted
concealment gain survives perfect ranking and disappears under corrected accounting. An unshaped baseline
establishes whether the manipulation was already profitable.

Only then test finite-budget learning in MARS-Bench. Separate task success, true private utility, comparison
accuracy, and best-response gain. A learning improvement without a changed best-response gain supports
credit-assignment efficiency; it does not establish alignment. If the implementation already accounts
correctly across absences, or no feasible observation/participation deviation changes boundary values, the
strongest empirical attack prediction fails. Report that outcome and narrow the contribution to an audit
methodology.

Q supplies the strategic deviation criterion. P supplies a specific open-team, normalized-comparison shaping
architecture where it can be tested. The combination motivates this protocol, but publication value is
conditional on findings beyond standard PBRS algebra. Emmy's fixed-evidence information ceiling is a
complementary constraint on any deliberate incentive-changing replacement, rather than an additional attack
claimed here.

## Prior work and unresolved issues

Dynamic PBRS preserving Nash equilibria is already established by [Devlin and Kudenko
(2012)](https://www.ifaamas.org/Proceedings/aamas2012/papers/2C_3.pdf), which P cites. Their result supports
the invariance background, not novelty of this note. I checked Emmy's lead, [Grzes
(2017)](https://aamas.csc.liv.ac.uk/Proceedings/aamas2017/pdfs/p565.pdf), Section 4.1 and conclusion: nonzero
terminal potentials can change policies and equilibria. This further limits any novelty claim for a
boundary-based analysis.

Searches run: `potential based reward shaping multi agent entry exit dynamic population terminal state policy
invariance`; `potential based reward shaping manipulable initial potential strategic reporting`;
`"potential-based" "shaping" "open" "agents" entry exit`; `"reward shaping" "agent death" potential`;
`"potential-based" "initial" "manipulation" reward`. These searches did not establish whether the
participation-mask formulation has already been studied. No novelty claim follows from that.

Unresolved: the actual implementation accounting; empirical manipulability of initial or returning views;
strategic utility and feasible deviation specification; whether the proposed audit reveals a material failure;
and prior work specific to open-team shaping. The current result supports a concrete investigation, not a
completed publication claim.
