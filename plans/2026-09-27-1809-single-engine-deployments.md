# One engine, adjustable deployments

Drafted 2026-09-27 for review; revised twice the same day after Astra's
reviews (see "Review response" at the end). Implementation started on
branch `single-engine` after the user asked for autonomous work; no release
is cut without the gate below.

## Goal

Keep a single Pathfinder engine, this repository, while statarb, in-repo
experiments such as the repeat and reinjection pilot, and pathfinder-julien-2
each adjust what they need. The difficulty is that every deployment adjusts
something, and today each does so by keeping its own copy of the engine.

Success means:

- every run records its complete effective deployment: the immutable engine
  commit, the resolved configuration, the deployment's own code and hooks,
  and the prompts and styles actually used, and every receipt names that run;
- any difference from a released engine is a declared setting, overlay or
  supported extension held in the deployment, not an edited copy of engine
  code or a runtime replacement of engine functions;
- a release is cut only after the candidate engine has passed a required
  test matrix covering every deployment the release supports, each at a
  named revision; the release notes list the live deployments it does not
  yet support, and why.

## Current state

| Deployment | Engine it runs | How it adjusts | Divergence |
|---|---|---|---|
| This repository | live `pathfinder/` | reference | none |
| statarb (`../statarb/arxiv_drip/research_protocol.py`) | per-job copy of `../pathfinder/pathfinder` and `prompts/`, with a file-digest manifest | `campaign.json` keys; its research brief appended to four prompts; `PATHFINDER_CODEX`; an extra `inputs/supporting.json`; engine styles and `paper.build` for its own implementation note | none in code, but the copy is taken live at job start, so each job silently runs whatever is on disk |
| Repeat and reinjection pilot (`experiments/2026-09-25-repeat-injection/`, finished and archived) | frozen `engine/` copy, 131 file digests checked at preflight | runtime replacement of `transport.call` (reservation counting around each call), `runner.pending` (restricted to one scheduled pair) and `health.snapshot` (two child campaigns); a coordinator loop running research, edit and paper per pair; `codex_adapter.py` mapping `--search` to `web_search`; an appended role instruction | engine behaviour changed by monkeypatching, invisible to the engine's tests |
| pathfinder-julien-2, at `5cc82db` (2026-09-27 17:25 +0200; since then `8c0aad3`) | two vendored copies: `dependencies/pathfinder/` and, for the EVA experiment, `experiments/eva-minus-reuse-01/dependencies/pathfinder/` | its own EVA and PCE controllers, which replace `transport.execute` and call `run_thread` directly; since `8c0aad3`, readable accounts rendered with the vendored `paper.build` and `pathfinder-readable` | two forks of upstream `57e9a7a`; see [the inventory](../deployments/pathfinder-julien-2/inventory.md) |

The [inventory](../deployments/pathfinder-julien-2/inventory.md) establishes
that both julien-2 copies fork upstream `57e9a7a` (2026-09-24). The main copy,
`dependencies/pathfinder/`, changes only `research.py`: inline assessment
evidence (`_assessment_evidence`), path and symlink rejection, configurable
stage attempts (`_stage_attempts`), changed tool-less consolidation
(`_consolidate_prompt`), and repair and restart fixes (each consolidation
response persisted by round and repair, previous accounts archived by hash,
an empty or failed fresh repair rejected instead of reusing the old note).
External citation declarations, branch evidence links, a changed `runner.py`
and the EVA research scheme exist only in the experiment copy,
`experiments/eva-minus-reuse-01/dependencies/pathfinder/`. The absent
`alerts.py` and `recovery.py`, and the other differing modules, prompts and
style, are upstream changes made after the fork, not julien-2 edits.

## What deployments need to change

1. **Settings.** Models, backend, seats, rounds, allowances, budgets, peer
   names, `inline_papers`, `inline_ledger`, `pair_kind`, Codex options,
   notifications. Handled by `campaign.json`.
2. **Prompt text.** statarb and the pilot append instructions to role
   prompts by copying and editing prompt files.
3. **Document presentation.** julien-2 uses its own preamble; statarb reuses
   the engine styles for a document the engine does not produce.
4. **Call admission with accounting.** The pilot reserves a slot before each
   model call, checks stop markers and a per-call budget, and releases the
   slot when the call ends, under a lock shared by concurrent calls.
