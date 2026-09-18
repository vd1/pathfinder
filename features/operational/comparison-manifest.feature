Feature: Define reproducible role comparisons

  Rule: A manifest freezes all comparison factors

    Scenario: A run manifest assigns execution independently by role
      Given a comparison includes roles "scan", "research", "consolidate", and "verify"
      When the operator defines a run manifest
      Then every role records its model, backend, execution class, prompt arrangement, tool policy, and budget

    Scenario: A controlled comparison varies one role assignment
      Given a baseline run manifest
      When the operator creates a comparison arm for role "verify"
      Then only role "verify" may differ in model or backend
      And corpus snapshots, prompts, budgets, and other role assignments remain unchanged

    Scenario: A run records the material needed for reproduction
      Given a valid run manifest and two prepared corpus snapshots
      When the comparison run starts
      Then it records the manifest digest, snapshot digests, and prompt digests before role execution

  Rule: Execution class follows role requirements

    Scenario: A self-contained role uses its assigned provider interface
      Given role "scan" is assigned model "Qwen/Qwen3.5-397B-A17B-FP8" through ELM
      And ELM authenticates with environment variable "ELM_API_KEY"
      When role "scan" executes a minimal frozen paper pair
      Then the receipt retains ELM's provider identifier, raw response, token usage, latency, and cost

    Scenario: A tool-using role uses its assigned agent harness
      Given role "research" requires workspace tools or multiple turns
      And its backend is "pi"
      When the comparison run schedules role "research"
      Then it executes the role through Pi with the manifest's tool policy

    Scenario: Subscription execution remains an explicit assignment
      Given role "consolidate" is assigned backend "claude"
      When the comparison run schedules role "consolidate"
      Then it executes through Claude Code rather than a batch provider

    Scenario: Direct-provider consolidation returns its account in the response
      Given role "consolidate" is assigned execution class "provider" through ELM
      And the provider cannot write campaign files
      When Pathfinder consolidates a frozen paper pair
      Then the provider response becomes the pair's research account

    Scenario: Provider-class consolidation bypasses the workspace agent harness
      Given retained provider events for pair "Q7P10" include workspace command execution
      And role "consolidate" is assigned execution class "provider" through ELM
      When Pathfinder consolidates the frozen paper pair
      Then consolidation executes through the ELM provider interface
      And the provider events contain no workspace command execution

    Scenario: Direct-provider verification assesses the consolidated account
      Given a direct-provider consolidation produced a research account
      And role "verify" is assigned execution class "provider" through ELM
      When Pathfinder verifies the frozen paper pair
      Then the pair records the provider's verification decision

    Scenario: Assigned comparison execution honours each role's execution class
      Given one frozen paper pair
      And each comparison role has a model, backend, and execution class assignment
      When Pathfinder runs the assigned comparison workflow
      Then each role follows its assigned execution route
      And consolidation completes before verification

    Scenario: Provider execution uses the route selected from its assignment
      Given role "consolidate" is assigned model "Qwen/Qwen3.5-397B-A17B-FP8" and execution class "provider" through ELM
      When Pathfinder executes role "consolidate" for one frozen paper pair
      Then consolidation executes through the ELM provider interface

    Scenario: Assigned provider execution has a focused timeout
      Given role "consolidate" is assigned model "Qwen/Qwen3.5-397B-A17B-FP8" and execution class "provider" through ELM
      When Pathfinder executes role "consolidate" for one frozen paper pair
      Then the provider call has a "120" second timeout

    Scenario: Assigned provider execution retains its tier budget
      Given role "consolidate" is assigned model "Qwen/Qwen3.5-397B-A17B-FP8" and execution class "provider" through ELM
      And role "consolidate" is assigned budget "1" in its comparison tier
      When Pathfinder executes role "consolidate" for one frozen paper pair
      Then the provider receipt retains budget "1" for role "consolidate"

    Scenario: Assigned research stages enter the campaign research workflow
      Given one frozen paper pair
      And each comparison role has a model, backend, and execution class assignment
      When Pathfinder runs the assigned comparison workflow
      Then consolidation and verification execute through the pair's research stages

  Rule: Receipts preserve comparable observations

    Scenario: Every role execution produces a comparable receipt
      Given a role executes within a comparison run
      When the execution finishes
      Then its receipt records role, backend, model, execution class, prompt digest, provider job identifier, raw response, outcome, latency, token usage, and cost

    Scenario Outline: ELM models can be assigned through supported harnesses
      Given role "research" is assigned model "<model>" through ELM
      And its backend is "<backend>"
      When the run manifest is validated
      Then the assignment is accepted

      Examples:
        | model                          | backend  |
        | gpt-5.6-sol                    | opencode |
        | gpt-5.6-sol                    | pi       |
        | Qwen/Qwen3.5-397B-A17B-FP8    | opencode |
        | Qwen/Qwen3.5-397B-A17B-FP8    | pi       |
