# Pathfinder experiment ledger

One row per experiment directory, plus the original root campaign. Updated 7 November 2026.
Historical states below come from retained records, not live process checks.
Scan scores are ex ante. Ratings are ex post. Missing ratings remain missing, never zero.
This initial inventory includes source audits and abandoned attempts; nested arms stay in their parent row.

| Date / ID | Experiment | Recorded outcome / comparison | Record |
| --- | --- | --- | --- |
| 2026-11-02 | Original 14 pairs rerun with single-peer EV: Astra-high research and consolidation, Opus 5.5-high verification | Complete 3 November: 4 DRAFT, 10 PAUSE; 56 blind ratings across 14 pairs; old mean 1.93, new mean 2.79, delta +0.86; 10 improved, 4 tied, none declined. 6 November: Q1P1 and Q7P1 papers accepted, presentation paused at PAUSE-ON-PRESENT, neither released | [EV comparison](experiments/2026-11-02-10x10-ev-astra-opus/README.md) |
| 2026-09-11 onward | Original root 10x10 campaign; 14 selected pairs | 5 DRAFT, 8 PAUSE, 1 PAUSE-ON-ITERATE; 5 accepted papers; Opus 5.5 rated each twice, all 2/10 | [Shortlist](shortlist.json); [retrieved ratings](experiments/2026-11-02-10x10-ev-astra-opus/operator/historical-paper-ratings.jsonl) |
| 2026-09-13-astra-medium-Q4P6-reassessment | Independent Astra-medium reassessment of Q4P6 | Retained artifacts; completion not established by thread-status records | [Record](experiments/2026-09-13-astra-medium-Q4P6-reassessment/run-outcome.json) |
| 2026-09-13-astra-medium-accepted2 | Astra-medium rerun of two accepted pairs | 1 DRAFT, 1 PAUSE | [Record](experiments/2026-09-13-astra-medium-accepted2/RESULTS.md) |
| 2026-09-13-astra-medium-top2 | Astra-medium rerun of two top-ranked pairs | 2 PAUSE | [Record](experiments/2026-09-13-astra-medium-top2/RESULTS.md) |
| 2026-09-13-paper-followups | Astra follow-up research and paper work | 1 DRAFT | [Record](experiments/2026-09-13-paper-followups/RESULTS.md) |
| 2026-09-14-Q7-source-audit | Q7 source and mathematical audit | Retained artifacts; completion not established by thread-status records | [Record](experiments/2026-09-14-Q7-source-audit/check-results.json) |
| 2026-09-16-Q1P7-rescan | Q1P7 targeted rescan | Retained artifacts; completion not established by thread-status records | [Record](experiments/2026-09-16-Q1P7-rescan/schedule.json) |
| 2026-09-16-Q3P3-continuation | Opus continuation of Q3P3 | 1 PAUSE | [Record](experiments/2026-09-16-Q3P3-continuation/campaign.json) |
| 2026-09-16-sonnet5-full-rescan | Sonnet 5 full-grid rescan | Retained artifacts; completion not established by thread-status records | [Record](experiments/2026-09-16-sonnet5-full-rescan/comparison.json) |
| 2026-09-17-gpt-5-6-sol-10x10-scan-20260917T202235Z | Sol 10x10 scan and shortlist research | 5 DRAFT, 7 PAUSE | [Record](experiments/2026-09-17-gpt-5-6-sol-10x10-scan-20260917T202235Z/research-outcomes.json) |
| 2026-09-17-qwen3-5-397b-10x10-scan | Qwen 10x10 scan and shortlist research | 8 BLOCKED, 1 PAUSE, 3 PAUSE-ON-ITERATE | [Record](experiments/2026-09-17-qwen3-5-397b-10x10-scan/research-outcomes.json) |
| 2026-09-18-gpt-5-6-sol-full-protocol | Sol full-protocol run | 6 DRAFT, 6 PAUSE | [Record](experiments/2026-09-18-gpt-5-6-sol-full-protocol/campaign.json) |
| 2026-09-18-qwen3-5-397b-full-protocol | Qwen full-protocol run | 3 DRAFT, 9 PAUSE-ON-ITERATE | [Record](experiments/2026-09-18-qwen3-5-397b-full-protocol/campaign.json) |
| 2026-09-19-claude-opus-full-protocol | Opus full-protocol run | 2 BLOCKED, 10 PAUSE | [Record](experiments/2026-09-19-claude-opus-full-protocol/campaign.json) |
| 2026-09-19-gpt-5-6-sol-full-protocol | Sol full-protocol attempt | 2 stopped | [Record](experiments/2026-09-19-gpt-5-6-sol-full-protocol/campaign.json) |
| 2026-09-19-gpt-5-6-sol-inline-consolidation | Sol full protocol with inline consolidation | 4 DRAFT, 8 PAUSE | [Record](experiments/2026-09-19-gpt-5-6-sol-inline-consolidation/campaign.json) |
| 2026-09-19-qwen3-5-397b-full-protocol | Qwen full-protocol attempt | 2 stopped | [Record](experiments/2026-09-19-qwen3-5-397b-full-protocol/campaign.json) |
| 2026-09-21-174126-astra-blind-Q1P2 | Blind Astra assessment of Q1P2 | Retained artifacts; completion not established by thread-status records | [Record](experiments/2026-09-21-174126-astra-blind-Q1P2/result.json) |
| 2026-09-23-gpt-6-sol-rerun-01 | Fresh repeat of original 14 pairs with GPT-6-Sol | 3 DRAFT, 11 PAUSE; fresh repeat baseline used by later reinjection study | [Record](experiments/2026-09-23-gpt-6-sol-rerun-01/outcomes.json) |
| 2026-09-25-repeat-injection | Matched repeat versus reinjection of generated papers, 14 pairs per arm | 28 pipelines finished; repeat 7 accepted papers, reinjection 3; claim audit identifies ranking and risk extensions | [Record](experiments/2026-09-25-repeat-injection/outcomes.json) |
| 2026-09-28-recursive-extension | Second-generation recursive extension versus repeat control, two pairs per arm | 4 investigations completed; recursion 2 accepted, repeat 1 accepted and 1 PAUSE; 34 calls | [Record](experiments/2026-09-28-recursive-extension/RUN.md) |
| 2026-09-28-risk-deepening | Conditional-risk follow-up and numerical checks | Protocol, numerical results and research note retained; see report | [Record](experiments/2026-09-28-risk-deepening/README.md) |
| 3peers | Three-peer research variant | 3 DRAFT, 5 PAUSE | [Record](experiments/3peers/campaign.json) |
| cache-run | Cache experiment (archived campaign) | 1 PAUSE, 1 stopped | [Record](experiments/cache-run/campaign.json) |