5. **Bounded execution.** The pilot runs exactly one scheduled pair at a
   time, then its paper stage, across two child campaigns.
6. **Monitoring.** The pilot aggregates the health snapshots of its children.
7. **Transport compatibility.** Mapping a legacy search flag onto the
   installed Codex CLI.
8. **Research-stage evidence rules.** julien-2's evidence and citation
   handling changes what the research stage accepts as evidence.

## Proposal

### Trust model

Deployment code runs in the same Python process as the engine and receives
engine objects. It is trusted code. The engine can validate what an
extension returns and keep its own records authoritative, but it cannot stop
extension code from writing files or mutating objects. The contracts below
say what is supported, not what is enforced. If enforcement is ever needed,
it requires a separate design with process isolation; that is out of scope.

Where a need is a known compatibility fix rather than a deployment choice,
it becomes plain engine functionality, not an extension point.

### Packaging and prompt resolution (prerequisite)

Today `pyproject.toml` packages only `pathfinder/`, and `scan.prompts_dir`
finds built-in prompts in the repository's top-level `prompts/`, outside the
wheel. An installed engine therefore has no prompts.

- Move built-in prompts and styles into the package
  (`pathfinder/resources/prompts`, `pathfinder/resources/styles`) and resolve
  them through `importlib.resources`. Keep top-level symlinks or a thin shim
  only if the repository layout needs them.
- Resolve prompts per file, not per directory. For role `R`, the effective
  prompt is: the campaign's `prompts/R.md` if present, otherwise the
  engine's; then the campaign's `prompts/R.append.md`, if present, appended
  after a blank line; then placeholder substitution (`{{...}}`) on the
  composed text. A campaign with only an append overlay for one role falls
  back to engine prompts for every other role.
- Styles resolve the same way: campaign `styles/` first, then the packaged
  styles, for both builds and agent calls.
- Test: build a wheel, install it into a fresh environment outside the
  checkout, and run a no-model-call smoke campaign through research and edit
  with and without overlays.

### Run provenance

Extend `runner.create_manifest` into a run record, written once per run as
`run.json` with a `run_id`:

- engine: resolved commit, tag if any, installation kind (checkout,
  installed dependency or frozen copy) and the verification result;
- deployment: repository and commit of the deployment code, digests of
  every loaded extension module;
- resolved configuration: `campaign.json` after defaults, and its digest;
- effective prompts and styles: digest of each composed prompt and each
  style file used;
- dependency lock digest (`uv.lock` of the deployment) and TeX engine
  version;
- corpus snapshot digests, as now.

Every receipt carries `run_id`. On resume, the runner recomputes the record;
if any component differs it refuses, unless the operator passes an explicit
`--accept-change REASON`, which starts a new `run_id` linked to the previous
one. Work recorded under the old run is kept, not re-attributed.

### Versions and frozen copies

- Tag releases as `engine-vMAJOR.MINOR` with a `CHANGELOG.md` entry. Minor
  releases keep the state machine, file layout and extension signatures.
  Tags are names; provenance always records the resolved commit.
- A deployment pins a release in one of two ways:
  - a uv git dependency on the tag, whose lock records the commit; or
  - a frozen copy made by `pathfinder freeze DIR --commit C`.
- Freeze and verification use an inventory taken from the source commit
  itself (`git ls-tree -r C` over the engine's runtime paths: the package
  and its packaged resources), not from whatever was copied. The inventory
  lists the expected file set and blob digests and is bound to the commit.
- `pathfinder verify-frozen DIR` compares the copy with that inventory and
  reports one of: **verified** (same file set, same digests), **modified**
  (changed, missing or unexpected files, each listed), or **unverifiable**
  (the commit is not available, for example offline or a deleted tag). An
  unverifiable copy is not treated as modified. Tests cover a changed, a
  missing and an added runtime file, and an unavailable commit.

### Extension points

Each is declared in `campaign.json` by `module:object`, loaded from the
deployment's code, and recorded by digest in the run record.

