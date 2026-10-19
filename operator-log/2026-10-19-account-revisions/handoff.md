# Bounded candidate revisions after terminal amendment reviews

Runtime: `605aba6000d9560ef02c7ccbf7752aa93f8d013f`.
Verified frozen runtime: `/private/tmp/pathfinder-account-revisions`.
Archive: `/private/tmp/pathfinder-account-revisions-605aba6.tar.gz`.
SHA256: see `archive.sha256` in this directory.

Keep all active engine files stable. Invoke this separate frozen runtime only after
the owning account root is idle. A rating controller also owns its campaign root.
Batch2 and its sequence require no upgrade for this handoff.

## Supported path

`account-amend-review` can repair evidence for an unchanged candidate. These findings
require changed prose, so that path alone is insufficient. The new command is:

```text
python -m pathfinder.cli --root CAMPAIGN account-amend-revise PAIR --id bounded-tail-20261019 --revision reader-clarity-1 --packet PACKET --reason "Approved bounded textual revision"
```

Preparation makes no calls. Repeat with `--apply` after explicit approval of the
new bounded review allowance. Record reviewed runtime migration with the global
`--accept-change` option. `actions.json` supplies each exact packet path and arguments.

The existing amendment identity remains selected. Each revision is stored beneath
its `revisions/` directory; it is not a new amendment or a reset. The engine binds the
previous terminal findings by exact quote and hash, checks changes against both the
original accepted wrapper and the failed candidate, and preserves old review files.
The revised candidate is fixed through one fresh PCE review with one fact-check
allowance. The original imported acceptance remains separate provenance. Only an
accepted exact candidate can enter fresh presentation and canonical release.

Saved results resume without renewed allowance. Interrupted preparation can resume
through its immutable staging and pointer installation. A later revision must be
explicit and cannot silently replace a running or accepted one. The shared pool,
OpenAI-only preflight, provider/stop/budget guards, receipts and run ownership remain
on the normal PCE path.

## Candidates and evidence

### Q010-P011

Two bounded replacements define the dipole offset vector, bit-weight matrix dimensions
and componentwise bit blocks, then define the encoded quadratic cost and strict
single-bit and adjacent-level minima. All numerical results, the Hilbert-Schmidt
repair and the production pause remain unchanged.

Support: retained `emmy/joint-investigation.md` product-angle derivation,
`emmy/carry_control.py` exhaustive flip/adjacent-level comparisons, and
`branches/branch-3/emmy/encoding-audit.md` neighbourhood control. These scientific
files were already in the approved transport. The terminal reader critique is bound
in `revision.json`; no new research is proposed.

### Q010-P046

The revision removes only the historical assertion that a cost-result file was
omitted from the original editorial transport. The scientific packet cannot establish
that custody assertion. The replacement retains the conditional ideal measurement
protocol, excluded optimisation/circuit costs and absence of a demonstrated total-cost
saving. There is no need to obtain historical custody evidence for a deleted assertion.
The failed mandatory finding is bound in `revision.json`.

### Q010-P072

The revision explicitly attributes the repository recipe/MAT-model inspection and
conditional attenuation-scaling analysis to branch 2. It preserves the distinction
between later repository inspection and the unresolved historical implementation.
No scaling formula, number or physical limitation changes. Retained branch-2 ledger
entries 32, 35 and 42 support the inspection; entry 33 supports the conditional scaling.
The fact-check findings C077 and C079 are bound separately in `revision.json`.

## Validation

- All three actual candidate packets compiled during copied-deployment stub reviews.
- Each copied terminal account reached separate amendment acceptance through five
  stub roles; previous files and scientific status were preserved except the active
  amendment revision pointer. This validates the engine path, not a live verdict.
- Focused tests cover preserved imported provenance, idempotence, wrong candidate
  hashes, undeclared changes, changed reviewer findings/history and interrupted pointer
  installation. Frozen regression results are recorded in `validation.json`.
- Artifact bans passed for every candidate. The style scanner's sole error was its
  existing false positive on the unchanged matrix product `K = Dᵀ B D` in the third account.
  After checking that expression, `--allow-placeholders` gave zero errors. The 155
  existing long-line warnings are retained to avoid unrelated manuscript reformatting.
- No live calls, research reruns, deployment writes or active-engine replacements.
