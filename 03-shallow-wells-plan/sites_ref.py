"""Independent reference for tool 03, "Five wells: which five?".

The page integrates the site's own part of the horizon-pick error exactly (it is an interval in depth) and
steps the dip, the cover and the thickness scale on a grid. This script does it another way: plain Monte
Carlo over all the errors, two million joint draws for the sites on each anchor horizon. The scoring, the
exhaustive search for the best set of wells, the drilling order and the choice of the wells still to drill
after the first cores then follow the rules written on the page.

Geometry, for one site. u is the stratigraphic distance below the top of the youngest unit, measured
normal to bedding. The anchor horizon h (the base of unit h) is picked at depth zH below the seabed; the
beds dip at theta; the cover, drilled without coring, is q thick; the hole stops at D below the seabed.
A point at depth z has
    u(z) = U_h - (zH - z) cos(theta),
so the core from q to D spans u in [U_h - (zH - q) cos theta, U_h + (D - zH) cos theta].
A thickness error scales every distance from the anchor horizon by one factor f.

Shared pick error. The +-e range of a pick is cut into M equal parts. Which part the true depth lies in is
common to the sites anchored on one horizon and picked on the same kind of seismic (2D only, or a high-res
line); where it lies inside that part is the site's own:
    zH = pick + e * (c + o / M),   c one of the M part centres -1 + (2j + 1) / M, drawn once per horizon
                                   and kind of seismic, o drawn per site, evenly in [-1, 1].
Each site's error is still spread evenly over +-e, whatever M. M = 1: nothing shared; M = 2: the sites
agree on the side of the pick, deeper or shallower; M = 4: on its quarter; M = 10: on its tenth.
So two such wells do not back each other up the way two wells on different horizons do.

After drilling. A site is drilled once a unit is identified in its core, or the depth at which its anchor
horizon was met is known (to the nearest metre: within 0.5 m). The draws that agree with what the cores
showed are kept and the rest dropped: that narrows where the horizon can lie at the other sites that share
its pick error. A drilled hole has delivered, and the unit identified in it is cored for sure; whether its
rock gives an age stays as entered. If no draw agrees, the horizon does not tie: its drilled sites count
the unit identified only, and all its sites still to drill are held.

Run: python sites_ref.py          prints the values the page checks against and writes ref_values.json
     python sites_ref.py 200000   a quicker look with fewer draws (ref_values.json is not written)
"""
import itertools
import json
import math
import os
import sys

import numpy as np

EXAMPLE = {
    "depth": 100, "minsec": 5, "side": 3, "okp": 80, "wells": 5,
    "ddip": 1.0, "dcover": 4.0, "dthick": 10.0, "ehr": 4.0, "e2d": 30.0, "share": 50.0,
    # name, thickness m, role, priority (3 high, 2 medium, 1 low, 0 skip), value of dating its base (2 key, 1 useful,
    # 0 skip), chance that core of the unit gives an age, %
    "units": [
        ["Fluvial red beds", 120, "Other", 1, 1, 20],
        ["Deltaic sandstone", 90, "Reservoir", 3, 1, 60],
        ["Marine mudstone", 50, "Seal", 3, 2, 90],
        ["Shoreface sandstone", 80, "Reservoir", 2, 2, 70],
        ["Organic-rich shale", 40, "Source rock", 3, 1, 90],
        ["Silty mudstone", 140, "Seal", 1, 1, 90],
        ["Basal sandstone", 80, "Reservoir", 2, 0, 60],
    ],
    # name, anchor horizon (h = base of unit h), its depth below seabed m, cover m, dip deg, high-res line
    "sites": [
        ["A", 1, 70, 10, 4, False],
        ["B", 2, 65, 30, 6, False],
        ["C", 3, 35, 20, 10, True],
        ["D", 3, 50, 45, 7, False],
        ["E", 5, 70, 35, 8, True],
        ["F", 4, 33, 12, 15, False],
        ["G", 7, 134, 62, 12, False],
        ["H", 7, 96, 40, 10, True],
        ["I", 1, 50, 30, 12, True],
        ["J", 2, 18, 8, 9, False],
        ["K", 4, 90, 50, 5, False],
        ["L", 6, 63, 20, 20, False],
    ],
}
# made-up results after the first two wells: site -> (unit dated in its core, depth at which its anchor horizon was
# met or None)
DEMO = {
    "moves": {"J": (2, 31), "F": (5, 29)},
    "breaks": {"J": (1, None), "F": (5, 29)},
}

