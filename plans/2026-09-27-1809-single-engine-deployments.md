# One engine, adjustable deployments

Drafted 2026-09-27 for review. No code has changed yet.

## Goal

Keep a single Pathfinder engine, this repository, while statarb, in-repo
experiments such as the repeat and reinjection pilot, and pathfinder-julien-2
each adjust what they need. The difficulty is that every deployment adjusts
something, and today each does so by keeping its own copy of the engine.

Success means: every run records which tagged engine it used; any difference
from that tag is a declared setting, overlay or hook held in the deployment,
not an edited copy of engine code; and a change to the engine is tested
against every deployment before the deployment meets it.

## Current state

| Deployment | Engine it runs | How it adjusts | Divergence |
|---|---|---|---|
| This repository | live `pathfinder/` | reference | none |
| statarb (`../statarb/arxiv_drip/research_protocol.py`) | per-job copy of `../pathfinder/pathfinder` and `prompts/`, with a file-digest manifest | `campaign.json` keys; its research brief appended to four prompts; `PATHFINDER_CODEX`; an extra `inputs/supporting.json`; engine styles and `paper.build` for its own implementation note | none in code: the copy is taken live at job start, so each job silently runs whatever is on disk |
| Repeat and reinjection pilot (`experiments/2026-09-25-repeat-injection/`, finished) | frozen `engine/` copy, 131 file digests checked at preflight | runtime replacement of `transport.call`, `runner.pending` and `health.snapshot`; a coordinator loop that runs research, edit and paper per scheduled pair; `codex_adapter.py` mapping `--search` to `web_search`; an appended role instruction | code behaviour changed by monkeypatching, invisible to the engine's tests |
| pathfinder-julien-2 | vendored `dependencies/pathfinder/`, pinned for reproducibility | its own EVA and PCE controller around the engine; its own XeLaTeX preamble for new notes; a reviewed 505-line patch to `research.py` (external citation declarations and branch evidence links) | a fork: it lacks `alerts.py` and `recovery.py`, and seven modules, four prompts and the shared style differ from this repository |

So there are, at least, four engines in use: the live one, one per statarb
job, the pilot's frozen copy and julien-2's fork. Only the last is a
deliberate fork; the other copies exist to freeze a version, which a tag
can do.

## What deployments need to change

Grouping the adjustments above by kind:

1. **Settings.** Models, backend, seats, rounds, allowances, budgets, peer
   names, `inline_papers`, `inline_ledger`, `pair_kind`, Codex options,
   notifications. Already handled by `campaign.json`.
2. **Prompt text.** statarb and the pilot append instructions to role
   prompts. A campaign-local `prompts/` directory already takes precedence
   (`scan.prompts_dir`), but appending is done by copying and editing files.
3. **Document presentation.** julien-2 uses its own preamble; statarb reuses
   the engine styles for a document the engine does not produce.
4. **Call admission.** The pilot checks stop markers and a per-call budget
   before every model call, across two child campaigns.
5. **Scheduling.** The pilot admits one pair at a time in a fixed
   interleaved order, and runs the paper stage inside the same loop.
6. **Monitoring.** The pilot aggregates the health snapshot of two child
   campaigns under one parent.
7. **Transport details.** Mapping a legacy search flag onto the installed
   Codex CLI.
8. **Research-stage evidence rules.** julien-2's external citation
   declarations and branch evidence links change what the research stage
   accepts as evidence.

## Proposal

### Versions

- Tag engine releases in this repository as `engine-vMAJOR.MINOR`. A minor
  release keeps the state machine, file layout and hook signatures; a major
  release may change them. Each tag gets a short entry in `CHANGELOG.md`.
- A deployment pins a tag. Two ways are acceptable:
  - a uv dependency, `pathfinder @ git+https://github.com/vd1/pathfinder@engine-vX.Y`,
    whose lockfile records the commit; or
  - a frozen copy, as now, but taken from a tag and verified against it.
    `pathfinder freeze DIR --tag engine-vX.Y` writes the copy and a manifest
    with tag, commit and file digests; `pathfinder verify-frozen DIR` checks it.
- Rule: a copy of the engine is a cache of a tag. If its digests do not
  match a tag, it is a fork, and the verify command says so.

### Adjustment layers

Every adjustment must use one of these, cheapest first.

