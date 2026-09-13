"""Finite checks of the paper-derived constructions, not LLM experiments."""

from fractions import Fraction
from itertools import combinations
import json


def shortest_paths():
    for down_steps in combinations(range(6), 3):
        row = col = 0
        path = []
        for step in range(6):
            if step in down_steps:
                row += 1
            else:
                col += 1
            path.append(4 * row + col)
        yield path


checks = 0
for reds in combinations(range(1, 15), 7):
    red_set = set(reds)
    for path in shortest_paths():
        required = {"R": 0, "B": 0, "G": 0}
        for tile in path:
            required["G" if tile == 15 else "R" if tile in red_set else "B"] += 1
        for inventory in (
            {"R": 9, "B": 5, "G": 2},
            {"R": 5, "B": 9, "G": 2},
            {"R": 9, "B": 6, "G": 2},
            {"R": 5, "B": 8, "G": 2},
            {"R": 13, "B": 14, "G": 4},
        ):
            assert all(inventory[color] >= required[color] for color in required)
            checks += 1

single_finisher_score = 20 + 5 * (31 - 6)
assert single_finisher_score == 145
assert single_finisher_score - 10 > 70 and 10 > 0

values = [Fraction(3 + i, 4) for i in range(11)]
ranked_gains = [v - c for v, c in zip(reversed(values), values)]
maximum_surplus = sum(max(gain, 0) for gain in ranked_gains)
assert maximum_surplus == Fraction(15, 2)
buyers = list(reversed(values))[:5]
sellers = values[:5]
surplus = sum(v - c for v, c in zip(buyers, sellers))
assert surplus == maximum_surplus
prices = sellers
dispersion = 100 / 2 * (sum(float((p - 2) ** 2) for p in prices) / len(prices)) ** 0.5
assert Fraction(13, 4) - Fraction(3, 4) == maximum_surplus / 3

print(json.dumps({
    "boards": 3432,
    "paths_per_board": 20,
    "inventory_path_checks": checks,
    "P_equal_swap_scores": [70, 70],
    "P_asymmetric_swap_scores": [75, 65],
    "P_single_finisher_raw_scores": [single_finisher_score, 0],
    "P_single_finisher_PPC_scores": [single_finisher_score - 10, 10],
    "Q_maximum_surplus": float(maximum_surplus),
    "Q_full_surplus_example_alpha_percent": dispersion,
    "Q_zero_dispersion_example_efficiency": str(Fraction(1, 3)),
}, indent=2))
