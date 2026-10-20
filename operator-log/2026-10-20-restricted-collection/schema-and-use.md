# Restricted historical collections and a shared budget

This opt-in mode supports classic Codex research only. It has no retrieval or editorial launch path. Existing campaigns without either new configuration key retain their behavior. Source files stay in their existing pool directories; input cards are immutable external references. No pool copying is performed.

## Campaign configuration

Add `restricted_collection` and `budget_group` to each child campaign. Each value is an object with `manifest` (an absolute filename or a path relative to the campaign root) and `sha256` (the exact UTF-8 file SHA256). Keep `research_scheme` absent. Use Codex routes only, no extensions, provider override, refusal fallback, persistent sessions or arbitrary Codex settings. Project/system Codex configuration is refused; user configuration and rules are ignored, host skills and external tools are disabled. Research stages remain peer, consolidate and verify with existing stop, provider, seat and campaign-budget guards.

The collection manifest has exactly these keys:

- `version`: integer 1.
- `pair_id`: the campaign's single actual Pathfinder pair identifier.
- `pool_roots`: nonempty list of unique canonical absolute source directories. Atlas may list Nobel's shared paper-pool, campaign/sources and arxiv-cache as its audited logical union. Listing a directory here does not grant access to all its files.
- `cutoff_utc`: explicit UTC timestamp ending in Z.
- `sources`: nonempty list. Each entry has exactly `id`, `version`, `first_appearance_utc`, `version_appearance_utc`, and `files`. Each file has exactly canonical absolute `path` and `sha256`. IDs must be unique. Each admitted version must satisfy first appearance <= version appearance < cutoff. The operator audits dates and version identities; the engine verifies those assertions and exact bytes, not historical metadata independently.
- `inputs`: exactly `Q` and `P`. Each is an object with exactly `id`, `title`, canonical absolute `path`, `sha256`, and nonempty `source_ids`. IDs match the campaign corpus rows. Input cards must be .txt, .md or .tex outside the writable campaign, and cite only admitted source IDs. Titles and cards are the only imported problem context; corpus abstracts and scan context are not imported.

Pool roots, cards and campaign roots must be outside runtime-readable directories. Symlinked source files, traversal, changed hashes, unversioned sources and post-cutoff versions are refused. Alias entries do not authorize files outside the declared roots. Audit the logical pool union and choose source versions before preparing manifests; unresolved pair membership is not a reason to skip a pair for convenience.

## Shared budget

The group manifest has exactly `version` (1), `campaigns` (unique canonical absolute roots), and `budget` (native nonnegative integer limits). Atlas's six roots should be runs/pair-1 through runs/pair-6 under the pilot root; its budget is input_tokens=1000000000 and output_tokens=14000000. Every member must bind the same manifest. Store the manifest under operator/budget-group.json, outside all agent-writable threads.

A cross-process file lock spans each admitted attempt and receipt. It serializes model calls across group members, including retry attempts. Native receipt accounting includes interrupted served calls and deduplicates receipts by call ID. Unknown token usage or unresolved active-call evidence stops further group admission. Existing campaign/provider/seat guards remain active. Do not delete or replace the lock file to resume work; it names a shared inode.

Token limits are receipt-based projected admission, not a hard token truncation mechanism. The first call has no observed mean; a longer-than-projected in-flight call can exceed a token cap before its receipt is available. There is no guaranteed numerical overshoot bound. The engine refuses subsequent admission at the limit or when the projection exceeds it. If a strict never-exceed service-side token ceiling is required, this interface cannot certify one. Missing usage must be resolved from authoritative receipts, never set to zero.

## Offline preflight and execution

Using the pinned frozen runtime on PYTHONPATH and the existing Python environment:

```sh
python -m pathfinder.cli --root /absolute/child/root collection-check
```

This reads manifests, hashes every admitted file/card, reports exact permission settings and group budget blockers, and makes no model calls or campaign writes. An existing thread must have the matching collection seal. A blocked group returns nonzero. Collection-check does not certify source dates, card neutrality or historical completeness.

After the operator has certified all six source/version cutoffs and input cards, canonical preparation and research is:

```sh
python -m pathfinder.cli --root /absolute/child/root launch -- research --pairs PAIR_ID
```

Run children sequentially in the declared audit order. This command is a live launch instruction for the operator, not something executed during maintainer validation. Preparation links the cards, seals the collection and omits fetch helpers. Missing-source requests are logged or reported, never fetched. Do not replace an active engine.

## Validation and limits

109 targeted regression tests passed, covering transport, admission, config, CLI, research and both new modes. Tests include fresh stub research with retrieval tripwires, exact-file permissions, source/version changes, prohibited settings/stages, pool unions, shared receipt projections, unknown usage, interrupted evidence, lock waiting with stop, and two competing members exhausting a single-call budget.

An offline Codex 0.163.0 sandbox probe read the admitted source and denied a sibling pool source, host workspace document, temporary file and network connection. The canonical Python interpreter and ledger helper also executed inside the generated profile. No model was called. Tool subprocesses receive a minimal environment rather than inherited host variables. The profile exposes runtime directories and individually admitted files, not the operator parent directory.

This limits retrieval and filesystem access; it does not erase pretrained model knowledge or certify that a model never recalls later literature. Scientific scripts were not run, and no deployment or campaign was launched by the maintainer.
