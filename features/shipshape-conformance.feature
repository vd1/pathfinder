Feature: Shipshape verification conformance

  @captain @conformance
  Scenario: The voyage watchbill file matches the Shipshape watchbill shape
    Given the Pathfinder repository root
    When the watchbill shape conformance check runs
    Then the watchbill file conforms when present

  @captain @conformance
  Scenario: The implementation tree contains no live perturbation marker
    Given the implementation paths from the rigging
    When the perturbation quiescence check runs
    Then no PERTURBATION marker is found
