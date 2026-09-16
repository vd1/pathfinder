"""Q Assumption 5 (nonexpansive proximal best response) and KM step, payment (40), interior linearisation.

Agent n PBR: (mu I - J_nn) z = mu s_n + sum_{m != n} J_nm s_m + const,
so the linear part of T is L = (mu I - D)^{-1} (mu I + (J - D)), D = blockdiag(J_nn).
KM map: (1 - tau) I + tau L.
Also tests the modified payment theta = zeta / N (zeta = 1), monotone but not strictly.
"""
import numpy as np
from check_psi import jacobian_eq40


def pbr_linear(J, N, mu):
    D = np.zeros_like(J)
    for n in range(N):
        D[2 * n:2 * n + 2, 2 * n:2 * n + 2] = J[2 * n:2 * n + 2, 2 * n:2 * n + 2]
    I = np.eye(2 * N)
    return np.linalg.solve(mu * I - D, mu * I + (J - D))


def stats(J, N, mu, tau):
    L = pbr_linear(J, N, mu)
    norm = np.linalg.norm(L, 2)
    rho = max(abs(np.linalg.eigvals(L)))
    KM = (1 - tau) * np.eye(2 * N) + tau * L
    rho_km = max(abs(np.linalg.eigvals(KM)))
    return norm, rho, rho_km


if __name__ == "__main__":
    for label, kw in [("(40)", {}), ("theta=1/N", {"theta": None})]:
        print(label, ": N, a, mu, ||L||_2, rho(L), rho(KM tau=0.2)")
        for N in [3, 10, 50]:
            for a in [0.8, 1.0, 3.0]:
                for mu in [1.0, N / (N - 1), 5.0]:
                    if label == "(40)":
                        J = jacobian_eq40(N, a=a, alpha=0.8)
                    else:
                        J = jacobian_eq40(N, a=a, alpha=0.8, theta=1.0 / N, zeta=1.0)
                    n2, r, rk = stats(J, N, mu, 0.2)
                    print(f"  {N:3d} {a:4.1f} {mu:5.2f}  {n2:.4f}  {r:.4f}  {rk:.6f}")
