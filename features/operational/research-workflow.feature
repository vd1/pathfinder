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
