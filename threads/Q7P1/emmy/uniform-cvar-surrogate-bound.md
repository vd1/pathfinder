# Uniform error of P's expected empirical-smoothed CVaR surrogate

Fix one agent and write `C(x) = CVaR_α(J(x, ξ))`. Under P's Assumption 3,
`|J(x, ξ)| ≤ U` and `J(·, ξ)` is `L`-Lipschitz on `X`. For batch size `s`,
let `Ĉ_s(z)` be the empirical CVaR and define P's deterministic surrogate

`C̃(x) = E_{ν,batch}[Ĉ_s(x + δν)]`, with `ν ~ Unif(B)` and `x ∈ X_δ`.

## Claim

For every `x ∈ X_δ`,

`|C̃(x) - C(x)| ≤ b := Lδ + (U/α)√(2π/s)`.

Consequently, `sup_{x∈X_δ}|C̃(x)-C(x)| ≤ b`. This is a uniform bound on
the deterministic expected surrogate. It is not a high-probability uniform
bound for one empirical objective.

## Proof

Let `F_x` and `F̂_{x,s}` be the true and empirical loss CDFs at a fixed `x`.
CVaR is `1/α`-Lipschitz in the one-dimensional Wasserstein-1 distance:

`|CVaR_α(F̂_{x,s}) - CVaR_α(F_x)| ≤ W₁(F̂_{x,s},F_x)/α`.

Both distributions are supported on `[-U,U]`, so

`W₁(F̂_{x,s},F_x) = ∫|F̂_{x,s}(t)-F_x(t)|dt ≤ 2U D_s`,

where `D_s = sup_t|F̂_{x,s}(t)-F_x(t)|`. The Dvoretzky-Kiefer-Wolfowitz
inequality gives `P(D_s>q) ≤ 2 exp(-2sq²)`. Integrating this tail bound,

`E[D_s] ≤ ∫₀^∞ 2 exp(-2sq²)dq = √(π/(2s))`.

Therefore, for every fixed `x`,

`E_batch|Ĉ_s(x)-C(x)| ≤ (U/α)√(2π/s)`.

The right side does not depend on `x`. Thus, for `x ∈ X_δ`, Jensen's
inequality and P's CVaR Lipschitz lemma yield

`|C̃(x)-C(x)|`

`≤ E_ν |E_batch Ĉ_s(x+δν)-C(x+δν)| + E_ν|C(x+δν)-C(x)|`

`≤ (U/α)√(2π/s) + Lδ`.

This proves the claim. The constant exactly matches the pre-gradient
finite-sample estimate implicit in P's proof: multiplying by `d/δ` produces
P's `dU√(2π)/(αδ√s)` gradient-error term.

## Corrected consequences

For several agents set `b_n = L_nδ_n + (U_n/α_n)√(2π/s_n)`.

For unnormalized costs, `|C̃_n-C_n| ≤ b_n`. If the total true cost is
`ρ`-strongly convex and `x̃` minimizes the sum of surrogates on the same
feasible set as the true optimizer `x⋆`, then

`Σ_n C_n(x̃)-Σ_n C_n(x⋆) ≤ 2Σ_n b_n`,

and strong convexity gives

`||x̃-x⋆|| ≤ 2√((Σ_n b_n)/ρ)`.

There is a domain caveat: P optimizes on the shrunken set `X_δ`, while Q's
true optimum is posed on the original feasible set. The displayed optimizer
bounds require a common feasible set. Otherwise an additional shrinkage
error must be included, as P does through its interior-ball construction.

For Q-style outside-option normalization,

`V_n(x) = -C_n(x)+C_n(0)` and
`Ṽ_n(x) = -C̃_n(x)+C̃_n(0)`,

so `sup_x|Ṽ_n(x)-V_n(x)| ≤ 2b_n`, not `b_n`. At a surrogate-game NE where
Q's deviation-to-zero argument gives surrogate utility at least zero, the
true utility at the same allocation is at least `-2b_n`, because only the
valuation at the realized allocation must be transferred between the two
normalized games. Hence the true IR deficit is at most `2b_n`. A generic
two-action approximate-best-response comparison would give the looser
`4b_n` bound.

Exact budget balance at the surrogate NE remains algebraic, subject to Q's
surrogate KKT construction and feasibility conditions.
