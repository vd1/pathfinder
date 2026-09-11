"""Numerical sanity checks for emmy/consensus_theorem.md.

Environment (Q, coupled rewards): agent i picks deviation x_i = a_i - theta,
payoff -(x_i - b_i)^2 + r_i(D), D = x_2 - x_1, b_2 = k*b_1.
Equilibria are found by grid best responses (global, not FOC-based).
"""
import numpy as np

GRID = np.linspace(-3, 3, 6001)


def best_response_1(x2, b1, r1):
    x1 = GRID
    pay = -(x1 - b1) ** 2 + r1(x2 - x1)
    return x1[np.argmax(pay)], pay.max()


def best_response_2(x1, b2, r2):
    x2 = GRID
    pay = -(x2 - b2) ** 2 + r2(x2 - x1)
    return x2[np.argmax(pay)], pay.max()


def is_equilibrium(x1, x2, b1, b2, r1, r2, tol=1e-6):
    _, p1 = best_response_1(x2, b1, r1)
    _, p2 = best_response_2(x1, b2, r2)
    own1 = -(x1 - b1) ** 2 + r1(np.array([x2 - x1]))[0]
    own2 = -(x2 - b2) ** 2 + r2(np.array([x2 - x1]))[0]
    return own1 >= p1 - tol and own2 >= p2 - tol


def cr_rewards(k, eta):
    # Q's (CR) specialised to f(b)=k b: h(x)=(k-1)x, g(s)=s/(k-1)
    def r1(D):
        return D ** 2 / (eta * (k - 1)) + D ** 2 / 2

    def r2(D):
        return -k * D ** 2 / (eta * (k - 1)) + D ** 2 / 2

    return r1, r2


print("== Q's (CR), countervailing k=-0.5, eta=0.2 ==")
k, eta = -0.5, 0.2
r1, r2 = cr_rewards(k, eta)
for b1 in [-1.0, -0.3, 0.4, 1.0]:
    b2 = k * b1
    x1s, x2s = -eta / 2 * (b2 - b1), eta / 2 * (b2 - b1)
    eq = is_equilibrium(x1s, x2s, b1, b2, r1, r2)
    # uniqueness check: iterate best responses from many starts
    ends = set()
    for s in np.linspace(-2, 2, 9):
        x1, x2 = s, -s
        for _ in range(400):
            x1, _ = best_response_1(x2, b1, r1)
            x2, _ = best_response_2(x1, b2, r2)
        ends.add((round(x1, 3), round(x2, 3)))
    print(f"b1={b1:+.1f}: predicted ({x1s:+.3f},{x2s:+.3f}) eq={eq}; BR-iteration limits={ends}")

print("\n== Same formula with same-direction k=2 (clone-like), eta=0.2: SOC fails ==")
k = 2.0
r1, r2 = cr_rewards(k, eta)
print("agent-1 own curvature from reward r1''=", 2 / (eta * (k - 1)) + 1, "(needs < 2)")

print("\n== Consensus kink r_i(D) = -K|D|, same-direction k=1 (clones), K=5 ==")
K = 5.0
rk = lambda D: -K * np.abs(D)
for b1 in [0.0, 0.5, 1.0]:
    b2 = b1
    commons = [c for c in np.linspace(-1.5, 2.5, 81) if is_equilibrium(c, c, b1, b2, rk, rk)]
    print(f"b1=b2={b1:.1f}: common actions c that are equilibria span [{min(commons):.2f},{max(commons):.2f}]")

print("\n== Consensus kink with k=0.5 over b1 in [0,1]: extreme type b1=1 ==")
k = 0.5
commons = [c for c in np.linspace(-1.5, 2.5, 161) if is_equilibrium(c, c, 1.0, k * 1.0, rk, rk)]
print(f"type b1=1: equilibrium common actions span [{min(commons):.3f},{max(commons):.3f}] (theorem: contains [0, min(1,k)L]=[0,0.5])")
