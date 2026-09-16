"""Attributed (CEF, P eq 23-24) vs physical carbon for spatial DDC moves on the
IEEE 33-bus feeder (Baran-Wu 1989 data), P's own testbed (P Sec 4.1, Fig 5, Fig 7).

Assumptions (P does not give them): substation import at e_grid = 0.8 tCO2/MWh,
PV 1.5 MW at bus 9, WT 0.6 MW at bus 22, gas unit G 0.4 MW at bus 30 with
e_G = 0.5, all dispatch fixed (P Sec 3.4 has no generation variables).
Fixed loads = Baran-Wu base loads (3.715 MW). DDC loads: 0.5 MW in total,
placed at bus 15, 22 or 28 (P Fig 7). Lossy DistFlow by backward-forward sweep.

Physical emissions E = e_grid * P_sub + e_G * P_G.
Kang CEF: bus intensity = injection-weighted mix of generation and received
branch power; carbon conservation E = sum_i e_i L_i + sum_branches e_src * loss.
LME_i = dE/dL_i by finite difference (dispatch fixed; curtailment optional).
"""
import numpy as np

BR = [(1, 2, .0922, .0470), (2, 3, .4930, .2511), (3, 4, .3660, .1864), (4, 5, .3811, .1941),
      (5, 6, .8190, .7070), (6, 7, .1872, .6188), (7, 8, .7114, .2351), (8, 9, 1.0300, .7400),
      (9, 10, 1.0440, .7400), (10, 11, .1966, .0650), (11, 12, .3744, .1238), (12, 13, 1.4680, 1.1550),
      (13, 14, .5416, .7129), (14, 15, .5910, .5260), (15, 16, .7463, .5450), (16, 17, 1.2890, 1.7210),
      (17, 18, .7320, .5740), (2, 19, .1640, .1565), (19, 20, 1.5042, 1.3554), (20, 21, .4095, .4784),
      (21, 22, .7089, .9373), (3, 23, .4512, .3083), (23, 24, .8980, .7091), (24, 25, .8960, .7011),
      (6, 26, .2030, .1034), (26, 27, .2842, .1447), (27, 28, 1.0590, .9337), (28, 29, .8042, .7006),
      (29, 30, .5075, .2585), (30, 31, .9744, .9630), (31, 32, .3105, .3619), (32, 33, .3410, .5302)]
LOAD = {2: (100, 60), 3: (90, 40), 4: (120, 80), 5: (60, 30), 6: (60, 20), 7: (200, 100), 8: (200, 100),
        9: (60, 20), 10: (60, 20), 11: (45, 30), 12: (60, 35), 13: (60, 35), 14: (120, 80), 15: (60, 10),
        16: (60, 20), 17: (60, 20), 18: (90, 40), 19: (90, 40), 20: (90, 40), 21: (90, 40), 22: (90, 40),
        23: (90, 50), 24: (420, 200), 25: (420, 200), 26: (60, 25), 27: (60, 25), 28: (60, 20),
        29: (120, 70), 30: (200, 600), 31: (150, 70), 32: (210, 100), 33: (60, 40)}
NB = 33
ZB = 12.66 ** 2 / 1.0  # 1 MVA base, MW units
E_GRID, E_G = 0.8, 0.5
GEN = {9: (1.5, 0.0), 22: (0.6, 0.0), 30: (0.4, E_G)}  # bus: (MW, intensity)
DDC_BUSES = (15, 22, 28)

parent = {t: (f, r / ZB, x / ZB) for f, t, r, x in BR}
children = {i: [] for i in range(1, NB + 1)}
for f, t, _, _ in BR:
    children[f].append(t)
order = [1]
for i in order:
    order.extend(children[i])


def flow(PL, QL, PG):
    V2 = np.ones(NB + 1)
    Ps, Pr = np.zeros(NB + 1), np.zeros(NB + 1)  # sending / receiving flow into branch ending at bus j
    Qs, Qr = np.zeros(NB + 1), np.zeros(NB + 1)
    for _ in range(60):
        for j in reversed(order[1:]):
            f, r, x = parent[j]
            Pr[j] = PL[j] - PG[j] + sum(Ps[c] for c in children[j])
            Qr[j] = QL[j] + sum(Qs[c] for c in children[j])
            S2 = (Pr[j] ** 2 + Qr[j] ** 2) / V2[j]
            Ps[j], Qs[j] = Pr[j] + r * S2, Qr[j] + x * S2
        for j in order[1:]:
            f, r, x = parent[j]
            V2[j] = V2[f] - 2 * (r * Ps[j] + x * Qs[j]) + (r * r + x * x) * (Ps[j] ** 2 + Qs[j] ** 2) / V2[f]
    return Ps, Pr, V2


