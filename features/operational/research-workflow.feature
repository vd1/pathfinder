Feature: Operate a paper-pair research workflow

  Rule: Research and independent assessment remain distinct stages

    Scenario: Substantive peer findings advance to independent assessment
      Given researchers have recorded substantive findings for pair "Q1P1"
      When the findings are consolidated into a research account
      Then an independent verifier assesses that account against both source papers

    Scenario: Empty peer findings pause before consolidation
      Given researchers have recorded no substantive finding for pair "Q1P1"
      When the peer stage finishes
      Then pair "Q1P1" is paused for an empty research record
      And no research account is produced

    Scenario: An empty successful consolidation response is retried
      Given pair "Q1P1" has substantive findings awaiting consolidation
      And its first consolidation returns no account and no provider error
      When Pathfinder consolidates pair "Q1P1"
      Then Pathfinder makes one more consolidation attempt

    Scenario: A direct-provider response becomes the research account
      Given pair "Q1P1" has substantive findings awaiting consolidation
      And its direct provider cannot write campaign files
      When the provider returns a research account for pair "Q1P1"
      Then Pathfinder stores the response as the pair's research account

    Scenario: Consolidation succeeds only with a stored research account
      Given pair "Q1P1" has substantive findings awaiting consolidation
      When both consolidation attempts produce no stored research account
      Then pair "Q1P1" is blocked at consolidation

    Scenario: Direct-provider consolidation requests a returned research account
      Given pair "Q1P1" has substantive findings awaiting consolidation
      And its direct provider cannot write campaign files
      When Pathfinder requests consolidation from the direct provider
      Then the request asks the provider to return the complete research account

    Scenario: A provider reply without a stored account remains retryable
      Given pair "Q1P1" has substantive findings awaiting consolidation
      And its direct provider returns text without producing a stored research account
      When Pathfinder evaluates the consolidation attempt
      Then Pathfinder makes one more consolidation attempt

    Scenario: A returned research account proceeds directly to verification
      Given pair "Q1P1" has substantive findings awaiting consolidation
      When the direct provider returns a complete research account on its consolidation retry
      Then Pathfinder stores that research account before verification
      And the verifier assesses it once

    @contract
    Scenario: Provider call receipts retain evidence of generated output
      Given an OpenAI-compatible provider call reports positive output tokens and no parsed text
      When Pathfinder records the completed provider call
      Then the receipt identifies the process exit and terminal response event
      And the receipt retains the raw response events needed to account for the output tokens

    @contract
    Scenario: Completed provider output remains inspectable after parsing fails
      Given an OpenAI-compatible provider call completes with positive output tokens
      When Pathfinder completes the provider call without a parsed research account
      Then the receipt records the process exit status
      And the receipt records the terminal response event
      And the receipt retains the raw response events

  Rule: Each assessment decision has one operational consequence

    Scenario: A draft decision completes the investigation
      Given the verifier assesses the current research account
      When the verifier returns "DRAFT"
      Then the investigation finishes with status "DRAFT"
      And the verdict records the assessed account's digest

    Scenario: An iterate decision starts another research round
      Given the campaign permits another research round
      When the verifier returns "ITERATE" with an unanswered question
      Then the unanswered question is added to the research record
      And the investigation returns to peer research

    Scenario: An iterate decision at the round limit pauses the investigation
      Given the investigation has reached its research round limit
      When the verifier returns "ITERATE"
      Then the investigation finishes with status "PAUSE-ON-ITERATE"

    Scenario: A revise decision repairs the current account without new research
      Given the campaign permits a repair of the research account
      When the verifier returns "REVISE" with a correction
      Then the current account is repaired using that correction
      And the repaired account is independently assessed again

    Scenario: A revise decision at the repair limit pauses the investigation
      Given the investigation has reached its account repair limit
      When the verifier returns "REVISE"
      Then the investigation finishes with status "PAUSE-ON-REVISE"
