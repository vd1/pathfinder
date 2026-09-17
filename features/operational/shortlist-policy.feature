Feature: Apply the research shortlist policy

  Rule: Combined feasibility and gain determine priority

    Scenario: A balanced connection outranks a weaker combined opportunity
      Given pair "Q1P1" has feasibility "50" and scientific gain "40"
      And pair "Q2P1" has feasibility "10" and scientific gain "10"
      When Pathfinder ranks the assessed connections
      Then pair "Q1P1" ranks before pair "Q2P1"

    Scenario: A fixed-capacity shortlist selects the top fraction
      Given all possible paper pairs have been assessed
      And the campaign reserves research capacity for the top "10" percent
      When Pathfinder builds the shortlist
      Then the highest-ranked "10" percent of assessed pairs are selected

    Scenario: An open-ended shortlist admits every pair above its threshold
      Given pair "Q1P1" has combined score "2000"
      And pair "Q2P1" has combined score "100"
      When the admission threshold is "1500"
      Then pair "Q1P1" is selected
      And pair "Q2P1" is not selected

  Rule: Started investigations retain their place

    Scenario: Rebuilding the shortlist preserves a started investigation
      Given research has started for pair "Q2P1"
      And pair "Q2P1" is below the current admission threshold
      When Pathfinder rebuilds the shortlist
      Then pair "Q2P1" remains selected