def evaluate(ddc, pv9=GEN[9][0], export_limit=None):
    """ddc: dict bus -> MW. export_limit: max reverse flow on branch 8-9 (curtails PV at 9)."""
    PL = np.zeros(NB + 1); QL = np.zeros(NB + 1); PG = np.zeros(NB + 1); EG = np.zeros(NB + 1)
    for b, (p, q) in LOAD.items():
        PL[b], QL[b] = p / 1000, q / 1000
    LF = PL.copy()
    for b, mw in ddc.items():
        PL[b] += mw
    for b, (mw, e) in GEN.items():
        PG[b], EG[b] = mw, e
    curt = 0.0
    if export_limit is not None:
        lo, hi = 0.0, pv9
        PG[9] = pv9
        if -flow(PL, QL, PG)[0][9] > export_limit:
            for _ in range(50):
                mid = (lo + hi) / 2
                PG[9] = pv9 - mid
                if -flow(PL, QL, PG)[0][9] > export_limit:
                    lo = mid
                else:
                    hi = mid
            curt = hi
            PG[9] = pv9 - curt
    Ps, Pr, V2 = flow(PL, QL, PG)
    Psub = Ps[2]
    # CEF: bus inflow = generation + received branch power; substation is a generator at bus 1
    PG1 = PG.copy(); EG1 = EG.copy(); PG1[1] = Psub; EG1[1] = E_GRID
    T = np.zeros((NB, NB)); g = np.zeros(NB)
    for j in range(1, NB + 1):
        T[j - 1, j - 1] += PG1[j]
        g[j - 1] += PG1[j] * EG1[j]
    lossc = []
    for j in order[1:]:
        f = parent[j][0]
        if Ps[j] >= 0:  # f -> j, j receives Pr
            T[j - 1, j - 1] += Pr[j]; T[j - 1, f - 1] -= Pr[j]; lossc.append((f, Ps[j] - Pr[j]))
        else:  # j -> f, f receives -Ps
            T[f - 1, f - 1] += -Ps[j]; T[f - 1, j - 1] -= -Ps[j]; lossc.append((j, Ps[j] - Pr[j]))
    e = np.linalg.solve(T + 1e-12 * np.eye(NB), g)
    e = np.concatenate([[0.0], e])
    E = E_GRID * Psub + sum(PG[b] * EG[b] for b in GEN)
    attributed_load = sum(e[b] * PL[b] for b in range(2, NB + 1))
    attributed_loss = sum(e[s] * l for s, l in lossc)
    fixed = sum(e[b] * LF[b] for b in range(2, NB + 1))
    gdl = sum(e[b] * mw for b, mw in ddc.items())
    return dict(E=E, e=e, attr=attributed_load, attr_loss=attributed_loss, fixed=fixed, gdl=gdl,
                Psub=Psub, curt=curt, loss=Psub + PG.sum() - PL.sum(), minV=np.sqrt(V2[1:].min()))


def lme(ddc, **kw):
    base = evaluate(ddc, **kw)["E"]
    out = np.zeros(NB + 1)
    for b in range(2, NB + 1):
        d = dict(ddc); d[b] = d.get(b, 0.0) + 1e-3
        out[b] = (evaluate(d, **kw)["E"] - base) / 1e-3
    return out


def report(title, **kw):
    print(f"\n=== {title} ===")
    res = {}
    for b in DDC_BUSES:
        res[b] = evaluate({b: 0.5}, **kw)
    r0 = res[DDC_BUSES[0]]
    print(f"conservation check: E={r0['E']:.4f}, sum e_i L_i + loss carbon={r0['attr'] + r0['attr_loss']:.4f}")
    print(f"base (no DDC) NCI at DDC buses and LME:")
    nd = evaluate({}, **kw); L0 = lme({}, **kw)
    for b in DDC_BUSES:
        print(f"  bus {b}: NCI={nd['e'][b]:.3f}  LME={L0[b]:.3f}")
    print("DDC 0.5 MW at bus: E_phys | GDL attributed | fixed-load attributed | loss MW | curtail MW | minV")
    for b, r in res.items():
        print(f"  {b:2d}: {r['E']:.4f} | {r['gdl']:.4f} | {r['fixed']:.4f} | {r['loss']:.4f} | {r['curt']:.4f} | {r['minV']:.3f}")
    for a in DDC_BUSES:
        for b in DDC_BUSES:
            if a < b:
                ra, rb = res[a], res[b]
                print(f"  move {a}->{b}: dE_phys={rb['E'] - ra['E']:+.4f}, dGDL_attr={rb['gdl'] - ra['gdl']:+.4f}, "
                      f"exogenous-NCI objective (26) change={0.5 * (nd['e'][b] - nd['e'][a]):+.4f}, "
                      f"dFixed_attr={rb['fixed'] - ra['fixed']:+.4f}")
    # full sweep of single-bus placement
    Es = np.array([evaluate({b: 0.5}, **kw)["E"] for b in range(2, NB + 1)])
    Js = 0.5 * nd["e"][2:]
    print(f"sweep over 32 buses: range of E_phys={Es.max() - Es.min():.4f}, range of 0.5*NCI={Js.max() - Js.min():.4f}, "
          f"corr={np.corrcoef(Es, Js)[0, 1]:+.3f}")
    print(f"sum_i LME_i L_i={sum(L0[b] * LOAD[b][0] / 1000 for b in LOAD):.4f} vs E={nd['E']:.4f}")


if __name__ == "__main__":
    report("A: no curtailment, dispatch fixed")
    report("B: PV at bus 9 with reverse-flow limit 0.3 MW on branch 8-9", export_limit=0.3)
