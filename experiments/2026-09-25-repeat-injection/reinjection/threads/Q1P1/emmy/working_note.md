# Costed stability of the peer ranking interface

The assigned pair is Q = the learning-augmented algorithms survey and P =
the anonymous paper on a conditional peer-signal interface. P's internal
letters name two other papers. The question here is whether P's identified
score can be treated as a prediction with an explicit error and access cost,
as Q requires. This narrows the original open-ended question to a checkable
stability and identifiability problem.

## Source facts

P assumes a shared latent binary comparison, conditionally independent
symmetric peer flips, positive peer reliabilities, a calibration triangle,
overlap paths, edge coverage, and a connected comparison graph
(P, lines 64-109). It proves population identification. It explicitly leaves
finite-sample graph-dependent rates and query allocation unresolved
(P, lines 132-156). Q says that prediction error needs a task-specific metric
(Q, lines 260-265, 325-333), error propagation needs sensitivity assumptions
(Q, lines 1095-1109), and obtaining predictions carries a cost
(Q, lines 973-980, 1242-1258).

## A deterministic stability statement

Use P's model. Let \(H\) be the peer-overlap graph and choose its observed
calibration triangle plus a rooted tree reaching every observer used for an
edge mean. Let \(D\) be the greatest tree depth from that triangle. Let
\(G\) be the connected comparison graph, with edge set \(E\) and unweighted
Laplacian \(L_G\). Assume all peer reliabilities obey
\(a_r\in[\alpha,1]\) and all edge probabilities obey
\(p_e\in[\tau,1-\tau]\), where \(\alpha>0\) and
\(0<\tau\leq 1/2\). The population moments are
\[
q_{rs}=a_ra_s,\qquad \mu_{er}=a_r(2p_e-1).
\]
Suppose measured moments satisfy
\(\lvert\widetilde q_{rs}-q_{rs}\rvert\leq\delta\) on the
chosen overlap links and
\(\lvert\widetilde\mu_{er}-\mu_{er}\rvert\leq\delta\)
for one calibrated observer on each comparison edge. Define
\[
u=\frac{2\delta}{\alpha^2},\qquad
T=\left(D+\frac32\right)u,\qquad
h=\frac{\delta e^T}{\alpha}+e^T-1.
\]
If \(\delta\leq\alpha^2/2\) and \(h\leq\tau\), perform P's
triangle calibration, propagate reliability estimates along the tree,
divide each edge mean by its estimated reliability, apply the logit, and
least-squares invert the edge differences. For centered score vectors,
\[
\lVert\widehat c-c\rVert_2
\leq
\frac{\sqrt{\lvert E\rvert}}{\sqrt{\lambda_2(L_G)}}
\frac{h}{\tau(1-\tau/2)}.
\]
Thus exact ordering follows if every distinct score gap exceeds
\(\sqrt{2}\) times the displayed bound. This is an upper bound, not a
matching rate or an end-to-end policy guarantee.

To prove it, every clean overlap moment is at least \(\alpha^2\).
For \(\delta\leq\alpha^2/2\), the mean-value theorem gives
\(\lvert\log\widetilde q-\log q\rvert\leq u\).
P's triangle formula therefore has log-reliability error at most
\(3u/2\). Each tree edge adds at most \(u\), so every used observer has
\(\lvert\log(\widehat a_r/a_r)\rvert\leq T\). Dividing its edge mean
gives
\(\lvert\widehat m_e-m_e\rvert\leq h\), where
\(m_e=2p_e-1\). Hence
\(\lvert\widehat p_e-p_e\rvert\leq h/2\), and both probabilities stay in
\([\tau/2,1-\tau/2]\). The derivative of logit is
\(1/[p(1-p)]\), giving edge logit error at most
\(h/[\tau(1-\tau/2)]\). Finally the least-squares inverse of the
oriented incidence matrix has operator norm
\(1/\sqrt{\lambda_2(L_G)}\) on centered scores.

