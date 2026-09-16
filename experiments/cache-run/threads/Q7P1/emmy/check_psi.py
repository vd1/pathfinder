"""Check Q's payment (40): monotonicity of the pseudo-gradient, P1(ii), and PBR/KM behaviour.

Scalar resources (K=1), agent strategy s_n = (x_n, p_n).
U_n = V_n(x_n) - t_n with V_n'' = -a (worst case allowed by Assumption 2 of Q).
"""
import numpy as np


def jacobian_eq40(N, a=1.0, alpha=1.0, theta=None, zeta=None):
    """Jacobian of the pseudo-gradient G = col(grad_{s_n} U_n) for payment (40).

    Coefficients are generalised: t_n contains
      alpha*[ 1/2 p_n^2 - p_n pbar_{-n}/(N-1) - theta p_n (x_n + xbar_{-n} - c) + beta pbar_{-n} x_n ]
    with (40) given by theta = 1/(N-1), beta = N/(N-1)^2, so that
      zeta := sum_m B^n_{mn} = -theta + (N-1) beta.
    """
    if theta is None:
        theta = 1.0 / (N - 1)
    beta = N / (N - 1) ** 2 if zeta is None else (zeta + theta) / (N - 1)
    J = np.zeros((2 * N, 2 * N))
    X = lambda n: 2 * n
    P = lambda n: 2 * n + 1
    for n in range(N):
        # grad_x U_n = V_n'(x_n) + alpha*(theta p_n - beta pbar_{-n})
        J[X(n), X(n)] = -a
        J[X(n), P(n)] = alpha * theta
        # grad_p U_n = alpha*(-p_n + pbar_{-n}/(N-1) + theta (x_n + xbar_{-n} - c))
        J[P(n), P(n)] = -alpha
        J[P(n), X(n)] = alpha * theta
        for m in range(N):
            if m == n:
                continue
            J[X(n), P(m)] = -alpha * beta
            J[P(n), P(m)] = alpha / (N - 1)
            J[P(n), X(m)] = alpha * theta
    return J


def report(N, **kw):
    J = jacobian_eq40(N, **kw)
    S = J + J.T
    ev = np.linalg.eigvalsh(S)
    z = np.zeros(2 * N)
    z[1::2] = 1.0  # price-consensus direction
    eigJ = np.linalg.eigvals(J)
    return ev.max(), z @ S @ z, eigJ.real.max()


if __name__ == "__main__":
    print("payment (40): N, lambda_max(J+J^T), z^T(J+J^T)z on price consensus, max Re eig(J)")
    for N in [2, 3, 5, 10, 50]:
        print(N, *[f"{v:+.4f}" for v in report(N)])
    print("\nmodified zeta = N*theta (theta=1/(N-1)) :")
    for N in [2, 3, 5, 10, 50]:
        th = 1.0 / (N - 1)
        print(N, *[f"{v:+.4f}" for v in report(N, theta=th, zeta=N * th)])
    print("\nmodified theta = zeta/N with zeta = 1 :")
    for N in [2, 3, 5, 10, 50]:
        print(N, *[f"{v:+.4f}" for v in report(N, theta=1.0 / N, zeta=1.0)])
    # general LMI claim: any Psi with sum_m A^n_{nm} = 0 has z^T Psi z = 0 on price consensus
    rng = np.random.default_rng(0)
    N = 4
    worst = 0.0
    for _ in range(200):
        Psi = rng.normal(size=(2 * N, 2 * N))
        # impose p-p row sums of agent n's own row zero: sum_m Psi[P(n), P(m)] = 0
        for n in range(N):
            row = [2 * m + 1 for m in range(N)]
            Psi[2 * n + 1, row] -= Psi[2 * n + 1, row].mean()
        z = np.zeros(2 * N)
        z[1::2] = rng.normal()
        worst = max(worst, abs(z @ Psi @ z))
    print("\nrandom Psi with P2(i): max |z^T Psi z| on price consensus =", worst)