1. **Admission, with an engine-owned reservation lifecycle.** The engine
   wraps every model call in `with admission(campaign, stage, role):`, before
   the active-call record is written. A deployment supplies
   `policy(campaign, stage, role, reserved) -> Admit | Defer | Stop`.
   - *Scope.* Reservations are counted per campaign root. A campaign run by
     a coordinator also carries its parent's root; the parent's stop marker
     is honoured, but reservations are not pooled across arms.
   - *Atomicity.* The stop checks, the policy evaluation and the increment
     happen under one lock, so two concurrent calls cannot both pass a cap
     that admits one.
   - *Defer.* Releases the lock while waiting, wakes at a bounded interval or
     when the campaign's or parent's stop marker appears, then re-evaluates.
   - *Stop.* The engine writes a stop marker with the policy's reason and a
     refusal receipt (outcome `refused`, no usage, no cost), and raises
     `Refused`. No active-call record exists for a refused attempt, so
     nothing looks like a crash. Research, edit and paper stages treat
     `Refused` as a stop, and `runner._loop` never turns it into a health
     failure.
   - *Release.* The reservation is released on success, provider failure,
     timeout and cancellation.
   Tests: concurrent admissions against a cap of one, a provider failure
   releasing its reservation, a deferral woken by a stop, and a refusal that
   makes no model call and leaves no active-call record.
2. **Bounded execution.** Not a hook: an engine API.
   - `runner.run(campaign, pairs=[...])` runs only the listed pairs, after
     checking that each is on the shortlist, not duplicated and not held by
     another runner. Unlisted pairs are ignored entirely, including BLOCKED
     ones: they neither run nor make the bounded run report failure.
   - Completion is defined over the requested stages. A pair is complete
     for research and edit when research is terminal and the edit is done;
     for paper, additionally when research is not DRAFT or the paper is
     ACCEPTED or PAUSE-ON-AMEND. So a DRAFT pair whose edit is unfinished
     resumes at edit, and a DRAFT pair with a finished edit but no finished
     paper resumes at paper.
   - A listed pair that is BLOCKED is reported as blocked and requires
     reconcile; it does not stop the other listed pairs.
   - When no listed pair has work left, the call returns immediately with
     status `nothing-to-run`, never "all threads terminal" for the campaign.
   - `run_pair(campaign, pair_id, stages=("research", "edit", "paper"))`
     runs one pair through the requested stages under campaign ownership and
     the thread lock, and returns each stage's outcome. The coordinator
     below is built on it.
3. **Monitoring.** `snapshot_extra(campaign, snapshot) -> dict` returns
   additional data, which the engine stores under `snapshot["extensions"]`.
   It cannot replace core fields (`runner`, `active_calls`, `work`,
   `warnings`, `failure_count`). A parent coordinator that needs child
   campaigns in its snapshot uses the coordinator's own aggregation instead.

Transport compatibility is not an extension: the Codex `web_search`
mapping goes into `transport` directly, selected from the installed CLI's
capabilities.

### Coordinator

`pathfinder coordinate SCHEDULE.json` runs a fixed schedule of (campaign,
pair) entries across one or more child campaigns, one pair at a time, using
`run_pair`. It keeps the pilot's semantics, each covered by a test ported
from `experiments/2026-09-25-repeat-injection/test_launch.py`: resume skips
completed pairs and accepted papers and preserves order; a budget stop
censors one arm and continues with the other; an operator stop halts
everything; a research, edit or paper failure stops before the next pair;
one parent heartbeat and an aggregated status. Its snapshot aggregates the
children's snapshots under the parent.

### Release matrix

- `deployments.toml` in this repository lists every live deployment with the
  exact revision to test against, and marks each as supported (required for
  the release) or not yet supported (listed, with the reason, and excluded
  from the gate). Each entry names how to obtain it (a checkout at a
  commit, or a versioned fixture stored here that reproduces how the
  deployment prepares a campaign and which extensions it loads).
- The release job provisions every entry, runs its contract tests against
  the **candidate** engine (the deployment's adapter is pointed at the
  candidate, not at its own pinned copy), and fails if any supported entry
  is missing, skipped or failing. Local runs may still skip absent siblings;
  the release job may not.
- Contract tests make no model call. Using the stub transport, they cover
  research, edit, the paper stage where the deployment uses it, coordinator
  runs where it uses them, and a real style build with its overlays.

## Migration

Past runs stay as they are. Frozen copies, the archived pilot and
julien-2's completed run bind digests in their manifests and remain
evidence. Only future runs move.

1. **Packaging.** Move prompts and styles into the package; per-file prompt
   and style overlays; installed-artifact smoke test.
