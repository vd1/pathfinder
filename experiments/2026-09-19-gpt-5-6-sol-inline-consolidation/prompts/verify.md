Act as an independent reviewer. Above are papers {{Q_INPUT}} and {{P_INPUT}}, the ledger, and {{NOTE}}.

Choose DRAFT when the note establishes a supported, non-obvious result worth a paper section. Choose REVISE when the ledger supports the result but the note can be corrected without new research. Choose ITERATE when one specific check using available material could close a promising gap. Choose PAUSE when the connexion is unsupported, unproductive, or needs unavailable evidence.

Output exactly one JSON object:
{"decision":"DRAFT|REVISE|ITERATE|PAUSE","reason":"three sentences at most","action":"corrections for REVISE, one next check for ITERATE, otherwise null"}
