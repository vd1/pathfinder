# New consolidation document normalisation

Implemented request: `operator-log/2026-10-27-atlas-consolidation-preamble/request.md`.

## Frozen runtime

Commit: `1f1524308919149e8f35e2e052a6a653cac8dbc0`.
Runtime: `/private/tmp/pathfinder-1f15243`.
Archive: `/private/tmp/pathfinder-1f15243.tar.gz`.
Archive SHA256: `c60c3a318b936cdec724e08737a121c38f7195238cd99c5d69eb66bb3bf25d40`.
The freeze verifies against its commit with no changed, missing or added runtime files.

The runtime delta from Atlas's a3d28c8/376c01f is confined to thread.py and research.py.
No prompt, route, allowance, budget or scoring rule changes. Unrelated working-tree note edits were not included.

## Behaviour

For new classic consolidation replies, existing Markdown-fence extraction runs first. The engine requires
an actual line beginning with the documentclass command, followed by begin-document and end-document.
An inline mention of the command cannot be selected. A reply lacking that complete boundary is blocked;
nonempty unreadable replies remain in consolidate-unreadable.txt, and no verifier is dispatched.

When prose precedes the document, the engine takes the first line-start documentclass through the last
end-document and appends a newline. Clean replies beginning with documentclass remain byte-identical,
including line endings and final-newline choice. Existing fenced extraction retains its previous result.
This is deterministic boundary extraction, not semantic LaTeX validation or a general TeX parser.

If extraction changes the selected text, the consolidation JSON preserves raw_text and a normalization
record with policy latex-document-v1, source, input SHA256 and output SHA256. The existing changed-file
fallback also uses this rule; when its written document changes, raw_note_text preserves that document
alongside the paid reply. The normalized response and audit data are retained atomically before the note
is installed. A subsequent interrupted-install resume reuses that response without another paid call.

Only newly received classic consolidation output is affected. The composable workflow and generic
unfence/is_latex_document helpers retain their existing contracts.

## Historical records

Retained consolidation JSON is replayed exactly as stored, without normalisation, including historical
preambles. Existing notes, records and verdicts are not migrated or rewritten. Previously verified hashes
remain valid. Newly verified notes bind the normalized bytes instead. The Pilot 9 prompt instruction can
remain unchanged; new classic replies no longer depend on the model obeying it.

## Verification

- 66 regression tests passed across normalisation, research revisions, research-only operation,
  ITERATE readiness, classic reopen and recovery.
- 31 focused tests passed again against the exact frozen runtime, including interruption/resume,
  clean CRLF/no-final-newline preservation, inline command mentions, fences, invalid documents,
  raw-evidence custody, written-file fallback and unchanged historical verdict hashes.
- Read-only audit of all 100 retained Pilot 6/8/9 consolidation records reproduced the reported counts:
  11/23, 20/38 and 9/39 have preambles. All 40 extract to the exact expected document span; the other
  60 remain unchanged. No invalid document was found. Every original record hash was rechecked.

The audit calls only the string normaliser on copies in memory. It does not update any Atlas record,
invoke scientific calculations or make model calls. evidence-result.json contains the bindings and results.

## Adoption

1. Preserve the archive in durable operator storage and verify its hash and frozen manifest.
2. Adopt only with idle ownership, no active provider calls, and a supported safe stage boundary.
   Do not replace a loaded engine. A classic peer stage with partially spent allowance is not a safe
   migration boundary; use the previously tested Pilot 7 drain procedure if a campaign is running.
3. Select the separate frozen runtime and use the normal canonical resume/coordinator command with an
   explicit accept-change reason naming the consolidation-normalisation engine update. Preflight must
   show engine-only changes; leave campaign files, prompts and budgets intact.
4. Resume from saved state. A retained consolidation remains untouched. The next newly generated
   consolidation receives the normalization policy. Do not reopen or reverify terminal notes merely
   to remove old chat text; presentation copies remain the operator's existing route for those notes.
5. Check the first affected new consolidation record for raw_text/normalization and verify that the
   subsequent verdict hash matches its installed text. A clean new response need not have an audit flag.

No live deployment writes, research calls, new allowances or historical repairs were performed.
