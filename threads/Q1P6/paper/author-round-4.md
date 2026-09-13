I've revised the paper for round 4. It builds cleanly with no warnings or undefined citations, and I checked all 7 pages visually. The style-ban check passes on `paper.tex` and `search.md`.

**What the paper claims.** MARS-RA's shaping term subtracts potential vectors of different lengths when the active coalition changes, so as written it is not well-defined. The repair puts every agent in a fixed population space: inactive agents take null actions and every agent keeps a reward record on every transition. Each agent's payoff then shifts by a constant, −ρΦ₀ⁱ, so best responses and Nash equilibria are preserved whatever the comparisons say. If rewards are recorded only while an agent is active, entry and exit leave boundary terms that can depend on policy. The paper also separates Bradley–Terry sampling error from semantic bias, and says why no finite-training guarantee follows without an assumption about how stable the learner is. Every claim carries ledger entry numbers in a comment.

**Searches and what they changed** (all recorded in `paper/search.md`):
- **Devlin and Kudenko, AAMAS 2012** (which P itself cites). I read the author-deposited PDF. It already proves invariance when the potential changes over time. The paper now says this covers the "arbitrary comparison outputs" clause of its theorem.
- **Grześ, AAMAS 2017.** I read the author's PDF. It shows that a nonzero potential at an action-dependent terminal state leaves a policy-dependent term. That is the main step behind the exit boundary term, and the paper now says so plainly. What remains new is the fixed-population record-keeping and placing these terms at individual agents' entry and exit.
- **Neither of these two is in the bibliography.** Their ACM DOIs return 404 at doi.org and Crossref, the ACM pages return 403, and neither is on arXiv, so I couldn't verify them. The paper names them in the text and says why they aren't cited.
- **Lu, Schwartz and Givigi.** I checked the arXiv abstract page and added arXiv:1401.3907 to its entry.
- **Other queries** (agents entering and leaving, variable numbers of agents, inactive agents, open ad hoc teamwork) turned up nothing on the specific result. That includes three arXiv abstracts I read and a survey of multi-agent learning in open environments, which never mentions shaping. Semantic Scholar was rate-limited.

**F1.**
- **Section 4:** the scalarisation paragraph now says only the coordinate sum is shown to erase comparison information (the credits always sum to 1). It says outright that the supporting notes (ledger entries 30 and 33, and the note) word this more broadly than the argument supports. Other scalar potentials, such as a weighted sum with unequal weights, can depend on the comparisons, and the paper doesn't rule them out.
- **Interpretation:** I removed "the only supported location of any benefit" and replaced it with a statement backed by ledger entries 4 and 7. Exact shaping, per-agent or scalar, changes return only by an initial offset, so any benefit lies in finite training. Per-agent redistribution is no longer called the only route.
- **Conclusion:** now limited to the coordinate sum, with other scalarisations marked as not analysed.
- **Limitations and open questions:** both now list comparison-dependent scalar team potentials.

**Also fixed:** the round-3 source used dollar-sign maths, which the form rules forbid. All inline maths now uses `\( ... \)`.

Build files are left in place. I haven't committed anything or run `/push`, because this directory is managed by the pipeline (`paper.json`).

Sources:
- [Lu, Schwartz, Givigi, arXiv:1401.3907](https://arxiv.org/abs/1401.3907)
- [Devlin and Kudenko 2012, White Rose record](https://eprints.whiterose.ac.uk/id/eprint/75121/)
- [Grześ 2017, author PDF](https://www.cs.kent.ac.uk/people/staff/mg483/documents/grzes17goals-in-pbrs.pdf)
- [arXiv:2412.14779](https://arxiv.org/abs/2412.14779), [arXiv:2305.18380](https://arxiv.org/abs/2305.18380), [arXiv:2511.00034](https://arxiv.org/abs/2511.00034), [arXiv:2312.01058](https://arxiv.org/pdf/2312.01058)