1. **Settings** in `campaign.json`, unchanged.
2. **Prompt overlays.** A campaign may hold `prompts/<role>.append.md`
   (appended) or `prompts/<role>.md` (replacing). The engine composes the
   final prompt and records its digest in the receipt. This removes the need
   to copy and edit prompt files, as statarb and the pilot do now.
3. **Style overlays.** A campaign-local `styles/` directory is placed before
   the engine's on `TEXINPUTS` for every build and every agent call. A
   deployment can replace `pathfinder-common.sty` or add its own document
   kind, which is how julien-2's preamble would fit.
4. **Hooks**, declared in `campaign.json` as `module:object` names loaded
   from the deployment's own code, with fixed signatures:

   | Hook | Signature | Replaces |
   |---|---|---|
   | `admit_call` | `(campaign, stage, role) -> None or raise Refused` | the pilot's `transport.call` wrapper |
   | `order_pairs` | `(campaign, pending: list[str]) -> list[str]` | the pilot's `runner.pending` replacement |
   | `snapshot_extra` | `(campaign, snapshot: dict) -> dict` | the pilot's `health.snapshot` replacement |
   | `codex_args` | `(campaign, args: list[str]) -> list[str]` | `codex_adapter.py` |

   Hooks may refuse, reorder, annotate or add arguments. They may not create
   transitions, write verdicts, edit the ledger or skip receipts; the engine
   applies its own guards after every hook, so a hook cannot make a run
   produce a record the state machine could not.

Anything that fits none of these is either a new hook, added to the engine
once with a test, or a change to the engine itself. There is no third route.

### Upstream candidates

- **Multi-campaign coordination.** The pilot's loop (a schedule of arm and
  pair, one pair at a time, research then edit then paper, shared stop) is
  likely to recur. Offer it as `pathfinder coordinate SCHEDULE.json`, built
  on `order_pairs` and `admit_call`, rather than as a hook.
- **Codex search flag.** Fold the `web_search` mapping into `transport`
  directly; it is a CLI compatibility fix, not a deployment choice.
- **julien-2's evidence rules.** External citation declarations are general
  and belong in the engine. Branch evidence links depend on EVA's branch
  layout; decide with julien-2 whether they are an engine feature behind a
  setting or a research-stage hook (see open questions).

### Contract tests

Each deployment contributes one test to this repository's suite that makes
no model call and is skipped when the sibling checkout is absent, following
`tests/test_statarb_bridge.py`. The test prepares a campaign the way the
deployment does, loads its hooks and overlays, and runs the engine against
the stub transport through one research and one edit transition. A release
tag is cut only when these pass.

## Migration

Past runs stay as they are: frozen copies and julien-2's completed run bind
digests in their manifests and remain archival evidence. Only future runs
move.

1. **Engine, step 1.** Tag the current engine `engine-v1.0`. Add
   `CHANGELOG.md`, `freeze` and `verify-frozen`.
2. **Engine, step 2.** Implement prompt overlays, style overlays and the four
   hooks, each with unit tests. Release `engine-v1.1`.
3. **Pilot.** It has finished (readout 2026-09-27). Archive it unchanged. For
   the next repeat or recursion experiment, express the schedule through
   `pathfinder coordinate` and hooks, with no monkeypatching.
4. **statarb.** Replace the live `copytree` with `freeze --tag`, and move its
   appended brief to `*.append.md` overlays. Add its contract test here.
5. **pathfinder-julien-2.** Upstream external citation declarations; settle
   branch evidence links; then replace `dependencies/pathfinder` with a
   pinned tag for new work and add its contract test. Its PCE controller
   stays in julien-2: it drives the engine rather than modifying it.

## Open questions

1. **Pin by dependency or by frozen copy?** A uv git dependency is simplest;
   a frozen copy keeps runs readable offline and self-contained. The
   proposal allows both, verified against a tag. Is one preferred?
2. **Branch evidence links.** Engine feature behind a setting, or a
   research-stage hook owned by julien-2? A hook keeps the engine smaller but
   adds a hook that touches evidence, where the engine's guarantees matter
   most.
3. **Release cadence.** Tag on demand when a deployment needs a change, or on
   a regular schedule?
4. **Where hook code lives.** In each deployment's repository (proposed), or
   collected under `deployments/` here so the contract tests need no sibling
   checkout?

## Not in scope

Changing the scientific state machine, rewriting past records, or merging
the deployments' own controllers (statarb's strategy stages, julien-2's EVA
and PCE loop) into this repository.
