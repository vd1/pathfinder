# Repeat and reinjection pilot: launch amendment

Authorized by the user on 2026-09-25 after clarifying that USD 200 per arm
means an API-equivalent workload cap, not additional subscription charges.
The allocation and seed selection are in
`plans/2026-09-25-1623-repeat-versus-reinjection.md` at repository root.

## Pre-outcome amendments

- Both arms receive the same neutral peer prompt without a scan hypothesis.
  Otherwise the repeat arm would receive historical hints unavailable to the
  reinjection arm. This changes comparability with historical runs, not between
  the new arms.
- The existing metadata switch suppresses automatic arXiv links in both arms.
  Generated inputs have local manuscript IDs, not invented arXiv identities.
- Compiled bibliographies are inlined into generated-paper TeX for complete
  standalone reading. Original accepted artifacts are archived unchanged.
- Nominally tool-less calls have shell tools disabled in both arms.
- Pair pipelines are admitted serially in the prescribed alternating block
  order. Peers remain concurrent and configured seats=2; only one pair occupies
  the runner at a time. No completion-dependent reselection occurs.
- A per-model-call admission check applies the same API-equivalent budget to
  research, editing and paper stages. Actual calls may exceed their reserved
  estimates; this is an admission cap, not a guaranteed exact usage ceiling.
- One coordinator and one existing Astra supervision timer cover both arms.
  Its snapshot includes both child campaigns. The empty coordinator shortlist
  must never be interpreted as completion. Calls and receipts stay in each arm.

## Accounting and operation

Codex login status was checked as ChatGPT authentication. No API provider is
configured. The official GPT-6-sol standard short-context rates remain USD 2
input, USD 0.20 cached input and USD 10 output per million tokens, checked
2026-09-25 at [the model page](https://developers.openai.com/api/docs/models/gpt-6-sol).
This is approximate workload accounting, not an invoice: the CLI aggregates
requests, and the existing estimator does not account for separately reported
cache writes or detect individual long-context pricing tiers.

Commands use the repository's Python environment through uv. The launcher
supports `prepare`, `preflight`, `launch`, `status`, `run` and `supervise`.
The manifest records hashes of the staged engine, prompts, inputs and launcher.
`launch` starts a detached, session-scoped supervisor so it survives the current
chat turn; it does not install a permanent service. Audits occur every 300
seconds for up to 6 hours. Keep the Mac awake and available.

An operational failure stops the coordinator for diagnosis. Budget stops are
preserved; the other arm may continue, and the final state is censored rather
than complete. The supervisor may resume only the unchanged full-pipeline
command after checking children and logging an incident. It may not increase
budgets or change the protocol. Operator stops are never cleared automatically.

No claim-level comparison is performed by the research workers. That evaluation
follows completion using the frozen historical baseline and seed ancestry.
