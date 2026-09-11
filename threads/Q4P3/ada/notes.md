# ada notes, pair Q4P3 (Q = Bergemann-Koh-Morris, P = Qiu-Gill)

Checks: `uv run --with sympy python ada/check_lq_agreement.py`

## 1. Agreement penalty in Q's coupled environment (closed form)

Environment of Q, "Competition through coupled rewards": v = -sum_i (a_i - theta)^2,
u_i = -(a_i - theta - b_i)^2, both agents know theta and both biases. Replace Q's (CR)
by r_i(D) = -kappa_i D^2 with D = a_2 - a_1. Agent 1 = reviewer R, agent 2 = critic C.
Own-action second derivative is -2(1+kappa_i) < 0, so the first-order conditions give the
unique Nash equilibrium:

- a_R - theta = ((1+kappa_C) b_R + kappa_R b_C) / (1+kappa_R+kappa_C)
- a_C - theta = (kappa_C b_R + (1+kappa_R) b_C) / (1+kappa_R+kappa_C)
- D = (b_C - b_R) / (1+kappa_R+kappa_C)

Readings for P (output = R's final review, P Fig. 1 "Review_k is the consistent review"):

- C moves R's output only through R's own agreement weight: leverage kappa_R/(1+kappa_R+kappa_C).
  kappa_R = 0 gives a_R = theta + b_R whatever C does.
- kappa_C large (P Case B, "C gives in") sends a_R to theta + b_R: AR collapses to Single-reviewer.
- kappa_R = kappa_C -> infinity: D -> 0, both actions -> theta + (b_R+b_C)/2, human loss
  -> (b_R+b_C)^2/2. Agreement is reached by shrinking D, not the error. Compare Q's
  Prop. "Coupled rewards make loss arbitrarily small": loss eta^2 (b_2-b_1)^2/2, because
  (CR) uses D to identify the biases.
- In that limit the critic beats a single reviewer iff |b_R + b_C| < 2|b_R|, i.e.
  b_C in (-3 b_R, b_R) for b_R > 0. A same-direction critic more biased than R (P Case A)
  makes AR worse than Single-reviewer (P Table 2: 0.457 vs 0.495).
- Same model for all roles (P sec. 3: Claude Sonnet 4.5 everywhere): b_R = b_C gives D = 0
  at every kappa and error b. Immediate agreement then says nothing about common-mode error.

## 2. Cross-check of emmy's consensus theorem (ledger #2), exact monotonicity step

Given a_2, agent 1 chooses D to maximize r_1(D) - (D - z_1)^2 with z_1 := (a_2 - theta) - b_1.
Optimality of D(b) for type b against D(b'), plus the same for b' against D(b), sums to

    (D(b) - D(b')) (z_1(b) - z_1(b')) >= 0      (exact, no slack term)

For agent 2, given a_1, D maximizes r_2(D) - (D - z_2)^2 with z_2 := b_2 - (a_1 - theta), so
(D(b) - D(b'))(z_2(b) - z_2(b')) >= 0. Near first best (|a_i - theta| <= eps):
z_1 = -b_1 + O(eps) and z_2 = k b_1 + O(eps). For k > 0 and |b - b'| > 2 eps / min(1,k),
the two inequalities force D(b) = D(b'). Chaining through a third type far from both extends
this to all pairs once the interval length L > 4 eps / min(1,k). This confirms emmy's step (i).
With D pinned, the reward is a pure consensus device and any common shift is self-enforcing,
which is Q's remark "they might simply choose the same fixed action".

## 3. Q's binary peer-scoring example also has an uninformative equilibrium

Q's score table: q(H,H) = 7/9, q(H,L) = 1/9, q(L,H) = 1, q(L,L) = -1. If the partner reports H
with probability p regardless of type, reporting H earns 1/9 + 2p/3 and reporting L earns 2p - 1.
These are equal at p* = 5/6. Both types mixing 5/6 on H is a symmetric equilibrium: on-path
utilities cancel and the -infinity penalty keeps obedience. Reports are uninformative and the
human gets 1/2 instead of 1. Symmetric pure pooling is not an equilibrium: under "always H",
deviating to L gives 1 > 7/9; under "always L", deviating to H gives 1/9 > -1. Correction
(emmy, ledger #13): asymmetric pure pooling (agent 1 always H, agent 2 always L) is an
equilibrium, since 1/9 > -1 and 1 > 7/9.

Contrast with P: P's inner loop rewards agreement absolutely, since it terminates on AGREE.
Q's proper score rewards agreement only as far as the agent's own type predicts the partner's
report. Operational analogue for P, a correlated-agreement audit (Dasgupta and Ghosh 2013;
Shnayder et al. 2016): compare C's AGREE rate on matched (review of PR i, diff of PR i) pairs
with its AGREE rate on mismatched (review of PR j, diff of PR i) pairs. If the rates are close,
C's AGREE carries no information.

## 4. Objection: P's LCB comparison confounds interaction with the acceptance rule

- Single-reviewer and Two-reviewers edit once (P sec. 3.2 and 3.3).
- MARS: K = 2 rounds (P sec. 3.4).
- AR: outer loop runs until the first-pass rule holds. No outer cap is stated for LCB (P sec. 3.5
  gives only the 5-round inner cap). The SWE-bench workflow caps outer iterations at 2
  (P appendix, AR SWE-bench instantiation).
- SWE-PRBench isolates the inner loop, and naive AR is worst there (0.457).

The run that separates the two: Single-reviewer inside AR's outer loop and first-pass rule, with
the same outer cap.

## 5. Open (not worked out): information version

Two-agent beauty contest in the style of Morris and Shin (2002). Shared prior mean y, private
signals x_i = theta + e_i with precisions alpha (prior) and beta (signal), loss
(1-r)(a_i - theta)^2 + r(a_i - a_j)^2. The linear equilibrium weight on private evidence is
w = (1-r) lambda / (1 - r lambda), with lambda = beta/(alpha+beta). This is below lambda for
r > 0 and goes to 0 as r -> 1. The model is simultaneous-move, though, while P's loop is
sequential, and truthful Bayesian exchange there would pool information
(Geanakoplos-Polemarchakis). So the claim to test is that conformity garbles C's message.

## 6. Where emmy's impossibility stops: a state measure, and whose bias it carries

Emmy's proposition (ledger #2 to #5) is about Q's taxonomy cell "exact action measure, no state
measure" (Q, table in "Dimensions of single-agent mechanisms"), where Q's (CR) also sits.
Evidence-grounded disagreement (P sec. 4.4) adds a coarse state measure: a checkable statement
about the code, that is, about theta. Minimal model: the protocol sees m = theta + beta_m + noise,
where beta_m is the checker's bias, and adds -lambda (a_i - m)^2 to each agent's payoff. Then
a_i = theta + (b_i + lambda beta_m)/(1 + lambda), which tends to theta + beta_m as lambda grows,
whether or not the biases co-move. The error moves onto the measure. In P the citation is judged
by R, the same model as C, so beta_m is roughly the common-mode bias. A mechanical check (the
cited snippet must occur in the diff) is unbiased but coarse: it checks existence, not relevance.

Conformity-weighted consensus (refines emmy's symmetric lemma). With kappa_R = alpha K and
kappa_C = (1 - alpha) K, K large, the consensus tends to theta + (1 - alpha) b_R + alpha b_C.
The weight on C's bias is R's share of the conformity, and C yielding (alpha -> 0) gives R's bias.

Revelation-principle reading. C's evidence types: E (holds contradicting code), N (doubt only),
A (no objection). E can send anything; N and A cannot send E if citations are checked. Q's
multi-agent revelation principle needs only monotone input menus, not transfers, so a typed-verdict
protocol with response rules replicates any richer exchange with the same evidence structure. This
is conditional on citations being checked and on R obeying the response rules. AGREE and C's added
bugs carry no certificate (emmy #2), so the order constrains only one channel.

## 7. Contrarian escape: affine form, stability, unknown ratio, and a selection caveat

Checks: `uv run --with sympy --with numpy python ada/check_ratio.py` (also confirms the identity
in emmy/general_rewards.md sec 1 and emmy's example in sec 2).

D-only quadratic rewards, c_i = 1/(1 + kappa_i), b_C = k b_R. R's equilibrium output is

    x_R = A b_R + (1 - A) b_C,   A = c_R / (c_R + c_C - c_R c_C),

an affine combination with a weight fixed by the design; A can take any real value. The error is
zero only at A* = k/(k - 1), so de-biasing needs the bias ratio and, for same-sign biases,
extrapolation (A outside [0, 1]).

- Stability. For 0 < k < 1 (C less biased, same direction), A* < 0. A < 0 iff
  (c_R - 1)(c_C - 1) > 1, and with rho_i = 1 - c_i this is rho_R rho_C > 1: alternating best
  responses diverge. Every exact de-biasing design with 0 < k < 1 has an unstable equilibrium
  (random search found none stable; emmy's example reaches 1e19 in 40 rounds). For k > 1
  (C more biased) stable designs exist: C states its bliss point (kappa_C = 0) and R plays
  a_R = c_R t_R + (1 - c_R) t_C with c_R = k/(k - 1); for k = 2 this is a_R = 2 t_R - t_C.
- Unknown ratio. A design tuned to k0 leaves beta_R(k) = (k - k0)/(1 - k0). All designs pass
  through beta_R = 1 at k = 1. Over k in [k_lo, k_hi] with k_hi < 1 the best worst case is
  (k_hi - k_lo)/((1 - k_lo) + (1 - k_hi)): 0.96 for [0.5, 0.99], 0.6 for [0.8, 0.95], 1/3 for
  [-2, -0.5]. R alone has 1.
- Any state-independent mechanism, unknown ratio. Types (b, k) in [0, B] x [k_lo, k_hi] contain
  (B (1 - k_hi)/(1 - k_lo), k_lo) and (B, k_hi), which share (t_R, t_C) and whose states differ
  by B (k_hi - k_lo)/(1 - k_lo). This extends emmy's k = 1 argument continuously.

Selection caveat (applies to the last bullet and to emmy/general_rewards.md sec 3). Identical
preference profiles give identical games, so the bound holds for full implementation and for any
equilibrium selection that depends only on the game. It does not hold under Q's standard, partial
implementation (Q footnote at line 543: "an equilibrium, not necessarily the unique one"). With
clones, a report-matching device (action = common report m, mismatch penalty -infinity) has every
common m as an equilibrium in every state, m = theta included. Both agents strictly prefer
m = t (payoff 0) to m = theta (payoff -b^2 each), so the agent-preferred equilibrium is the
biased consensus. For clones the question is which equilibrium the models select, which ties
this to sec 3 and ledger #13.

## 8. A P-side anchor without model spend, and what outside work measures (round 2)

Responds to the verifier (#20) and to emmy/same_diff_test.md (#21). No model calls were made:
there is no API key in this shell, and nobody has authorised spending.

P's published numbers. P reports F1 only (P lines 294-312): no precision, recall or comments per
PR. The two case studies have opposite signatures.

| mechanism | P passage | precision vs Single-reviewer | recall vs Single-reviewer |
|---|---|---|---|
| Case A: C confirms R's hedges and adds flags (co-moving over-flagging) | lines 317-326 | lower | same or higher |
| Case B: C yields to a rebuttal that cites no code | lines 328-336 | about the same | lower |
| text constraint: R must cite or drop on DISAGREE_CONCERN | lines 351-356 | higher, capped by C's added flags | about the same |

P's judge already labels each comment (line 321: "marks 3 of 5 comments as fabricated"), so the
split needs P's logs and no new calls. The logs are not public (line 728). SWE-PRBench itself is
public under CC BY 4.0, with diffs and human comments but no model reviews
(https://huggingface.co/datasets/foundry-ai/swe-prbench).

Two effects in the outside work.

- Ownership (content fixed, role varied). arXiv 2606.05976 injects one false claim into a
  model's own thought block. Relabeling it as a user, tool or memory message raises explicit
  correction by 23 to 93 percentage points in 10 of 12 settings (9 models, math and logic).
  P's C always receives R's review as another agent's message, so this effect is absent in P.
- Disposition (the model's own kind of error, shown as external input). DeltaBench
  (arXiv 2502.19361): self-critique is below cross-model critique for three reasoning models,
  and 36% below for DeepSeek-R1. arXiv 2408.10495: GPT-3.5 and GPT-4 repair other LLMs'
  insecure code at 33.2 to 59.6% but do poorly on their own. Both are confounded by source
  (own outputs differ in difficulty), and neither covers code review or Sonnet 4.5. Emmy's
  crossover contrast I removes that confound.
- Kim et al. (arXiv 2506.07962): errors are more correlated within a provider. This is
  co-movement of correctness across items, not of flagging. arXiv 2605.21537 tests self-review
  only, so it cannot separate the two effects.

Extra arm for #21: show the same own-model false flag to C once inside R's review (P's
condition) and once as C's own earlier draft. The gap between the two is ownership. The
own-versus-other gap inside the external arm is disposition, and only disposition bears on P.
Supply of candidate flags: SWE-PRBench (arXiv 2603.26130) reports single-pass hallucination
rates of 0.19 to 0.42 on diff-only (0.227 for Sonnet 4.6), so most diffs should have some.
A person still has to confirm that each flag is false.
