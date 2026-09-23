# Rigging

Project tooling values for Shipshape roles. Values only, not procedure.
Procedure lives in the skills. Every role reads this on open.

## Stack

- language: Python
- runtime: Python 3.12 via `nix develop path:.`
- packageManager: uv via `nix develop path:.`

## Directories

- implementation: pathfinder
- specs: features
- verification: features/steps
- verification: tests
- assets: prompts
- assets: pathfinder/styles
- assets: pathfinder/monitor.html
- scantlings: none

## Commands

- discover: `nix develop path:. -c uv run behave --dry-run --tags="not @captain and not @shipwright"`
- focused: `set -a; . "$HOME/.aienv"; set +a; ref="{scenario}"; file="${ref%%:*}"; name="${ref#*:}"; nix develop path:. -c uv run behave "$file" --name "^${name}$" --tags="not @captain and not @shipwright"`
- broad: `nix develop path:. -c uv run behave --tags="not @captain and not @shipwright"`
- broad-sandbox: `set -a; . "$HOME/.aienv"; set +a; nix develop path:. -c uv run behave --tags="@sandbox and not @captain and not @shipwright"`
- coverage: `set -a; . "$HOME/.aienv"; set +a; nix develop path:. -c uv run coverage run --branch --source=pathfinder -m behave --tags="not @captain and not @shipwright"`
- broad-unit: `nix develop path:. -c uv run pytest -q`
- coverage-unit: `nix develop path:. -c uv run pytest --cov=pathfinder --cov-branch --cov-report=term-missing -q`
- step-usage: `nix develop path:. -c uv run behave --steps-catalog --tags="not @captain and not @shipwright"`
- plank-inventory: `nix develop path:. -c python -c 'from pathlib import Path; print("".join(f"{p}:{n}:{line.strip()}\\n" for p in Path("pathfinder").rglob("*.py") for n,line in enumerate(p.read_text().splitlines(),1) if "@planks(" in line or "@planks-provisional(" in line), end="")'`
- typecheck: `nix develop path:. -c python -m compileall -q pathfinder`
- lint: none
- conformance: none

## Perturbation

- message: `PERTURBATION: consider current durable context; remove when fixed`
- perturb: `raise RuntimeError("PERTURBATION: consider current durable context; remove when fixed")`

## Tiers

- default: untagged
- sandbox: `@sandbox`
- policy: untagged structural scenarios run locally via `nix develop path:.` without provider substitution
- policy: `@sandbox` scenarios source `~/.aienv` and exercise ELM with `ELM_API_KEY`
- weather: .shipshape/behave-timings.json
- runrecord: .shipshape/runrecord.jsonl

## Dependencies

- policy: locked
- dependency: behave
- dependency: pytest
- dependency: pytest-cov
- dependency: ELM OpenAI-compatible request interface at `https://elm.edina.ac.uk/api/v1` with `Qwen/Qwen3.5-397B-A17B-FP8`; authenticate from `ELM_API_KEY` after sourcing `~/.aienv` without reading it

## Outbound

- outbound: none

## Known false-failure modes

- mode: plank inventory uses text search and cannot prove docstring attachment to a declaration
- mode: Behave `--steps-catalog` is plain text and does not report scenario usage as structured data
