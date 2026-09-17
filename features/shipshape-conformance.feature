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

  @conformance
  Scenario: Production planks match current executable step patterns
    Given the implementation paths and executable scenarios from the rigging
    When the plank trace conformance check runs
    Then every plank is attached to a declaration and matches a current step pattern
    And every provisional plank names a scenario that carries "@captain"

  @conformance
  Scenario: Verification doubles carry an exceptional-double justification
    Given the verification paths from the rigging
    When the verification-double conformance check runs
    Then every test double carries an "@exceptional-double" justification

  @conformance
  Scenario: The configured default tier executes binding scenarios
    Given the binding scenarios and default tier from the rigging
    When the default tier coverage command runs
    Then at least one binding scenario executes
