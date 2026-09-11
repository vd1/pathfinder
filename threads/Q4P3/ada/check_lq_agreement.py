# Checks for ada's ledger claims. Run: uv run --with sympy python ada/check_lq_agreement.py
import sympy as sp

th, b1, b2, k1, k2, a1, a2 = sp.symbols('theta b1 b2 kappa1 kappa2 a1 a2', real=True)
D = a2 - a1
# Q's coupled-reward environment (sec. "Competition through coupled rewards"),
# with Q's reward (CR) replaced by a pure agreement penalty -kappa_i * D^2.
U1 = -(a1 - th - b1)**2 - k1*D**2
U2 = -(a2 - th - b2)**2 - k2*D**2
sol = sp.solve([sp.diff(U1, a1), sp.diff(U2, a2)], [a1, a2], dict=True)[0]
e1 = sp.simplify(sol[a1] - th); e2 = sp.simplify(sol[a2] - th)
print("a1-theta =", sp.factor(e1))
print("a2-theta =", sp.factor(e2))
print("D        =", sp.factor(sp.simplify(sol[a2] - sol[a1])))
# concavity in own action
print("d2U1/da1^2 =", sp.diff(U1, a1, 2), " d2U2/da2^2 =", sp.diff(U2, a2, 2))
# symmetric kappa -> infinity
k = sp.symbols('kappa', positive=True)
print("sym limit a1-theta:", sp.limit(e1.subs({k1: k, k2: k}), k, sp.oo))
print("sym human loss limit:", sp.simplify(sp.limit((e1**2 + e2**2).subs({k1: k, k2: k}), k, sp.oo)))
# critic yields: kappa2 -> infinity with kappa1 fixed
print("C yields (k2->oo): a1-theta ->", sp.limit(e1, k2, sp.oo), " a2-theta ->", sp.limit(e2, k2, sp.oo))
# reviewer not conformist: kappa1 = 0
print("k1=0: a1-theta =", sp.simplify(e1.subs(k1, 0)))
# critic-helps condition in symmetric-kappa limit, output = consensus (b1+b2)/2 vs single reviewer b1
x = sp.symbols('x', real=True)
print("|(b1+x)/2| < |b1| for b1=1 :", sp.solve_univariate_inequality(sp.Abs((1 + x)/2) < 1, x))

# ---- Q's binary peer-scoring example: uninformative symmetric equilibrium? ----
p = sp.symbols('p')
betaH = {'H': sp.Rational(2, 3), 'L': sp.Rational(1, 3)}
betaL = {'H': 1, 'L': 0}
def q(rep, other):
    b = betaH if rep == 'H' else betaL
    return 2*b[other] - sum(v**2 for v in b.values())
print("score table:", {(i, j): q(i, j) for i in 'HL' for j in 'HL'})
# partner reports H w.p. p regardless of type
sH = p*q('H', 'H') + (1 - p)*q('H', 'L')
sL = p*q('L', 'H') + (1 - p)*q('L', 'L')
pstar = sp.solve(sp.Eq(sH, sL), p)
print("indifference p* =", pstar)
# pure pooling 'always H' / 'always L': profitable deviation?
print("always H: stay", q('H', 'H'), "deviate", q('L', 'H'))
print("always L: stay", q('L', 'L'), "deviate", q('H', 'L'))
# human payoff in babbling equilibrium: a=1 iff both report H; v=1{a1=a2=theta}; P(theta=1)=1/2 indep of reports
ps = pstar[0]
print("human payoff babbling =", sp.simplify(ps**2*sp.Rational(1, 2) + (1 - ps**2)*sp.Rational(1, 2)))
