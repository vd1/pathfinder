# Pairwise welfare credit under private values

## Publication question

Can a pairwise judge distinguish welfare-improving quotes in a private-value
double auction when it receives only the acting trader's permitted information?
This adapts P's comparison procedure from *agents* to *alternative actions by
one agent*. P does not itself make that adaptation (P, Method, lines 281-329).

Q supplies an exact welfare target: allocative efficiency is realized buyer
plus seller profit divided by the maximal available surplus (Q, Results,
lines 295-302). Its traders know their own reservation price, the standing
quotes, and public and private histories, but not other reservation prices
(Q, Information and Objective, lines 261-278; prompt, lines 515-527). Q's
market has 11 buyers and 11 sellers, each side using the reservation-value
grid from \(0.75\) to \(3.25\) in increments of \(0.25\), with at most one
trade per agent per round and a 300-iteration cap (Q, lines 210-259). P
turns pairwise LMM judgments into Bradley-Terry scores and then potential
rewards, while its statistical proposition concerns recovery of the LMM's
latent preference rather than agreement with an external welfare target
(P, Method and Theory, lines 281-389).

## Observationally identical worlds

Construct two states immediately before iteration 299, with iteration 300
remaining. Buyer \(B_2\) is selected now, has value \(v_2=2.25\), and sees a
standing ask \(a^*=1.50\) from seller \(S\) with cost \(c=0.75\). Set the
standing best bid below \(1.49\). Both states have identical public history
and identical information for \(B_2\). Two buyers who have not posted, \(B_1\)
and \(B_3\), hold values \(3.25\) and \(1.75\). Assign \(v_1=3.25\) in world
A and \(v_1=1.75\) in world B, swapping \(B_3\)'s value to keep Q's complete
reservation-value multiset fixed. This assumes the assignment of the two
values has no identity or history signal visible to \(B_2\).

Compare \(B_2\)'s legal crossing bid \(1.50\) with its legal improving bid
\(1.49\). Couple both continuations to the same final random selection of
\(B_1\). Stipulate that, if \(S\) remains, \(B_1\) bids \(1.50\), which is
profitable under either value. Assume all other welfare contributions are
identical across continuations. These are specified continuations, not
measurements of Q's LLM policies. Q's matching rule executes a crossing bid
against the standing ask and removes both counterparties (Q, Trading
Mechanism, lines 239-259).

Crossing now trades \(B_2\) with \(S\), yielding welfare
\[
W_{\mathrm{cross}}=v_2-c=2.25-0.75=1.50.
\]
Improving the bid leaves \(S\) available for \(B_1\), yielding
\[
W_{\mathrm{improve}}^A=3.25-0.75=2.50,\qquad
W_{\mathrm{improve}}^B=1.75-0.75=1.00.
\]
Consequently, the counterfactual difference
\(\Delta=W_{\mathrm{cross}}-W_{\mathrm{improve}}\) is \(-1.00\) in A and
\(+0.50\) in B. The welfare-preferred action reverses while \(B_2\)'s
permitted information remains unchanged.

For an equal conditional prior on A and B, no judge whose input is limited
to \(B_2\)'s information can exceed \(1/2\) accuracy on the *realized* sign
of \(\Delta\), even with arbitrarily many repeated comparisons. Its best
conditional action is nonetheless to improve: expected welfare is
\((2.50+1.00)/2=1.75\), compared with \(1.50\) for crossing. A judge that
also learns \(B_1\)'s value can choose improve in A and cross in B, obtaining
\((2.50+1.50)/2=2.00\). The value of that private information is therefore
\(0.25\) welfare units under this prior and continuation. The accuracy
ceiling is about ex post labels, not an inability to make the best decision
under limited information.

## Test and limits

Replay Q decision states and compare legal crossing versus incremental
quotes using the same future random schedule and fixed continuation policies.
Estimate each action's final surplus with paired rollouts. Test pairwise
judgments under acting-trader information, added counterpart information,
and complete valuations. Report regret relative both to a conditional
information oracle and to a complete-information oracle. Compare with a
direct expected-welfare predictor; P's pairwise and rank method must add
predictive value beyond this baseline. For a price-only diagnostic, freeze
the matched buyer and seller, allocation, and continuation: their joint
surplus \((v-p)+(p-c)=v-c\) is then independent of transaction price. Run a
separate causal perturbation that allows later quotes to respond to the price,
since changed market history can alter final welfare. Also check role and
remaining-horizon perturbations.

Two candidate quotes need only a direct pairwise judgment. Rank aggregation
becomes relevant if the test expands to three or more legal quotes, and that
extension would need care with P's unregularized Bradley-Terry objective: for
two entities with
\(K\) unanimous comparisons, a connected comparison graph still gives
loss \(L(d)=K\log(1+e^{-d})\) with no finite minimizer as \(d\to\infty\).
Use a penalized fit or symmetric pseudocounts and report separation
frequency (P, Rank Aggregation and robustness proof, lines 313-329 and
682-748). P's potential shaping does not itself solve Q's strategic welfare
problem. With fixed initial state and zero terminal potential, its discounted
sum telescopes to a policy-independent constant; Q's agents are prompted to
maximize private profit rather than trained on a team reward (P, lines
331-349; Q, lines 261-278).

P already acknowledges that tasks relying on domain-specific internal states
unavailable to observations may lie outside its scope (P, Limitations,
lines 642-646). The construction gives a quantitative market instance of
that boundary rather than a contradiction of P's stated limitations.

The construction proves an information boundary for the specified states
and continuation. It does not establish how often such states occur under
Q's LLM policies, whether a pairwise judge beats direct prediction, or
whether any training intervention raises market efficiency. Those are the
empirical requirements for a publication claim.
