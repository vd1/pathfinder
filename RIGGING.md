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
- focused: `ref="{scenario}"; file="${ref%%:*}"; name="${ref#*:}"; nix develop path:. -c uv run behave "$file" --name "^${name}$" --tags="not @captain and not @shipwright"`
- broad: `nix develop path:. -c uv run pytest -q`
- coverage: `nix develop path:. -c uv run pytest --cov=pathfinder --cov-branch --cov-report=term-missing -q`
- step-usage: none
- plank-inventory: `nix develop path:. -c python -c 'from pathlib import Path; print("".join(f"{p}:{n}:{line.strip()}\\n" for p in Path("pathfinder").rglob("*.py") for n,line in enumerate(p.read_text().splitlines(),1) if "@planks(" in line or "@planks-provisional(" in line), end="")'`
- typecheck: none
- lint: none
- conformance: none

## Perturbation

- message: `PERTURBATION: consider current durable context; remove when fixed`
- perturb: `raise RuntimeError("PERTURBATION: consider current durable context; remove when fixed")`

## Tiers

- default: @logic
- sandbox: none
- policy: @logic via `nix develop path:.`; current scenarios are non-binding `@captain` skeletons
- weather: none
- runrecord: .shipshape/runrecord.jsonl

## Dependencies

- policy: locked
- dependency: behave
- dependency: pytest
- dependency: pytest-cov

## Outbound

- outbound: none

## Known false-failure modes

- mode: plank inventory uses text search and cannot prove docstring attachment to a declaration
