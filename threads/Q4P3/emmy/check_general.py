# Checks for emmy ledger entries after #12. Run: uv run --with numpy python emmy/check_general.py
from fractions import Fraction as F
import numpy as np

# ---- 1. Q's binary peer-discipline example (Q, "A binary state") ----
# On path the payoff is Lambda*q(report_i, report_j): the -a_i term cancels u_i = a_i.
q = {('H', 'H'): F(7, 9), ('H', 'L'): F(1, 9), ('L', 'H'): F(1), ('L', 'L'): F(-1)}
def score(rep, pH):  # partner reports H with prob pH, independent of own type
    return pH * q[(rep, 'H')] + (1 - pH) * q[(rep, 'L')]
# (a) ada #8: symmetric babbling, both mix 5/6 on H
p = F(5, 6)
print("babbling p=5/6: H", score('H', p), " L", score('L', p))
# (b) asymmetric pure pooling: agent 1 always H, agent 2 always L
print("agent1 vs always-L partner: H", score('H', 0), " L", score('L', 0), "-> H is BR")
print("agent2 vs always-H partner: H", score('H', 1), " L", score('L', 1), "-> L is BR")
# Human payoff: common action a*=1 iff reports (H,H); theta independent of reports in both profiles
print("human payoff: babbling", p * p * F(1, 2) + (1 - p * p) * F(1, 2), " asym pooling", F(1, 2))
# Ex-ante agent scores. Truthful: P(type H)=3/4, H-type 5/9, L-type 1 (Q's numbers)
print("ex-ante score truthful", F(3, 4) * F(5, 9) + F(1, 4) * 1,
      " babbling", score('H', p), " asym pooling (agent1, agent2)", (score('H', 0), score('L', 1)))

# ---- 2. Linear-quadratic class: any quadratic state-independent rewards r_i(a1, a2) ----
# Best responses a_i = c_i t_i + rho_i a_j + d_i with c_i = 2/(2 - r_i,ii) > 0 (SOC), rho_i any real.
# t_1 = theta + b, t_2 = theta + k b. Equilibrium loadings on theta (L_i) and on b (beta_i).
# Identity: (beta_1 - k L_1)(L_2 - beta_2) = (1-k)^2 c_1 c_2 / Delta^2 >= 0, Delta = 1 - rho_1 rho_2.
rng = np.random.default_rng(0)
worst = {}
for _ in range(200000):
    c1, c2 = np.exp(rng.normal(0, 2, 2))
    r1, r2 = rng.normal(0, 3, 2)
    k = rng.choice([-1.0, -0.5, 0.25, 0.5, 0.9, 1.0, 1.5, 3.0])
    Dl = 1 - r1 * r2
    if abs(Dl) < 1e-6:
        continue
    L1 = (c1 + r1 * c2) / Dl; b1 = (c1 + k * r1 * c2) / Dl
    L2 = (c2 + r2 * c1) / Dl; b2 = (k * c2 + r2 * c1) / Dl
    lhs = (b1 - k * L1) * (L2 - b2); rhs = (1 - k) ** 2 * c1 * c2 / Dl ** 2
    assert abs(lhs - rhs) <= 1e-8 * max(1, abs(rhs)), (lhs, rhs)
# Bounded loss over theta in R forces L_1 = L_2 = 1, whose only solution is rho_i = 1 - c_i
# (the D-only quadratic class: c_i = 1/(1+kappa_i), kappa_i > -1). Then
# beta_1 = (c1 + k(1-c1)c2)/Delta, beta_2 = (k c2 + (1-c2)c1)/Delta, Delta = c1 + c2 - c1 c2.
def betas(c1, c2, k):
    Dl = c1 + c2 - c1 * c2
    return (c1 + k * (1 - c1) * c2) / Dl, (k * c2 + (1 - c2) * c1) / Dl, Dl
for k in [-0.5, 0.25, 0.5, 0.9, 1.5, 3.0]:
    best, best_R, best_R_conf = np.inf, np.inf, np.inf
    for _ in range(400000):
        c1, c2 = np.exp(rng.normal(0, 3, 2))
        b1, b2, Dl = betas(c1, c2, k)
        if abs(Dl) < 1e-9:
            continue
        best = min(best, max(abs(b1), abs(b2)))
        best_R = min(best_R, abs(b1))
        if c1 <= 1:  # R agreement-seeking: kappa_R >= 0
            best_R_conf = min(best_R_conf, abs(b1))
    print(f"k={k:5}: min max|beta_i| = {best:.4f} (bound {min(k,1) if k>0 else 0});"
          f" min |beta_R| = {best_R:.4f}; min |beta_R| with kappa_R>=0 = {best_R_conf:.4f}"
          f" (bound {min(k,1) if k>0 else 0})")
# Example: k = 0.5, kappa_R = -0.5, kappa_C = -0.75 (both rewarded for disagreement): c1 = 2, c2 = 4
print("example k=0.5, c1=2, c2=4 -> (beta_R, beta_C, Delta) =", betas(2.0, 4.0, 0.5))
