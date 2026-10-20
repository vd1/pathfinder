# Exact raw-literal reuse: offline capacity diagnostic

Status: the measured full-evidence profile fits with useful stress headroom. This is a diagnostic
prototype, not an installed engine codec, frozen launch handoff or permission to prepare a grant.
No production engine file, live grant, receipt, source, acceptance or deployment was changed.

## Exact transport model

Each file retains its path, full character length and UTF-8 SHA-256. Literal segments are readable
raw text with sequential IDs, lengths and hashes. A copy may reference only a previously completed
raw literal ID and a valid half-open Unicode-code-point range. Copy segments never define IDs.
Consequently copies cannot reference copied data, themselves, forward data or reconstructed files.
Within-file reuse becomes available after a raw chunk is completed. All unmatched text stays literal.
Whole-file aliases retain separate path/status identities and are not independent evidence.

The prototype does not parse scientific JSON, select fields, summarise text or compress opaque bytes.
Every expanded mapping was compared for exact equality and every full file hash was retained.
Both new scientific files are complete. Every old external input is byte-identical. The runner was
read as source text, never executed; no scientific computation or new model judgment occurred.

## Measurements

The editor profile includes the actual retained claims, current/history reviews, and archivist
custody/evidence-diff reports. The copied candidate is the existing held full-file P1 proposal.
The raw-literal explanatory instruction is included in the reported lengths.

| Profile | Characters | Remaining capacity |
| --- | ---: | ---: |
| Preparation wire plus unchanged 100000 reserve | 845482 | 154518 |
| Full actual editor profile | 928765 | 71235 |
| Additional 8192-character fact note, also in archivist JSON | 945954 | 54046 |
| Additional 32768-character fact note, also in archivist JSON | 971364 | 28636 |

Structured stress uses valid reserialised fact JSON in current/history reports and in the archivist
`fact_check` field. The fresh note is deterministic unique text. These reports are sizing fixtures,
not scientific reviews. Separate literal-append stress cases are also recorded in `measurement.json`.
Fresh live report lengths remain unpredictable; actual over-cap requests must still stop before calls.

The supplement alone reuses 105772 exact characters from earlier raw literals within that file.
The full editor profile uses 526 segments, 26224 indexed anchors, 880669 probes and 5898689 character
comparisons, taking about 1.09 seconds here. The strongest structured stress uses 546 segments,
27405 anchors and 6750123 comparisons, taking about 1.21 seconds. Preparation takes about 0.70 seconds.
Timing is an observation on this host, not a portable latency guarantee.

Fixed limits are 65536 anchors, four candidates per anchor, 2000000 probes, 8000000 character
comparisons and 8192 segments plus final per-file literals. Budget exhaustion retains the remainder
literally rather than dropping content. Literal chunks are 4096 code points, anchors 32, and the
minimum copied span is 256. The prototype decoder also bounds total expanded content.

## Verification and limits

All 15 tests pass, covering within-file reuse, aliases, Unicode, CRLF, marker/instruction-like text,
length framing, duplicate keys/IDs, bad hashes, invalid ranges, forward/copy-chain references,
trailing data, empty files and adversarial budget exhaustion. The actual and stress mappings all
round-trip exactly. `codec.py` is only under this operator-log directory; production does not import it.

Before any live use, a canonical implementation must declare this encoding immutably for fresh
grants only. Actual author, archivist, fact-checker, critic and editor prompts must use the declared
wire format with their existing scopes. Preparation must count that real format, including its
instruction and the unchanged reserve, rather than borrowing this smaller estimate while sending
JSON. Existing grants without the declaration must retain their exact old prompt/receipt behavior.
The fresh path still needs copied five-role dispatch, source-basis, real-build, custody/resume and
old-grant compatibility tests, followed by an exact freeze. Neither the 1000000 cap nor the 100000
reserve may change. No source or scientific/administrative boundary may be removed to make it fit.
