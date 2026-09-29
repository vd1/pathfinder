# Costed certificates for conditional risk advice

## Scope and source checks

The supplied Q is Zhao et al.'s survey of learning-augmented algorithms. It is not the mechanism-design paper called Q inside the supplied P; P says so explicitly in its Section 1. Q's “Inference Graphs, and How Guarantees Compose” (source lines 1024–1109) requires conditional component guarantees and relations between downstream instances and benchmarks. Its “Pricing the Prediction” (lines 1242–1258) assigns a declared charge \(\kappa\) to an invocation. It does not turn a risk estimate into an incentive certificate. Q's discussion of distributional advice (lines 600–602) also warns that a risk bound for a fixed decision need not bound the optimizer's downstream cost.

P's Section 2 constructs, for every finite batch size, a two-signal policy supported under expected empirical conditional CVaR and unsupported under true conditional CVaR. Its Section 3 gives deterministic results from a bound \(\lvert U(a,s)-\widetilde U(a,s)\rvert\leq e\): cycle sums move by at most \(2Ke\), and a directed graph tests whether one reward works for every utility array in an error box. P explicitly says neither result guarantees one realised batch. All claims below retain P's one-type, finite-signal, state-independent action reward, conditional-risk interpretation. Unprescribed actions are prohibited, or every available action is included among the prescribed actions. The signal policy is fixed before sampling.

## Sharpened question

Can a finite number of priced loss samples produce a checkable reward witness whose obedience inequalities hold exactly for the true conditional CVaR utilities, with a stated confidence level? This is narrower than a general learning-augmented system guarantee. It separates a statistical coverage statement, a finite graph check, and any separate claim about a system objective.

## A realised-batch certificate

Let \(S\) and \(A\) be finite, \(N=|S||A|\), and \(a:S\to A\) be the prescribed policy. For each cell \((a,s)\), suppose \(m\) independent samples are drawn from a fixed conditional loss law on \([0,U]\). Samples within a cell are identically distributed and independent; the union bound does not require independence across cells. Let \(R(a,s)=\operatorname{CVaR}_{\beta}(X_{a,s})\) for upper-tail mass \(\beta\in(0,1]\), let \(\widehat R_m(a,s)\) be empirical CVaR of the *realised* batch, and set \(U(a,s)=-R(a,s)\), \(\widehat U(a,s)=-\widehat R_m(a,s)\). Define

\[
e_m=\frac{U}{\beta}\sqrt{\frac{\log(2N/\delta)}{2m}}.
\]