N_DRAWS = 2_000_000
REPS_AFTER = 5   # the cases after drilling keep few draws, so they take five times as many


def tops(units):
    U = [0.0]
    for u in units:
        U.append(U[-1] + u[1])
    return U


def parts(m):
    """Number of equal parts of the pick range whose choice is shared along a horizon: 1 / (1 - share)."""
    return max(1, round(1 / (1 - m["share"] / 100)))


def age_both(m, k):
    """Chance that the rock on both sides of the base of unit k gives an age; below the deepest unit the
    older rock is taken to give ages like that unit."""
    units = m["units"]
    below = units[k + 1][5] if k + 1 < len(units) else units[k][5]
    return units[k][5] / 100 * below / 100


def draw_horizon(m, h, n, seed, facts):
    """Joint draws for the sites anchored on horizon h. For each site, three tables of n draws by unit:
    the core holds at least minsec m of unit k; it holds side m on both sides of the base of unit k; it
    touches unit k at all; and, for a drilled site, the draws that agree with what its core showed.
    Also the shared part of the pick error, one for the 2D-only sites and one for the sites on a high-res line."""
    rng = np.random.default_rng(seed)
    U = tops(m["units"])
    M = parts(m)
    shared = {hr: -1 + (2 * rng.integers(0, M, n) + 1) / M for hr in (False, True)}
    out = {}
    for i, site in enumerate(m["sites"]):
        if site[1] != h:
            continue
        _, _, zH, q, dip, hr = site[:6]
        e = m["ehr"] if hr else m["e2d"]
        z = zH + e * (shared[bool(hr)] + rng.uniform(-1, 1, n) / M)
        th = np.abs(dip + m["ddip"] * rng.uniform(-1, 1, n)) * math.pi / 180
        qq = np.maximum(0.0, q + m["dcover"] * rng.uniform(-1, 1, n))
        f = 1 + m["dthick"] / 100 * rng.uniform(-1, 1, n)
        cs = np.cos(th)
        top = U[h] - (z - qq) * cs
        bot = U[h] + (m["depth"] - z) * cs
        has = qq < m["depth"]
        Us = [U[h] + (u - U[h]) * f for u in U]
        cu, cb, ca = [], [], []
        for k in range(len(m["units"])):
            ov = np.minimum(bot, Us[k + 1]) - np.maximum(top, Us[k])
            cu.append(has & (ov >= m["minsec"]))
            ca.append(has & (ov > 0))
            b = Us[k + 1]
            cb.append(has & (top <= b - m["side"]) & (bot >= b + m["side"]))
        agree = None
        if i in facts:
            unit, met = facts[i]
            agree = has.copy()
            if unit:
                agree &= ca[unit - 1]
            if met is not None:
                agree &= (np.abs(z - met) <= 0.5) & (met > qq) & (met < m["depth"])
        out[i] = (cu, cb, ca, agree)
    return shared, out


