Feature: Define reproducible role comparisons

  Rule: A manifest freezes all comparison factors

    Scenario: A run manifest assigns execution independently by role
      Given a comparison includes roles "scan", "research", "consolidate", and "verify"
      When the operator defines a run manifest
      Then every role records its model, backend, execution class, prompt arrangement, tool policy, and budget

    Scenario: A run manifest freezes every peer assignment
      Given a comparison includes peers "critic" and "specialist"
      When the operator defines their run manifest assignments
      Then every peer records its name, model, backend, execution class, thinking limit, output token limit, and allowed tools
      And a peer with no tools records an empty allowed-tools list

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

    Scenario: Each provider stage receives an immutable evidence pack
      Given one frozen paper pair has source records, prompts, and prior stage outputs
      When Pathfinder prepares role "consolidate" for provider execution
      Then the provider request identifies the digests of every supplied input
      And later campaign changes do not alter that request

    Scenario: Consolidation receives complete evidence independent of its harness
      Given one frozen paper pair has source text "QUESTION-EVIDENCE" and "PROPOSAL-EVIDENCE"
      And its peer ledger contains "LEDGER-EVIDENCE"
      And its prior account contains "PRIOR-ACCOUNT"
      And its campaign has no inline-evidence switches
      When Pathfinder builds its consolidation model request
      Then the request contains "QUESTION-EVIDENCE", "PROPOSAL-EVIDENCE", "LEDGER-EVIDENCE", and "PRIOR-ACCOUNT"
      And the request asks for the complete research account
      And the request contains no file-reading instruction
      And the request states that its inline evidence is complete and no tools are available

    Scenario: Provider stages consume prepared evidence without acquisition
      Given one frozen paper pair contains all evidence required by role "verify"
      When Pathfinder executes role "verify" through its assigned provider
      Then the role completes without fetching or discovering additional evidence

    Scenario: Provider stages enforce their assigned context and output budgets
      Given role "consolidate" has an assigned input context limit of "64000" tokens and an output token limit
      When Pathfinder prepares role "consolidate" for one frozen paper pair
      Then the request stays within the assigned input context limit
      And the provider call enforces the assigned output token limit

    Scenario: Oversized evidence is compressed or blocked before provider execution
      Given role "consolidate" has more than "64000" input tokens of frozen evidence
      When Pathfinder prepares role "consolidate" for provider execution
      Then Pathfinder uses a recorded compression result or blocks the request
      And Pathfinder does not silently truncate the evidence

    Scenario: Provider-class execution invokes the provider without agent tools
      Given role "verify" is assigned execution class "provider"
      When Pathfinder executes role "verify" for one frozen paper pair
      Then the provider request exposes no workspace or search tools

    Scenario: Execution routing depends on assignment capabilities rather than provider identity
      Given two providers support the same provider execution class
      When Pathfinder schedules the same frozen stage through each provider
      Then both stages use the provider execution route

    Scenario: Independent provider stages can be submitted as a batch
      Given several frozen paper pairs are ready for role "scan"
      When Pathfinder prepares their provider stage jobs
      Then each job has independent immutable inputs and a stable result identity
      And submitting the jobs together does not change their results

    Scenario: Campaign stages share one model execution request seam
      Given one frozen paper pair enters scanning and research with two configured peers
      When Pathfinder executes scan, peer, consolidation, and verification model requests
      Then scan, both peers, consolidation, and verification submit immutable requests through the same model execution seam

    Scenario: Pi is one synchronous model execution adapter
      Given a model request requires synchronous workspace tools
      When Pathfinder assigns the request to Pi
      Then Pi executes the same immutable request accepted by other synchronous adapters

    Scenario: Batch execution consumes the synchronous request contract
      Given several independent immutable model requests
      When Pathfinder assigns them to a batch adapter
      Then the adapter returns one result for each unchanged request identity

    Scenario: A campaign peer stage invokes every manifest assignment once per attempt
      Given a campaign loaded from a manifest assigns models "m1" and "m2" to two peers
      And one frozen paper pair is ready for peer research
      When Pathfinder executes one peer stage attempt
      Then one peer request is recorded for model "m1"
      And one peer request is recorded for model "m2"

    Scenario: Provider routing verification exercises the campaign execution path
      Given a campaign loaded from a manifest assigns execution adapters to scan, two peers, consolidation, and verification
      And one frozen paper pair is ready for campaign execution
      When Pathfinder verifies execution routing
      Then every recorded campaign call follows its manifest assignment

    Scenario: Provider consolidation executes without tools through the campaign workflow
      Given a campaign is loaded from a manifest that assigns role "consolidate" to model "Qwen/Qwen3.5-397B-A17B-FP8" through ELM with an empty allowed-tools list
      And one frozen paper pair has substantive findings awaiting consolidation
      When Pathfinder runs consolidation through the campaign workflow
      Then the consolidation transport request uses the assigned model and backend
      And the consolidation transport request exposes no tools

    Scenario: Adapter selection does not depend on Codex command semantics
      Given an immutable model request and a non-Codex synchronous adapter
      When Pathfinder executes the request
      Then the adapter receives the request without Codex command configuration

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
