# What Q's mean table identifies about welfare loss

## Source claims

Q, Section "Market Environment," specifies eleven buyer values and eleven
seller costs, each running from \(0.75\) to \(3.25\) in steps of \(0.25\).
Q, Section "Market-Wide Outcomes," reports the mean trade count and mean
allocative efficiency from ten simulations for each model and round.
It attributes the weak GPT Large results partly to reluctance to cross
the spread. P, Sections "Calibrated selective certificate" and
"Limitations," makes a useful methodological distinction: a guarantee
for an early gate does not itself certify the downstream outcome. The
market analogue is to measure the *realized* surplus gap and distinguish
its count and selection components.

## Exact decomposition

With exactly \(k\) trades, maximum surplus selects the \(k\) highest
buyer values and \(k\) lowest seller costs. For \(0\le k\le11\),

\[
W_{\max}(k)
=\sum_{j=1}^{k}\left(2.5-0.5(j-1)\right)
=2.75k-0.25k^2.
\]

The unconstrained maximum is \(W^*=7.5\), attained by either five or
six optimally selected trades. For realized count \(N\) and realized
surplus \(W\), define

\[
Q_{\mathrm{loss}}=W^*-W_{\max}(N),\qquad
S_{\mathrm{loss}}=W_{\max}(N)-W.
\]

Both are nonnegative and
\(W^*-W=Q_{\mathrm{loss}}+S_{\mathrm{loss}}\). The first is loss
forced by the number of trades. The second is loss due to the identities
of the traders who transacted. Transaction prices cancel from \(W\).
This remains true even though Q's exchange permits a transaction that
violates an agent's reservation price.

## A lower bound from the published means

Let \(\mu=\mathbb E N\), \(a=\lfloor\mu\rfloor\), and \(f=\mu-a\).
Because \(W_{\max}(k)\) is concave on integer \(k\), its greatest possible
mean at this \(\mu\) occurs when \(N\) takes only \(a\) and \(a+1\):

\[
\mathbb E W_{\max}(N)
\le (1-f)W_{\max}(a)+fW_{\max}(a+1).
\]

Equivalently,
\(\mathbb E W_{\max}(N)
=W_{\max}(\mu)-0.25\operatorname{Var}(N)\), and integer-valued
\(N\) has \(\operatorname{Var}(N)\ge f(1-f)\). Therefore

\[
\mathbb E Q_{\mathrm{loss}}
\ge 7.5-W_{\max}(\mu)+0.25f(1-f).
\]

For GPT Large in round 4, Q reports \(\mu=2.2\) and mean efficiency
\(0.36\). The best possible mean fixed-count surplus is
\(0.8W_{\max}(2)+0.2W_{\max}(3)=0.8(4.5)+0.2(6)=4.8\).
Hence mean quantity loss is at least \(7.5-4.8=2.7\) surplus
units. Mean total welfare loss is approximately
\(7.5(1-0.36)=4.8\), so at least about \(56\%\) of this gap
comes from count alone. The remainder, at most \(2.1\) units,
could be trader selection loss. Q's rounded efficiency makes the
percentage approximate.

Applying the same calculation to the five GPT Large rows gives:

| Round | Mean trades | Minimum mean count loss | Mean total loss | Minimum count share |
| --- | ---: | ---: | ---: | ---: |
| 1 | 2.6 | 2.10 | 3.975 | 53% |
| 2 | 3.8 | 0.70 | 3.075 | 23% |
| 3 | 3.0 | 1.50 | 3.300 | 45% |
| 4 | 2.2 | 2.70 | 4.800 | 56% |
| 5 | 3.5 | 1.00 | 2.475 | 40% |

Across these five rows, at least about \(45\%\) of the aggregate
reported welfare deficit is forced by trade count. This supports
Q's stalling explanation in a limited quantitative sense. It does not
show that incremental bidding *caused* the low counts, and it leaves
the actual selection loss unidentified. The run-level records are
needed to compute both components exactly.

## The cross-paper test

P's episode-level rank construction could be applied to a complete
five-round market run, using a score such as the maximum total welfare
gap, quantity loss, or selection loss across its rounds. This would
give a marginal simultaneous bound for a new run of a *frozen* model,
prompt, and mechanism, provided calibration runs are exchangeable.
The policy and any intervention must be calibrated separately. With
only ten calibration runs, a finite \(95\%\) split-conformal order
statistic is unavailable: \(k=\lceil11(0.95)\rceil=11>10\).

A publishable test would use run-level data and a prespecified
randomized crossing intervention to ask whether the intervention
reduces quantity loss without increasing selection loss or the lower
tail of total welfare loss. The table bound is an analytical finding;
neither source paper supplies the required intervention result.
