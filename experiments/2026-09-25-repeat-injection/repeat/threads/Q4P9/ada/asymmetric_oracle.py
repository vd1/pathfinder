"""Enumerate CT-Bench asymmetric boards and a points-contract witness."""

from collections import Counter
from itertools import combinations


def neighbors(tile: int) -> list[int]:
    row, col = divmod(tile, 4)
    return [
        next_row * 4 + next_col
        for next_row, next_col in (
            (row - 1, col),
            (row + 1, col),
            (row, col - 1),
            (row, col + 1),
        )
        if 0 <= next_row < 4 and 0 <= next_col < 4
    ]


def all_simple_paths() -> list[tuple[int, ...]]:
    paths: list[tuple[int, ...]] = []

    def visit(tile: int, path: tuple[int, ...]) -> None:
        if tile == 15:
            paths.append(path)
            return
        for neighbor in neighbors(tile):
            if neighbor not in path:
                visit(neighbor, path + (neighbor,))

    visit(0, (0,))
    return paths


def main() -> None:
    paths = all_simple_paths()
    assert len(paths) == 184
    shortest_paths = [path for path in paths if len(path) == 7]
    counts: Counter[int] = Counter()
    ptc_scores: Counter[tuple[int, int]] = Counter()

    for red_cells in combinations(range(1, 15), 7):
        red = set(red_cells)
        red_can_finish_alone = any(
            all(tile in red for tile in path[1:-1]) for path in paths
        )
        blue_can_finish_alone = any(
            all(tile not in red for tile in path[1:-1]) for path in paths
        )
        if not red_can_finish_alone or blue_can_finish_alone:
            continue

        red_shortest_alone = any(
            all(tile in red for tile in path[1:-1]) for path in shortest_paths
        )
        assert red_shortest_alone
        k = min(sum(tile in red for tile in path[1:-1]) for path in shortest_paths)
        counts[k] += 1

        # Both players can use this same six-move path. A tile contract
        # makes Red pay each red intermediate tile for Blue and Blue pay
        # each blue intermediate tile for Red. Each pays for their own
        # matching tiles too, plus one green goal tile.
        shared_path = next(
            path
            for path in shortest_paths
            if sum(tile in red for tile in path[1:-1]) == k
        )
        assert sum(tile not in red for tile in shared_path[1:-1]) == 5 - k
        red_chips_left = 16 - (2 * k + 1)
        blue_chips_left = 16 - (2 * (5 - k) + 1)
        ptc_score = (20 + 5 * red_chips_left, 20 + 5 * blue_chips_left)
        assert ptc_score == (95 - 10 * k, 45 + 10 * k)
        assert ptc_score[0] > 70 and ptc_score[1] > 0
        assert sum(ptc_score) == 140
        ptc_scores[ptc_score] += 1

        # Red follows a six-move path, supplies k chips to Blue, and
        # receives x points when Blue finishes. Blue's six-move path
        # includes k red cells, covered by Red.
        x = 5 * k + 1
        red_payoff = 70 - 5 * k + x
        blue_payoff = 70 + 5 * k - x
        assert x <= 20
        assert (red_payoff, blue_payoff) == (71, 69)

        # In regular trading, Blue can instead give k+1 blue chips
        # for k red chips. The exchanged quantities conserve chips.
        red_inventory_after_trade_and_path = 16 - k + (k + 1) - 6
        blue_inventory_after_trade_and_path = 16 + k - (k + 1) - 6
        assert (red_inventory_after_trade_and_path, blue_inventory_after_trade_and_path) == (11, 9)
        assert (20 + 5 * red_inventory_after_trade_and_path,
                20 + 5 * blue_inventory_after_trade_and_path) == (75, 65)

    assert counts == Counter({1: 314, 2: 82})
    print(f"asymmetric boards: {sum(counts.values())}")
    print(f"required red coverages on a shortest blue path: {dict(sorted(counts.items()))}")
    print(f"reciprocal tile-contract scores (Red, Blue): {dict(sorted(ptc_scores.items()))}")
    print("contract witness: x = 5k + 1; payoffs (Red, Blue) = (71, 69)")
    print("regular-trade witness: k red for k+1 blue; payoffs (Red, Blue) = (75, 65)")


if __name__ == "__main__":
    main()
