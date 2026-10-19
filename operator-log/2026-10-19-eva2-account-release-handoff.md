# Imported EVA2 account publication compatibility

Runtime commit: `ea5fb9d2d2015d5648c16f6c27a65c1c62e67bd8`.
Frozen engine: `/private/tmp/pathfinder-eva2-ea5fb9d`.
Archive: `/private/tmp/pathfinder-eva2-ea5fb9d.tar.gz`.
SHA-256: `a022b8dd07501346928823199c27ca32c1b41ab552af61b6bc52976c6b54fa19`.

This targeted compatibility update includes the preceding PCE recovery,
paper-pool, ITERATE, account presentation and dated-release fixes. No new
all-deployment release tag is claimed.

## Batch 1

The supported path is unchanged at the command line:

```sh
pathfinder --root CAMPAIGN --accept-change 'Pin imported EVA2 publication compatibility' present PAIR --edited
pathfinder --root CAMPAIGN release PAIR --edited
```

Each batch-1 pair has its own campaign root, for example
`campaign-2-batch-1/Q024-P011`. Pin and verify the new engine through the
deployment's upgrade mechanism. Configure the authorised OpenAI routes and
release acknowledgement. Do not replace the frozen engine used by an
active batch-2 process in place.

The adapter verifies the existing import, accepted delivery and render
records. It checks the installed body and PDF against their recorded
hashes, verifies the retained wrapper, and confirms that it contains the
exact body. Publication starts from a byte-identical copy of that wrapper.
Original bodies, PDFs, edit records and EVA2 history stay unchanged.
Publication `acceptance.json` identifies the imported acceptance and hashes
its supporting records. No native PCE result, `accepted_note` flag, research
verdict or scientific paper acceptance is manufactured. No PCE grant or
rerun is needed for these already accepted imports.

These ten accounts use prose references without citation commands. The
publication workspace supplies an empty bibliography; it does not invent
BibTeX entries. Missing dependencies for actual bibliography or citation
commands block publication. An acknowledgement that tries to cite absent
BibTeX keys also remains a blocker; use the owner's approved prose wording.

Presentation can correct the publication copy while the original body is
retained. The scientific-status boundary and prohibition on automatic
scientific amendment still apply. Wrappers without `maketitle` receive a
visible fixed UTC release line in the exported copy. All dated-release
hash, leak-check, collision and retry protections remain in force.

## Batch 2 sequential recovery

After the active reconciliation process exits, `reconcile --apply` without
a pair iterates `shortlist.json` sequentially. This is supported for the
prepared grants. Inspect the shortlist first: every actionable entry should
be an intended PCE continuation, since this general command can select
other recovery actions too. It creates no grant implicitly and bypasses no
campaign ownership, provider pause, stop marker or budget guard. A failure
may interrupt the loop; a later invocation resumes pending eligible work
without repeating completed PCE calls. Do not run competing reconciliation
processes for the same campaign.

## Verification

The final frozen artifact passed 25 focused tests in 22.51 seconds,
including native PCE recovery, imported presentation through dated release,
rejection of altered import evidence, release date/hash protections, and
pairless reconciliation of two prepared grants through real stub transport.
Log: `/private/tmp/pathfinder-eva2-ea5fb9d-tests.log`; matching JUnit XML is
beside it.

All ten actual batch-1 imports were validated and their exact retained
wrappers compiled on copies with the frozen engine. All 369 pre-existing
copied editorial files remained byte-identical. Evidence is retained in
`2026-10-19-eva2-publication-validation.json` beside this handoff. No live
campaign writes or model calls were made by the maintainer.

The owner has authorised the deployment agent to collect validated releases
and send them to Julien in the latest email thread with human and agent
synopses. This engine handoff makes no claim that the live presentation,
release or email-delivery work has already completed.
