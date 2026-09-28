"""Deterministic finite checks for the second-generation claim audit.

No model calls or file writes. These checks supplement, not replace, proofs.
"""
from fractions import Fraction as F
from itertools import combinations, permutations, product
from math import atanh, tanh


def ranking_orders():
    nodes = tuple(range(4))
    pairs = list(combinations(nodes, 2))
    dags = incomparable = 0
    for choices in product((-1, 0, 1), repeat=len(pairs)):
        edges = [(u, v) if choice == 1 else (v, u)
                 for (u, v), choice in zip(pairs, choices) if choice]
        orders = [order for order in permutations(nodes)
                  if all(order.index(u) < order.index(v) for u, v in edges)]
        if not orders:
            continue
        dags += 1
        reach = set(edges)
        for k in nodes:
            for i in nodes:
                for j in nodes:
                    if (i, k) in reach and (k, j) in reach:
                        reach.add((i, j))
        for u, v in pairs:
            signs = {order.index(u) < order.index(v) for order in orders}
            assert (signs == {True}) == ((u, v) in reach)
            assert (signs == {False}) == ((v, u) in reach)
            if len(signs) == 2:
                incomparable += 1
        # All linear extensions admit the same positive edge mean 1/4.
        for order in orders:
            scores = {u: -order.index(u) for u in nodes}
            for u, v in edges:
                gap = scores[u] - scores[v]
                assert gap > 2 * atanh(0.25)
                rate = 0.25 / tanh(gap / 2)
                assert 0 < rate < 1
                assert abs(rate * tanh(gap / 2) - 0.25) < 1e-14
    assert dags == 543
    print(f"Ranking: all {dags} four-vertex DAGs; {incomparable} incomparable pair cases")


def peer_score():
    for w, a, b in product((F(-1, 2), F(0), F(1, 3)), (F(1, 3), F(3, 4)), (F(1, 4), F(2, 3))):
        joint = {(x, y): (1 + x*a*w + y*b*w + x*y*a*b)/4
                 for x, y in product((-1, 1), repeat=2)}
        conditional = {x: {y: joint[x, y]/sum(joint[x, z] for z in (-1, 1))
                           for y in (-1, 1)} for x in (-1, 1)}
        difference = sum(y*(conditional[1][y]-conditional[-1][y]) for y in (-1, 1))
        assert difference == 2*a*b*(1-w*w)/(1-a*a*w*w) > 0
        for true in (-1, 1):
            def expected(report):
                norm = sum(value**2 for value in conditional[report].values())
                return sum(conditional[true][y]*(2*conditional[report][y]-norm) for y in (-1, 1))
            advantage = expected(true)-expected(-true)
            assert advantage == sum((conditional[true][y]-conditional[-true][y])**2 for y in (-1, 1)) > 0
    print("Peer score: conditional-mean formula and strict score gap checked exactly")


def potentials(weights, n):
    out = []
    for start in range(n):
        best = F(0)
        rest = [i for i in range(n) if i != start]
        for length in range(1, n):
            for tail in permutations(rest, length):
                path = (start, *tail)
                best = max(best, sum(weights[a, b] for a, b in zip(path, path[1:])))
        out.append(best)
    assert all(out[a]-out[b] >= weight for (a, b), weight in weights.items())
    return out


def reward_caps():
    n, e, gamma = 3, F(1, 100), F(1, 10)
    reference = [F(0), F(1, 3), F(1)]
    utility = {(a, b): F(0) if a == b else reference[a]-reference[b]-gamma
               for a, b in product(range(n), repeat=2)}
    true = {(a, b): utility[a, b]-utility[a, a]
            for a, b in utility if a != b}
    cap = max(potentials(true, n))
    for errors in product((-e, e), repeat=n*n):
        empirical = {cell: value+error for (cell, value), error in zip(utility.items(), errors)}
        robust = {(a, b): empirical[a, b]-empirical[a, a]+2*e for a, b in true}
        assert all(true[edge] <= value <= true[edge]+4*e for edge, value in robust.items())
        estimated = max(potentials(robust, n))
        assert cap <= estimated <= cap+4*(n-1)*e
    print("Reward cap: 512 confidence-box corners satisfy the claimed bound")


def comparator():
    grid = [F(k, 100) for k in range(-100, 101)]
    local = lambda x: (1+max(1-x, x))/2
    aggregate = lambda x: max(2-x, x)
    xp = min(grid, key=local)
    xa = min(grid, key=aggregate)
    assert xp == F(1, 2) and xa == 1
    assert aggregate(xp)-aggregate(xa) == 2*local(xp)-aggregate(xa) == F(1, 2)
    # The September 11 construction already has distinct local/system optima.
    a = F(1, 3)
    old_local = lambda x: (1-x)*a+x
    old_system = lambda x: (1-x)*a
    assert min((F(0), F(1)), key=old_local) == 0
    assert min((F(0), F(1)), key=old_system) == 1
    print("Comparator: new U/2 witness and historical optimiser mismatch reproduced")


if __name__ == "__main__":
    ranking_orders()
    peer_score()
    reward_caps()
    comparator()
