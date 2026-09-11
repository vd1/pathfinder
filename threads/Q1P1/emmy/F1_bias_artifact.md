# F1. The e_s/delta_min term in P is an artifact of the proof; the plug-in fixed point is Theta(delta + e_s)

Notation follows P. C^{i,s}(x) := E_xi[ hat C^i(x; xi_{1:s}) ] is the expected empirical CVaR of agent i
at a query point x with a fresh batch of size s. b_i(x) := C^{i,s}(x) - C^i(x) is its bias.

## Step 1. The estimator is an exact gradient of a convex surrogate (P already uses this in Thm 2)

P assumes that the batch is independent of u_k^i and of F_k (Sec. 3, below eq. (EDF)). Hence
  E[ hat g_k^i | F_k ] = (d/delta_i) E_u[ C^{i,s_k^i}(y_k^i + delta_i u) u ] = grad (C^{i,s_k^i})_delta(y_k^i),
with (.)_delta the uniform-ball smoothing. This is P's eq. (surrogate-unbiased-gradient), which P states only
for fixed s but which holds for each k with s = s_k^i. C^{i,s} is convex: for each sample realization the
Rockafellar-Uryasev objective is jointly convex in (x, tau), partial minimisation over tau keeps convexity,
and expectation keeps it (P says this in the proof of Thm 2).

## Step 2. Uniform bias bound (P's own ingredients)

P's Lemma A.1 (Wang et al. 2022, Lemma 3) plus DKW give, for every fixed x,
  |b_i(x)| <= E| hat C^i(x) - C^i(x) | <= (2 U_i / alpha_i) sqrt(pi / (2 s)) = sqrt(2 pi) U_i / (alpha_i sqrt(s)) =: beta_i(s).
Because the batch is fresh at every query, this is a bound on a deterministic function, uniformly in x.
Smoothing keeps it: |(C^{i,s})_delta - C^i_delta| <= beta_i(s).

## Step 3. Replace P's gradient-error step by a function-value step

P bounds E<e_k^i, y - z> by D_x E||e_k^i|| <= D_x (d/delta_i) beta_i(s), which costs d D_x / delta.
Instead, with tilde C := (C^{i,s})_delta,
  <grad tilde C(y), y - z> >= tilde C(y) - tilde C(z) >= C_delta^i(y) - C_delta^i(z) - 2 beta_i(s).
Everything else in P's proofs of Prop. (iterate relation), Thm 1, Prop. (liminf), Thm 2 and the centralized
corollaries goes through unchanged, with
  D_1' = 2 L_max delta_max + (2/m) sum_i beta_i(s_k^i) <= 2 L_max delta_max + 2 sqrt(2 pi) max_i(U_i/alpha_i) e_s,
  D_2' = D_1' + D_x L_max delta_max / r.
For Thm 2 the step is even shorter: bar x_inf minimises tilde C over X_delta, so tilde C(bar x_inf) <= tilde C(z_delta),
and C(bar x_inf) - C* <= 2 L delta + 2 bar beta + D_x L delta / r with no gradient comparison at all.

Result: limiting gap O(delta_max + e_s), not O(delta_max + e_s / delta_min). No factor d, no factor 1/delta.
The transient term rho_beta(T)/delta_min^2 (variance of the one-point estimator) is unchanged.

Size of the change in P's own experiment (d = 10, X = {||x||_inf <= 10} so D_x = 20 sqrt(10) ~ 63, delta = 0.4):
P's sampling term / corrected sampling term = d D_x / (2 delta) ~ 790.

## Step 4. Consequences for P's remarks

- P, Remark after Cor. 1: "If a diminishing delta_k scheme is selected ... the sample size s_k^i must increase
  asymptotically to control the resulting estimation error." Not needed: with fixed s and delta_k -> 0 with
  sum eta_k = inf, sum eta_k^2 / delta_k^2 < inf, the same per-step inequality gives limsup gap <= 2 bar beta(s) = O(e_s).
  (Care needed for the growing projection sets X_{delta_k}; standard.)
- P's abstract: "This distributed bound matches the parameter dependence of the centralized benchmark." Both
  upper bounds share the same removable 1/delta_min amplification. In Q's Axis B vocabulary (Q Sec. 2.3 and the
  Axis B paragraph after P5) this is an achieved-vs-achieved comparison (E0 vs E0), and the shared dependence was on
  a loose term.

## Step 5. The corrected order is attained by P's algorithm (tightness for this algorithm, not a minimax bound)

(a) e_s part. X = [-1, 1], J(x, xi) = ((1-x)/2) A(xi) + ((1+x)/2) b, A ~ Bernoulli with P(A = 1) = alpha, b constant.
    CVaR_alpha(A) = 1, and the empirical CVaR of A is min(1, N/(alpha s)) with N ~ Bin(s, alpha), whose bias is
    -c_s with c_s = E[(1 - N/(alpha s))_+] = Theta(sqrt((1-alpha)/(alpha s))). True C(x) = ((1-x)/2) + ((1+x)/2) b and
    C^s(x) = ((1-x)/2)(1 - c_s) + ((1+x)/2) b are both linear. Take b = 1 - c_s/2: truth minimised at x = 1,
    surrogate minimised at x = -1 (up to the X_delta shrinkage), true excess (1 - b) = c_s / 2 = Theta(1/sqrt(s)).
(b) delta part. Deterministic C(x) = max(a x, -b x) in 1-D, b > a. Ball smoothing moves the minimiser to
    x = delta (b - a)/(a + b), true excess a delta (b - a)/(a + b) = Theta(delta).
So the fixed point of P's algorithm has limiting true excess Theta(delta + e_s) over the instance class of P.

## Step 6. Alternative that removes e_s altogether (to check against literature)

Lift tau into the decision: phi_i(x, tau_i) = tau_i + (1/alpha_i) E (J^i(x, xi) - tau_i)_+ is jointly convex; tau_i stays
local (no consensus needed on tau, only on x), tau_i in [-U_i, U_i]. A one-point estimator on (x, tau_i) with a single
sample per query is unbiased for the smoothed phi_i. Limit bias O(delta) only; price: Lipschitz constant in x
becomes L_i/alpha_i and the estimator magnitude grows by ~1/alpha_i (transient variance), and no batch of size s is needed.
