# Q and P: Structured Comparator Drift, Not Generic Noise

## Changed question

The abstract-scan question is too broad and transfers a finding about LLM traders to an LMM referee without evidence. I would replace it with:

> When MARS-RA repeats pairwise contribution queries, does rank aggregation remain robust when comparator errors are correlated and change with task phase or active coalition, or does repetition concentrate a stable bias into the shaping reward?

This is a direct test of P's robustness claim. Q contributes a diagnostic hypothesis and method, not proof that MARS-RA fails.

## Evidence from Q

Q identifies structured behavioral dependence rather than featureless output noise:

- Models differ greatly in willingness to cross the spread, and GPT Small buyers and sellers behave differently despite a symmetric market design (Q, lines 370-374).
- An opening quote anchors even unconstrained agents on the opposite side (Q, lines 397-402).
- For Gemini Large, reasoning language differs between incremental and trade-closing phases, shifting from strategy and optimization toward urgency and execution (Q, lines 405-438).
- Q explicitly limits that last result: it covers one model, is associational rather than causal, and reasoning traces may not reveal the true computation (Q, lines 409-442).

Therefore, Q supports testing context-, role-, and phase-dependent LLM behavior. It does not show that LLM pairwise judges are urgency-biased.

## Evidence from P

P's robustness theorem assumes that the LMM has a latent preference vector at step t and that comparisons follow a Bradley-Terry model (P, lines 361-376). The proof uses mean-zero bounded errors around that model (P, lines 707-733). Under those assumptions, more comparisons reduce estimation variance.

The empirical checks do not identify this assumption:

- Comparison quality is pooled agreement with dense per-agent reward, averaged over comparisons and tasks (P, lines 550-552 and 1072-1074).
- Ordered prompt reversal addresses position bias, but does not test phase or coalition dependence (P, lines 285-303 and 642).
- Dynamic participation is produced by battery depletion, removal, and respawn (P, line 427). P shows task success under this process, but does not report comparator calibration before, during, and after active-set changes.

P is already candid that comparison accuracy matters and that nonstationarity remains (P, line 642). The new point is that aggregation guarantees variance reduction only for errors centered on a stable, correctly specified preference model.

## Minimal formal result

Let the true pairwise log-odds be c_i - c_j, but let context z affect the comparator:

`Pr(Y_ij = 1 | z) = sigmoid(c_i - c_j + d_ij(z))`.

If d_ij(z) has a persistent component, the Bradley-Terry estimator converges to a pseudo-true ranking, not necessarily c. A simple identifiable case is d_ij = b_i - b_j. Then unlimited queries recover c + b, so variance vanishes while the bias norm does not. If d_ij cannot be written as score differences, it induces cycles and model misfit. Either case invalidates interpreting the usual 1/sqrt(K) rate as convergence to contribution truth.

This yields a crisp prediction: increasing query count can make credits more repeatable without making them more valid. P's own query-count ablation can be extended to separate variance reduction from bias.

## Concrete study

Use MARS-Bench because it already supplies dense diagnostic rewards and controlled active-set changes.

1. At sampled states, repeat identical ordered comparisons with fresh calls. Stratify by task phase, visible energy, visibility, agent role, active-set size, and windows around removal or respawn.
2. Estimate repeat correlation, calibration against dense reward, pairwise reversal consistency, cycle rates, and Bradley-Terry goodness of fit. Report conditional metrics rather than only pooled accuracy.
3. Apply controlled prompt and observation perturbations: mask or randomize the energy icon, swap identity labels, balance image order, and replay the same pair under different active-coalition descriptions. P's deployed input includes the energy icon but does not clearly include the coalition list, so explicit horizon or coalition cues are interventions rather than faithful replays. This distinguishes visual ambiguity from contextual bias.
4. Re-run the query-count ablation under naturally observed and injected correlated errors. Compare standard aggregation with a context-aware or uncertainty-weighted model.
5. Evaluate both credit validity and downstream success. The decisive result is a bias floor or performance degradation that more queries do not repair, followed by recovery from the context-aware method.

Q's lexical/convergence analysis can be adapted only if the referee emits rationales. Lexical phase markers should be treated as secondary diagnostics, with outputs and dense-reward agreement as primary evidence.

### Dynamic-membership mechanism

P constructs a fixed n-by-n comparison matrix but fits scores and applies softmax over the active set (P, lines 285-345). The paper then subtracts successive potential vectors even when membership may change. The text does not specify the identity alignment used for that subtraction. A fixed-population embedding can make it well typed, but active-set softmax still changes every survivor's normalized potential when a peer enters or exits, even if all survivor scores remain fixed. This gives the dynamic-agent angle a concrete mechanism beyond generic judge reliability.

The two mechanisms should first be tested separately. Comparator drift is tested by frozen-state input interventions, including the visible energy cue (P, lines 285-303 and 397). Boundary credit shocks are tested by replaying fixed raw scores through active-set and entry/exit-invariant potentials. Their interaction should be claimed only if membership or exit proximity measurably changes judgments in the actual comparator input.

That discontinuity is not automatically a policy-bias result. If the padded potential is Markov and consistently applied, standard potential shaping may still preserve the target policy. The empirical concern is whether membership-driven shaping impulses corrupt credit validity or raise learning variance. Compare active-set softmax against fixed-population, masked, and entry/exit-invariant potentials while holding raw contribution scores constant.

## Publication assessment

The generic statement that LLM judges are noisy is not enough for a paper. A publishable contribution would require the formal distinction between iid noise and structured drift, a conditional diagnostic benchmark around open-team transitions, and an intervention that restores calibrated credits or downstream learning.

This project is feasible within P's stack and does not require integrating Q's market simulator. The market paper mainly supplies the motivation for looking beyond pooled accuracy and a template for connecting individual decision modes to system-level convergence.

## Failure conditions and unresolved issues

- The connection weakens substantially if repeated referee calls are conditionally independent, Bradley-Terry fit remains adequate across all strata, and query count improves conditional calibration as predicted.
- Dense instantaneous rewards may be an imperfect ground truth for delayed contribution, so the study needs synthetic states with known contributions or counterfactual rollouts as a second reference.
- P defines a new c*_t at every step. Fast temporal change alone does not contradict its theorem. The test must hold the evaluated state fixed and probe prompt/context dependence, or explicitly model drift within the set of comparisons aggregated for that state.
- Active-set robustness in P partly means that the mechanism remains defined as team size changes. It should not be misreported as a demonstrated theorem that LMM judgment semantics are invariant to coalition changes.
