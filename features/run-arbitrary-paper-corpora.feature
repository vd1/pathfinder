Feature: Run Pathfinder on arbitrary paper corpora

  Scenario: Prepared corpora define a new discovery campaign
    Given two prepared paper corpora from domains chosen by the operator
    When the operator starts a Pathfinder campaign from those corpora
    Then Pathfinder examines connections between the papers in those corpora
    And every result identifies its two source papers

  Scenario: A campaign preserves the exact corpus population it examined
    Given a Pathfinder campaign was created from two prepared corpus snapshots
    When the campaign is inspected or repeated
    Then the exact source snapshots used by the campaign are identifiable

  Scenario: Corpus size changes the workload without changing discovery semantics
    Given two prepared corpus snapshots conform to the Pathfinder corpus contract
    When their number of papers changes
    Then Pathfinder applies the same connection assessment to every cross-corpus pair
