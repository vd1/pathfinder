Feature: Edit an accepted research account through PCE

  Rule: A DRAFT investigation with real source text enters editing automatically

    Scenario: A DRAFT pair with real full text starts the edit stage
      Given pair "Q3P10" finished research with status "DRAFT"
      And pair "Q3P10" has full text fetched from its original source for "Q" and "P"
      When Pathfinder finishes running pair "Q3P10"
      Then the edit stage starts for pair "Q3P10"

    Scenario: A non-DRAFT outcome does not enter editing
      Given pair "Q1P1" finished research with status "PAUSE-ON-ITERATE"
      When Pathfinder finishes running pair "Q1P1"
      Then pair "Q1P1" does not enter the edit stage
      And pair "Q1P1" has no edited artifact recorded

  Rule: The edit stage runs PCE's role loop against real evidence

    Scenario: The editor stages a brief separating internal and external evidence
      Given pair "Q3P10" enters the edit stage
      When the editor stage begins
      Then the editor's brief cites the accepted research account as internal source
      And the editor's brief cites the fetched full text of "Q" and "P" as external source

    Scenario: The author drafts from the staged brief and the archivist preserves it
      Given pair "Q3P10" has a staged brief and source set
      When the author role executes
      Then a draft is produced
      And the archivist records the draft in its revision history before review

    Scenario: The fact-checker gate checks claims against real external sources only
      Given pair "Q3P10" has an archived draft
      When the fact-checker gate runs
      Then it checks the draft's claims against the fetched full text of "Q" and "P"
      And it does not read the accepted research account

    Scenario: The critic gate reviews the draft without the editor's internal notes
      Given pair "Q3P10" has an archived draft
      When the critic gate runs
      Then the critic's review has no access to the editor's brief or prior reviews

  Rule: Editing ends by editor acceptance or a fixed round limit

    Scenario: The editor accepts the draft within the round limit
      Given pair "Q3P10" is in its edit stage
      When the editor accepts the draft on or before round "3"
      Then the edit stage finishes with outcome "accepted"
      And the accepted draft is recorded as the pair's edited artifact

    Scenario: The round limit ends editing without acceptance
      Given pair "Q3P10" has completed round "3" of editing without acceptance
      When the editor evaluates round "3"
      Then the edit stage finishes with outcome "round-limit"
      And the last produced draft is recorded as the pair's edited artifact

  Rule: Every edit-stage dispatch produces a comparable receipt

    Scenario: Each PCE role dispatch in a round produces its own receipt
      Given the edit stage dispatches the editor, author, fact-checker, and critic for one round
      When each dispatch finishes
      Then each dispatch's receipt records role, backend, model, execution class, prompt digest, provider job identifier, raw response, outcome, latency, token usage, and cost

  Rule: Draft history is append-only

    Scenario: A later draft does not overwrite earlier draft history
      Given pair "Q3P10" has an archived round "1" draft
      When the author produces a round "2" draft
      Then the round "1" draft remains recorded in revision history
      And the round "2" draft becomes the current draft
