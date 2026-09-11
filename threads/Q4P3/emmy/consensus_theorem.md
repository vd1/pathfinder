# Disagreement cannot discipline same-direction biased agents (emmy)

Status: proof written out below; numerical sanity check in `emmy/check_consensus.py`.

## Setting (Q, "Competition through coupled rewards")

Two agents, state theta in R observed by both, agent i picks a_i, payoff
-(a_i - theta - b_i)^2 + r_i(D), D := a_2 - a_1. Human loss (a_1-theta)^2 + (a_2-theta)^2.
Q's class of rewards: r_i depends only on D (Q's (CR) is of this form). We allow r_i : R -> R u {-inf}.
Write x_i := a_i - theta. Since payoffs depend on theta only through x_i, equilibria in x do not depend on theta.

Bias structure: b_2 = k b_1, b_1 in B = [b_lo, b_hi], L := b_hi - b_lo > 0.
Q assumes f strictly decreasing (k < 0 in the linear case): countervailing biases.
The P-relevant case is k > 0: reviewer and critic are the same model (Claude Sonnet 4.5, P Sec 3),
and P's Case A shows the critic erring in the reviewer's direction.

## Step 1: global best response gives an upper parabola

Fix type b (= b_1) and an equilibrium (x_1(b), x_2(b)), D(b) = x_2 - x_1.
Agent 1 chooses D' given x_2; its payoff is -(x_2 - D' - b)^2 + r_1(D'). Optimality at D(b), with y = D' - D(b):

  r_1(D(b) + y) <= r_1(D(b)) + s(b) y + y^2  for all y,   s(b) := 2(b - x_1(b)).

Agent 2 chooses D' given x_1; payoff -(x_1 + D' - k b)^2 + r_2(D'). Optimality:

  r_2(D(b) + y) <= r_2(D(b)) + sigma(b) y + y^2  for all y,   sigma(b) := 2(x_2(b) - k b).

(No differentiability used; -inf values satisfy the inequalities trivially.)

## Step 2: two types, add the inequalities

For types b, b' with Delta := D(b') - D(b), apply agent 1's inequality at b (y = Delta) and at b' (y = -Delta), add:

  (s(b') - s(b)) Delta <= 2 Delta^2.     Same for agent 2:  (sigma(b') - sigma(b)) Delta <= 2 Delta^2.

## Step 3: near-first-best forces pooling when k > 0

Suppose every type has an equilibrium with |x_i(b)| <= eps. Then |Delta| <= 4 eps,
s(b') - s(b) >= 2(b' - b) - 4 eps, and sigma(b') - sigma(b) <= -2k(b' - b) + 4 eps.