If each required link population supplies \(N\) independent shared-draw
items and each edge population supplies \(N\) independent items, there are
\(M=\lvert L_H\rvert+\lvert E\rvert\) measured means. Hoeffding and a
union bound give simultaneous error
\[
\delta_{N,\zeta}=b+
\sqrt{\frac{2\log(2M/\zeta)}{N}}
\]
with probability at least \(1-\zeta\), where \(b\) bounds the deviation
of actual population moments from P's clean model. No independence between
different measured means is needed for this union bound. A direct collection
plan uses at most \(N(2\lvert L_H\rvert+\lvert E\rvert)\) observer labels,
counting two labels per shared-draw overlap item. Reused labels can lower
this count. This makes Q's prediction-access charge explicit, conditional
on a conversion from labels to objective units. In the small-error regime,
the displayed score bound has a term proportional to \(N^{-1/2}\) and a
floor proportional to \(b\). A downstream use needs its own sensitivity
or error-dependent performance theorem before this becomes a system bound.

## Why moment fit cannot certify the target

There are observationally identical worlds with different target scores.
Choose any two score vectors \(c\) and \(c'\) with different rankings.
In both worlds draw an observed shared comparison
\(Z_e\in\{-1,+1\}\) with
\(\Pr(Z_e=+1)=\sigma(c'_i-c'_j)\), and let all
observers independently flip \(Z_e\) with fixed positive reliabilities
\(a_r\). In world A, define the intended latent comparison to be \(Z_e\).
In world B, define the intended latent comparison independently with
\(X_e\in\{-1,+1\}\) and
\(\Pr(X_e=+1)=\sigma(c_i-c_j)\). The complete joint
distribution of all reports is identical in A and B. The observed
cross-peer moments have exact rank-one factorization, every edge mean fits
\(c'\), and repeated data can never distinguish the worlds. World B
violates P's assumption that peers flip the intended latent comparison.
Therefore no report-only diagnostic, including all of P's proposed moment
checks, certifies that the recovered score equals true contribution. An
external anchor or a substantive assumption connecting the shared signal
to the target is necessary. This does not contradict P's conditional
identification theorem.

Ada's ledger entry 4 gives a sharper example within a single shared-flip
misspecification. Let each item have an unobserved common sign \(B\) with
\(\mathbb E B=1/2\), and let \(Y_r=X B Z_r\), where the \(Z_r\) are
independent peer flips. Peer agreements still equal \(a_ra_s\). On a
four-vertex path with oriented true edge score differences
\((4,-1.5,-1.5)\), the endpoint difference is \(1>0\). The observed
edge means instead correspond to transformed differences
\(f_{1/2}(d)=2\operatorname{artanh}[(1/2)\tanh(d/2)]\). Their endpoint sum
is \(f_{1/2}(4)-2f_{1/2}(1.5)\approx-0.265<0\). A path has no cycle
constraint, so these transformed edge probabilities fit another
Bradley--Terry score exactly and reverse the endpoint order. A direct
endpoint comparison would expose this example as a cycle inconsistency,
under its stated shared-flip class. It would not validate the intended
target against unrestricted common bias.

## A restricted shared-flip model admits self-calibration

The preceding path failure also suggests a positive extension. Assume
\(Y_{er}=X_eB_eZ_{er}\), where \(X_e\) follows P's Bradley--Terry
law, \(B_e\in\{-1,+1\}\) is an item-level sign independent of
\(X_e\) and the peer flips, and \(\mathbb E B_e=b\in(0,1]\) is the
same on every comparison edge. The independent peer signs have
\(\mathbb E Z_{er}=a_r>0\). A different \(B_e\) may be drawn on each
item, but its mean must be common across edges. This violates P's
conditional independence given the intended \(X_e\), while retaining
\(q_{rs}=a_ra_s\). P's overlap calibration can therefore still recover
\(a_r\). The calibrated edge mean is
\[
w_{ij}=\frac{\mathbb E Y_{er}}{a_r}
=b\tanh((c_i-c_j)/2).
\]
This sharpens P's limitation sentence at line 141. Correlation
conditional on the intended comparison does not necessarily destroy
the observable agreement factorization. In this model, that
factorization survives exactly while the inferred target is attenuated.
The conditional-independence premise in P's theorem remains necessary
for its interpretation of the calibrated means.
For a comparison triangle with consistent orientations
\((i,j),(j,k),(i,k)\), write
\(A=w_{ij}\), \(B=w_{jk}\), and \(C=w_{ik}\). The addition identity
for hyperbolic tangent gives
\[
C=\frac{A+B}{1+AB/b^2},\qquad
b^2=\frac{ABC}{A+B-C}.
\]
If \(ABC\ne0\), the denominator is nonzero under this model. The
positive root identifies \(b\), after which
\(c_i-c_j=2\operatorname{artanh}(w_{ij}/b)\) on every covered edge.
Connectivity then identifies all scores up to translation. Thus an
observed comparison triangle supplies a population-level self-calibration
for this restricted common-noise class, without a trusted comparison
label. Numerical substitution with \(b=1/2\), adjacent differences
\(4\) and \(-1.5\), gives \(A\approx0.4820\),
\(B\approx-0.3176\), \(C\approx0.4241\), and the formula returns
\(b^2=0.25\).

On a comparison tree there is no analogous identification of \(b\).
For each admissible \(b\) with \(b>\max_e|w_e|\), edge differences
\(2\operatorname{artanh}(w_e/b)\) integrate to a score vector because
a tree has no cycle equation. Ada's four-vertex example shows that
distinct admissible values can even give opposite endpoint rankings.
This does not make every tree ordinally unsafe. Ada's ledger entry 11
shows that a star preserves all pairwise orders under positive uniform
attenuation: each path has at most two edges, and the transformation is
odd and strictly increasing. The star still does not identify numerical
score gaps, which P uses in its shaping potential.
One nondegenerate triangle is sufficient, but no claim of a globally
minimal audit design follows. The formula becomes unstable when one of
\(A,B,C\) approaches zero or when \(A+B-C\) is small. Edge-dependent
or adversarial common bias remains unidentified by this argument.

### A four-cycle can calibrate the same rate

The direct endpoint comparison in Ada's four-vertex example creates a
four-cycle. It can do more than flag inconsistency with the clean model.
Orient all four edges around the cycle, with calibrated means
\(w_1,\ldots,w_4\). Under the constant positive shared-flip model, the
true edge differences sum to zero, so
\[
\sum_{i=1}^{4}\operatorname{artanh}(w_i/b)=0.
\]
For an admissible \(b>\max_i|w_i|\), this is equivalent to
\[
\prod_{i=1}^{4}(1+w_i/b)
=\prod_{i=1}^{4}(1-w_i/b).
\]
Writing \(S_1=\sum_iw_i\) and
\(S_3=\sum_{i<j<k}w_iw_jw_k\), the even terms cancel and the
cycle equation becomes \(S_1b^2+S_3=0\). If \(S_1\ne0\), this
identifies \(b^2=-S_3/S_1\); the positive admissible root is unique.
If \(S_1=S_3=0\), the equation holds for every admissible \(b\), and
this cycle supplies no calibration. The triangle formula above is the
three-edge version of the same odd-term identity.

For the path differences \((4,-1.5,-1.5)\) and direct closing difference
\(-1\), with \(b=1/2\), the four calibrated means are approximately
\((0.4820,-0.3176,-0.3176,-0.2311)\). They give
\(S_1\approx-0.3842\), \(S_3\approx0.09605\), and hence
\(b^2=0.25\). This refines the audit-design question: a nondegenerate
four-cycle can be as informative as a triangle for identifying a
uniform shared flip. It does not validate the model against unrestricted
shared bias.

Related work must be checked before any novelty claim. The primary
[Crowd-BT paper](https://pages.stern.nyu.edu/~xchen3/images/crowd_pairwise.pdf)
already models worker-dependent symmetric mistakes and jointly fits
worker qualities with Bradley--Terry scores. The present algebra
concerns an extra *shared* item-level flip plus peer-specific flips.
Searches for `Bradley Terry common flip noise triangle cycle identify noise
rate pairwise comparisons` and `Bradley-Terry symmetric noise cycle
identification` did not establish that this special case is new.

## Publication direction and limits

The sharper publication line is to characterize a budgeted audit design
for common-mode noise: trees allow exact observational aliases, whereas
a nondegenerate triangle or four-cycle self-calibrates a uniform shared flip.
The finite-sample bound above supplies a starting point for cost and error
accounting in the clean class. A publication would need a stability bound
for the cycle estimate of \(b\), graph-aware sample allocation, lower
bounds in the same model, and a downstream decision theorem. P itself
cites prior single-coin calibration and heterogeneous-worker ranking
(P, lines 126-130), so rank-one recovery alone cannot be sold as new.
Neither source supplies truthful report generation under an unknown
belief map, nor an error-sensitive policy guarantee for P's reward shaping
(P, lines 116-124, 149-156). The present derivation does not fill those
gaps.
