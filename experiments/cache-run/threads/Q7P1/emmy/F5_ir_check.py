"""emmy F5: is payment (40) individually rational?  K=1.  Q P4(ii) needs sum_m a^n_m <= 0;
for (40) a^n_n = alpha c/(N-1), a^n_m = -alpha c/(N(N-1)), sum = alpha c/(N(N-1)) > 0.
Claim: t_n(s*) = alpha k_N p~ (x_n^o - c/N), k_N = N/(N-1) + 1/(N-1)^2, so IR can fail when one agent
takes more than c (N^2-N+1)/N^2 of the capacity.  Check with near-linear valuations V_n = beta_n x - (h/2) x^2."""
import numpy as np


def t40(n, x, p, al, c):
    N = len(x)
    pb = p.sum() - p[n]; xb = x.sum() - x[n]
    sp = (p**2).sum() - p[n]**2; spx = (p*x).sum() - p[n]*x[n]
    return al*(0.5*p[n]*(p[n] - 2*pb/(N-1)) - p[n]*(x[n] + xb - c)/(N-1) + N*pb*(x[n] - c/N)/(N-1)**2
               + sp/(2*(N-1)) - (spx - pb*c/N)/(N-1)**2)


def best_response_gap(n, x, p, beta, h, al, c, X):
    """max over (x_n,p_n) in [0,X]x[0,50] of U_n minus U_n at the candidate; dense grid + local refine."""
    def U(xn, pn):
        xx = x.copy(); pp = p.copy(); xx[n] = xn; pp[n] = pn
        return beta[n]*xn - 0.5*h*xn**2 - t40(n, xx, pp, al, c)
    u0 = U(x[n], p[n])
    gx = np.linspace(0, X, 801); gp = np.linspace(0, 3*p[n] + 1, 801)
    best = max(U(a, bb) for a in gx[::8] for bb in gp[::8])
    return best - u0, u0


for N in [2, 3, 5]:
    al = h = 0.05; c = 1.0; X = 2.0; lam = 1.0
    share = 0.92
    x = np.full(N, (1 - share)/(N - 1)); x[0] = share
    beta = lam + h*x                      # makes x the welfare optimum with multiplier lam, sum x = c
    p = np.full(N, lam/al)
    kN = N/(N-1) + 1/(N-1)**2
    t = np.array([t40(n, x, p, al, c) for n in range(N)])
    Uv = beta*x - 0.5*h*x**2 - t
    gap, _ = best_response_gap(0, x, p, beta, h, al, c, X)
    print(f"N={N}: x={np.round(x,3)}, t={np.round(t,4)}, formula alpha k_N p (x-c/N)={np.round(al*kN*p*(x-c/N),4)}, sum t={t.sum():.2e}")
    print(f"      U={np.round(Uv,4)}  IR threshold share c(N^2-N+1)/N^2={(N*N-N+1)/N**2:.3f}; grid best-response gain of agent 0 = {gap:.2e}")
