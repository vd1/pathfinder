Feature: Discover connections between paper corpora

  @captain
  Scenario: The search reveals a promising connection across two fields
    Given one corpus contains research questions from "mechanism design"
    And another corpus contains techniques from "agentic cooperation"
    When Pathfinder examines the possible paper connections
    Then it identifies connections with evidence for both feasibility and scientific gain

  @captain
  Scenario: The strongest opportunities receive the available research effort
    Given Pathfinder has assessed more connections than the campaign can research
    When the campaign chooses its research candidates
    Then the candidates with the strongest combined feasibility and scientific gain are prioritized

  @captain
  Scenario: Continued discovery can reveal new research candidates
    Given Pathfinder has assessed the papers currently available from both fields
    When the campaign extends both corpora with earlier research
    Then newly available cross-field connections are assessed for admission to research
