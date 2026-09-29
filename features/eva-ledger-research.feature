Feature: Research with EVA and EVA-minus
  EVA-minus reviews the shared research ledger before narrative synthesis.
  EVA retains synthesis and scientific verification for joint research.

  Scenario: An imported EVA-minus investigation begins with direct ledger review
    Given an EVA-minus investigation with imported peer research and its evidence
    When Pathfinder prepares its first Vera review
    Then Vera receives both papers and the complete attributed research ledger
    And Vera receives all referenced peer evidence without a consolidated account

  Scenario: A fresh EVA-minus investigation researches before direct review
    Given a fresh EVA-minus investigation with two papers
    When its peer research round finishes
    Then its next stage is Vera ledger review
    And its thread contains no consolidated account

  Scenario: Vera asks researchers to revise their ledger
    Given an EVA-minus investigation awaiting review with research allowance remaining
    When Vera requests REVISE of a ledger argument from existing evidence
    Then the review is appended to the ledger with its reviewed evidence identity
    And Emmy and Ada receive the correction request before the next direct review

  Scenario: Vera asks researchers to investigate a gap
    Given an EVA-minus investigation awaiting review with research allowance remaining
    When Vera requests ITERATE with a concrete research gap
    Then the review is appended to the ledger with its reviewed evidence identity
    And Emmy and Ada receive the investigation request before the next direct review

  Scenario: A branch hands off without a scientific verdict
    Given an EVA-minus investigation with all previous review requests resolved or explicitly deferred
    When Vera returns no further actionable requests
    Then the branch is ready for handoff because no further requests remain
    And the handoff preserves deferred objections without a scientific verdict

  Scenario: Research exhaustion preserves unanswered objections
    Given an EVA-minus investigation with no research rounds remaining
    When Vera requests ITERATE with a concrete research gap
    Then the branch is ready for handoff because its allowance is exhausted
    And the handoff preserves the unanswered request without a scientific verdict

  Scenario: Empty new requests cannot erase earlier objections
    Given an EVA-minus investigation with an active review request
    When Vera returns no new requests and omits disposition of the active request
    Then Pathfinder records an operational review error rather than a handoff

  Scenario: Invalid review text cannot certify a handoff
    Given an EVA-minus investigation awaiting review
    When the retained Vera response has no valid request list
    Then Pathfinder records an operational review error rather than a handoff

  Scenario: EVA-minus refuses a terminal scientific verdict
    Given an EVA-minus investigation awaiting review
    When Vera returns PAUSE instead of a request review
    Then Pathfinder records an operational review error rather than a handoff

  Scenario: Every request disposition remains attributable
    Given an EVA-minus investigation with an active review request
    When a later Vera review defers that request with a missing-input reason
    Then the ledger retains the original request and its attributed deferral

  Scenario: Replaying a saved Vera review appends feedback once
    Given a completed Vera response whose feedback is already on the ledger
    And a restart before the review transition was persisted
    When Pathfinder resumes the investigation
    Then the review occurs once in the ledger
    And the retained response is applied without another model dispatch

  Scenario: New evidence invalidates a saved review
    Given a Vera response bound to a research ledger and evidence snapshot
    When the evidence changes before that response is applied
    Then Pathfinder blocks the stale response before a research transition

  Scenario: Sequential reviews have distinct dispatch identities
    Given an EVA-minus investigation whose first review requested REVISE
    When the next research and review cycle is prepared
    Then its calls have identities distinct from the earlier review cycle

  Scenario: Missing referenced research evidence blocks strict direct review
    Given an EVA-minus ledger referencing a missing calculation output
    When Pathfinder prepares its first Vera review
    Then the review is blocked before a provider call with the missing path identified

  Scenario: Frozen branch evidence is visible throughout joint EVA
    Given a joint EVA investigation with three namespaced frozen branch bundles
    When Pathfinder prepares peer research and synthesis and scientific verification
    Then each stage receives all three ledgers and their referenced evidence
    And the original branch bundles remain unchanged

  Scenario: Joint research preserves disagreements and develops new connections
    Given a joint EVA investigation with three namespaced frozen branch bundles
    When Pathfinder prepares the peer research instructions
    Then the instructions require investigating disagreements and new connections
    And the instructions distinguish inherited evidence from new derivations and conjectures

  Scenario: Joint EVA records terminal feedback on the ledger
    Given an EVA investigation with a synthesised account awaiting verification
    When Vera returns PAUSE with a missing-input reason
    Then the full review is appended to the ledger exactly once
    And the existing PAUSE scientific ending is preserved

  Scenario: Joint EVA retains feedback when further iteration is exhausted
    Given an EVA investigation with a synthesised account and no research rounds remaining
    When Vera requests ITERATE with a concrete research gap
    Then the full review is appended to the ledger exactly once
    And the existing PAUSE-ON-ITERATE ending retains the unanswered request

  Scenario: Positive EVA verdict has an explicit acceptance mapping
    Given an EVA investigation whose scientific verifier returns DRAFT
    When its composable research outcome is exported
    Then the public scientific verdict is ACCEPT
    And the original verifier decision remains DRAFT in provenance

  Scenario: Existing EVA keeps synthesis and revision semantics
    Given an ordinary EVA investigation awaiting research consolidation
    When Vera requests REVISE of the returned account using existing evidence
    Then Emmy repairs the account before scientific verification
    And no additional peer research occurs for that repair

  Scenario: An exhausted review allowance preserves the latest research
    Given an EVA-minus investigation whose research advanced after its latest review
    And no Vera calls remain
    When Pathfinder advances the branch
    Then the branch hands off the latest research with an explicit unreviewed-head marker
    And no scientific verdict is inferred

  @contract
  Scenario: Campaign configuration selects the composable research scheme
    Given a campaign configuration with research_scheme "eva_minus"
    And imported_research is true with rounds 2 and ledger_reviews 4
    When the standard research entry point opens the investigation
    Then it starts direct ledger review with at most two new peer rounds and four review calls

  @contract
  Scenario: Joint evidence locations are part of campaign configuration
    Given a campaign configuration with research_scheme "eva"
    And research_bundles lists "branches/branch-1", "branches/branch-2", and "branches/branch-3"
    When Pathfinder prepares the research evidence for that investigation
    Then it includes those thread-relative bundle directories with their original reference namespaces

  Scenario: Campaign runner retains handoff without editing a branch
    Given an EVA-minus investigation ready for handoff
    When the campaign runner completes that investigation
    Then it records the branch handoff without invoking account editing