def tables(m, facts=None, n=None, reps=1):
    """For every anchor horizon and every set T of its sites: the chance that no well of T cores unit k,
    and that no well of T dates the base of unit k. facts: site index -> (unit dated, horizon depth met)."""
    n = n or N_DRAWS
    facts = facts or {}
    nu = len(m["units"])
    ok = m["okp"] / 100
    E, held, shift, broken_h, touch = {}, set(), {}, [], {}
    for h in sorted({s[1] for s in m["sites"]}):
        sites = [i for i, s in enumerate(m["sites"]) if s[1] == h]
        drilled = [i for i in sites if i in facts]
        subsets = [T for r in range(1, len(sites) + 1) for T in itertools.combinations(sites, r)]
        # two counts side by side: the draws that agree with the cores (fit), and all draws with the drilled
        # sites counting their dated unit only (the tie broken); which one stands is known at the end
        acc = {mode: {T: (np.zeros(nu), np.zeros(nu)) for T in subsets} for mode in ("fit", "broken")}
        kept, own, csum, tsum = 0, {i: 0 for i in drilled}, {False: 0.0, True: 0.0}, {i: np.zeros(nu) for i in sites}
        for rep in range(reps):
            c, G = draw_horizon(m, h, n, 10 + h + 1000 * rep, facts)
            mask = np.ones(n, dtype=bool)
            for i in drilled:
                own[i] += int(G[i][3].sum())
                mask &= G[i][3]
            kept += int(mask.sum())
            for hr in (False, True):
                csum[hr] += float(c[hr][mask].sum())
            for i in sites:
                tsum[i] += np.array([G[i][2][k].mean() for k in range(nu)]) / reps
            for mode in (("fit", "broken") if drilled else ("fit",)):
                # For site i and unit k the chance of missing the target in one draw is 1 - w * G, G being a
                # yes/no table of the draws (None: yes in every draw). The mean of a product of such terms
                # over the draws kept is counted exactly, by inclusion and exclusion over the sites of T.
                term = {}
                for i in sites:
                    cu, cb = G[i][0], G[i][1]
                    if i in facts:
                        kn = facts[i][0] - 1 if facts[i][0] else None
                        if mode == "broken":
                            tu = [(1.0, None) if k == kn else (0.0, None) for k in range(nu)]
                            tb = [(0.0, None) for k in range(nu)]
                        else:
                            tu = [(1.0, None) if k == kn else (1.0, cu[k]) for k in range(nu)]
                            tb = [(age_both(m, k), cb[k]) for k in range(nu)]
                    else:
                        tu = [(ok, cu[k]) for k in range(nu)]
                        tb = [(ok * age_both(m, k), cb[k]) for k in range(nu)]
                    term[i] = (tu, tb)
                w = mask if mode == "fit" else None
                total = int(mask.sum()) if mode == "fit" else n
                counts = {}

                def count(R, kind, k):
                    key = (R, kind, k)
                    if key not in counts:
                        tabs = [term[i][kind][k][1] for i in R if term[i][kind][k][1] is not None]
                        if w is not None:
                            tabs.append(w)
                        if not tabs:
                            counts[key] = total
                        else:
                            both = tabs[0]
                            for x in tabs[1:]:
                                both = both & x
                            counts[key] = int(both.sum())
                    return counts[key]

                for T in subsets:
                    for kind in (0, 1):
                        for k in range(nu):
                            s = float(total)
                            for r in range(1, len(T) + 1):
                                for R in itertools.combinations(T, r):
                                    wprod = 1.0
                                    for i in R:
                                        wprod *= term[i][kind][k][0]
                                    if wprod:
                                        s += (-1) ** r * wprod * count(R, kind, k)
                            acc[mode][T][kind][k] += s
        broken = bool(drilled) and (kept == 0 or any(own[i] == 0 for i in drilled))
        if broken:
            broken_h.append(h)
            held.update(i for i in sites if i not in facts)
        elif drilled:
            for hr in {bool(m["sites"][i][5]) for i in drilled}:
                shift[(h, hr)] = csum[hr] / kept
        mode, denom = ("broken", n * reps) if broken else ("fit", kept)
        for T in subsets:
            E[frozenset(T)] = ([float(x) / denom for x in acc[mode][T][0]], [float(x) / denom for x in acc[mode][T][1]])
        for i in sites:
            touch[i] = [float(x) for x in tsum[i]]
    return {"E": E, "held": held, "shift": shift, "broken": broken_h, "touch": touch}


def misses(m, T, S):
    nu = len(m["units"])
    mu, mb = [1.0] * nu, [1.0] * nu
    groups = {}
    for i in S:
        groups.setdefault(m["sites"][i][1], []).append(i)
    for g in groups.values():
        eu, eb = T["E"][frozenset(g)]
        for k in range(nu):
            mu[k] *= eu[k]
            mb[k] *= eb[k]
    return mu, mb


def value(m, T, S):
    mu, mb = misses(m, T, S)
    return sum(u[3] * (1 - mu[k]) + u[4] * (1 - mb[k]) for k, u in enumerate(m["units"]))


