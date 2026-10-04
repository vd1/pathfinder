# proofTree on the canonical engine only

**Goal:** proofTree imports everything it uses from the canonical engine (`../pathfinder`), nothing from julien-2; it is then pinned in `deployments.toml` with a contract test.

**Decision (user, 2026-10-05):** every Pathfinder deployment imports what it imports from the canonical engine.

**Baseline:** proofTree e937aa4, 39 tests pass (with julien-2 present). Only `prooftree/reuse.py` reaches into julien-2: `eva2.evidence` (freeze, verify_bundle), `eva2.transport` (permissions, toml), `julien2/*.py`; `evidence_policy.py` monkeypatches `eva2.evidence._check_references`.

## Engine additions (each with its test first)

- **E1 sandbox.** `pathfinder/sandbox.py`: `profile(cwd, engine_root, tools, read=(), deny=())` and `toml(value)`, a port of julien-2's permission profile (cwd writable, sibling branches absent, /tmp and TMPDIR denied, control files and `branch-runs/` read-only); optional `codex.filesystem_profile` applies it per request. Test in `tests/test_transport.py`.
- **E2 by-products in evidence.** `evidence.byproduct(name, names)` (proofTree's predicate merged with `gc.BYPRODUCTS`); campaign key `"evidence_byproducts": "exclude"` honoured by `composable.freeze` and the peer listing in `review_evidence`; a cited PDF whose `.tex` is present is not missing. Tests in `tests/test_composable.py` and the review-evidence tests.
- **E3 reading recorded eva2 bundles.** `import_eva2.verify_bundle(path)`, inventory only; a changed, added or symlinked file is refused. Test in `tests/test_import_eva2.py`; all 48 recorded proofTree bundles verify.
- **E4 arXiv with back-off.** `corpus.query(params, timeout=60, attempts=3)` with the 429 back-off of `paper._arxiv_titles` (10 s, 20 s) and a User-Agent; `_arxiv_titles` rebased on it. Test in `tests/test_corpus.py`.
- Optional: the stricter handoff checks eva2 makes (ledger head, provenance, unreviewed head) in `composable._check_handoff`, if they matter.
- Release (tag) after E1 to E4.

## proofTree changes

- `workflow.research_link`: one composable campaign per link (`research_scheme: composable`, `branches: 3`, `evidence_byproducts: exclude`) run by `research.run_thread`, then `edit.run`; prompts, binding, input manifest, admission and offline extensions and the stop marker kept; discoveries read after the joint thread.
- `codex_isolated.py` on `pathfinder.sandbox`; `cli.py` and `adaptive.py` on `corpus.query`; `carrie.py` and `refinement.py` on `contracts.extract_json`, old-layout bundles through `import_eva2.verify_bundle`, new ones through `composable.check_frozen`; `view.py` and `carrie.prepare` read both layouts.
- Delete `reuse.py` and `evidence_policy.py`; rewrite (not delete) the tests that used them, keeping 39.
- Rebase onto proofTree's latest commit before starting; run its suite after each file.

## Contract

- `test_prooftree_researches_a_link_on_the_candidate_engine`: init on the stub backend, one fixture link through `scan_links` and `research_link`; three frozen branches that verify, an accepted verdict and an edited PDF, stub receipts under one run, the engine imported from the candidate, no `eva2` module loaded, overlays composed.
- A read-only replay of `campaigns/sphere-packing-rounds2`: loads, every recorded bundle verifies, tree unchanged.
- `clean_paths = ["prooftree", "pyproject.toml", "uv.lock", "campaigns/sphere-packing-rounds2/adaptive"]`.

## Risks

- The 8 recorded links (old layout) all have outcomes; the legacy reader must land with the new flow, since `workflow.run` reads every outcome.
- Without the read-only rule, joint peers could write into `branch-runs/`.
- `strict_evidence` stays off until the PDF case is settled.
- proofTree is under active development: pin only after the migration commit.
