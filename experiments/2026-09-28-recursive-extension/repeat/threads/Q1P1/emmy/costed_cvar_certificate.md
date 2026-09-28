# A costed, selective CVaR certificate for a distributed decision

## Scope and source passages

P defines \(\mathcal C(x)=m^{-1}\sum_i C^i(x)\), with \(C^i(x)=\operatorname{CVaR}_{\alpha_i}(J^i(x,\xi^i))\), in its introduction and CVaR preliminaries (P, lines 269-331). Its algorithm uses \(s_k^i\) fresh loss evaluations per agent and iteration, and projects into \(\mathcal X_\delta\) so that both decisions and perturbed query points lie in \(\mathcal X\) (P, lines 415-488). Theorem 1 bounds \(\mathbb E[\mathcal C(\hat x_T)-\mathcal C^*]\) at finite \(T\) (P, lines 657-723). Here \(\hat x_T\) is a weighted time average of the network-wide mean iterate, so an implementation must also collect or reproduce it. For fixed batch sizes, the last-iterate proof identifies an expected empirical-smoothed surrogate and proves a pathwise true-risk bound \(\mathcal C(\bar x_\infty)-\mathcal C^*\le D_2\) at its random limit (P, lines 857-975). Neither statement is a finite-\(T\), realised-batch risk certificate.

Q defines an augmented competitive cost that charges \(\kappa\) per predictor invocation (Q, lines 1242-1258). Its composition discussion requires conditional component guarantees, common benchmark comparisons, and sensitivity at downstream interfaces (Q, lines 1023-1109). The construction below uses its cost-accounting principle, with a declared oracle-call cost in the units of the loss. This changes Q's exact invocation type, so that modeling choice must be stated.

## Conditional certificate

Assume all local tail levels equal \(\alpha\), the bounded-loss and fresh-sample assumptions of P hold, and the downstream physical loss is the sum \(S(x,\xi)=\sum_i J^i(x,\xi^i)\) at the same decision \(x\). Local losses may be dependent across agents when the decision is deployed; their marginal distributions must match the evaluation oracles. Run P for \(T\) iterations and choose its feasible ergodic iterate \(X=\hat x_T\in\mathcal X_\delta\). After freezing \(X\), obtain independent validation batches of size \(n_i\) at \(X\), independent of the optimization transcript. Let \(\widehat C_i(X)\) be the empirical CVaR in P's equation for that batch, and set

\[
\epsilon_i=\frac{2U_i}{\alpha}\sqrt{\frac{\log(2m/\zeta)}{2n_i}},\qquad
R=\sum_{i=1}^{m}\bigl(\widehat C_i(X)+\epsilon_i\bigr).
\]

Conditional on the optimization transcript, the DKW inequality and P's CVaR stability lemma (P, lines 1289-1320) give simultaneous \(|\widehat C_i(X)-C^i(X)|\le\epsilon_i\) with probability at least \(1-\zeta\). P's appendix notes CVaR subadditivity at a common level (P, lines 1280-1288). Thus, on the validation event,

\[
\operatorname{CVaR}_\alpha(S(X,\xi))
\le \sum_i C^i(X)\le R,
\qquad
\Pr_\xi\{S(X,\xi)>R\mid X,\text{validation}\}\le\alpha.
\]

The last implication uses \(\operatorname{VaR}_{1-\alpha}(S)\le\operatorname{CVaR}_\alpha(S)\). It is a statement about a fresh deployment draw, conditional on a validation event of confidence \(1-\zeta\). If a fixed operational threshold \(b\) is required, accept \(X\) only when \(R\le b\). Then \(\Pr\{\text{accept and }\operatorname{CVaR}_\alpha(S(X,\xi))>b\}\le\zeta\). A fallback needs its own risk and feasibility proof. The action \(X\in\mathcal X\) is exactly feasible pathwise because of P's projection; the risk constraint is certified with confidence, not exactly satisfied for every possible validation batch or future loss.

Suppose each training or validation oracle call costs \(\kappa\) in loss units, and the calls are offline evaluations rather than physical deployments. For deterministic batch sizes, \(N=\sum_{k<T,i}s_k^i+\sum_i n_i\), so the observable costed tail threshold is \(R+\kappa N\). This charges sample acquisition only. A total implementation cost must also charge any communication needed to form \(\hat x_T\), collect local audit values, and coordinate deployment. If a query is a physical action, its actual incurred loss must also be included; charging only \(\kappa\) would omit it. If the downstream loss is an adapted policy cost rather than \(S(X,\xi)\), Q's interface conditions must additionally relate that cost, its benchmark, and its sensitivity to \(X\).

## What P's optimization bound adds

Let \(B_T\) be a deterministic upper bound on P's finite-time right-hand side, including network disagreement, smoothing, and sampling terms. Since \(G=\mathcal C(X)-\mathcal C^*\ge0\), Markov's inequality gives \(\Pr\{G>B_T/\gamma\}\le\gamma\). The two-sided validation event also gives \(R\le m\mathcal C(X)+2\sum_i\epsilon_i\). Therefore, with probability at least \(1-\gamma-\zeta\),