2. **Provenance.** Run record, `run_id` on receipts, resume check.
3. **Freeze.** Commit-bound inventory, `freeze`, `verify-frozen`, with the
   three outcomes tested.
4. **Execution APIs.** Admission lifecycle with policy; `run(pairs=...)` and
   `run_pair`; `snapshot_extra`; Codex search mapping in `transport`.
5. **Coordinator.** `pathfinder coordinate`, with the pilot's tests ported.
6. **Deployment compatibility, before any release.**
   - statarb: a fixture reproducing how it prepares a campaign (settings,
     append overlays instead of edited prompts, supporting inputs, its
     implementation-note build), passing against the candidate engine.
   - pathfinder-julien-2: a classified inventory of every behaviour
     difference between its engine at the pinned commit and this
     repository, each with its regression test: upstream as general,
     upstream behind a setting, or keep in julien-2 as an extension. Until
     the upstream work it calls for is done, julien-2 is listed in the matrix
     as not yet compatible, and the first release states that it does not
     cover julien-2.
7. **Release matrix and first release.** `deployments.toml`, fixtures,
   contract tests, release job; then tag `engine-v1.0` once every entry
   marked required passes.
8. **Pin upgrades, after release.** statarb replaces its live copy with a
   pin or a verified freeze and moves its brief to overlays; julien-2 points
   new work at a release once its inventory is resolved. Its EVA and PCE
   controller stays in julien-2; it drives the engine rather than modifying
   it.
9. **Next pilot.** Express the schedule with `pathfinder coordinate`, with no
   monkeypatching.

## Open questions

1. **Pin by dependency or by frozen copy?** Both are supported and verified
   against a commit. Is one preferred as the default?
2. **julien-2's evidence rules.** After the step 8 inventory: which parts
   are general engine behaviour, which belong behind a setting, and whether
   any evidence rule should ever be an extension at all, given that evidence
   handling is where the engine's guarantees matter most.
3. **Release cadence.** Tag on demand when a deployment needs a change, or
   on a regular schedule?
4. **Fixtures or checkouts in the release matrix?** Fixtures here keep the
   job self-contained but can drift from the deployment; checkouts at pinned
   revisions are exact but need access to private repositories.

## Not in scope

Changing the scientific state machine, rewriting past records, isolating
extension code, or merging the deployments' own controllers (statarb's
strategy stages, julien-2's EVA and PCE loop) into this repository.

## Review response

Astra's review of the first draft, 2026-09-27, and what changed:

| Comment | Change |
|---|---|
| P1 admission needs a lifecycle | Engine-owned reservation context with a policy returning Admit, Defer or Stop; refusals are stops, not health failures; concurrency, failure and refusal tests |
| P1 release must fail when deployments are absent | Required matrix in `deployments.toml` with exact revisions; release fails on missing or skipped entries; candidate engine injected; paper, coordinator and style builds covered |
| P1 uv path needs packaged prompts | Prompts and styles move into the package; per-file overlay resolution with stated precedence and substitution order; installed-wheel smoke test |
| P1 record the complete deployment | Run record with engine commit, resolved config, deployment and extension digests, prompt and style digests, lock; `run_id` on receipts; resume refuses on change |
| P2 ordering cannot bound execution | `order_pairs` hook replaced by `run(pairs=...)` and `run_pair` with validation and explicit empty result; coordinator added to the migration before any pilot uses it; pilot semantics ported as tests |
| P2 hook guarantees overstated | Trust model stated; returned values validated; core snapshot fields protected; Codex search made engine functionality, not a hook |
| P2 freeze needs an immutable inventory | Inventory from the commit's tree, exact file set, verified, modified or unverifiable outcomes, with tests |
| P2 refresh julien-2's inventory | Commit recorded; known extra behaviours listed; migration step requires a classified inventory with regression tests before any replacement |

Astra's second review, of `4a094be`:

| Comment | Change |
|---|---|
| Bounded completion across stages | Completion defined per requested stage, preserving edit and paper resumes; unlisted BLOCKED pairs ignored; listed BLOCKED pairs reported without stopping the rest |
| Release gate before deployments join | Compatibility work and the julien-2 inventory moved before the first release; pin upgrades after it |
| Atomic admission, Defer and refusals | Stop checks, policy and increment under one lock; Defer waits outside the lock and wakes on stop; refusals leave no active-call record; per-campaign scope with parent stop |