The Dvoretzky–Kiefer–Wolfowitz inequality and a union bound give \(\Pr\{\max_{a,s}|\widehat U(a,s)-U(a,s)|\leq e_m\}\geq1-\delta\). To see the risk transfer, the variational form \(\operatorname{CVaR}_{\beta}(F)=\inf_t\{t+\beta^{-1}\mathbb E_F(X-t)_+\}\) gives \(|\operatorname{CVaR}_{\beta}(F)-\operatorname{CVaR}_{\beta}(G)|\leq W_1(F,G)/\beta\). For distributions on \([0,U]\), \(W_1(F,G)=\int_0^U|F(x)-G(x)|\,dx\leq U\|F-G\|_\infty\). The empirical-CVaR concentration ingredient has substantial prior work: [Prashanth, Jagannathan, and Kolla](https://arxiv.org/abs/1901.00997) and [Prashanth and Bhat](https://arxiv.org/abs/1902.10709).

For distinct prescribed actions \(a,b\), compute

\[
w_m(a,b)=\max_{s:a(s)=a}\{\widehat U(b,s)-\widehat U(a,s)+2e_m\}.
\]

If this finite directed graph has no positive directed cycle, solve the difference constraints \(r(a)-r(b)\geq w_m(a,b)\) and output the reward vector \(r\), the sample count, the confidence radius, and the edge inequalities. The graph test and inequalities are exactly checkable from the recorded estimates. On the confidence event, for every signal \(s\) and deviation \(b\), \(U(b,s)-U(a(s),s)\leq w_m(a(s),b)\leq r(a(s))-r(b)\). Hence the *same reported reward* supports the policy under true conditional CVaR. A failed graph test means “uncertified,” not “infeasible”; a negative upper confidence bound on one true cycle gives a separate infeasibility certificate. The probability qualifier concerns the sample draw. The reward inequalities themselves are exact on the coverage event.

If every nontrivial simple true cycle has utility sum at least \(K\gamma\), where \(K\) is its length, then \(e_m<\gamma/4\) suffices for the graph certificate on the coverage event: each empirical cycle sum loses at most \(2Ke_m\), and the robust graph subtracts another \(2Ke_m\). A sufficient uniform choice is \(m>8U^2\log(2N/\delta)/(\beta^2\gamma^2)\). This is a sufficient cost, not an optimal adaptive allocation theorem.

If one sample costs \(\kappa_s\) in the decision objective's units, the acquisition charge is \(\kappa_sNm\), plus a declared graph-computation charge if material. A fixed batch may instead be one invocation charged \(\kappa_b\); Q's per-invocation convention alone does not decide which model applies. This accounting assumes access to counterfactual conditional losses in every compared cell. No competitive ratio follows until the downstream objective, the prediction-free benchmark, and their relation to this reward problem are specified, as Q's composition conditions require.

### The reward bill is a separate downstream cost

P's cycle test allows unrestricted rewards, so existence does not bound the payment. For example, two action constraints \(r(a)-r(b)\geq M\) and \(r(b)-r(a)\geq-M-\gamma\), with \(M,\gamma>0\), have a nonpositive cycle sum and hence a supporting reward, but any nonnegative supporting reward needs a cap of at least \(M\). If rewards share the objective's units, declare limited liability \(r(a)\geq0\) and a one-decision reward cap \(R\). The finite linear program

\[
\text{find }r\quad\text{such that}\quad
r(a)-r(b)\geq w_m(a,b),\qquad 0\leq r(a)\leq R
\]

is a checkable certificate of both exact obedience on the confidence event and a pathwise reward bill at most \(R\). Minimizing \(R\) gives the cheapest robust cap for the rectangular confidence set. Thus a declared budget can be compared with \(\kappa_sNm+R\), but a ratio to Q's prediction-free optimum still needs a common system objective and benchmark relation.

There is also a quantitative cost comparison with an oracle that knows the true conditional risk array. Write

\[
w^*(a,b)=\max_{s:a(s)=a}\{U(b,s)-U(a,s)\},
\qquad n=|A|.
\]

Suppose every directed simple cycle of distinct prescribed actions has average true edge weight at most \(-\gamma<0\). On the simultaneous confidence event, \(w^*(a,b)\leq w_m(a,b)\leq w^*(a,b)+4e_m\). Thus \(e_m<\gamma/4\) rules out positive cycles in the robust graph. Let \(R^*\) be the least possible cap \(\max_a r(a)\) over nonnegative rewards supporting the true array, and \(R_m^*\) the corresponding least robust cap. Then

\[
R^*\leq R_m^*\leq R^*+4(n-1)e_m.
\]

For proof, the coordinatewise smallest nonnegative reward solving \(r(a)-r(b)\geq w(a,b)\) is the maximum of zero and the weights of paths starting at \(a\). A graph with no positive cycles needs only simple paths, of length at most \(n-1\). Each path weight rises by at most \(4(n-1)e_m\) when replacing \(w^*\) by \(w_m\). The one-decision resource bound is therefore \(\kappa_sNm+R^*+4(n-1)e_m\), with confidence \(1-\delta\), under the stated sample and margin assumptions. The oracle cap is a local benchmark for support payments, not Q's offline system optimum.

This bound is conditional on the statistical coverage event. To obtain Q's *expected* augmented-cost guarantee, one must also specify the fallback on uncertified instances and bound cost and feasibility on the probability-\(\delta\) failure event. A high-confidence exact-obedience statement alone does not supply that expectation or a competitive ratio.

More precisely, an estimate such as \(\kappa_sNm+B+\delta M\) requires cost at most \(B\) on the entire coverage event, including abstention, and cost at most \(M\) on every draw. A margin that forces certificate acceptance on coverage or a fallback whose cost is included in \(B\) supplies the first condition. In Q's adaptive pipeline, the coverage bound must hold conditional on each reachable pre-sampling history, using fresh conditional samples or another valid design. A marginal guarantee for one fixed policy is insufficient for its composition proposition.

The bound also makes a basic sampling tradeoff explicit. Put \(L=\log(2N/\delta)\) and \(A=4(n-1)(U/\beta)\sqrt{L/2}\). Its variable part is \(\kappa_sNm+A m^{-1/2}\). For \(\kappa_s>0\), the continuous minimizer is \(m_0=(A/(2\kappa_sN))^{2/3}\). Certification under the true cycle margin additionally requires \(m>m_{\min}=8U^2L/(\beta^2\gamma^2)\), so round upward after taking the larger of \(m_0\) and \(m_{\min}\). This optimizes a sufficient upper bound; it is not an optimal sampling theorem. This observation was added by Ada in ledger entry 17 and checked by differentiating the bound.

### Counterfactual access cannot be assumed from logs

Every edge compares the prescribed action with a deviation at the *same* signal. On-policy logs that contain only prescribed-action losses cannot identify the deviation law. In a two-signal swapped-action example, let each prescribed action have constant loss \(3/2\) in both worlds. Set the unplayed deviation loss to \(2\) in world A and \(1\) in world B. On-policy data are identical under the worlds for any sample size, while the true two-edge cycle sums are \(+1\) and \(-1\), respectively. Therefore no certificate from those logs alone can distinguish exact feasibility. A generative conditional sampler, covered randomized exploration with known propensities, or a structural model is an additional assumption; its cost and validity must be stated. This is the concrete observability issue flagged by Q (lines 975–980).

## Boundary lower bound

P's two-signal pattern also yields a finite-budget indistinguishability argument. Take upper-tail mass \(\beta=1/2\), risky loss \(0\) or \(2h\), and safe constant \(c=2h-2h\varepsilon\), with \(0<\varepsilon\leq1/4\). In two symmetric signals the prescribed action is risky, with the risky and safe actions swapped. In world \(-\), the probability of risky loss \(2h\) is \(p_-=1/2-\varepsilon\); in world \(+\), it is \(p_+=1/2+\varepsilon\). The true upper-tail risks are \(2h-4h\varepsilon\) and \(2h\), respectively. The two-signal utility cycle therefore has sum \(+4h\varepsilon\) in world \(-\) and \(-4h\varepsilon\) in world \(+\). It is reward-feasible in the first world and infeasible in the second.

Suppose any, possibly adaptive, algorithm obtains at most \(B\) risky-loss draws and must output yes or no. The per-draw Kullback–Leibler divergence is \(d=2\varepsilon\log((1+2\varepsilon)/(1-2\varepsilon))\leq32\varepsilon^2/3\). Constant-loss draws convey no information. The chain rule bounds transcript divergence by \(Bd\), and Pinsker's inequality bounds transcript total variation by \(4\varepsilon\sqrt{B/3}\). If both error probabilities are at most \(\delta<1/2\), total variation must be at least \(1-2\delta\), so

\[
B\geq\frac{3(1-2\delta)^2}{16\varepsilon^2}.
\]

Thus a uniformly correct fixed-budget exact yes/no decision is impossible as the cycle margin tends to zero. The lower bound supports the need for a positive margin, an abstention option, or more samples. It does not prohibit a sound one-sided method that often abstains.

A sharper sequential version is available away from the CVaR saturation point: set the safe loss to \(1\), the risky loss to \(2X\), and \(p_{\pm}=1/4\pm\varepsilon\). The two true cycle sums are \(\pm8\varepsilon\). For any sequential yes/no test with both errors at most \(\delta\), the binary change-of-measure inequality gives \(\mathbb E_{p_-}T\,\operatorname{kl}(p_-,p_+)\geq\operatorname{kl}(1-\delta,\delta)\), provided \(T\) has finite expectation and samples are drawn under the stated oracle. Since \(\operatorname{kl}(p_-,p_+)=O(\varepsilon^2)\), expected sampling cost is \(\Omega(\kappa_s\varepsilon^{-2}\log(1/\delta))\) as \(\varepsilon\to0\) and \(\delta\to0\). This is the stronger version of the partner's ledger entry 6, included after checking the two cycle signs and the KL chain rule. A general bandit change-of-measure result appears in [Kaufmann, Cappé, and Garivier](https://arxiv.org/abs/1407.4443).

## Expected surrogate versus realised data

P's \(q_m\) is \(\mathbb E[\widehat R_m]\), an expectation over fresh batches. Its strict inequality \(q_m<c_m<2h\) proves that a policy chosen from expected empirical CVaR can cross an exact feasibility boundary. A realised batch has additional sampling variation; the displayed simultaneous radius covers both bias and variation relative to true risk. A small expected value error, a high-confidence value interval, and a reward that satisfies exact true obedience are distinct statements.

## Publication assessment and prior work

The elementary concentration plus graph composition is a valid bridge between the supplied papers, but by itself looks too incremental for a standalone paper. [Chen's 2026 risk-conscious persuasion paper](https://arxiv.org/html/2605.12094v1) proves value-margin stability and strict incentive compatibility under a margin in a different signal-design model (Section 5.3). [Balcan, Sandholm, and Vitercik](https://arxiv.org/abs/1902.09413) estimate approximate incentive compatibility from samples. A stronger project would need an optimal, cost-sensitive, adaptive certificate with reward construction under a clearly stated sampling oracle and incentive model, or a genuine downstream objective reduction. The query strings used were `CVaR empirical concentration DKW bounded losses sample complexity`, `statistical certification incentive compatibility samples approximate obedience cycle`, `obedience cycle sample estimation rewards implementability`, and `CVaR incentive compatibility finite sample`. These searches do not establish priority.