\[
R+\kappa N
\le m\mathcal C^*+\frac{mB_T}{\gamma}
+2\sum_i\epsilon_i+\kappa N.
\]

This is a weak quality guarantee for the data-dependent certificate. The observed \(R\) is the verifiable bound; \(\mathcal C^*\) is a theoretical comparator. The comparator is \(\min_x\sum_i\operatorname{CVaR}_\alpha(J^i(x))\), which can exceed \(\min_x\operatorname{CVaR}_\alpha(\sum_iJ^i(x))\) because subadditivity can be strict. Calling the displayed bound near-optimal for aggregate CVaR would therefore be unjustified without a bound on this diversification gap. The cost term also needs an explicit benchmark convention, as Q explains.

The benchmark mismatch has an exact additive form. Write
\(A(x)=\operatorname{CVaR}_\alpha(S(x,\xi))\),
\(A^*=\min_{x\in\mathcal X}A(x)\), and
\(D=m\mathcal C^*-A^*\ge0\). Since
\(A(x)\le m\mathcal C(x)\) for every \(x\), P's bound yields

\[
\mathbb E[A(X)-A^*]\le mB_T+D.
\]

The extra term \(D\) is a required benchmark comparison for Q's
composition principle. An audit at \(X\) can upper bound \(A(X)\), but
does not determine \(A^*\) or \(D\).

Ada's ledger entry 23 gives a tight decision example. Let \(m=2\),
\(\alpha=1/2\), \(\mathcal X=[-1,1]\), and
\(Z\sim\operatorname{Bernoulli}(1/2)\). Set
\(J^1(x,Z)=UZ\) and
\(J^2(x,Z)=U((1-x)Z+x(1-Z))\).
The local CVaRs are \(C^1(x)=U\) and
\(C^2(x)=U\max\{1-x,x\}\). Thus P's exact optimum is
\(x_P=1/2\) with \(m\mathcal C^*=3U/2\). The jointly coupled
aggregate loss takes values \(U(2-x)\) and \(Ux\), so
\(A(x)=U(2-x)\) on \(\mathcal X\). Its optimum is \(x_A=1\),
with \(A^*=U\). Hence
\(A(x_P)-A^*=D=U/2\) at zero local optimization gap.
Both losses are bounded and affine in \(x\), satisfying P's loss
assumptions. This makes the comparator gap an actual decision loss,
not merely slack in a certificate.
For any budget \(b\in[U,3U/2)\), the aggregate optimum is
risk-feasible while P's exact local-objective optimum is not.

The gap can defeat selective deployment even with unlimited local samples. Let an outcome be uniform on \(\{1,\ldots,m\}\), and set \(J_i=U\mathbf 1\{\text{outcome}=i\}\). At \(\alpha=1/m\), each local CVaR equals \(U\), so their sum equals \(mU\), yet \(S=\sum_iJ_i=U\) surely and its CVaR equals \(U\). Any budget \(b\in[U,mU)\) is feasible for the aggregate loss but cannot pass the local-sum certificate in the large-sample limit. This is a dependency effect, not an estimation error.

Local marginal samples cannot reveal this dependence. For \(m=2\), \(\alpha=1/2\), and Bernoulli \(Z\), the couplings \((J_1,J_2)=(UZ,UZ)\) and \((J_1,J_2)=(UZ,U(1-Z))\) have identical local marginals. Their aggregate CVaRs are respectively \(2U\) and \(U\). The obstruction also holds at P's exact optimizer: set \(\mathcal X=[-1,1]\) and \(J^i(x,Z_i)=UZ_i+x^2\). Each local CVaR is \(U+x^2\), so \(x^*=0\) and the P objective gap there is zero under both couplings. Yet the aggregate CVaR at \(x^*\) is \(2U\) when \(Z_1=Z_2\) and \(U\) when \(Z_2=1-Z_1\). All losses meet P's compact-domain, bounded, convex, and Lipschitz assumptions. If oracle calls are generated separately from the local marginals, with no paired deployment outcomes or dependence information, every local observation transcript has the same law under both couplings. Consequently, any upper certificate valid with confidence \(1-\zeta\) for both must report at least \(2U\) with probability at least \(1-\zeta\) even in the lower-risk world. This is an information limit at zero optimization error, not a finite-sample approximation effect. It does not apply if synchronized cross-agent outcomes are observed and their pairing is preserved. Fresh paired observations of the deployed sum would permit a direct DKW/CVaR certificate and could remove this slack, but they require a joint observation interface and its own acquisition cost. If independence is known and preserved in deployment, independently drawn local validation losses can instead be paired to simulate that joint law. This choice of observation interface is a sharper publication question than applying DKW to each local CVaR.

## Selective deployment with a safe baseline

