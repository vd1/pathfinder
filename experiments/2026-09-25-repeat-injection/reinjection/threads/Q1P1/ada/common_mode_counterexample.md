# A common-mode ambiguity in the supplied P's ranking interface

## Source claims and scope

The supplied Q is Zhao et al.'s survey of learning-augmented algorithms.
It treats a ranking as an ordinal prediction (Q, lines 345-384) and requires
an explicit error measure for prediction-sensitive guarantees (Q, lines
298-340). Partly observable prediction quality and query cost need separate
modeling (Q, lines 970-980 and 1242-1258). Error propagation requires a
metric and a sensitivity bound (Q, lines 1097-1110).

The supplied P is an essay about a different pair of works. Its theorem
assumes that, conditional on each shared latent comparison, peer reports are
independent symmetric flips with positive reliability. A calibration triangle
identifies those reliabilities, and a connected comparison graph identifies
Bradley--Terry scores up to translation (P, lines 64-110). P says that
correlated errors destroy its factorization (P, lines 139-144). That claim
is too broad if it means the observable peer-agreement factorization:
the example below has correlated errors, passes that check exactly, and
changes the recovered order.

## Two observationally identical worlds

Let the agent-comparison graph be the path with oriented edges from vertex
\(1\) to \(2\), \(2\) to \(3\), and \(3\) to \(4\). In world A, choose scores
with edge differences

\[
(d_{12},d_{23},d_{34})=(4,-3/2,-3/2).
\]

One choice is \(c=(1,-3,-3/2,0)\), so \(c_1-c_4=1>0\). On each independent
item for edge \(e\), draw a latent comparison \(X_e\in\{-1,1\}\) with

\[
\mathbb E[X_e]=\tanh(d_e/2).
\]

Draw a common flip \(B_e\in\{-1,1\}\) independently for that item, with
\(\mathbb E[B_e]=b=1/2\). For each observer \(r\), draw an independent
flip \(Z_{er}\in\{-1,1\}\) with \(\mathbb E[Z_{er}]=a_r>0\), and report
\(Y_{er}=X_eB_eZ_{er}\). All observers assigned to one item share its
\(X_e\) and \(B_e\). Conditional on \(X_e\), their reports are correlated
because of \(B_e\); world A lies outside P's conditional-independence
premise. Nevertheless, for every observer pair,

\[
\mathbb E[Y_{er}Y_{es}]=a_ra_s,
\qquad
\mathbb E[Y_{er}]=a_rb\tanh(d_e/2).
\]

