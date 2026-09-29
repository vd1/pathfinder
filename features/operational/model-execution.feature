Feature: Execute every model request through one seam

  Rule: Campaign stages submit immutable requests to interchangeable adapters

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

    Scenario: Adapter selection does not depend on Codex command semantics
      Given an immutable model request and a non-Codex synchronous adapter
      When Pathfinder executes the request
      Then the adapter receives the request without Codex command configuration
