# Handoff to the Pathfinder maintainer: chat text saved into consolidated notes

Request from the Atlas operator, filed here as a trace. Source: `~/Code_2026/qap-atlas/operator-log/2026-10-27-consolidation-preamble-handoff.md` (commit `41a7d59`). Repository paths below are relative to `~/Code_2026/qap-atlas`; engine paths are relative to this repository.

From the Atlas operator, 27 October 2026. Engine as frozen for Pilot 9: `a3d28c8`
(runtime-identical `376c01f` for Pilot 7). No live pilot, prompt or engine file was changed for this handoff.

## Problem

On the Opus 5.5 research route (Claude Code CLI, subscription), the consolidation reply often opens with a
chat-style status message before `\documentclass`. The engine writes that reply verbatim as the research
note, so the text becomes part of the note that Vera verifies and that the terminal verdict binds by SHA-256.

Examples of the opening lines:

- "I've finished checking the sources. Here is the repaired note."
- "I've written the consolidated note below. It keeps the results from rounds 1 and 2 that still stand and adds ..."
- "I've checked the cited theorem labels against the pool sources. Next I'm writing out the final consolidated note ..."

Count over every retained consolidation reply (`runs/pair-*/threads/Q001-P002/consolidation/*.json`),
measured on 27 October 2026:

| Pilot | Research route | Replies with text before `\documentclass` |
| --- | --- | --- |
| 1 to 4 | GPT-6.1-Sol | 0 of 92 |
| 5, 7 | Astra | 0 of 38 |
| 6 | Opus 5.5 | 11 of 23 |
| 8 | Opus 5.5 | 20 of 38 |
| 9 | Opus 5.5, with the prompt line below | 9 of 39 |

Pilot 9 added to `prompts/consolidate.md`: "Your reply is saved verbatim as the .tex file. Its first
characters must be \documentclass". This reduced the rate from about one half to about one quarter, but did
not remove it. The most recent case is Pilot 9 pair 6, round 3 repair 0, at 2026-10-26T11:36:21Z.

All 40 affected replies became the current note and were verified. Five are terminal notes:
Pilot 6 pair 3, Pilot 8 pairs 3, 4 and 6, and Pilot 9 pair 2 (all PAUSE). The Pilot 9 operator log records
that its verdicts do not cite the opening text. In Pilot 8 pair 4 the reviews did cite it: the terminal note
lists "conversational preamble" as a presentation correction requested three times (line 990), and the
reply that claims to remove it opens with a new preamble announcing "The chat text that sat before
`\documentclass` is gone" (line 7). Prompting alone does not resolve this. No effect on scores is known. No reply had text after
`\end{document}`, and none still contained a Markdown fence.

## Cause

In `pathfinder/research.py` (`a3d28c8`, around line 235) the new reply passes through `unfence()` and
`is_latex_document()` from `pathfinder/thread.py` (lines 166 to 175):

- `unfence()` only extracts a document wrapped in a fenced code block; any other text is returned unchanged.
- `is_latex_document()` only tests that `\documentclass` and `\begin{document}` occur somewhere in the text.

A reply of prose followed by a complete document therefore passes both checks and is written as is to the
note and to `consolidation/round-N-repair-M.json`.

## Requested change

A deterministic normalisation of new consolidation replies, independent of the model and the prompt:

1. If the reply does not begin with `\documentclass`, take the text from the first line that begins with
   `\documentclass` to the last `\end{document}`, plus a final newline. Match at the start of a line only:
   Pilot 8 pair 4 mentions the command inline in its opening text.
2. Keep the paid reply as evidence whenever text is removed, for example as `raw_text` in the consolidation
   JSON or a sidecar file, and record that normalisation took place, so the step can be audited.
3. If no line begins with `\documentclass`, keep the present behaviour (`consolidate-unreadable.txt` and
   BLOCKED).

For retained replies replayed on resume (around line 224), please decide whether to normalise them as well.
Normalising them would change the bytes of a note that was already verified; leaving them as they are keeps
existing records byte-stable. The Atlas side has no preference beyond keeping existing verdict hashes valid.

Out of scope: rewriting existing notes, consolidation records or verdict files. The Atlas operator already
handles presentation copies (result copies and the PDF builder start at `\documentclass`).

## Suggested tests

- A clean reply is unchanged, byte for byte.
- Prose, then a document: the note starts at `\documentclass`; the raw reply and the flag are kept.
- Prose containing an inline `\documentclass`, then a document on its own line: cut at the line start.
- A fenced reply: same result as today.
- Prose with no document: BLOCKED, with `consolidate-unreadable.txt` kept.
- Resume with a retained reply: behaviour as decided above, with existing verdict hashes still valid.

## Adoption

A frozen release with its archive hash, adopted at an idle boundary as usual. The Pilot 9 prompt line can
stay; with the engine change it is no longer needed for correctness.

## Evidence

- Retained replies: `pilots/atlas-pilot-{6,8,9}/runs/pair-*/threads/Q001-P002/consolidation/*.json`.
- Operator findings: `operator-log/atlas-pilot-8/2026-10-25T0415.md`; preamble checks in
  `operator-log/atlas-pilot-9/` (latest `2026-10-26T1155.md`); goal item 2 in
  `operator-log/GOAL_apex_2026-10-25.md`.
- Prompt line: `pilots/atlas-pilot-9/prompts/consolidate.md`, line 33.
