Feature: Preserve research revisions and supply complete assessment evidence

  Rule: Each consolidation result belongs to its own research or repair round

    Scenario: A revise decision replaces the current account with the returned repair
      Given pair "Q1P1" has an existing account and a verifier correction
      When the research workflow receives a nonempty repair account after "REVISE"
      Then the current account equals the returned repair account
      And the previous account remains available as an immutable version
      And the next verifier receives the repaired account

    Scenario: An iterate decision replaces the current account with the next round result
      Given pair "Q1P1" has an existing account and an unanswered research question
      When the research workflow receives a nonempty next-round account after "ITERATE"
      Then the current account equals the returned next-round account
      And the previous account remains available as an immutable version
      And the next verifier receives the next-round account

    Scenario: Restart recovers a retained consolidation response without another consolidation call
      Given pair "Q1P1" has an older account and a retained successful consolidation response for its current round
      When the interrupted research workflow resumes
      Then the current account equals the retained consolidation response
      And the older account remains available as an immutable version
      And recovery makes no new consolidation call

    Scenario: An empty repair response cannot reuse the older account as success
      Given pair "Q1P1" has an existing account and a verifier correction
      When every fresh repair response is empty
      Then consolidation is blocked without assessing the older account again
      And the existing account remains available for inspection

    Scenario: A failed repair response cannot reuse the older account as success
      Given pair "Q1P1" has an existing account and a verifier correction
      When every fresh repair response reports a provider failure
      Then consolidation is blocked without assessing the older account again
      And the existing account remains available for inspection

    Scenario: A campaign can disable automatic stage retries
      Given a campaign sets "stage_attempts" to 1
      When its consolidation response is empty or failed
      Then consolidation is blocked after exactly one provider call

    Scenario: Campaigns preserve the default stage retry limit
      Given a campaign omits "stage_attempts"
      When its first consolidation response is empty and its next response contains an account
      Then consolidation succeeds after exactly two provider calls

    Scenario: Invalid stage retry limits fail before provider dispatch
      Given a campaign sets "stage_attempts" to an invalid non-positive or non-integer value
      When the research workflow starts
      Then configuration validation fails before any provider call

  Rule: Consolidator and verifier read the evidence with their own tools

    Scenario: Consolidation and verification point to the evidence instead of inlining it
      Given peer artefacts with calculation evidence beside an existing account
      When the research workflow prepares its consolidation and verification requests
      Then both requests have file tools and name the peer directories
      And neither request inlines the peer artefact contents

  Rule: Readiness verification stays offline

    These regression scenarios MUST exercise real local research workflow orchestration,
    file persistence, request assembly, and restart state. Provider returns MAY be controlled
    at the transport boundary to make revision, interruption, empty response, and failure
    conditions reproducible. Verification MUST NOT invoke a live model, campaign, or PCE run.
    Offline verification proves workflow handling and evidence assembly, not model quality.
