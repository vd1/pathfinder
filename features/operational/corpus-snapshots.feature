Feature: Consume prepared corpus snapshots

  Rule: Prepared snapshots are the campaign input boundary

    Scenario: A valid snapshot supplies stable paper records
      Given a prepared corpus snapshot contains records with stable identifiers, titles, and abstracts
      And a record may reference optional full text within the snapshot
      When Pathfinder validates the snapshot
      Then every record can be used without an acquisition adapter

    Scenario: A run leaves its source snapshots unchanged
      Given a run references two prepared corpus snapshots
      When Pathfinder completes or resumes the run
      Then both source snapshot digests remain unchanged

  Rule: Pair provenance derives from immutable snapshots

    Scenario: A run manifest pins both corpus snapshots
      Given prepared snapshots "questions" and "techniques"
      When a comparison run is created
      Then its manifest records the digest of each snapshot

    Scenario: Pair identities remain stable for identical snapshots
      Given two runs reference identical ordered corpus snapshots
      When both runs enumerate their cross-corpus pairs
      Then corresponding source records have the same pair identity in both runs

    Scenario: Every result traces to source records and snapshots
      Given a run produces a result for one cross-corpus pair
      When the result provenance is inspected
      Then it identifies both source record identifiers
      And it identifies both source snapshot digests
