# Fixed-candidate account amendment handoff

Runtime commit: `b667e6a0c2dca7f6c55a445237ed20aed105f2c5`.
Frozen runtime: `/private/tmp/pathfinder-amend-b667e6a`.
Archive: `/private/tmp/pathfinder-amend-b667e6a.tar.gz`.
SHA256: `396da954d4f9913e44702befd12593dd2cf0c6697923d10bd414c22ce3e66515`.

This is a targeted batch-1 update. Leave the active batch-2 engine and runner unchanged.
It includes the existing paper pool, ITERATE readiness, PCE continuation, imported EVA2
account support, presentation checks and dated release policy.

## Contract

`account-amend` takes an explicit identity, owner authority/reason, candidate packet,
and evidence root. It requires a RETURNED account presentation, terminal research,
and validated original editorial acceptance. Preparation makes no model calls.

The packet contains `account-candidate.tex`, `changes.json` and `evidence.json`.
The command verifies baseline/candidate hashes, exactly applies the declared unique
before/after replacements, matches their finding IDs to the returned findings, and
verifies every retained evidence file within the same thread. Branch evidence is
frozen as generated research evidence; the original accepted body remains internal
editorial context. Scripts are read as evidence, never executed by this command.

An explicit `--apply` permits one PCE pass, at most five calls: claim extraction,
archivist, fact-checker, critic, editor. The host supplies the exact candidate bytes
and appends every replacement as a mandatory claim for checking. The author cannot
rewrite the candidate. Every claim must be supported; both independent gates must
pass and the editor must accept without an evidence-change request. A numeric critic
score never overrides a revise verdict here. All routes are OpenAI-only, with no
refusal fallback, tools, research rerun or paper commissioning.

Reviews, dispatch receipts, evidence snapshots and build records remain under
`edited/account-amendments/ID/`. A successful build and review create separate
`acceptance.json`, binding the candidate, original acceptance and retained files.
`edited/account-amendment.json` selects this revision for account publication.
Original `edit.json`, `note.tex`, EVA2 records, research state and native PCE state
are preserved. Pending or rejected amendments block account presentation/release.
A retry resumes retained dispatches and never grants another pass. A terminal
rejection stays rejected; report it rather than resetting files or changing IDs.

## Julien Q024-P011 execution

Use the frozen runtime only for the independent batch-1 campaign. Verify its
manifest and Python import path before any dispatch. Run from a directory outside
the maintainer source checkout, such as `/private/tmp`.

```bash
export PYTHONPATH=/private/tmp/pathfinder-amend-b667e6a
export UV_CACHE_DIR=/private/tmp/pathfinder-uv-cache
uv run --project /Users/v/Code_2026/pathfinder --offline --no-sync python -c 'import pathfinder; print(pathfinder.__file__)'
uv run --project /Users/v/Code_2026/pathfinder --offline --no-sync python -m pathfinder.cli verify-frozen /private/tmp/pathfinder-amend-b667e6a --repo /Users/v/Code_2026/pathfinder
```

Prepare, then repeat the same arguments with `--apply`. The global change reason
records the explicit engine migration; the amendment reason records owner authority.

```bash
amend_args=(
  --accept-change 'Install bounded account amendment support for batch1 only'
  --root /Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-1/Q024-P011
  account-amend Q024-P011
  --id definition-20261019
  --packet /Users/v/Code_2026/pathfinder-julien-2/reviews/q024-p011-definition-amendment-20261019
  --evidence-root /Users/v/Code_2026/pathfinder-julien-2
  --reason 'Vincent authorises the two definition amendments and fresh independent review, presentation and release; OpenAI only'
)
uv run --project /Users/v/Code_2026/pathfinder --offline --no-sync python -m pathfinder.cli "${amend_args[@]}"
uv run --project /Users/v/Code_2026/pathfinder --offline --no-sync python -m pathfinder.cli "${amend_args[@]}" --apply
```

After `accepted`, run `present Q024-P011 --edited` on that same campaign with the
same frozen engine. A new content-addressed publication directory starts fresh;
`--restart` is unnecessary. Only after CLEARED, run `release Q024-P011 --edited`.
Presentation must resolve internal source labels and paths before release. Keep
all original and RETURNED presentation artifacts. If review, presentation or release
blocks, report the retained findings without bypassing a gate.

## Validation

The implementation passed 79 broader regressions before the final additional guards,
then 58 account-amendment/PCE tests on the committed implementation. The frozen
runtime passed all 39 focused tests. Logs: `/private/tmp/pathfinder-amend-b667e6a-tests.log`
and `/private/tmp/pathfinder-amend-b667e6a-tests.xml`. The frozen manifest was
verified before and after testing.

An isolated copy of the real Q024-P011 campaign validated candidate SHA256
`62df29e5c880785a5a3dcf61ba2adf8eff105b61261a059f330b452402bc6c5a`,
compiled it, exercised acceptance/presentation with stub responses, and preserved
all 502 pre-existing thread files byte-for-byte. The real release leak check
correctly blocked the unpolished stub presentation because internal labels remained.
The synthetic regression fixture passed the complete presentation and dated release.
These are software checks, not scientific acceptance by live reviewers.

No live model calls, deployment mutations or batch-2 engine changes were made by
the maintainer. The Julien operator performs the authorized live review and tail.
