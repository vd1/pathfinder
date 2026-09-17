Feature: Operate the connection discovery pipeline

  Rule: The pipeline examines each cross-corpus paper pair once

    Scenario: A completed pair assessment records its evidence
      Given paper "q1" is in the question corpus
      And paper "p1" is in the technique corpus
      When the connection judge assesses pair "Q1P1"
      Then pair "Q1P1" records feasibility, scientific gain, a proposed connection, and rationale

    Scenario: A resumed scan skips completed pair assessments
      Given pair "Q1P1" already has a recorded assessment
      And pair "Q1P2" has no recorded assessment
      When the connection scan resumes
      Then pair "Q1P1" is not assessed again
      And pair "Q1P2" is assessed

  Rule: Continued discovery preserves stable paper identities

    Scenario: Earlier papers extend a corpus without changing existing positions
      Given corpus "Q" contains papers "q1" and "q2" in that order
      When its next page contains papers "q2" and "q3"
      Then corpus "Q" contains papers "q1", "q2", and "q3" in that order
      And the next page begins after the previously requested papers
