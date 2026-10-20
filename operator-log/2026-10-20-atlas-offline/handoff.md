# Atlas offline research integration

Keep frozen bbafa93e3b020104d2ac4028047d7956b195e898 for Atlas. The subsequent clean-review changes concern
Julien account amendments; no demonstrated Atlas blocker requires an upgrade.

The copied Atlas integration test passes native ITERATE followed by DRAFT, with six stub receipts and zero
model calls. It uses the actual Atlas prompt replacements and append overlays, original restricted collection
manifest and input cards, and the aggregate budget guard. All original integration files and admitted source
hashes remain unchanged.

Only the private copies switch default and stage-route backends to stub. They retain model names, route
efforts and allowances. Their copied aggregate budget manifest names six private campaign roots. The test
injects the two deterministic verdicts at the stub reply layer, leaving native dispatch, admission, budget
accounting, receipts and stage transitions active. It does not patch the transport or controller.

Run the test from the Pathfinder checkout with this command. The private output directory must not contain
useful work: pytest owns its basetemp. Use a location outside runtime-readable directories; restricted
campaigns deliberately reject /private/tmp. The explicit Python -P and test assertion ensure imports come from
the named frozen runtime.

```sh
UV_CACHE_DIR=/private/tmp/pathfinder-uv-cache \
PYTHONPATH=/private/tmp/pathfinder-restricted-bbafa93 \
uv run --offline --no-sync python -P -m pytest \
  --import-mode=importlib --rootdir=/private/tmp \
  --basetemp=/Users/v/Code_2026/pathfinder/.atlas-offline-copy \
  -q operator-log/2026-10-20-atlas-offline/test_atlas.py -s
```

The proof directory under that private copy contains effective-prompts.json and verification.json, including
all six receipts, overlay digests and group membership. This is a deterministic integration check, not a
scientific evaluation or a live sandbox penetration test. The earlier OS permission probes cover the latter
boundary separately.

Collection dates and versions remain fixture assertions pending Atlas certification. Passing this test does
not certify source eligibility, authorize pool additions, or clear live research. The existing approval
rejection for pool writes is unchanged.
