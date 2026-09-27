# A learning-dynamics test for rank-based reward shaping

## Source facts and sharpened question

Q defines prediction error against a task target and distinguishes consistency, robustness, and smoothness (Q, lines 257-344). Its inference-graph discussion says that local guarantees need an error-sensitive edge and a common downstream objective before they compose (Q, lines 1023-1110). It also proposes charging for predictor calls (Q, lines 1242-1258).

P obtains per-step comparisons from an LMM, fits Bradley-Terry scores, softmaxes the scores, and uses \(F_t=\gamma\psi_{t+1}-\psi_t\) as a vector reward increment (P, lines 281-349). Its estimator proposition addresses distance to a latent LMM preference vector (P, lines 358-377); its experiments associate better pairwise accuracy and more queries with better training outcomes (P, lines 550-552, 1070-1074). P reports 30 hours for MARS-RA against 16 hours for MAPPO under its setup (P, lines 781-783), and comparisons are made during training rather than deployment (P, lines 1119-1122).

The sharpened question is: **which measurable learning mechanism converts the LMM potential and its query budget into better final unshaped return under approximate MAPPO?** This changes the initial broad question about transferring Q's competitive ratios. The output here is a derivation and an experimental design, not a claim that a new performance guarantee already follows.

## Exact cancellation

Fix a policy, a predictor protocol, and one complete episode. Let \(h_t\) include all information used to produce the potential before action \(a_t\), including the active-agent set and the sampled LMM output. Define one cached potential \(\psi_{i,t}=\psi_i(h_t)\) for each population member, using the same value in both adjacent shaping terms. Put \(\psi_{i,T}=0\) at the terminal transition. Then, for every trajectory,

\[
\begin{aligned}
G_i^{\mathrm{shape}}
&=\sum_{t=0}^{T-1}\gamma^t\bigl(r_t+\rho(\gamma\psi_{i,t+1}-\psi_{i,t})\bigr)\\
&=G^{\mathrm{env}}-\rho\psi_{i,0}.
\end{aligned}
\]

Conditioning on \(h_t\), assuming the potential is determined before the current action, gives \(Q_i^{\pi,\mathrm{shape}}(h_t,a_t)=Q^{\pi,\mathrm{env}}(h_t,a_t)-\rho\psi_{i,t}\) and \(V_i^{\pi,\mathrm{shape}}(h_t)=V^{\pi,\mathrm{env}}(h_t)-\rho\psi_{i,t}\). Thus \(A_i^{\pi,\mathrm{shape}}=A^{\pi,\mathrm{env}}\). This is a direct consequence of potential shaping, not a new invariance theorem. It says the best possible advantage does not improve as pairwise accuracy increases. Improvements can still occur during finite-data learning through representation, critic fitting, exploration, truncation, or implementation details.

For an arbitrary unshaped critic estimate \(\widehat V_i\), define the matched shaped critic \(\widehat V_i^{\mathrm{match}}=\widehat V_i-\rho\psi_i\). The temporal-difference residuals cancel pathwise:

\[
\delta_{i,t}^{\mathrm{shape}}(\widehat V_i^{\mathrm{match}})
=r_t+\rho(\gamma\psi_{i,t+1}-\psi_{i,t})
+\gamma(\widehat V_i(h_{t+1})-\rho\psi_{i,t+1})
-(\widehat V_i(h_t)-\rho\psi_{i,t})
=\delta_{i,t}^{\mathrm{env}}(\widehat V_i).
\]

Every generalized-advantage estimate made from these same residuals is therefore identical. If the implemented shaped critic is instead \(\widetilde V_i=\widehat V_i-\rho\psi_i+e_i\), then

\[
\delta_{i,t}^{\mathrm{shape}}(\widetilde V_i)-\delta_{i,t}^{\mathrm{env}}(\widehat V_i)
=\gamma e_i(h_{t+1})-e_i(h_t).
\]

For \(L\) residuals, \(\lvert e_i\rvert\le\epsilon\), and GAE parameter \(\lambda\), the resulting absolute advantage difference is bounded by \((1+\gamma)\epsilon\sum_{\ell=0}^{L-1}(\gamma\lambda)^\ell\). This is an error channel Q's inference-graph account demands. It involves critic mismatch, not merely Bradley-Terry parameter error.

