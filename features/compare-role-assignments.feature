Feature: Compare models and backends by Pathfinder role

  Scenario: A comparison changes one role assignment while preserving its evidence base
    Given two Pathfinder runs use the same corpus snapshots, prompts, budgets, and tool policies
    And the runs differ in the model or backend assigned to one role
    When the runs are compared
    Then differences in that role's outcomes, cost, and latency are reported

  Scenario: Every role selects its model and backend independently
    Given a comparison includes scanning, research, consolidation, and verification
    When the operator defines a run
    Then each role has its own model and backend assignment

  Scenario: Repeating an assignment produces comparable evidence
    Given a role assignment has been run against frozen campaign inputs
    When the same assignment is repeated
    Then both runs retain the information needed to compare variation in outcomes, cost, and latency

  @sandbox
  Scenario: One frozen pair completes through independently assigned roles
    Given one frozen paper pair
    And role "scan" is assigned model "Qwen/Qwen3.5-397B-A17B-FP8" through ELM
    And roles "research", "consolidate", and "verify" are assigned model "Qwen/Qwen3.5-397B-A17B-FP8" through ELM
    When Pathfinder runs the assigned comparison workflow
    Then each role leaves a provider-produced receipt for its assigned model and backend
    And the comparison records the pair's final verification outcome