World B defines \(X'_e=X_eB_e\) as the latent comparison and uses
\(Y_{er}=X'_eZ_{er}\). Conditional on \(X'_e\), observer flips are
independent, so P's premise holds. Every joint distribution of observable
reports is exactly the same in worlds A and B. Three overlapping observers
and arbitrarily many repeated items do not separate them.

Because the comparison graph is a tree, the edge means in world B determine
a valid Bradley--Terry score vector \(c'\). Its edge differences are

\[
d'_e=f_b(d_e),
\qquad
f_b(d)=2\operatorname{artanh}\!\left(b\tanh(d/2)\right).
\]

At \(b=1/2\), \(f_b(4)\approx1.05120849\) and \(f_b(3/2)\approx0.65789441\). Therefore

\[
c'_1-c'_4=f_b(4)-2f_b(3/2)\approx-0.26458033<0.
\]

The two worlds give opposite orders for vertices \(1\) and \(4\) but the
same distribution of all collected data. For any randomized estimator based
only on these data, its error probabilities on the event \(c_1>c_4\) in
world A and \(c'_1<c'_4\) in world B sum to at least one. Thus one world has
error probability at least \(1/2\), even with unlimited samples. This is a
model ambiguity, not a concentration failure.

## An exact tree boundary for this error class

For any fixed \(0<b<1\), let each edge of a comparison tree undergo the same positive
common-flip attenuation. The inferred edge difference is \(f_b(d_e)\).
The recovered ordering is correct for every score vector if and only if the tree
has diameter at most two.

For sufficiency, each pair of vertices is joined by a path of at most two edges.
The function \(f_b\) is odd and strictly increasing. Hence it preserves the sign
of a single edge difference, and
\(\operatorname{sgn}(f_b(x)+f_b(y))=\operatorname{sgn}(x+y)\):
this is immediate if \(x\) and \(y\) have the same sign, while for opposite
signs it follows from strict monotonicity.

For necessity, every tree of diameter at least three contains a three-edge path.
Assign differences \((2t+1,-t,-t)\) along it and zero to the other edges.
The true difference between its endpoints is \(1>0\). As \(t\) grows,

\[
f_b(2t+1)-2f_b(t)\longrightarrow-2\operatorname{artanh}(b)<0.
\]

Thus some finite \(t\) reverses the order. The four-vertex numerical example
above uses \(b=1/2\), \(t=3/2\), and \(2t+1=4\).

## What an audit can and cannot do

An additional direct comparison of vertices \(1\) and \(4\) exposes this
particular ambiguity. World A's direct edge has positive mean
\(b\tanh(1/2)\), whereas the score vector inferred from the path predicts
a negative Bradley--Terry difference. The enlarged edge set creates a
four-cycle; its nondegenerate cycle equation also calibrates the shared-flip
rate, as shown below.

Emmy's ledger entry 13 gives a stronger repair within the constant-flip
model. Add a chord that creates a triangle with three distinct score levels.
For its calibrated edge means \(A=w_{ij}\), \(B=w_{jk}\), and \(C=w_{ik}\),
the Bradley--Terry addition rule gives

\[
C=\frac{A+B}{1+AB/b^2},
\qquad
b^2=\frac{ABC}{A+B-C},
\]

provided \(ABC\ne0\). The positive root identifies \(b\); then each
edge difference is \(2\operatorname{artanh}(w_e/b)\). A chord from vertex
\(1\) to \(3\), or from \(2\) to \(4\), creates such a triangle in the
four-vertex example. This calibration is model-conditional and may be
unstable near a degenerate triangle.

## What one comparison cycle can identify

The observer-overlap triangle in P calibrates peer reliabilities; the cycles
here are in the separate agent-comparison graph. Under a uniform positive
common flip, let \(w_e=b\tanh(d_e/2)\) be the calibrated mean on each
consistently oriented edge of a comparison cycle. A candidate \(b\) must
satisfy \(b>\max_e|w_e|\), \(b\leq1\), and

\[
\sum_e 2\operatorname{artanh}(w_e/b)=0.
\]

Write \(S_k\) for the degree-\(k\) elementary symmetric sum of the cycle's
\(w_e\). Expanding the hyperbolic addition law gives

\[
S_1b^{2}+S_3=0
\]

for a four-cycle. Thus \(S_1\ne0\) gives the unique admissible positive
\(b=\sqrt{-S_3/S_1}\), confirming emmy's ledger entry 22. A triangle and a
nondegenerate four-cycle each generically calibrate \(b\). For a five- or
six-cycle, however, the equation is

\[
S_1b^{4}+S_3b^{2}+S_5=0,
\]

which can have two admissible positive roots. Hence one cycle alone is not a
universal cardinal calibration design.

The ambiguity can change the ranking on a six-cycle. Orient its edges as
\(1\to2\to3\to4\to5\to6\to1\), and take the exact calibrated means

\[
(w_1,\ldots,w_6)=(-65,60,-52,-23,62,16)/100.
\]

Here \(S_1=-1/50\), \(S_3=12749/500000\), and
\(S_5=-497471/62500000\). Both roots satisfy the admissibility condition
\(\max_e|w_e|=0.65<b\leq1\): they are approximately \(0.738909\) and
\(0.853765\). For each root, define
\(d_e(b)=2\operatorname{artanh}(w_e/b)\). The cycle equation makes these
edge differences integrable to Bradley--Terry scores. With \(c_1=0\), the
first root gives \(c_3-c_6\approx0.042834>0\), while the second gives
\(c_3-c_6\approx-0.126036<0\). In each world draw the latent comparison
from its Bradley--Terry edge law, a common independent item flip of mean
\(b\), and independent observer flips of the same positive reliabilities.
The resulting effective binary comparison has mean \(w_e\) in both worlds,
so every observable joint report distribution is identical. Even with
unlimited labels on every edge of this one-cycle graph, ordinal truth is
not identified within this restricted correlated-error class.

There is a useful ordinal exception. If a connected comparison graph has
diameter at most two, every vertex pair has a path of at most two edges.
For any admissible \(b>0\), \(d_e(b)\) is an odd, strictly increasing
function of \(w_e\), and the sign of a sum along at most two edges is
independent of \(b\). Thus the entire ranking is identified even when the
shared-flip rate and cardinal score magnitudes are not. A five-cycle has
this property; the six-cycle above does not.

This is not a universal certification rule. With all pairs directly compared,
a positive edge-independent common flip preserves each pair's sign, so it
preserves the ordinal ranking while still changing score magnitudes. More
general correlated errors can evade different checks. The audit claim must
specify an error class and a query design.

## Pair-specific research question

P supplies a label-free predictor whose identification rests on an untestable
conditional-independence premise. Q supplies the requirements for using such
a predictor in a decision algorithm: a meaningful ordinal error, a
sensitivity theorem for downstream cost, and an accounting of prediction
queries. A concrete next question is: under a declared class of common-mode
or correlated peer errors, which additional comparison edges or trusted
anchors make ranking error identifiable, and what is the least query cost
needed for a downstream error-dependent guarantee? The example establishes
a sharp obstruction for connected tree comparison graphs. The star boundary
and triangle repair indicate that ordinal and cardinal outputs can require
different comparison designs. They do not prove the general audit design
result or a downstream competitive ratio.

Related work already studies [correlated crowd workers][li],
[pairwise co-occurrence identification][ibrahim], and
[semi-verified learning][meister].
The graph-design question needs a fuller novelty review before any
publication claim.

[li]: https://proceedings.mlr.press/v97/li19i.html
[ibrahim]: https://proceedings.neurips.cc/paper/2019/hash/c0e19ce0dbabbc0d17a4f8d4324cc8e3-Abstract.html
[meister]: https://proceedings.mlr.press/v75/meister18a.html
