Feature: Explicit external research citations preserve local evidence checks
  Research notes may name files in a public repository without downloading them.
  External citations remain visible to every reviewer with their availability status.

  Rule: External citation declarations bind to exact source text
    A thread may contain external-references.json with version 1 and a references array.
    Each record has document, path, url, status and text_sha256.
    Status is external or unavailable. The URL is an absolute HTTP or HTTPS citation.
    The document and cited path are safe thread-relative paths without parent traversal.
    A ledger.jsonl record also has ledger_seq and binds text_sha256 to that entry's text.
    Other records bind text_sha256 to the exact UTF-8 document bytes.
    A declared path must occur in its bound text. The declaration is an explicit citation,
    not evidence that the remote file was downloaded or scientifically validated.
    Present local evidence remains subject to all ordinary read and alias checks.
    Each branch bundle keeps its own declarations and namespace.

    Scenario: Declared repository paths remain citations during direct review
      Given an EVA-minus ledger cites external "ammo/msm/_msm.py" in a bound declaration
      When Pathfinder prepares its first Vera review
      Then Vera receives the ledger and its external citation declaration
      And the cited repository file is not required in the local workspace

    Scenario: Ledger growth preserves entry-scoped citation binding
      Given an EVA-minus ledger cites external "ammo/msm/_msm.py" in a bound declaration
      And another attributed ledger entry is appended
      When Pathfinder prepares its first Vera review
      Then Vera receives the ledger and its external citation declaration

    Scenario: Changed citation text invalidates its declaration
      Given an EVA-minus ledger cites external "ammo/msm/_msm.py" in a bound declaration
      And the declared ledger entry text is changed after declaration
      When Pathfinder prepares its first Vera review
      Then research blocks before provider dispatch because the citation binding is stale

    Scenario: External declarations cannot hide missing local calculations
      Given an EVA-minus ledger cites external "ammo/msm/_msm.py" in a bound declaration
      And another ledger entry references missing local "calculations/missing.json"
      When Pathfinder prepares its first Vera review
      Then research blocks before provider dispatch and identifies "calculations/missing.json"

    Scenario: A declaration cannot exempt another ledger entry
      Given an EVA-minus ledger cites external "ammo/msm/_msm.py" in a bound declaration
      And another ledger entry references missing local "ammo/msm/_msm.py"
      When Pathfinder prepares its first Vera review
      Then research blocks before provider dispatch and identifies "ammo/msm/_msm.py"

    Scenario: Present cited files retain ordinary alias protection
      Given an EVA-minus ledger cites external "ammo/msm/_msm.py" in a bound declaration
      And that cited workspace path is an alias to a file outside the thread
      When Pathfinder prepares its first Vera review
      Then research blocks before reading the aliased citation file

    Scenario: Unavailable external inputs remain visible in joint EVA
      Given joint EVA imports a branch with a bound unavailable external citation
      When Pathfinder prepares joint research
      Then the joint researcher receives the citation URL and unavailable status
      And the external citation is resolved only in its originating branch namespace

  Rule: Verification uses retained responses and local fixtures
    These scenarios exercise real request preparation without invoking live providers.
    Existing missing-evidence, traversal, symlink and EVA regression contracts remain binding.
