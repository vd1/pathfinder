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

  Rule: Roles without file tools receive the full evidence they are asked to assess

    Scenario: The consolidator receives complete prior account and peer evidence inline
      Given a tool-less consolidator has an existing account and peer artefacts with calculation evidence
      When the research workflow prepares its consolidation request
      Then the request contains the complete prior account and peer artefact contents
      And the request contains the complete calculation evidence with its source paths

    Scenario: The verifier receives complete current account and peer evidence inline
      Given a tool-less verifier has a revised account and peer artefacts with calculation evidence
      When the research workflow prepares its verification request
      Then the request contains the complete current account and peer artefact contents
      And the request contains the complete calculation evidence with its source paths

    Scenario: Unreadable referenced evidence blocks strict tool-less assessment
      Given a tool-less assessment requires a peer artefact that cannot be read
      When the research workflow prepares the assessment request
      Then the assessment is blocked before a provider call with the unreadable evidence identified

    Scenario: Evidence references stay inside their investigation
      Given a tool-less assessment ledger references a calculation outside its investigation through parent traversal
      When the research workflow prepares the assessment request
      Then the assessment is blocked before reading outside evidence or calling a provider

    Scenario: Evidence symlinks cannot expose another investigation
      Given a tool-less assessment peer artefact or calculation path is a symlink to outside evidence
      When the research workflow prepares the assessment request
      Then the assessment is blocked before reading outside evidence or calling a provider

    Scenario: Evidence path aliases are rejected even when their targets stay inside the investigation
      Given a tool-less assessment references an internal evidence target through a symlink or parent traversal
      When the research workflow prepares the assessment request
      Then the assessment is blocked before reading the aliased evidence or calling a provider

  Rule: Readiness verification stays offline

    These regression scenarios MUST exercise real local research workflow orchestration,
    file persistence, request assembly, and restart state. Provider returns MAY be controlled
    at the transport boundary to make revision, interruption, empty response, and failure
    conditions reproducible. Verification MUST NOT invoke a live model, campaign, or PCE run.
    Offline verification proves workflow handling and evidence assembly, not model quality.