Ada's ledger entry 8 sharpens the decision claim by adding a known baseline \(x_0\in\mathcal X\) with \(\operatorname{CVaR}_\alpha(S(x_0,\xi))\le b\), a known margin \(m\mathcal C^*\le b-h\) for \(h>0\), and validation sizes satisfying \(2\sum_i\epsilon_i\le h/2\). Execute \(X\) when \(R\le b\), otherwise execute \(x_0\). If the validation event holds and \(\mathcal C(X)-\mathcal C^*\le h/(2m)\), then \(R\le b\). Hence

\[
\Pr\{\text{reject }X\}\le\zeta+\frac{2mB_T}{h},
\qquad
\Pr\{\operatorname{CVaR}_\alpha(S(X_{\rm deploy},\xi))>b\}\le\zeta.
\]

Writing \(\Delta=\mathcal C(x_0)-\mathcal C^*\), the deployed decision also satisfies

\[
\mathbb E[\mathcal C(X_{\rm deploy})-\mathcal C^*]
\le B_T+\Delta\bigl(\zeta+2mB_T/h\bigr).
\]

The first term pays for P's optimization error and the second for rejected advice. The known margin is a substantial assumption; P does not supply it. This theorem addresses an identity downstream action and a common loss model. A general downstream adapter still needs Q's conditional transfer and benchmark conditions.

## Paired audit and the remaining benchmark term

Suppose a fresh oracle can return paired losses drawn from the actual
deployment joint law at the frozen decision \(X\). Let
\(U_\Sigma=\sum_iU_i\), and obtain \(n\) independent paired vectors.
Their summed empirical losses yield an empirical aggregate CVaR
\(\widehat A(X)\). The same DKW argument gives

\[
\epsilon_J=\frac{2U_\Sigma}{\alpha}
\sqrt{\frac{\log(2/\zeta)}{2n}},
\qquad R_J=\widehat A(X)+\epsilon_J,
\qquad
\Pr\{A(X)\le R_J\le A(X)+2\epsilon_J\}\ge1-\zeta.
\]

Let a known safe baseline satisfy \(A(x_0)\le b\), and assume the
aggregate optimum has a known margin \(A^*\le b-h\), with \(h>0\).
If \(2\epsilon_J\le h/2\), accept \(X\) when \(R_J\le b\) and
otherwise deploy \(x_0\). Since
\(\mathbb E[A(X)-A^*]\le mB_T+D\), Markov's inequality yields

\[
\Pr\{\text{reject }X\}
\le\zeta+\frac{2(mB_T+D)}{h},
\qquad
\Pr\{A(X_{\rm deploy})>b\}\le\zeta.
\]

With \(\Delta_A=A(x_0)-A^*\), the deployed aggregate objective obeys

\[
\mathbb E[A(X_{\rm deploy})-A^*]
\le mB_T+D+
\Delta_A\left(\zeta+\frac{2(mB_T+D)}{h}\right).
\]

If a local training call costs \(\kappa_L\) and a paired audit vector
costs \(\kappa_J\), its declared acquisition charge is
\(\kappa_L\sum_{k<T,i}s_k^i+\kappa_Jn\). The second price must include
paired sensing and communication. A paired audit improves the
certificate at the chosen decision, but the decision-quality and
rejection bounds still pay \(D\). Removing that term needs a
structural comparison or aggregate-aware optimization.
For an all-in budget \(B\), the acceptance threshold must be reduced
to \(b=B-\kappa_L\sum_{k<T,i}s_k^i-\kappa_Jn\), with any other
implementation charges subtracted as well.

## Limits and publication test

Finite samples cannot give an exact, nontrivial distribution-free risk-feasibility certificate. Ada's ledger entries 9-10 give a counterexample even with a known safe fallback: let \(\mathcal X=[-1,1]\), \(x_0=0\), and \(J(x,Z)=\max\{0,x\}Z\). Under one law \(Z=0\) surely; under another \(Z=U\) with probability \(p\in(\alpha b/U,\alpha)\), where \(0<b<U\). The loss is bounded, convex, and Lipschitz on \(\mathcal X\), so it lies in P's class. The candidate \(x=1\) has CVaR zero under the first law and \(Up/\alpha>b\) under the second, while \(x_0\) remains safe under both. Every finite all-zero transcript has probability \((1-p)^q>0\) under the unsafe law. A procedure that accepts the candidate on that transcript can violate the risk budget. Thus finite IID samples alone cannot remove the confidence failure term while accepting every safe candidate.

The holdout bound is a straightforward consequence of P's DKW lemma, not a claimed new CVaR-confidence result. Existing work explicitly studies confidence bounds for CVaR: [Liang and Luo, ICML 2023](https://proceedings.mlr.press/v202/liang23c.html). Dependence uncertainty in aggregate risk is also a developed subject; see [Cheung, 2010](https://doi.org/10.1016/j.insmatheco.2010.06.001). A publication would need a sharper contribution, such as jointly optimizing distributed training, local or joint validation, and abstention costs with matching lower bounds and a proved downstream interface. The source-grounded question is whether that full costed policy can improve on a safe baseline after including the conservative local-to-aggregate CVaR gap. I have not established that improvement.
