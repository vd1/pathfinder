# Uniform bound for P's fixed-batch surrogate

Fix an agent and suppress its index. Let the loss satisfy P's Assumption 3:
for every feasible `x`, `|J(x,ξ)| ≤ U`, and let the risk level be
`α ∈ (0,1)`. For a batch of size `s`, write `Ĉ_s(z)` for its empirical CVaR
and `C(z)` for the population CVaR. P defines the deterministic surrogate

`C̃(x) = E_{ν,batch}[Ĉ_s(x + δν)]`, with `ν` uniform on the unit ball,

for `x ∈ X_δ`. Its shrunken-domain construction ensures
`x + δν ∈ X` (P, lines 480-489).

For each fixed `z ∈ X`, P's CVaR stability lemma (lines 1287-1295) and the
DKW calculation in its proof (lines 1297-1308) give

`E_batch |Ĉ_s(z) - C(z)| ≤ (2U/α) sqrt(π/(2s))`

`= (U/α) sqrt(2π/s)`.

The right side is independent of `z`. No uniform empirical-process bound
over the decision class is needed because P's surrogate takes the batch
expectation separately at every `z`. Define

`b := Lδ + (U/α) sqrt(2π/s)`.

Using Jensen's inequality, Tonelli's theorem, and P's smoothing lemma
`|E_ν C(x+δν)-C(x)| ≤ Lδ` (lines 503-508), for every `x ∈ X_δ`,

`|C̃(x)-C(x)|`

`≤ E_ν |E_batch Ĉ_s(x+δν)-C(x+δν)|`

`  + |E_ν C(x+δν)-C(x)|`

`≤ (U/α) sqrt(2π/s) + Lδ = b`.

Consequently,

`sup_{x∈X_δ}|C̃(x)-C(x)| ≤ b`.

This is a deterministic uniform bound under P's stated boundedness and
Lipschitz assumptions. Convexity is not needed for this approximation
step, though it is needed for P's optimization theorem.

For agents `n`, let `B = Σ_n b_n`. If `x*` minimizes `Σ_n C_n` and `x̃`
minimizes `Σ_n C̃_n` on the same feasible set, then

`Σ_n C_n(x̃)-Σ_n C_n(x*) ≤ 2B`.

If `Σ_n C_n` is `ρ`-strongly convex, then

`||x̃-x*|| ≤ 2 sqrt(B/ρ)`.

The same-feasible-set qualification matters: P optimizes over `X_δ`, so
comparison with an optimizer over the original `X` also needs a domain
shrinkage term or an assumption that the true optimizer belongs to
`X_δ`.

For Q's individual-rationality normalization, define
`V_n(x)=-C_n(x)+C_n(0)` and
`Ṽ_n(x)=-C̃_n(x)+C̃_n(0)`. Then `V_n(0)=Ṽ_n(0)=0` and
`sup_x |V_n(x)-Ṽ_n(x)| ≤ 2b_n`. At a surrogate equilibrium whose Q-style
payment gives nonnegative surrogate utility, the true utility is therefore
at least `-2b_n`. This anchored comparison costs `2b_n`, not `4b_n`, because
the true and surrogate valuations agree exactly at the normalized outside
option `x=0`.

Thus the corrected fixed-parameter claim is: exact budget balance at the
surrogate equilibrium, true welfare loss at most `2B`, allocation distance
at most `2 sqrt(B/ρ)`, and true IR deficit at most `2b_n`, subject to a common
feasible set and Q's mechanism conditions for the surrogate game.
