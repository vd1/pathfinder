# Q and P: a finite-training robustness gap

## Verdict

The proposed mapping is mostly a category correction, not yet a positive transfer. P's use of "robustness" is statistical concentration around an assumed LMM preference. Q's robustness is a prediction-independent task-performance bound for arbitrary predictions. The publishable question is narrower:

> Can pairwise-comparison error yield a finite-training guarantee for the return or sample efficiency of MARS-RA?

From the two papers alone, the answer is no. They support a useful decomposition and identify the exact missing assumption, but do not provide that assumption.

## Textual evidence

- Q defines robustness as a bound that holds "for all" predictor outputs and does not depend on prediction error (Q, lines 314-323). It also says semantic output needs a task-defined error and that marginal coverage does not automatically bound downstream cost (Q, lines 1177-1204).
- P assumes that the LMM comparator follows a Bradley-Terry model with latent preference `c*` (P, lines 361-369). Its estimator converges to that preference, not to true contribution. P identifies `c*` with Shapley value `v*` only as an idealized premise (P, lines 383-389).
- P's shaped reward is `r_t + rho [gamma psi_{t+1} - psi_t]`, with terminal potential zero (P, lines 331-349).
- P reports that more queries and higher pairwise accuracy improve empirical training performance (P, lines 550-552), but gives no finite-training performance theorem.

## Two-error decomposition

Choose a gauge for the translation-invariant Bradley-Terry vectors and define semantic bias

`delta_t = ||c*_t - v*_t||_2`.

The triangle inequality applied to P's proposition gives, with its stated probability,

`||c-hat_t - v*_t||_2 <= C0 n sqrt(log(n)/K) + delta_t`.

This uses P's displayed normalized bound exactly. The paper itself is inconsistent about the dimension factor: the proposition, appendix restatement, and final appendix calculation state different scalings. Any formal result must first repair that rate and expose dependence on graph connectivity and score range.

The Jacobian of softmax is `diag(p) - p p^T`, whose spectral norm is at most `1/2`. Therefore

`||softmax(c-hat_t) - softmax(v*_t)||_2 <= (1/2)[sampling term + delta_t]`.

For an individual shaping step this yields an error bound proportional to `rho(1 + gamma)/2`. This is only reward-signal sensitivity, not return sensitivity.

## Telescoping obstruction

For a trajectory of length `T`, discounted shaping sums to

`sum_{t=0}^{T-1} gamma^t [gamma psi_{t+1} - psi_t] = -psi_0 + gamma^T psi_T`.

With P's terminal convention `psi_T = 0`, the total is `-psi_0`. If the initial potential is fixed independently of the chosen actions, all policies receive the same offset. Thus arbitrary comparison outputs do not change the optimal policy under the standard PBRS premises. Their observed benefit must concern the optimization path, gradient variance, exploration, or finite-sample behavior.

This blocks a direct Q-style consistency or robustness curve for final task quality: the asymptotic objective is invariant, while finite-training quality depends on the learning algorithm's stability under reward perturbations. Neither Q nor P supplies such a stability theorem. A comparison-error curve alone cannot determine learned-policy return because two learners can consume the same shaped rewards and have arbitrarily different finite-time outputs.

## Concrete research program

A defensible paper would define a prediction object and error with two coordinates:

`eta_t = (sampling error around c*_t, semantic bias from c*_t to v*_t)`.

It would then add an explicit finite-time learner contract, such as Lipschitz stability of policy updates or a regret bound under adaptive reward perturbations, and derive a cost-aware frontier in query count `K`. The frontier should charge LMM calls as Q proposes in its prediction-cost discussion (Q, lines 1242-1258). P's query-count experiment is a direct empirical test bed.

Without the learner contract, the strongest supported contribution is a diagnostic or impossibility statement: repeated LMM queries reduce variance but can lock in semantic bias, and PBRS transfers their value only through learning dynamics rather than through a changed optimal solution.

## Fixed-population repair for changing coalitions

P already declares a fixed population `N`, but its estimated score and potential live in `R^{|I_t|}`. The following construction makes successive potentials comparable. Let the augmented state be `x_t = (s_t, I_t, h_t)`, where `h_t` contains any prompt, model version, sampled LMM output, or history needed to make the potential measurable. For every nonterminal state, define `Phi_t in R^n` by

`Phi_t^i = 1{i in I_t} softmax_{I_t}(c-hat_t)^i`,

and set all coordinates to zero at a terminal state. If `|I_t| < 2`, a declared fallback is required, for example uniform credit on a nonempty singleton coalition and the zero vector for an empty coalition. This is a modeling choice that P currently omits.

Give every population member a null action while inactive and maintain a reward ledger for every `i in N` on every transition. Define

`F_t^i = gamma Phi_{t+1}^i - Phi_t^i` and `r-tilde_t^i = r_t^i + rho F_t^i`.

Then, pathwise and componentwise,

`sum_{t=0}^{T-1} gamma^t F_t^i = -Phi_0^i + gamma^T Phi_T^i = -Phi_0^i`.

Hence for any fixed initial augmented state and any joint policy, player `i`'s shaped expected payoff equals its original payoff minus the same constant `rho Phi_0^i`. Every unilateral policy comparison is unchanged, so the best-response correspondence and Nash equilibria are unchanged. The same argument preserves the ordering of joint policies for a team objective after summing coordinates. It does not require accurate comparisons. Stochastic or history-dependent LMM outputs are covered only if their realized state is included in `h_t`, or if the proof is stated pathwise on a common realization.

The reward-ledger convention is substantive. If rewards are delivered only during an agent's active intervals, telescoping across the full horizon no longer follows automatically. For an active interval `[a,b)`, the retained shaping sum has boundary terms `-gamma^a Phi_a^i + gamma^b Phi_b^i`, with the exact second term depending on whether the exit transition is paid. Entry state, exit state, and coalition changes can depend on prior actions, so these terms need not be policy-independent. A valid alternative must therefore specify transition ownership and add compensating entry and exit transfers that reproduce the fixed-ledger sum.

There is also a useful sanity check: on each nonempty nonterminal coalition, `sum_i Phi_t^i = 1`. Thus the population-summed shaping signal is largely a time-dependent constant. MARS-RA's effect is redistribution among individual learning signals, not additional team return. This reinforces that any positive theorem must concern finite-time multi-agent optimization and must state how inactive-agent ledger credits enter the learner.
