Feature: Distinguish local calculation evidence from citation and command text

  Rule: Assessment evidence retains research artefacts without treating citations as files

    Scenario: DOI citations remain bibliography rather than missing local evidence
      Given a research ledger cites "10.5281/zenodo.14901404" and "10.1021/acs.jpcb.1c00399" as bare DOIs and resolver URLs
      And the ledger references a readable local calculation artefact
      When the workflow prepares tool-less consolidation and verification requests
      Then both requests retain the DOI citations and complete local calculation contents
      And no DOI or fragment of a resolver URL is read as a local file

    Scenario: An absolute interpreter command does not create a relative evidence reference
      Given a research ledger records the command "/usr/local/opt/python@3.14/bin/python3.14 ada/check_sector.py"
      And the referenced calculation script is readable
      When the workflow prepares tool-less consolidation and verification requests
      Then both requests contain the complete calculation script and command provenance
      And no fragment of the interpreter path is read as local evidence

    Scenario: A scholarly figure locator remains citation text rather than local evidence
      Given a research ledger cites "Methods/Fig.1" as the location of a published finding
      And the ledger references a readable local calculation artefact
      When the workflow prepares tool-less consolidation and verification requests
      Then both requests retain the scholarly locator and complete local calculation contents
      And the scholarly figure locator is not read as a local file

    Scenario: Local calculation evidence outside peer directories remains complete
      Given a research ledger references calculation artefacts under "calculations/results" and "shared" outside peer directories
      When the workflow prepares tool-less consolidation and verification requests
      Then both requests contain every referenced local calculation artefact in full

    Scenario: A missing local calculation outside peer directories still blocks assessment
      Given a research ledger references the missing local calculation "calculations/results/missing.json"
      When the workflow prepares a tool-less assessment request
      Then assessment blocks before provider dispatch and identifies "calculations/results/missing.json"

  Rule: Offline regression checks preserve evidence isolation

    These scenarios MUST exercise real local evidence assembly and workflow orchestration.
    Verification MAY control provider replies at the transport boundary.
    Verification MUST NOT invoke live models, campaigns, or PCE.
    Existing missing-file, parent-traversal, and symlink refusal scenarios remain binding.