def value_alone(m, T, S):
    """The score with every well counted on its own chances, as if no pick error were shared."""
    v = 0.0
    for k, u in enumerate(m["units"]):
        a = b = 1.0
        for i in S:
            eu, eb = T["E"][frozenset([i])]
            a *= eu[k]
            b *= eb[k]
        v += u[3] * (1 - a) + u[4] * (1 - b)
    return v


def cored(m, S):
    return sum(max(0, m["depth"] - m["sites"][i][3]) for i in S)


def better(m, v, S, bv, bS):
    """The page's rule: higher score; on a tie, more metres cored; on a tie again, the earlier set."""
    if bS is None or v > bv + 1e-9:
        return True
    return abs(v - bv) <= 1e-9 and cored(m, S) > cored(m, bS) + 1e-9


def best_set(m, T, n, cand=None, base=()):
    """The best n sites out of cand (all sites if None), added to the wells in base."""
    cand = list(range(len(m["sites"]))) if cand is None else cand
    if n <= 0:
        return [], value(m, T, list(base))
    bS, bv = None, -1.0
    for S in itertools.combinations(cand, n):
        full = list(base) + list(S)
        v = value(m, T, full)
        if better(m, v, full, bv, None if bS is None else list(base) + bS):
            bS, bv = list(S), v
    return bS, bv


def drill_order(m, T, S, base=()):
    """Greedy: each next well is the one that adds most to the wells already drilled."""
    order, left = [], list(S)
    while left:
        bi, bg = None, -1.0
        for i in left:
            g = value(m, T, list(base) + order + [i])
            if bi is None or better(m, g, [i], bg, [bi]):
                bi, bg = i, g
        order.append(bi)
        left.remove(bi)
    return order


