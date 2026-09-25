# Rigging

Project tooling values for Shipshape roles. Values only, not procedure.
Procedure lives in the skills. Every role reads this on open.

## Stack

- language: Python
- runtime: Python >=3.12 from the local uv environment; verified Python 3.13.5
- packageManager: local uv; verified uv 0.10.5

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

- discover: `uv run --offline --locked behave --dry-run --tags="not @sandbox and not @captain and not @shipwright"`
- focused: `ref="{scenario}"; file="${ref%%:*}"; name="${ref#*:}"; uv run --offline --locked behave "$file" --name "^${name}$" --tags="not @sandbox and not @captain and not @shipwright"`
- broad: `uv run --offline --locked behave --tags="not @sandbox and not @captain and not @shipwright"`
- broad-sandbox: `: "${ELM_API_KEY:?ELM_API_KEY must be supplied by the operator}"; uv run --offline --locked behave --tags="@sandbox and not @captain and not @shipwright"`
- coverage: `uv run --offline --locked coverage run --branch --source=pathfinder -m behave --tags="not @sandbox and not @captain and not @shipwright"`
- broad-unit: `uv run --offline --locked pytest -q`
- coverage-unit: `uv run --offline --locked pytest --cov=pathfinder --cov-branch --cov-report=term-missing -q`
- step-usage: `uv run --offline --locked behave --steps-catalog --tags="not @sandbox and not @captain and not @shipwright"`
- plank-inventory: `uv run --offline --locked python -c 'from pathlib import Path; print("".join(f"{p}:{n}:{line.strip()}\\n" for p in Path("pathfinder").rglob("*.py") for n,line in enumerate(p.read_text().splitlines(),1) if "@planks(" in line or "@planks-provisional(" in line), end="")'`
- typecheck: `uv run --offline --locked python -m compileall -q pathfinder`
- lint: none
- conformance: none

## Perturbation

- message: `PERTURBATION: consider current durable context; remove when fixed`
- perturb: `raise RuntimeError("PERTURBATION: consider current durable context; remove when fixed")`

## Tiers

- default: untagged
- sandbox: `@sandbox`
- policy: default commands exclude `@sandbox`; untagged scenarios still require inspection for external calls before offline execution
- policy: `@sandbox` scenarios exercise ELM with operator-provisioned `ELM_API_KEY` in the environment
- weather: .shipshape/behave-timings.json
- runrecord: .shipshape/runrecord.jsonl

## Dependencies

- policy: locked
- dependency: behave
- dependency: pytest
- dependency: pytest-cov
- dependency: PCE packaged `pce` executable from `../pce`, invoked through `nix run path:../pce --`
- dependency: ELM OpenAI-compatible request interface at `https://elm.edina.ac.uk/api/v1` with `Qwen/Qwen3.5-397B-A17B-FP8`; authenticate from operator-provisioned `ELM_API_KEY` in the environment

## Outbound

- outbound: none

## Known false-failure modes

- mode: plank inventory uses text search and cannot prove docstring attachment to a declaration
- mode: Behave `--steps-catalog` is plain text and does not report scenario usage as structured data
- mode: uv `--offline` prevents package downloads only; it does not isolate scenario network access
- mode: untagged edit-stage scenarios invoke PCE through Nix and live agent runtimes
- mode: prepared-corpora verification patches `transport.call` while scanning uses `transport.execute`; it can invoke a live agent despite passing
