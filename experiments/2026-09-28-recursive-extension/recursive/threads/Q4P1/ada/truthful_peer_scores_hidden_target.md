# Truthful peer reports can hide an inverted target ranking

## Source claims and scope

The actual Q is *Mechanism Design for Alignment and Control*. In its peer discipline example, a supported type
\(t_i\) has a known predictive distribution \(\beta_i[t_i]\) over co-player types. Distinct supported types
must have distinct predictions. Its quadratic score has truthful-report advantage
\(\Lambda\|\beta_i[t_i]-\beta_i[\hat t_i]\|_2^2\); utility cancellation and action support restrictions then
implement an action rule (Q.tex, lines 1651-1734). Q allows correlated agent information (Q.tex, lines
1477-1506). These are strategic conditions, and they do not establish that the co-player reports reveal a
chosen external target.

The supplied P is a manuscript about a different internal paper pair. Its four-vertex path example gives a
clean world and a shared-flip world with exactly the same report distribution but opposite endpoint score
orders (P.tex, lines 63-96). Its graph results and repairs assume a constant positive common-flip mean
independent of intended comparisons (P.tex, lines 99-135 and 180-185).

## Composition proposition

There is a two-agent, finite-type peer-scoring game satisfying Q's strict co-player-belief separation in each
of P's two worlds. The same quadratic score makes truthful reporting of private peer labels a strict best
response in both worlds, while no rule based on those reports can uniformly identify the intended endpoint
order with error below \(1/2\).

