Feature: Research a shortlisted paper pair

  @captain
  Scenario: A promising connection becomes an independently assessed research account
    Given Pathfinder has selected a promising connection between two papers
    When researchers investigate how one paper can advance the other
    Then Pathfinder produces a research account grounded in both papers
    And an independent assessment states whether the connection is ready for a draft

  @captain
  Scenario: An unsupported connection does not become a draft
    Given Pathfinder has selected a promising connection between two papers
    When research finds no support for a useful connection
    Then Pathfinder records that the investigation is paused
    And it produces no draft claim from the connection

  @captain
  Scenario: Independent criticism can deepen the investigation
    Given researchers have proposed a connection between two papers
    When an independent assessment identifies a substantive unanswered question
    Then Pathfinder returns the question to research before deciding whether the connection is ready

  @captain
  Scenario: Independent criticism can narrow an overstated claim
    Given researchers have written an account of a connection between two papers
    When an independent assessment finds that a claim exceeds the evidence
    Then Pathfinder revises the account before assessing it again