def main():
    quick = len(sys.argv) > 1
    n = int(sys.argv[1]) if quick else N_DRAWS
    m = EXAMPLE
    nu = len(m["units"])
    names = [s[0] for s in m["sites"]]
    nm = lambda S: "".join(names[i] for i in S)
    M = len(names)
    T = tables(m, n=n)
    one = lambda i: T["E"][frozenset([i])]
    vmax = sum(u[3] + u[4] for u in m["units"])
    print("max score", vmax)
    for i in range(M):
        print(names[i], "units", " ".join(f"{1 - p:.4f}" for p in one(i)[0]), "| bounds", " ".join(f"{1 - p:.4f}" for p in one(i)[1][:6]))
    curve, sets = [], []
    for k in range(1, M + 1):
        S, v = best_set(m, T, k)
        curve.append(v)
        sets.append(nm(S))
        print(k, nm(S), f"{v:.4f}")
    S, v = best_set(m, T, m["wells"])
    order = drill_order(m, T, S)
    prefix = [value(m, T, order[:j]) for j in range(1, len(order) + 1)]
    rest = [i for i in range(M) if i not in S]
    adds = sorted(((value(m, T, S + [i]) - v, -i) for i in rest), reverse=True)
    mu, mb = misses(m, T, S)
    print("order", nm(order), "prefix", [round(x, 4) for x in prefix])
    print("reserves", [(names[-j], round(g, 4)) for g, j in adds])
    print("reach units", [round(1 - x, 4) for x in mu], "bounds", [round(1 - x, 4) for x in mb])
    v_alone = value_alone(m, T, S)
    print("best set, wells counted one by one", round(v_alone, 4))
    # wells that share an anchor horizon: the chance that at least one of the pair reaches a target
    pairs = {}
    for a, b in itertools.combinations(range(M), 2):
        if m["sites"][a][1] == m["sites"][b][1]:
            eu, eb = T["E"][frozenset([a, b])]
            pairs[names[a] + names[b]] = {"units": [round(1 - x, 4) for x in eu], "bounds": [round(1 - x, 4) for x in eb]}
            alone_u = [round(1 - one(a)[0][k] * one(b)[0][k], 4) for k in range(nu)]
            alone_b = [round(1 - one(a)[1][k] * one(b)[1][k], 4) for k in range(nu)]
            print("pair", names[a] + names[b], pairs[names[a] + names[b]], "| one by one:", alone_u, alone_b)
    hr = dict(m, sites=[s[:5] + [True] for s in m["sites"]])
    td = dict(m, sites=[s[:5] + [False] for s in m["sites"]])
    vhr = best_set(hr, tables(hr, n=n), m["wells"])
    vtd = best_set(td, tables(td, n=n), m["wells"])
    print("all high-res", nm(vhr[0]), round(vhr[1], 4), "| all 2D", nm(vtd[0]), round(vtd[1], 4))
    # stand-in for each planned site: the site outside the plan that best keeps the score without it
    standins = []
    for i in order:
        others = [x for x in S if x != i]
        bj, bS, bv = None, None, -1.0
        for j in rest:
            X = others + [j]
            g = value(m, T, X)
            if better(m, g, X, bv, bS):
                bj, bS, bv = j, X, g
        standins.append([names[i], names[bj], round(bv, 4)])
    print("stand-ins", standins)
    # the best set again with every hole delivering, with the 2D pick error halved and half as large again,
    # and with no part of the pick error shared
    var = {}
    for key, mv in (("okp100", dict(m, okp=100)), ("e2d_half", dict(m, e2d=m["e2d"] / 2)), ("e2d_x1.5", dict(m, e2d=m["e2d"] * 1.5)),
                    ("share0", dict(m, share=0))):
        Sv, vv = best_set(mv, tables(mv, n=n), m["wells"])
        var[key] = [nm(sorted(Sv)), round(vv, 4)]
    print("variants", var)
    # after drilling: made-up results of the first two wells, then the best wells to drill next
    after = {}
    for key, demo in DEMO.items():
        facts = {names.index(k): u for k, u in demo.items()}
        drilled = sorted(facts, key=lambda i: order.index(i) if i in order else 99)
        Tf = tables(m, facts, n=n, reps=REPS_AFTER)
        cand = [i for i in range(M) if i not in facts and i not in Tf["held"]]
        need = max(0, min(m["wells"] - len(drilled), len(cand)))
        Sn, vn = best_set(m, Tf, need, cand, drilled)
        nxt = drill_order(m, Tf, Sn, drilled)
        shifts = {}
        for (h, hr), ec in Tf["shift"].items():
            for i, s in enumerate(m["sites"]):
                if s[1] == h and bool(s[5]) == hr and i not in facts:
                    shifts[names[i]] = round((m["ehr"] if s[5] else m["e2d"]) * ec, 3)
        after[key] = {"facts": {k: list(u) for k, u in demo.items()}, "drilled_score": round(value(m, Tf, drilled), 4), "next": nm(nxt), "score": round(vn, 4),
                      "held": nm(sorted(Tf["held"])), "broken": [f"H{h}" for h in Tf["broken"]], "expected_shift_m": shifts,
                      "fit": {names[i]: round(T["touch"][i][u[0] - 1], 4) for i, u in facts.items() if u[0]}}
        print("after drilling,", key, after[key])
    out = {
        "note": f"Monte Carlo, {n:,} joint draws per anchor horizon, seeds 10 + horizon number; after drilling {REPS_AFTER} times as many",
        "best_set": nm(S), "best_score": round(v, 4), "best_score_wells_one_by_one": round(v_alone, 4),
        "order": nm(order), "prefix": [round(x, 4) for x in prefix],
        "curve": [round(x, 4) for x in curve], "curve_sets": sets,
        "reserves": [[names[-j], round(g, 4)] for g, j in adds],
        "reach": [round(1 - x, 4) for x in mu], "reach_bounds": [round(1 - x, 4) for x in mb],
        "p_units": {names[i]: [round(1 - p, 4) for p in one(i)[0]] for i in range(M)},
        "p_bounds": {names[i]: [round(1 - p, 4) for p in one(i)[1]] for i in range(M)},
        "p_any": {names[i]: [round(p, 4) for p in T["touch"][i]] for i in range(M)},
        "pairs_on_one_horizon": pairs,
        "all_high_res": [nm(vhr[0]), round(vhr[1], 4)],
        "all_2d": [nm(vtd[0]), round(vtd[1], 4)],
        "standins": standins,
        "variants": var,
        "after_drilling": after,
    }
    if not quick:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ref_values.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
