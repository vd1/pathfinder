# The edit stage under "edit_scheme": "pce": julien-2's PCE role loop (author, archivist, fact-checker,
# critic, editor) ported into the engine (pathfinder/pce.py, prompts/pce-*.md). The single editor's note is
# the round's frozen baseline. Scenarios tagged @pce exercise the role loop; every dispatch here runs on the
# stub backend or a scripted dispatcher, never a live model, so the broad suite runs them.
Feature: Edit a readable note through PCE

  Rule: A finished investigation enters PCE editing with the single editor's note as its baseline

    Scenario: A finished pair starts the PCE round from the editor's note
      Given pair "Q3P10" finished research on a PCE campaign
      When the campaign processes pair "Q3P10" to completion
      Then the edit stage starts for pair "Q3P10"
      And the round's frozen baseline is the readable note the single editor wrote from the research account
      And that baseline is the editor's own note, not a copy of the account itself

    Scenario: An unfinished investigation does not enter editing
      Given pair "Q1P1" is still in research on a PCE campaign
      When Pathfinder runs the edit stage for pair "Q1P1"
      Then pair "Q1P1" does not enter the edit stage
      And pair "Q1P1" has no edited artifact recorded

  Rule: The edit stage runs PCE's role loop against real evidence

    @pce
    Scenario: Pathfinder runs PCE's role loop inside the engine
      Given pair "Q3P10" enters the edit stage
      When Pathfinder runs one PCE pass through the assigned runtime
      Then the PCE workflow directory contains its current draft, archived draft, gate reviews, and state
      And the campaign receipts record the author, archivist, fact-checker, critic, and editor dispatches in workflow order
      And each role's prompt is an engine prompt a campaign extends with an append overlay

    Scenario: The editor stages a brief separating internal and external evidence
      Given pair "Q3P10" enters the edit stage
      When the editor stage begins
      Then the editor's brief cites the accepted research account as internal source
      And the editor's brief cites the fetched full text of "Q" and "P" as external source

    @pce
    Scenario: The author drafts from the staged brief and the archivist preserves it
      Given pair "Q3P10" has a staged brief and source set
      When the author role executes
      Then a draft is produced
      And the archivist records the draft in its revision history before review

    @pce
    Scenario: The fact-checker gate checks claims against real external sources only
      Given pair "Q3P10" has an archived draft
      When the fact-checker gate runs
      Then it checks the draft's claims against the fetched full text of "Q" and "P"
      And it does not read the accepted research account

    @pce
    Scenario: The critic gate reviews the draft without internal sources or prior reviews
      Given pair "Q3P10" has an archived draft
      When the critic gate runs
      Then the critic's review has no access to the internal sources or prior reviews

    Scenario: Oversized edit-stage evidence is blocked before dispatch
      Given pair "Q3P10"'s staged brief and source set exceeds its assigned context limit
      When the edit stage prepares a role dispatch
      Then Pathfinder blocks the dispatch and the round ends for review
      And the round keeps the whole evidence rather than truncating it

  Rule: Editing ends by editor acceptance or a fixed pass limit

    Scenario: Campaign completion runs the PCE edit stage for a DRAFT pair
      Given pair "Q3P10" finished research on a PCE campaign
      When the campaign processes pair "Q3P10" to completion
      Then PCE produces pair "Q3P10"'s edited artifact
      And the campaign records PCE's final edit outcome

    Scenario: The edited paper passes the existing LaTeX and BibTeX checks
      Given PCE has produced pair "Q3P10"'s edited paper and references
      When Pathfinder validates the edited artifact
      Then the edited paper builds successfully with its bibliography
      And every cited reference passes Pathfinder's reference checks

    @pce
    Scenario: The editor accepts the draft within the pass limit
      Given pair "Q3P10" is in its edit stage
      When the editor accepts the draft on or before pass "3"
      Then the edit stage finishes with outcome "accepted"
      And the accepted draft is recorded as the pair's edited artifact

    @pce
    Scenario: The pass limit ends editing without acceptance
      Given pair "Q3P10" is in its edit stage
      When the editor asks for a revision on every pass up to the limit of "3"
      Then the edit stage finishes with outcome "review_required"
      And the last produced draft stays in the round while the editor's note remains the pair's edited artifact

  Rule: Every edit-stage dispatch produces a comparable receipt

    @pce
    Scenario: Each PCE role dispatch in a round produces its own receipt
      Given the edit stage dispatches the author, archivist, fact-checker, critic, and editor for one pass
      When each dispatch finishes
      Then each dispatch's receipt records role, backend, model, execution class, prompt digest, provider job identifier, raw response, outcome, latency, token usage, and cost

    @pce
    Scenario: PCE role receipts persist in the campaign evidence
      Given PCE completes one edit pass for pair "Q3P10"
      When the campaign is inspected after the edit stage
      Then every PCE role dispatch remains recorded in the campaign receipts

  Rule: Draft history is append-only

    @pce
    Scenario: A later draft does not overwrite earlier draft history
      Given pair "Q3P10" has an archived pass "1" draft
      When the author produces a pass "2" draft
      Then the pass "1" draft remains recorded in revision history
      And the pass "2" draft becomes the current draft
