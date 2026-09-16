"""Numerical checks of Q's quadratic payment family (K=1, quadratic valuations).

Family (eq40 is a=alpha, theta=alpha/(N-1), beta=alpha N/(N-1)^2):
  A^n_nn=a, A^n_nm=A^n_mn=-a/(N-1), A^n_mm=a/(N-1) (m!=n), else 0
  B^n_nl=-theta (all l), B^n_mn=beta (m!=n), B^n_mm=-theta/(N-1) (m!=n), else 0
  a^n_n=theta c, a^n_m=-zeta c/(N(N-1)) (m!=n), zeta=-theta+(N-1) beta
Payment t_n = 1/2 p'A^n p + p'B^n x + p'a^n.  V_n(x)=-h/2 (x-xt_n)^2 + h/2 xt_n^2.
"""
import numpy as np

np.set_printoptions(precision=4, suppress=True)


def family(N, a, theta, beta, c):
    zeta = -theta + (N - 1) * beta
    A = np.zeros((N, N, N)); B = np.zeros((N, N, N)); av = np.zeros((N, N))
    for n in range(N):
        for m in range(N):
            if m == n:
                A[n, n, n] = a
                av[n, n] = theta * c
            else:
                A[n, n, m] = A[n, m, n] = -a / (N - 1)
                A[n, m, m] = a / (N - 1)
                B[n, m, n] = beta
                B[n, m, m] = -theta / (N - 1)
                av[n, m] = -zeta * c / (N * (N - 1))
            B[n, n, m] = -theta
    return A, B, av, zeta


def jacobian(N, A, B, h):
    # s = (x_1..x_N, p_1..p_N); F_n = (dU_n/dx_n, dU_n/dp_n)
    J = np.zeros((2 * N, 2 * N))
    for n in range(N):
        J[n, n] = -h
        for m in range(N):
            J[n, N + m] = -B[n, m, n]        # d/dp_m of (grad V_n - sum_m B^n_mn p_m)
            J[N + n, N + m] = -A[n, n, m]
            J[N + n, m] = -B[n, n, m]
    return J


def lmi_checks(N, A, B, h, zeta, theta):
    J = jacobian(N, A, B, h)
    S = J + J.T
    ev = np.linalg.eigvalsh(S)
    return J, ev.min(), ev.max()


def ne_and_budget(N, A, B, av, zeta, h, c, rng):
    xt = rng.uniform(1.0, 2.0, N)
    lam = h * (xt.sum() - c) / N
    assert lam > 0
    x = xt - lam / h
    p = np.full(N, lam / zeta)
    # pseudogradient residual at candidate NE (interior)
    F = np.zeros(2 * N)
    for n in range(N):
        F[n] = -h * (x[n] - xt[n]) - B[n, :, n] @ p
        F[N + n] = -(A[n, n, :] @ p) - B[n, n, :] @ x - av[n, n]
    t = np.array([0.5 * p @ A[n] @ p + p @ B[n] @ x + p @ av[n] for n in range(N)])
    V = -h / 2 * (x - xt) ** 2 + h / 2 * xt ** 2
    return np.abs(F).max(), t.sum(), (V - t).min(), lam


def pbr_matrix(N, J, mu):
    # T(s) = (mu I - D)^{-1} (mu I + O) s + const for the unconstrained PBR
    D = np.zeros_like(J)
    for n in range(N):
        idx = [n, N + n]
        D[np.ix_(idx, idx)] = J[np.ix_(idx, idx)]
    O = J - D
    return np.linalg.solve(mu * np.eye(2 * N) - D, mu * np.eye(2 * N) + O)


rng = np.random.default_rng(0)
for label, N, h, mu in [("Q sim scale", 50, 0.8, 1.0), ("small", 3, 1.0, 1.0), ("small, mu big", 3, 1.0, 3.0)]:
    alpha = h
    c = 0.5 * N
    designs = {
        "eq40": (alpha, alpha / (N - 1), alpha * N / (N - 1) ** 2),
    }
    th = alpha * np.sqrt((N - 1) / N) * 0.99
    designs["skew (zeta=N theta)"] = (alpha, th, (N + 1) * th / (N - 1))
    print(f"=== {label}: N={N}, h=alpha={h}, mu={mu}")
    for name, (a, theta, beta) in designs.items():
        A, B, av, zeta = family(N, a, theta, beta, c)
        J, emin, emax = lmi_checks(N, A, B, h, zeta, theta)
        res, tsum, umin, lam = ne_and_budget(N, A, B, av, zeta, h, c, rng)
        Tm = pbr_matrix(N, J, mu)
        tau = 0.2
        Fm = (1 - tau) * np.eye(2 * N) + tau * Tm
        eJ = np.linalg.eigvals(J)
        print(f"  {name}: zeta={zeta:.4f} theta={theta:.4f}")
        print(f"    eig(J+J^T) in [{emin:.4g}, {emax:.4g}]  (P1(ii) needs max<0)")
        print(f"    max Re eig(J)={eJ.real.max():.4g}, max |Im|/|Re| on eigs={np.max(np.abs(eJ.imag)/np.abs(eJ.real)):.3f}")
        print(f"    NE residual={res:.2e}, sum t_n at NE={tsum:.2e}, min U_n={umin:.4g}")
        print(f"    PBR ||T||_2={np.linalg.norm(Tm, 2):.4f}, rho(T)={np.abs(np.linalg.eigvals(Tm)).max():.4f}, rho(Krasnoselskij tau=.2)={np.abs(np.linalg.eigvals(Fm)).max():.4f}")
    # loss of strong concavity: h -> 0 with eq40 structure (payment scale kept at alpha)
    for hh in [0.1, 0.01, 0.0]:
        a, theta, beta = designs["eq40"]
        A, B, av, zeta = family(N, a, theta, beta, c)
        J = jacobian(N, A, B, hh)
        eJ = np.linalg.eigvals(J)
        Tm = pbr_matrix(N, J, mu)
        Fm = 0.8 * np.eye(2 * N) + 0.2 * Tm
        Ps = np.array([[hh, -theta], [-theta, a]])
        print(f"  eq40 payment, valuation curvature h={hh}: min eig Psi_nn-block PSD test={np.linalg.eigvalsh(Ps).min():.4g}, max Re eig(J)={eJ.real.max():.4g}, rho(Krasnoselskij)={np.abs(np.linalg.eigvals(Fm)).max():.5f}, ||T||={np.linalg.norm(Tm,2):.4f}")
