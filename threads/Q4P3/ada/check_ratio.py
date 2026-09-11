# Checks for ada notes sec 7. Run: uv run --with sympy --with numpy python ada/check_ratio.py
import numpy as np
import sympy as sp

c1, c2, k, k0, b, th, rho1, rho2 = sp.symbols('c1 c2 k k0 b theta rho1 rho2', real=True)

# ---- 1. emmy general_rewards.md sec 1 identity, general linear best responses ----
tR, tC = th + b, th + k * b
aR, aC = sp.symbols('aR aC')
sol = sp.solve([aR - (c1 * tR + rho1 * aC), aC - (c2 * tC + rho2 * aR)], [aR, aC], dict=True)[0]
L1 = sp.diff(sol[aR], th); B1 = sp.diff(sol[aR], b)
L2 = sp.diff(sol[aC], th); B2 = sp.diff(sol[aC], b)
Dl = 1 - rho1 * rho2
print("emmy identity holds:",
      sp.simplify((B1 - k * L1) * (L2 - B2) - (1 - k) ** 2 * c1 * c2 / Dl ** 2) == 0)

# ---- 2. D-only quadratic class (rho_i = 1 - c_i): R's output is an affine combination ----
s = {rho1: 1 - c1, rho2: 1 - c2}
xR = sp.simplify(sol[aR].subs(s) - th)
A = c1 / (c1 + c2 - c1 * c2)
print("x_R = A b_R + (1-A) b_C:", sp.simplify(xR - (A * b + (1 - A) * k * b)) == 0)
# A < 0  <=>  c1 + c2 - c1 c2 < 0  <=>  (c1-1)(c2-1) > 1 = rho1*rho2 > 1
print("Delta = 1 - (c1-1)(c2-1):", sp.expand(c1 + c2 - c1 * c2 - (1 - (c1 - 1) * (c2 - 1))) == 0)

# ---- 3. Sensitivity: design with beta_R(k0) = 0 has A = -k0/(1-k0) ----
Astar = -k0 / (1 - k0)
betaR = k + Astar * (1 - k)
print("beta_R(k) under k0-design = (k-k0)/(1-k0):", sp.simplify(betaR - (k - k0) / (1 - k0)) == 0)

# Minimax over unknown ratio k in [klo, khi], khi < 1: beta_R(k) = 1 - sgap*(1-k), sgap = 1 - A free
for klo, khi in [(0.5, 0.99), (0.7, 0.9), (0.8, 0.95), (-2.0, -0.5), (0.2, 0.4)]:
    grid = np.linspace(-50, 50, 2000001)
    val = np.maximum(np.abs(1 - grid * (1 - klo)), np.abs(1 - grid * (1 - khi))).min()
    print(f"k in [{klo},{khi}]: numeric minimax |beta_R| = {val:.4f},"
          f" formula (khi-klo)/((1-klo)+(1-khi)) = {(khi-klo)/((1-klo)+(1-khi)):.4f}")

# ---- 4. Stability of the de-biasing equilibrium under alternating best responses ----
def alt_br(c1v, c2v, kv, n=40, bv=1.0):
    a_R, a_C = bv, kv * bv  # start from own bliss points (theta = 0)
    for _ in range(n):
        a_R = c1v * bv + (1 - c1v) * a_C
        a_C = c2v * kv * bv + (1 - c2v) * a_R
    return a_R, a_C
print("emmy example k=0.5, c1=2, c2=4 (eq x_R=0, x_C=2b); 40 alternating rounds:", alt_br(2, 4, 0.5))
# k=2 (C more biased): c2=1 (C states its bliss), c1=k/(k-1)=2 -> a_R = 2 t_R - t_C
print("k=2, c1=2, c2=1; 40 rounds:", alt_br(2, 1, 2.0))
# random search: any exact de-biasing design with 0<k<1 must have (c1-1)(c2-1) > 1
rng = np.random.default_rng(1)
bad = 0
for _ in range(200000):
    kv = rng.uniform(0.01, 0.99); c2v = np.exp(rng.normal(0, 2))
    if kv * c2v <= 1:
        continue  # emmy: beta_R = 0 reachable iff k c2 > 1, then c1 = k c2/(k c2 - 1)
    c1v = kv * c2v / (kv * c2v - 1)
    bad += (c1v - 1) * (c2v - 1) <= 1 + 1e-12
print("de-biasing designs with 0<k<1 and stable alternating BR:", bad)

# ---- 5. Identification bound, unknown ratio, game-measurable selection ----
# types (theta, b, k), b in [0,B], k in [klo,khi]; (b1,klo) and (B,khi) with the same (t_R, t_C)
B, klo, khi = sp.symbols('B klo khi', positive=True)
b1 = B * (1 - khi) / (1 - klo)
print("same profile:", sp.simplify((klo - 1) * b1 - (khi - 1) * B) == 0,
      "; theta gap =", sp.simplify(B - b1))
