Feature: Steward a research campaign

  @captain
  Scenario: The campaign remains within its research budget
    Given the campaign has a finite research budget
    When further research would exceed that budget
    Then Pathfinder starts no further investigations
    And work already completed remains available

  @captain
  Scenario: The operator can suspend the campaign without losing active work
    Given the campaign has active and waiting investigations
    When the operator suspends the campaign
    Then active investigations preserve their latest completed work
    And waiting investigations remain available for a later continuation

  @captain
  Scenario: A suspended campaign continues from its recorded progress
    Given a campaign was suspended before every investigation finished
    When the operator continues the campaign
    Then Pathfinder continues the unfinished investigations without repeating completed work

  @captain
  Scenario: An interrupted investigation presents a clear recovery decision
    Given an investigation cannot continue automatically
    When the operator reviews the campaign
    Then Pathfinder identifies the affected investigation
    And Pathfinder presents the next safe recovery action