## Boundaries and a discriminating experiment

P's dynamic coalition requires the potential to be defined consistently for each agent across entry and exit.
One sufficient convention is a full-population potential vector and a complete reward stream for every agent,
including transitions while inactive. An active-only reward mask is a different operation. If
\(a_{i,t}=\mathbf 1\{i\in I^t\}\), then the shaping sum with masked rewards is

\[
\sum_{t=0}^{T-1}\gamma^t a_{i,t}F_{i,t}
=-a_{i,0}\psi_{i,0}
+\sum_{t=1}^{T-1}\gamma^t(a_{i,t-1}-a_{i,t})\psi_{i,t},
\]

assuming terminal potential zero. At reentry, \(a_{i,t-1}=0\), \(a_{i,t}=1\), and \(\psi_{i,t}>0\),
so a new negative term remains even if the inactive potential was zero. This corrects the simpler
terminal-only account: zero potential upon exit is insufficient for repeated entry under active-only
reward accounting. P's displayed equations do not specify the mask or full-population embedding,
so the exact policy-invariance application to its implementation remains to be verified.

Softmax also gives \(\sum_{i\in I^t}\psi_{i,t}=1\) on a nonterminal state with active agents.
If training pools shaping rewards over the full population before its critic update, the summed
shaping term is independent of the rank scores. Pooling over active agents alone can retain
rank dependence at coalition changes. The critic and reward-routing code would decide which case applies.

The experiment should hold environment steps, wall-clock time, and predictor-call accounting visible. Compare P's standard MAPPO integration with a matched-critic condition that subtracts the exact cached potential from the critic output, and controls using a uniform potential and a randomized potential matched for scale. Record held-out unshaped return, critic error, advantage discrepancy, \(K_t\), and query latency for the same trajectories. A finding that the matched-critic condition erases P's advantage gain would identify critic approximation as the channel; persistence would direct attention to exploration, partial observation, or data collection. Vary the call budget only after these controls separate mechanisms.

The query-cost objective should be a training objective, such as held-out unshaped return after a specified environment-step and wall-clock budget minus a declared cost per LMM call. Q's competitive ratio uses an offline optimum for online decisions and does not directly apply to this training process. P's accuracy metric compares LMM judgments to dense per-agent reward signs (P, lines 550-552, 1070-1074); its link to the critic mismatch channel is a hypothesis to test.

## Objections and prior work

Ada's ledger finding identifies a separate finite-sample obstruction in P: for two agents and two unanimous Bradley-Terry outcomes, the unregularized maximum-likelihood estimate diverges despite a connected comparison graph (P, lines 313-329, 363-377). The calculation is correct under independent draws. Regularization, a score constraint, and a gauge convention are prerequisites before using P's stated score-distance bound as an input to a new theorem. Softmax outputs remain bounded, which does not rescue the stated finite MLE claim.

Potential shaping invariance and learning-speed questions predate this pair.
Wiewiora's [2003 paper](https://www.cs.cmu.edu/afs/cs.cmu.edu/project/jair/pub/volume19/wiewiora03a.pdf)
relates static potential shaping to value initialization, and Devlin and Kudenko's
[dynamic shaping paper](https://aamas.csc.liv.ac.uk/Proceedings/aamas2012/papers/2C_3.pdf)
treats time-varying potentials. Gupta et al.'s
[NeurIPS 2023 paper](https://proceedings.neurips.cc/paper_files/paper/2023/file/a5357781c204d4412e44ed9cbcdb08d5-Paper-Conference.pdf)
explicitly proves unchanged expected policy gradients and shows that shaping can increase
gradient variance. The search queries were `potential based reward shaping advantage invariant
actor critic exact value function TD error theorem paper`, `Wiewiora 2003 potential based
reward shaping equivalent q value initialization pdf`, and `multiagent potential based reward
shaping generalized advantage estimation critic approximation`. These results prevent a
novelty claim for cancellation or variance increase alone. The candidate contribution is a
tested, cost-aware mechanism for P's LMM-generated, changing-coalition potentials under
approximate MARL, if the proposed controls reveal a reproducible effect.
