# A clock-aware executable fallback for LLM double auctions

## Sharpened question

I replace the broad question "can contracts improve LLM markets?" with a narrower one:

> When LLM traders stall in a continuous double auction, can an exact market clock plus an executable limit-on-close commitment recover gains from trade without destroying price discovery, and does a natural-language intention fail to do so because it becomes another anchor?

The intervention is unilateral, so it does not add a 22-agent contract-negotiation problem. Before or during a round, each trader may authorize: at iteration τ, if still unfilled and the opposite standing quote is individually rational, execute against it, subject to the trader's private reservation price. This is a limit-on-close order rather than a bilateral promise.

## Evidence supplied by Q

Q's agents know that a cap exists but are not told its value. The mechanism sets T = 300 and says termination occurs at that cap (Q, lines 247-259), while the system prompt says that a round also ends "once no one can post an improving order" and gives no value for the cap (Q, lines 515-543). Market-history lines reveal the iteration of accepted and newly posted orders (Q, lines 621-634), so elapsed time is partly inferable, but T and the remaining fraction of the horizon are not. Thus the claim that agents give "little regard" to failure-to-trade risk (Q, line 368) is not cleanly separable from horizon opacity or ambiguous perceived stopping hazard.

An audit of the released repository at commit `af6f792` resolves the mechanism side for the current code. `make_check_round_node` ends a round at the tick cap, with fewer than two active agents, or on `_deadlocked`; `_deadlocked` returns false whenever an active strategy is not `zi_c`, explicitly treating LLM and ZI-U agents as live. Active LLM populations therefore do not terminate under the prompt's no-improving-order description. They run to the cap unless attrition leaves fewer than two agents. Q links the repository but does not identify a frozen experiment commit, so this audit cannot establish that the historical runs used the same control logic. Source: https://github.com/jswistak/competitive-market-simulation/blob/af6f7925384efed3a8b84b55996e6b31d6014f7d/src/market_simulation/graph/nodes/control.py#L313-L395

The market consequence is large. GPT Large makes small improvements until termination, completes only 2.2 to 3.8 trades per round, and reaches allocative efficiency 0.36 to 0.67 (Q, line 360). Q also finds that crossing is associated with urgency and execution language rather than margin optimization (Q, lines 407-438). This makes clock visibility and a deadline-contingent execution instruction targeted interventions, not generic prompting.

## Evidence supplied by P

P shows that commitment representation changes downstream exchange. Programmatic tile contracts execute structured obligations automatically, while natural-language contracts retain the dialogue and require judge interpretation (P, lines 248-303). On mutually dependent boards, both representations cover nearly the same number of moves, about 2.6 per game, yet natural-language contracts reduce residual trade: 1.95 versus 3.28 trades in the regular-trading appendix (P, lines 1381-1393). Agents declining trade cite the contract more often under natural language, 86% versus 60% (same passage). In the main Pay-for-Partner results, both-finished is 46% under natural-language contracts, 61% without a contract, and 79% under programmatic tile contracts (P, lines 405-414).

This cautions against an ordinary natural-language promise to "trade before the deadline." It may add a salient artifact without making execution reliable. P therefore supplies the representation contrast that Q lacks.

## Minimal experiment and predictions

Use Q's released environment and cross two factors:

1. Horizon information: the existing vague cap versus explicit T and a remaining-iterations or t/T signal.
2. Commitment: none, a natural-language stated intention with matched wording, or a machine-executable limit-on-close authorization.

Pre-register trade count, allocative efficiency, price dispersion α, surplus per agent, time to fill, and the distribution of concession sizes. Preserve reservation-price privacy and prohibit loss-making execution. Compare the same models, value schedules, random activation sequences, and token budgets.

The key comparison is not merely executable versus baseline. Horizon-only disclosure tests whether Q's failure is horizon opacity. Natural-language intention versus executable authorization tests whether semantics alone help or instead anchor behavior. Pin the implementation version, make the mechanism and prompt consistent across conditions, and sweep T to distinguish an interface artifact from persistent slow convergence. A useful positive result requires executable authorization to improve surplus and completion beyond horizon disclosure without materially worsening α. If horizon disclosure alone closes the gap, P's commitment machinery is unnecessary. If all deadline mechanisms cause agents to wait strategically until close, reduce price discovery, or misallocate units, the proposed repair fails.

## Limits and unresolved points

P studies two-player spatial cooperation, not a many-agent double auction, so transport of its anchoring effect is a hypothesis. Its natural-language and programmatic conditions differ in runtime interpretation as well as surface representation. Similar contract-covered move counts reduce, but do not eliminate, the possibility that contract quality differs. Q's lexical traces are available for one model and are correlational. Q's prompt describes a no-improvement endpoint that the audited current code does not operationalize for LLMs; because Q does not pin the experiment commit, historical code provenance remains unresolved. The executable fallback may mechanically improve trade volume while producing poor prices, which is why both surplus and α are required.

The publishable contribution would be an institution-interface result: market alignment depends jointly on time information and whether commitments are executable, and a salient but incomplete natural-language commitment can crowd out the residual exchange needed for efficiency.
