Feature: Operate and recover a research campaign

  Rule: New work starts only within campaign limits

    @captain
    Scenario: Projected spend prevents an unaffordable admission
      Given recorded spend is "1.00" dollars
      And the next investigation is estimated to cost "1.00" dollars
      And the campaign budget is "1.50" dollars
      When Pathfinder considers admitting the investigation
      Then the investigation is not admitted
      And the campaign records a budget stop

  Rule: Suspension preserves resumable progress

    Scenario: A stop request drains admitted work
      Given pair "Q1P1" is being investigated
      And pair "Q1P2" is waiting for admission
      When the operator requests a stop
      Then pair "Q1P1" finishes and preserves its active stage
      And pair "Q1P2" remains waiting

    Scenario: Completed stages are not repeated after continuation
      Given pair "Q1P1" stopped after its research account was produced
      When the campaign continues
      Then pair "Q1P1" continues with independent assessment

  Rule: Recovery follows recorded state

    Scenario: A missing research account returns to consolidation
      Given pair "Q1P1" stopped before its research account was produced
      When the operator inspects pair "Q1P1"
      Then the next safe recovery action is "run consolidate"

    Scenario: An existing research account proceeds to assessment
      Given pair "Q1P1" stopped with a research account awaiting assessment
      When the operator inspects pair "Q1P1"
      Then the next safe recovery action is "run verify"

    Scenario: A blocked investigation waits for operator recovery
      Given pair "Q1P1" cannot continue automatically
      When Pathfinder admits pending investigations
      Then pair "Q1P1" is not admitted
