"""(1) Assumption 5 of Q along price-consensus z for eq40, sweep mu.
(2) weighted monotonicity of eq40 in metric diag(I_x, (N-1)/N I_p), heterogeneous curvature h_n in [alpha, 3 alpha].
(3) Krasnoselskij threshold in tau as valuation curvature h shrinks (payment scale alpha fixed)."""
import numpy as np
from check import family, jacobian, pbr_matrix
rng = np.random.default_rng(1)
alpha = 1.0
for N in [3, 10, 50]:
    a, theta, beta = alpha, alpha/(N-1), alpha*N/(N-1)**2
    A, B, av, zeta = family(N, a, theta, beta, 0.5*N)
    z = np.concatenate([np.zeros(N), np.ones(N)])/np.sqrt(N)
    worst = []
    for mu in [0.5, 1, 1.02*N/(N-1), 2, 5, 20, 100, 1000]:
        J = jacobian(N, A, B, alpha)
        T = pbr_matrix(N, J, mu)
        worst.append((mu, np.linalg.norm(T @ z), np.linalg.norm(T, 2)))
    print(f"N={N} eq40, h=alpha: (mu, ||T z||/||z||, ||T||_2):", [(round(m,3), round(r,4), round(s,4)) for m, r, s in worst])
    # weighted monotonicity with heterogeneous curvature
    w = (N-1)/N
    P = np.diag(np.concatenate([np.ones(N), w*np.ones(N)]))
    mx = -np.inf; mx_eu = -np.inf
    for trial in range(200):
        J = jacobian(N, A, B, alpha)
        h = rng.uniform(alpha, 3*alpha, N)
        J[np.arange(N), np.arange(N)] = -h
        mx = max(mx, np.linalg.eigvalsh(P@J + J.T@P).max())
        mx_eu = max(mx_eu, np.linalg.eigvalsh(J + J.T).max())
    print(f"   max eig over 200 heterogeneous draws: Euclidean J+J^T {mx_eu:.4g}; weighted PJ+J^TP {mx:.3g}")
    # tau threshold for Krasnoselskij spectral radius < 1, mu=1
    for h in [1.0, 0.3, 0.1, 0.03, 0.01]:
        J = jacobian(N, A, B, h)
        M = pbr_matrix(N, J, 1.0) - np.eye(2*N)
        ev = np.linalg.eigvals(M)
        # |1 + tau lam| < 1  iff tau < -2 Re(lam)/|lam|^2 for all lam (Re<0)
        bad = ev[np.abs(ev) > 1e-12]
        tmax = np.min(-2*bad.real/np.abs(bad)**2) if np.all(bad.real < 0) else 0.0
        print(f"   h={h}: largest admissible Krasnoselskij tau (mu=1) = {tmax:.4g}")
