# Market welfare, gate correctness, and tail certification

## Question

Can the room-level, selective certification principle of P be used to say more about Q's claim that LLM double auctions are inefficient? The useful transfer is the **unit of statistical coverage**, a complete market run. Transferring P's wall-distance margin to the exchange's bid-ask test would require a new and presently unsupported model of quote error: Q's simulator knows the submitted prices exactly.

Q's *Trading Mechanism* defines a hard crossing rule, \(b_{i,t}\geq a_t^\star\) for a buyer, and Q's *Market-Wide Outcomes* reports mean trade counts and mean allocative efficiency over ten simulations per model. P's *Calibrated selective certificate* takes exchangeable, ground-truthed episodes as units and uses one order statistic to cover every non-abstained decision within a new episode. P expressly does not infer downstream task success from first-gate correctness. Those facts suggest a sharper question: what can be certified about a **whole future market run**, and what part of Q's welfare deficit is actually attributable to the number of trades?

## Exact welfare decomposition in Q's market

Q's *Market Environment* gives each side the eleven reservation values \(0.75,1.00,\ldots,3.25\), with one trade per agent per round. The maximum surplus from exactly \(k\) trades is obtained by selecting the \(k\) highest-value buyers and \(k\) lowest-cost sellers. Its marginal increments are

\[
2.5,\ 2.0,\ 1.5,\ 1.0,\ 0.5,\ 0,\ -0.5,\ldots,-2.5,
\]

so

\[
W_{\max}(k)=\sum_{j=1}^{k}\left(2.5-0.5(j-1)\right)
=2.75k-0.25k^2,
\qquad W^*=7.5.
\]

The sixth equilibrium trade has zero surplus. Thus five appropriately selected trades already realize \(W^*\); the condition \(N<6\) does not imply inefficient allocation. Conversely, six trades need not be efficient if they select the wrong agents. The transaction prices cancel from total surplus, though they matter for individual profit and behavior.

For each round, let \(N\) be its trade count and \(W\) its realized surplus. The identity

\[
W^*-W=
\underbrace{W^*-W_{\max}(N)}_{\text{quantity loss}}+
\underbrace{W_{\max}(N)-W}_{\text{selection loss}}
\]

has nonnegative terms. The first measures the best allocation possible at the realized count. The second measures lost value from which agents traded. It remains valid if a submitted offer yields negative profit, which Q's *Market Environment* says the mechanism permits. Q's summary table cannot recover the exact two components; the per-run trade records are needed for that. It does, however, bound the quantity component below.

Let \(\mu=\mathbb E N\), \(a=\lfloor\mu\rfloor\), and \(f=\mu-a\). Since \(N\) is integer valued, \(\operatorname{Var}(N)\geq f(1-f)\). The quadratic formula above gives

\[
\mathbb E[W^*-W_{\max}(N)]
=7.5-W_{\max}(\mu)+0.25\operatorname{Var}(N)
\geq7.5-W_{\max}(\mu)+0.25f(1-f).
\]

For GPT Large in Q's fourth round, mean count \(\mu=2.2\) implies a minimum mean quantity loss of \(2.70\) surplus units. Reported mean efficiency \(0.36\) implies total mean loss of about \(4.80\), so at least about \(56\%\) of that gap must come from trade count. Across all five GPT Large rounds, the corresponding lower bounds sum to \(8.00\) against about \(17.625\) total loss, or about \(45\%\). These percentages use rounded table values. The bounds partially support Q's stalling account, but cannot show that incremental bidding caused the low counts or measure the remaining selection loss exactly.

This is a specific instance of P's interface warning: certifying or counting the first threshold event does not certify the downstream objective. The table-level bound tests part of Q's proposed mechanism without refuting Q's observed inefficiency. Q's efficiencies below one establish that inefficiency independently of its trade counts.

## Finite-sample next-run statement

Fix a model, prompt, market institution, and five-round protocol before calibration. Treat each independent complete simulation as an episode. Let \(E_{ir}=W_{ir}/7.5\) be efficiency for round \(r\) in calibration run \(i\), and define the whole-run score

\[
R_i=\max_{1\leq r\leq 5}(1-E_{ir})=1-\min_{1\leq r\leq5}E_{ir}.
\]

For \(n\) exchangeable calibration runs and a new run from the same population, set \(k=\lceil(n+1)(1-\alpha)\rceil\). Let \(q_\alpha=R_{(k)}\), with \(q_\alpha=+\infty\) if \(k>n\). P's rank argument gives

\[
\Pr\!\left\{\min_{1\leq r\leq5}E_{\mathrm{new},r}
\geq1-q_\alpha\right\}\geq1-\alpha.
\]

This certifies a *future run's five rounds simultaneously*, marginally across runs. It does not certify the conditional outcome for a particular market history, a changed model, or an intervention chosen after seeing calibration results. The bound can be uninformative if the worst observed run is poor.

Q's *Experimental Conditions* says there are ten runs per model. At \(\alpha=0.05\), \(k=\lceil11(0.95)\rceil=11>10\), so this split-conformal construction yields no nontrivial 95% lower bound. At \(\alpha=0.10\), \(k=10\), so its bound is the worst observed complete run. At least nineteen exchangeable calibration runs are needed for a finite 95% order statistic. The published per-round means do not supply the five-round run scores. Pooling the three models is not justified by Q's own reported model heterogeneity.

## What would make this publishable?

The calculation above is a direct application of P's theorem and is not itself a new conformal method. The testable contribution would be a study that (i) decomposes Q's actual run-level welfare gap into quantity and selection losses, (ii) varies a prespecified, profit-respecting crossing intervention to test whether small quote increments cause the quantity loss, and (iii) calibrates and reports a lower-tail, whole-run efficiency guarantee together with intervention cost. Randomization must be at the market-run level, and the certificate must be recalibrated separately for each frozen policy. A null or negative result, such as crossing more often without improving selection loss, would still identify the limit of the proposed mechanism.

Q gives neither the run-level records in the assigned text nor a tested intervention. P gives no market data. The present pair supports the decomposition and the validation design, not an empirical guarantee or a claim that crossing is the sole cause of lost welfare. A direct price-margin adaptation of P is unsupported until a meaningful quote-error process and reference prices are specified.

Related work already uses conformal acceptance rules for statistical strategy-proofness in auctions: [Lotan, Talgam-Cohen, and Romano](https://arxiv.org/abs/2405.12016). This cautions against claiming novelty for conformal calibration in auctions generally. The targeted question here concerns realized allocative efficiency in Q's repeated double auction.
