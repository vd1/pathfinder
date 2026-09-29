# Risk-certificate deepening

This completed supervisor-led worked application follows recursive Q1P2,
not a new pair campaign. See `PROTOCOL.md` for the design fixed before
execution and `../../notes/recursive-risk-deepening.pdf` for the derivation,
results and limitations.

## Findings

- A conditional simulator, explicit fallback and bounded failure surcharge
  make an expected-cost comparison possible in a synthetic routing model.
- With known safe losses, the paid instance at 4000 samples per risky cell
  has a sufficient expected-cost bound of 0.579 against fallback cost 1
  at a per-draw price of 0.00001. Simulated mean cost is 0.428.
- More samples eventually make deployment uneconomical. Both boundary
  scenarios abstain throughout the declared grid.
- Six deployment errors occurred in 120000 regime decisions, all outside
  their confidence boxes. Their costs are included. No false refutations
  occurred. This is probabilistic certification, not zero-error validation.

The numerical result is not real-world evidence or proof of publication
novelty. The stronger access regime changes both information and sampling
cost. The original repeat-versus-recurse results are not changed.

## Reproduce

From the repository root:

```sh
uv --cache-dir /private/tmp/pathfinder-plan-uv-cache run --no-sync pytest -q experiments/2026-09-28-risk-deepening/test_study.py
uv --cache-dir /private/tmp/pathfinder-plan-uv-cache run --no-sync python experiments/2026-09-28-risk-deepening/study.py
latexmk -pdf -interaction=nonstopmode -halt-on-error -cd notes/recursive-risk-deepening.tex
```

The study prints JSON by default. Its optional `--output` refuses to overwrite
an existing file. `results.json` records seed, interpreter version and the
SHA-256 hashes of the parent, protocol and study script. Monte Carlo standard
errors are descriptive; confidence coverage is per fixed-batch decision.

No paid model calls were launched. The next research question is whether a
budget-aware sequential certificate or a declared stationary multi-decision
horizon can make the difficult cases useful without invalid stopping rules.
