"""Proportional-sharing carbon emission flow (P eq 23-24) on a 3-bus star feeder.

Bus 0: substation, grid import at intensity e_g. Buses 1, 2 hang off bus 0.
PV of size G at bus 2 (zero carbon). Fixed loads F1, F2; one geographically
dispatchable load (GDL) of size D placed at bus 1 or bus 2. Lossless.
Reverse-flow limit R on line 2->0 (R = inf: no curtailment).

Compare P's objective (26) restricted to the GDL, J = e_bus * D, with physical
system emissions E = e_g * import, and with the locational marginal emission
LME_i = dE/dL_i (finite difference).
"""
import math

E_G, F1, F2, G, D = 0.8, 1.0, 1.0, 1.5, 0.5


def solve(L1, L2, R):
    export2 = max(0.0, min(G - L2, R))  # PV surplus sent from bus 2 to bus 0
    curtail = max(0.0, G - L2 - export2)
    imp = L1 + L2 - (G - curtail)
    assert imp >= -1e-12, "net export to grid not modelled"
    e2 = 0.0 if L2 <= G else (L2 - G) * E_G / L2
    # bus 0 mixture: grid import plus PV export from bus 2
    e0 = E_G if export2 == 0 else imp * E_G / (imp + export2)
    e1 = e0
    E = E_G * imp
    attributed = e1 * L1 + e2 * L2
    return dict(e1=e1, e2=e2, E=E, attributed=attributed, curtail=curtail)


def lme(L1, L2, R, h=1e-6):
    base = solve(L1, L2, R)["E"]
    return (solve(L1 + h, L2, R)["E"] - base) / h, (solve(L1, L2 + h, R)["E"] - base) / h


for R in (math.inf, 0.0):
    print(f"--- reverse-flow limit R = {R}")
    for where in (1, 2):
        L1, L2 = F1 + D * (where == 1), F2 + D * (where == 2)
        s = solve(L1, L2, R)
        e_gdl = s["e1"] if where == 1 else s["e2"]
        m1, m2 = lme(L1, L2, R)
        print(f"GDL at bus {where}: NCI e1={s['e1']:.3f} e2={s['e2']:.3f} | J_GDL={e_gdl*D:.3f}"
              f" | fixed-load attributed={s['attributed']-e_gdl*D:.3f} | E_phys={s['E']:.3f}"
              f" (sum e_i L_i={s['attributed']:.3f}) | curtail={s['curtail']:.3f} | LME=({m1:.2f},{m2:.2f})")
