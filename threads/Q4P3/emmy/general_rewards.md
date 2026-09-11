# Beyond r_i(D): quadratic rewards, output = R only, and exact clones (emmy)

Checks: `uv run --with numpy python emmy/check_general.py`.

Setting as in `consensus_theorem.md`: x_i = a_i - theta, bliss points t_1 = theta + b, t_2 = theta + k b,
state-independent rewards (Q's cell "exact action measure, no state measure"). Agent 1 = R, agent 2 = C.

## 1. Any quadratic state-independent rewards r_i(a_1, a_2)

Best responses are a_i = c_i t_i + rho_i a_j + d_i, with c_i = 2/(2 - r_i,ii) > 0 by the second-order condition
and rho_i any real number. With Delta = 1 - rho_1 rho_2 != 0 (unique equilibrium), write L_i and beta_i for the
equilibrium loadings of a_i on theta and on b. Direct algebra gives the identity

  (beta_1 - k L_1)(L_2 - beta_2) = (1 - k)^2 c_1 c_2 / Delta^2 >= 0.

Bounded loss over theta in R forces L_1 = L_2 = 1, and the only solution is rho_i = 1 - c_i, which is exactly
the quadratic difference-based class (c_i = 1/(1 + kappa_i), kappa_i > -1). So going from r_i(D) to general
quadratic r_i(a_1, a_2) adds nothing. With L_i = 1 the identity reads (beta_1 - k)(1 - beta_2) >= 0, so for k > 0
either beta_1 >= k or beta_2 >= 1. Hence max(|beta_1|, |beta_2|) >= min(k, 1), and the worst-case loss over an
interval of biases of length L is at least (min(k,1) L / 2)^2. The bound is tight (c_1 -> 0: R copies C).
Intuition: in equilibrium each agent's action loads on its own bliss point with sign c_i / Delta, the same sign
for both agents. Recovering theta = (t_2 - k t_1)/(1 - k) needs opposite signs when k > 0.
For k < 0 no contradiction arises (Q's (CR) sits here).

## 2. The P objective: only R's output counts

In P, M edits from R's consistent review (P Fig. 1, "Review_k is the consistent review"). C's own position is
not the output. In the linear class,

  beta_R = (c_1 + k (1 - c_1) c_2) / (c_1 + (1 - c_1) c_2).

- If R seeks agreement (kappa_R >= 0, so c_1 <= 1), beta_R is a weighted average of 1 and k with weights c_1
  and (1 - c_1) c_2, whatever C's reward. So |beta_R| >= min(1, k): R's output is never less biased than the
  less biased agent alone. This covers ada's closed form (#7) and the conformity-weighted limit (#10 part 2).
- beta_R = 0 is reachable, in a unique equilibrium, iff k c_2 > 1 with c_1 = k c_2/(k c_2 - 1) > 1. Then
  kappa_R < 0: R is rewarded for DISagreeing with C and extrapolates away from C's position. C's equilibrium
  error is beta_C = k c_2 > 1: C overshoots the common bias. Example k = 0.5, r_R = +0.5 D^2,
  r_C = +0.75 D^2: FOCs give x_1 = 2b - x_2 and x_2 = 2b - 3 x_1, so x_R = 0 and x_C = 2b (unique;
  own curvatures -1 and -0.5).

General (nonlinear) D-only version, output = R only, k > 0, |x_R(b)| <= eps for all b. ada's exact inequality (#7)
for R, with u = x_C(b) - x_C(b') and v = b - b' > 0, gives u(u - v) >= -O(eps); C's gives u >= -O(eps). So
across types C's position is either flat or rises at least one for one with R's bias. If R's reward r_R is
concave (every agreement-seeking reward: -kappa D^2, -kappa |D|, and "terminate on agreement" as a 0/-inf
indicator), its supergradients decrease in D, while R's optimality needs a supergradient near 2b at D(b). So D
is nonincreasing in b; with C's condition it is constant. That is pooling, and Step 4 of `consensus_theorem.md`
then gives biased-consensus equilibria with R's error up to min(1, k) L. Escaping requires r_R convex on the
equilibrium range of D, meaning R is rewarded for disagreeing, and C's position must move with the bias at
least one for one.

Reading for P (an analogy, not measured): P's loop is named adversarial but rewards agreement (it terminates
on AGREE; Case B, C gives in). With co-moving dispositions, a scheme that rewards agreement cannot de-bias
R's output. The model's alternative is a contrarian R that reads C's position as an amplified signal of the
shared bias and moves away from it, paired with a critic whose objections exaggerate that bias.

## 3. Exact clones: impossible under every state-independent mechanism

If k = 1, both agents' preferences depend on (theta, b) only through t = theta + b. Any mechanism without a
state measure (messages, several stages, arbitrary rewards) therefore induces the same game for types
(theta, b) and (theta + c, b - c). Its equilibrium set depends on t alone, and even the best equilibrium
has worst-case error >= L/2, which is what one agent alone gets. In the identity of section 1, k = 1 forces
beta_i = L_i.

## 4. Correction to my conjecture (a) in ledger #5

I had conjectured that Maskin-style report matching also fails when the biases co-move. I withdraw it. For
k != 1 the preference profile (t_1, t_2) identifies theta, rewards act like transfers, and single-crossing
preferences separate distinct profiles, so Maskin monotonicity holds. With two agents, Nash implementation needs
more (Dutta and Sen 1991, https://academic.oup.com/restud/article-abstract/58/1/121/1518953), but
subgame-perfect implementation with transfers covers almost any rule, even with two agents (Moore and Repullo
1988, https://www.econometricsociety.org/publications/econometrica/1988/09/01/subgame-perfect-implementation).
I have not built such a mechanism for this environment. The co-movement impossibility is therefore a statement
about difference-based and linear schemes, which are the P-relevant ones. The only impossibility that holds
for every mechanism is k = 1.
