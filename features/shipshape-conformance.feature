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
  Scenario: Structural verification does not substitute provider execution
    Given the verification paths from the rigging
    When the provider-substitution conformance check runs
    Then verification does not replace the model execution seam

  @conformance
  Scenario: The configured default tier executes binding scenarios
    Given the binding scenarios and default tier from the rigging
    When the default tier coverage command runs
    Then at least one binding scenario executes

  @conformance
  Scenario: Provider-class execution verification routes from its assigned inputs
    Given a provider-class execution scenario with an assigned backend, model, and execution class
    When the verification invokes the provider-class execution seam
    Then the invocation routing inputs match the scenario assignment

  @conformance
  Scenario: Campaign routing verification exercises the production workflow
    Given a campaign-routing scenario asserts a model transport request
    When the verification path to that request is inspected
    Then the path enters through the campaign workflow rather than a transport helper