- Agent 1: if Delta > 0 then s(b') - s(b) <= 2 Delta <= 8 eps, so b' - b <= 6 eps. Hence b' - b > 6 eps implies Delta <= 0.
- Agent 2 (k > 0): if Delta < 0 then sigma(b') - sigma(b) >= 2 Delta >= -8 eps, so b' - b <= 6 eps / k. Hence b' - b > 6 eps / k implies Delta >= 0.

With m := 6 eps max(1, 1/k): every pair more than m apart has Delta = 0. If L > 2m, an endpoint argument
(every b is at distance >= L/2 > m from one endpoint, and the endpoints are L > m apart) gives D(b) = D_0 for all b in B,
with |D_0| <= 2 eps. The equilibrium disagreement is type-independent: it reveals nothing about the bias.

For k < 0 both agents require Delta <= 0 (D decreasing in b), which is consistent; Q's (CR) has
D* = eta (k - 1) b_1, decreasing, as required. So no pooling is forced.

## Step 4: pooling implies biased-consensus equilibria

At D_0, the set of slopes s for which r_1(D_0 + y) <= r_1(D_0) + s y + y^2 holds for all y is convex
(the minimum of two linear functions lies below any convex combination). It contains s(b) for every b, hence
[s(b_lo), s(b_hi)], an interval of length >= 2L - 4 eps. Likewise agent 2's valid slopes contain
[sigma(b_hi), sigma(b_lo)], length >= 2kL - 4 eps.

Take type b_hi and shift both actions by a common c (D stays D_0). Agent 1's slope becomes s(b_hi) - 2c and
agent 2's becomes sigma(b_hi) + 2c. Both remain valid, so the shifted profile is still an equilibrium, for every

  c in [0, min(1, k) L - 2 eps].

The largest shift gives a consensus action about theta + min(1,k) L, with human loss >= 2 (min(1,k) L - 2 eps)^2 - O(eps).
For k >= 1 and b_lo = 0 this is consensus at agent 1's own bliss point.

## Statement

Proposition (emmy). In Q's two-agent quadratic environment with b_2 = k b_1 and difference-based rewards r_i(D):
(a) if k < 0, Q's (CR) gives a unique equilibrium with loss eta^2 (b_2 - b_1)^2 / 2 -> 0 (Q, Prop. "Coupled rewards make loss arbitrarily small");
(b) if k = 0, r_2 = 0 and r_1(D) = -K D^2 / 2 gives x_2 = 0, x_1 = 2 b_1 / (2 + K) -> 0 (unique);
(c) if k > 0 (same-direction, clones k = 1 included) and L > 12 eps max(1, 1/k), any mechanism under which every type has
an equilibrium within eps of first best is a pure consensus device (type-independent D) and has, for the extreme type,
a continuum of equilibria reaching loss >= 2 (min(1,k) L - 2 eps)^2. No difference-based mechanism is eps-good in all equilibria.

Reading for P: false consensus is structural for a reviewer and critic whose error tendencies point the same way.
Interaction can only help through a channel other than disagreement-based incentives: countervailing dispositions
(roles that make signed errors negatively correlated), or hard evidence (Q's verification order), which reduces the
designer's uncertainty about theta rather than relying on the agents' incentives.

## Limits (stated, not hidden)

- Rewards depending only on D. With theta ranging over R and state-independent rewards this is the natural class
  (Q's (CR) is in it), but general r_i(a_1, a_2) is not covered by this proof.
- Linear bias curve b_2 = k b_1. The proof uses only monotone co-movement: for a general curve f, the same argument
  goes through with k replaced by the sign of co-movement over pairs far enough apart (to be checked).
- Complete information between agents and a common observed theta, as in Q. P's R and C see the same artifact, so this fits.
- The mapping from LLM verdicts to scalar actions and "biases" is a modelling analogy, not something P measures.

## Lemma: symmetric agreement rewards keep the mean bias

If r_1 = r_2 = rho(D) with rho differentiable at the equilibrium, the first-order conditions are
-2(x_1 - b_1) - rho'(D) = 0 and -2(x_2 - b_2) + rho'(D) = 0. Adding them gives x_1 + x_2 = b_1 + b_2 for every rho,
so human loss >= (x_1 + x_2)^2 / 2 = (b_1 + b_2)^2 / 2 at any penalty strength. Example: rho = -kappa D^2 gives, as
kappa -> inf, the common action theta + (b_1 + b_2)/2. An agreement penalty that treats both agents alike moves them to
consensus at their mean bias, and it helps only when the biases cancel. Q's (CR) avoids this by using r_1 != r_2.
An agreement-terminated reviewer-critic loop treats R and C alike, so the most it can do is average their dispositions.

## Numerical check (emmy/check_consensus.py, run with `uv run --with numpy`)

- Q's (CR), k = -0.5, eta = 0.2, b_1 in {-1, -0.3, 0.4, 1}: the predicted equilibrium passes a global grid best-response
  test, and best-response iteration from 9 starting points converges to it (to within grid step 1e-3): unique, as Q states.
- Same formula at k = 2: the reward's own curvature for agent 1 is r_1'' = 11 > 2, so the second-order condition fails.
- Kink penalty r_i = -5|D| with clones (k = 1) and with k = 0.5: every common action on the tested grid [-1.5, 2.5] is an
  equilibrium, which contains the interval [0, min(1,k)L] from Step 4. This checks Step 4 only. Steps 1-3 rest on the proof.

## Prior work to position against

- Krishna and Morgan (2001), "A Model of Expertise", QJE 116(2):747-775
  (https://faculty.haas.berkeley.edu/rjmorgan/Experts%20Final%20QJE%20Version.pdf). Cheap talk: with like biases a second
  expert gives no gain over the best single-expert equilibrium; with opposing biases a rebuttal stage can yield full
  revelation. The proposition above is the reward-design counterpart for Q's difference-based class. The like-versus-opposing
  point itself is theirs.
- Correlated errors among same-family LLMs: https://arxiv.org/pdf/2506.07962 and https://arxiv.org/abs/2605.29800.
- Queries run: "mechanism design two agents countervailing biases versus same-direction biases collusion consensus
  implementation delegation"; "LLM reviewer critic same model correlated errors false consensus multi-agent debate conformity theory".
  I found no reward-design version of the like-bias impossibility with these queries. That is a record of the search, not a novelty claim.

## General f: the condition is co-movement, not sign

The proof uses b_2 only through sigma(b) = 2(x_2(b) - f(b)). For any strictly increasing f on B:
sigma(b') - sigma(b) <= 4 eps - 2(f(b') - f(b)). Agent 2's step becomes: if Delta < 0 then f(b') - f(b) <= 6 eps.
Let m be such that b' - b > m implies both b' - b > 6 eps and f(b') - f(b) > 6 eps (a modulus exists for continuous
strictly increasing f on compact B). If L > 2m, the endpoint argument gives type-independent D = D_0. Step 4 then gives,
for type b_hi, equilibria with common shift c in [0, min(L, f(b_hi) - f(b_lo)) - 2 eps].

Example: f(b) = b - 1 on B = [0, 1]. The two biases have OPPOSITE signs for every type, yet the impossibility holds,
because they move together across types. Q's (Curve) (f strictly decreasing, f(0) = 0) makes the biases opposite in sign
AND moving in opposite directions across types; only the second property is used. Correct statement: difference-based
discipline reaches near-first-best in a unique equilibrium when biases move in opposite directions across types (Q), and
cannot when they move together. This is a different condition from Krishna and Morgan's "like biases" (a sign condition
on known biases). It lines up with what the correlated-errors literature measures: positive across-item correlation of
two models' signed errors. For P, that is the across-task correlation of R's and C's tendency to over- or under-flag.