Take P's oriented path \(1\to2\to3\to4\). In world \(W\), the intended independent comparisons have
Bradley--Terry edge differences \((4,-3/2,-3/2)\). Each edge draw has an independent common flip with mean
\(b=1/2\). In world \(W'\), there is no common flip and the intended edge differences are
\((f_b(4),f_b(-3/2),f_b(-3/2))\), where
\[
f_b(d)=2\operatorname{artanh}\bigl(b\tanh(d/2)\bigr).
\]
Both agents label all three edges. For each agent \(i\) and edge \(e\), let \(Z_{ei}\) be a symmetric personal
flip with known mean \(a_i\in(0,1)\). These flips are independent across agents and edges and from the
comparisons. The observed label is \(Y_{ei}=S_eZ_{ei}\). The private type reported by agent \(i\) is its
three-label vector \(T_i=(Y_{ei})_{e=1}^3\in\{-1,+1\}^3\). It is observed before reporting; there are no later
signals and the feasible action is a singleton. Thus the only incentive problem is truthful reporting of
\(T_i\).

Let \(S_e=X_eB_e\) in \(W\), and \(S_e=X'_e\) in \(W'\). Their means are identical:
\[
w_e=\mathbb E S_e=b\tanh(d_e/2)=\tanh(f_b(d_e)/2).
\]
The \(S_e\) are independent across edges in both worlds, and the same personal-flip channel maps them to
\((T_1,T_2)\). Therefore the **entire joint law** of private type vectors, and every co-player predictive
distribution \(\beta_i[t]=\mathcal L(T_j\mid T_i=t)\), coincide between worlds.

The predictive distributions nonetheless separate distinct types. On any edge, \(\mathbb E Y_{ei}=a_iw_e\),
\(\mathbb E Y_{ej}=a_jw_e\), and \(\mathbb E[Y_{ei}Y_{ej}]=a_ia_j\). Direct conditioning yields
\[
\mathbb E[Y_{ej}\mid Y_{ei}=+1]-\mathbb E[Y_{ej}\mid Y_{ei}=-1]
=\frac{2a_ia_j(1-w_e^2)}{1-a_i^2w_e^2}>0.
\]
All type vectors have positive probability. Independence across edges means that if two vectors differ on edge
\(e\), their predictive laws for the other agent differ on that edge. Thus \(\beta_i[t]\ne\beta_i[t']\) for
every \(t\ne t'\), exactly the separation needed for the scoring step in Q.

Set the report reward to Q's quadratic peer score, with no other utility:
\[
R_i(r_i,r_j)=\Lambda\left(2\beta_i[r_i](r_j)-\|\beta_i[r_i]\|_2^2\right),\qquad \Lambda>0.
\]
When the other agent reports truthfully, the expected loss from reporting \(r_i\ne t_i\) is
\[
\Lambda\|\beta_i[t_i]-\beta_i[r_i]\|_2^2>0.
\]
The score table is the same in both worlds because the joint private-type law is the same. Hence truthful peer
reporting is a strict Bayesian best response in both worlds. This is an existence claim about the truthful
equilibrium, not equilibrium uniqueness.

The intended endpoint differences have opposite signs:
\[
c_1-c_4=4-3/2-3/2=1>0,
\qquad
c'_1-c'_4=f_{1/2}(4)-2f_{1/2}(3/2)\simeq-0.26458<0.
\]
At the truthful equilibrium, a decision rule based on any number of independent report repetitions has the
same output distribution in the two worlds. Its two endpoint-order error probabilities sum to at least one, so
one is at least \(1/2\). Strict strategic truthfulness of peer labels therefore does not certify the intended
Bradley--Terry endpoint ranking.

This is a claim about certification from the peer-report interface. Q's full universal type includes beliefs
about the payoff-relevant state, and its designer is given a model of the joint state and types (Q.tex, lines
1450-1493). If that model already identifies the intended score vector, the designer can distinguish the two
worlds by assumption. The same-law argument applies when the target relation is to be learned from peer
reports; it does not contradict Q's theorem with its full information and reward access.

## Information that changes the conclusion

The impossibility applies to the four-vertex path and the class containing both a clean and a common-flip
world. Under P's restricted constant positive common-flip model, an independently known \(b\) lets one invert
each calibrated edge mean by \(d_e=2\operatorname{artanh}(w_e/b)\). P also derives a nondegenerate triangle or
four-cycle formula that identifies \(b\) from population edge means, then integrates the differences over a
connected graph (P.tex, lines 118-134). The edge means first require known observer reliabilities or P's
three-observer overlap calibration (P.tex, lines 46-60). External target labels could instead anchor the sign
or rate if their relation to the intended comparisons is known. These extra inputs address statistical
identification. Q's known predictive map, belief separation, and adequate incentive scale address strategic
reporting. Neither set of conditions replaces the other.

## Exact ordinal boundary with heterogeneous shared flips

The short-cycle repair has a sharp limit. Suppose the common flip remains independent from item to item and
from the intended comparison, but its positive mean \(b_e\in(0,1]\) can vary freely by comparison edge.
Retain positive personal observer reliabilities, independent comparison draws, and a connected comparison
graph. The observable calibrated mean is
\[
w_e=b_e\tanh((c_u-c_v)/2),\qquad e=(u,v).
\]
Assume every \(w_e\ne0\) and the observed means are feasible under this model. Orient an edge from its
higher-score endpoint to its lower-score endpoint according to the sign of \(w_e\), and call the resulting
directed graph \(H\). Then \(c_u>c_v\) is forced by the full peer-report law exactly when \(H\)
contains a directed path from \(u\) to \(v\). The pairwise order is determined if the vertices are
comparable in this directed reachability order. Incomparable vertices may have either order in two worlds
with the same full report law.

The nonzero-mean assumption avoids ties. If \(w_e=0\) and \(b_e>0\), then \(c_u=c_v\); those
endpoints can be contracted before applying the reachability test, provided the observed signs are
compatible with some score vector. Across all possible distinct-score vectors, a graph certifies every
pairwise order under arbitrary positive edge-specific flip means exactly when it is complete. Direct edges
suffice. For any missing pair, choose scores that place those two vertices above all others and swap only
their relative order; preserve the observed edge signs by choosing small enough calibrated means and
adjusting the separate flip rates. This uniform graph statement is weaker than the data-specific
reachability certificate above.

For sufficiency, every edge on a directed path has a positive score drop, so the path endpoints have the
same order in every compatible world. For necessity, the orientation is acyclic because it comes from a
score vector. If \(u\) and \(v\) are incomparable, a directed acyclic graph has a linear extension with
\(u\) before \(v\) and another with \(v\) before \(u\). For either extension, assign scores descending
by a fixed spacing \(M>\max_e2\operatorname{artanh}|w_e|\). Every edge difference then has the observed
sign and magnitude larger than \(2\operatorname{artanh}|w_e|\). Set
\[
b_e=\frac{w_e}{\tanh((c_u-c_v)/2)}\in(0,1).
\]
The corrupted latent sign \(S_e=X_eB_e\) is binary with mean \(w_e\) in either construction. With
independent draws across edges and the same personal-flip channels, both constructions induce the same
complete peer-report distribution. They reverse the order of \(u\) and \(v\). The conditional peer laws
and Q-style quadratic score table are consequently the same, and the strict separation argument above
continues to apply. This is a partial-identification statement inside the stated heterogeneous noise class,
not a claim that an arbitrary correlated-noise law has this form.

In particular, a triangle only recovers the flip mean if edge homogeneity is assumed. The new edge
\(1\)--\(3\) proposed for P's path creates a cycle, but with unrestricted \(b_e\) it does not force the
order of vertices \(1\) and \(4\). A direct comparison of \(1\) and \(4\), or another directed path
whose signs connect them, certifies their order under positive edge-specific flips. Thus a report-only
cycle consistency check cannot validate the homogeneity premise that makes P's inversion formula work.

The loss of ordinal identification already occurs on a three-vertex path, even though its diameter is two.
Set the observable calibrated means to \(w_{12}=1/5\) and \(w_{23}=-1/5\). One world has intended edge
differences \((2,-1)\), giving \(c_1-c_3=1\); another has \((1,-2)\), giving \(c_1-c_3=-1\).
In either world set each \(b_e=w_e/\tanh(d_e/2)\), which lies in \((0,1)\). The independent corrupted
signs have the same law in both worlds. With the same peer channels, the full report law and Q-style
truthful-report incentives also coincide. P's diameter-two ordinal guarantee therefore depends on its
edge-constant flip restriction.

This ordinal certificate needs less calibration than numerical score recovery. If a single observer on
each edge has positive reliability \(a_e\ge\alpha>0\), then
\(\operatorname{sgn}\mathbb E Y_e=\operatorname{sgn}w_e\), so the edge signs require no estimate of the
\(a_e\) values. If \(|w_e|\ge\kappa>0\) and each edge has \(N\) independent reports, Hoeffding's
inequality and a union bound make all edge signs correct with probability at least \(1-\zeta\) when
\[
N\ge\frac{2}{\alpha^2\kappa^2}\log\frac{2|E|}{\zeta}.
\]
The transitive-closure orders then hold with the same probability. Without a lower bound on the
observable edge signal \(a_e|w_e|\), no fixed finite sample count provides a uniform sign guarantee.
This sampling claim presumes reports are truthful; Q's peer-score assumptions address that separate
strategic condition.

## Boundary and publication assessment

The general idea of using a peer's report to score truthful private signals is established in Miller, Resnick,
and Zeckhauser's [peer prediction paper](https://doi.org/10.1287/mnsc.1050.0379). Shnayder et al.'s [informed
truthfulness paper](https://arxiv.org/abs/1603.03151) studies the separate problem of uninformative
equilibria. Neither source, as checked here, establishes novelty of the structured Bradley--Terry reversal in
this note.

This construction is a precise cross-paper impossibility, but its statistical half is already P's path example
and its strategic half follows directly from Q's quadratic score. A publication would need further work, such
as a general criterion for when peer-scoring equilibrium outcomes certify a target under specified noise
classes, or an efficient audit design with finite-sample guarantees and strategic incentives. The present
result alone is a supported research direction, not a novelty claim.

The heterogeneous-noise result above gives one such criterion and an edge-sign sample bound, but it is an
elementary partial-order consequence of positive corruption rates. Targeted searches for
"pairwise comparisons unknown edge-specific flipping probabilities ranking identifiability directed graph
partial order peer labels" and "Bradley Terry model comparison graph unknown per-edge noise rates
identifiability partial order" did not establish whether this exact formulation is new. It should be
treated as a candidate lemma for a broader paper, not an established novelty claim.
