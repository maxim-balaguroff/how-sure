# -*- coding: utf-8 -*-
"""Independent count behind the checks of the page "How much, and how sure?" (how-sure, tool 04).

The page calculates with 50,000 evenly spread points in JavaScript. This file works the same cases another way:
plain Monte Carlo with numpy, 4,000,000 independent draws per case, written from the definitions and
sharing no code with the page. Where an exact answer exists (every input lognormal), it is worked out
by formula as well.

Definitions (the same on the page):
  volume = c * area * net pay * porosity * (1 - Sw) / Bo        c = 6.2898 for million barrels, area in km2, pay in m
  each input is given by a low and a high value: the values it exceeds with 90 % and with 10 % chance
  lognormal input: ln(x) is normal, centred between ln(low) and ln(high)
  normal input:    x is normal, centred between low and high; values below 0 count as 0, Sw above 1 counts as 1
  two pairs of inputs may move together (porosity with Sw, area with net pay): their normal scores are correlated
  P90 is the low case: the volume exceeded with 90 % chance. P10 is the high case.

Run:  python volume_ref.py            writes ref_values.json next to this file
"""
import json
import math
from pathlib import Path

import numpy as np

Z = 1.2815515655446004            # normal score of the 90th percentile
C_BBL = 6.2898                    # million barrels per (km2 * m)
N = 4_000_000
NAMES = ["area", "pay", "por", "sw", "bo"]

EXAMPLE = {
    "area": (12.0, 40.0, "lognormal"),
    "pay": (15.0, 45.0, "lognormal"),
    "por": (0.14, 0.22, "normal"),
    "sw": (0.25, 0.45, "normal"),
    "bo": (1.20, 1.40, "normal"),
}
THRESHOLD = 230.0                 # million barrels in place: the least volume worth a well in the example
NEED = 50.0                       # chance of clearing the threshold that the decision asks for, %


def value(name, spec, z, widen=1.0):
    """The input at normal score z (array or number)."""
    lo, hi, shape = spec
    if shape == "lognormal":
        m, s = (math.log(lo) + math.log(hi)) / 2, (math.log(hi) - math.log(lo)) / (2 * Z) * widen
        return np.exp(m + s * z)
    m, s = (lo + hi) / 2, (hi - lo) / (2 * Z) * widen
    x = np.maximum(m + s * z, 0.0)
    return np.minimum(x, 1.0) if name == "sw" else x


def volume(v, c=C_BBL):
    return c * v["area"] * v["pay"] * v["por"] * (1 - v["sw"]) / v["bo"]


def scores(seed, rho_ps=0.0, rho_ah=0.0, fixed=None):
    """Normal scores of the five inputs. fixed = (name, z): that input is known, its partner follows it."""
    rng = np.random.default_rng(seed)
    z = {k: rng.standard_normal(N) for k in NAMES}
    if fixed:
        z[fixed[0]] = np.full(N, fixed[1])
    for a, b, rho in (("por", "sw", rho_ps), ("area", "pay", rho_ah)):
        if rho:
            if fixed and fixed[0] == b:          # the second of the pair is the known one: the first follows it
                z[a] = rho * z[b] + math.sqrt(1 - rho * rho) * z[a]
            else:
                z[b] = rho * z[a] + math.sqrt(1 - rho * rho) * z[b]
    return z


def draws(spec, seed, rho_ps=0.0, rho_ah=0.0, widen=1.0, fixed=None):
    z = scores(seed, rho_ps, rho_ah, fixed)
    return volume({k: value(k, spec[k], z[k], widen) for k in NAMES})


def summary(v, threshold=THRESHOLD):
    p90, p50, p10 = np.percentile(v, [10, 50, 90])
    return {"p90": float(p90), "p50": float(p50), "p10": float(p10), "mean": float(v.mean()),
            "swanson": float(0.3 * p90 + 0.4 * p50 + 0.3 * p10), "chance": float((v > threshold).mean() * 100)}


def at(spec, which):
    """Volume with every input at its low-volume end, its middle or its high-volume end."""
    v = {}
    for k in NAMES:
        lo, hi, _ = spec[k]
        down = k in ("sw", "bo")                  # a larger Sw or Bo gives a smaller volume
        v[k] = {"low": hi if down else lo, "high": lo if down else hi, "mid": float(value(k, spec[k], 0.0))}[which]
    return float(volume(v))


def tornado(spec):
    """One input at a time at its low and high value, the others at their middle."""
    mid = {k: float(value(k, spec[k], 0.0)) for k in NAMES}
    out = {}
    for k in NAMES:
        lo, hi, _ = spec[k]
        a, b = float(volume({**mid, k: lo})), float(volume({**mid, k: hi}))
        out[k] = {"at_low": a, "at_high": b}
    tot = sum(math.log(o["at_high"] / o["at_low"]) ** 2 for o in out.values())
    for o in out.values():
        o["share"] = math.log(o["at_high"] / o["at_low"]) ** 2 / tot * 100
    return out


def known(spec, seed, rho_ps=0.0, rho_ah=0.0, threshold=THRESHOLD):
    """Chance of clearing the threshold if one input were known to sit at its low or at its high value."""
    out = {}
    for j, k in enumerate(NAMES):
        out[k] = {}
        for tag, z in (("at_low", -Z), ("at_high", Z)):
            v = draws(spec, seed + 10 * j + (1 if z > 0 else 0), rho_ps, rho_ah, fixed=(k, z))
            out[k][tag] = float((v > threshold).mean() * 100)
    return out


def ncdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def breakeven(spec, seed, threshold=THRESHOLD, need=NEED):
    """For each input: the value at which the chance of clearing the threshold equals the chance required,
    and how often the input lies on the unfavourable side of that value. Independent inputs.
    Method: with the input held at x, volume = x-part * (the rest); the chance is the share of draws
    whose "rest" exceeds threshold / x-part, so the x-part needed is threshold / (the rest exceeded `need` % of the time)."""
    z = scores(seed)
    v = {k: value(k, spec[k], z[k]) for k in NAMES}
    total = volume(v)
    out = {}
    for k in NAMES:
        part = {"area": v["area"], "pay": v["pay"], "por": v["por"], "sw": 1 - v["sw"], "bo": 1 / v["bo"]}[k]
        rest_q = float(np.percentile(total / part, 100 - need))      # the rest is above this `need` % of the time
        need_part = threshold / rest_q
        x = {"area": need_part, "pay": need_part, "por": need_part, "sw": 1 - need_part, "bo": 1 / need_part}[k]
        lo, hi, shape = spec[k]
        if shape == "lognormal":
            zz = (math.log(x) - (math.log(lo) + math.log(hi)) / 2) / ((math.log(hi) - math.log(lo)) / (2 * Z))
        else:
            zz = (x - (lo + hi) / 2) / ((hi - lo) / (2 * Z))
        beyond = (1 - ncdf(zz)) if k in ("sw", "bo") else ncdf(zz)   # unfavourable side: high Sw or Bo, low anything else
        out[k] = {"value": float(x), "chance_beyond": float(beyond * 100)}
    return out


def exact_lognormal(spec, c=C_BBL, rho_ah=0.0):
    """Every input lognormal and no cap: the volume is lognormal too, so the answer is a formula."""
    m = math.log(c)
    var = 0.0
    sd = {}
    for k in NAMES:
        lo, hi, _ = spec[k]
        sign = -1 if k == "bo" else 1
        m += sign * (math.log(lo) + math.log(hi)) / 2
        sd[k] = (math.log(hi) - math.log(lo)) / (2 * Z)
        var += sd[k] ** 2
    var += 2 * rho_ah * sd["area"] * sd["pay"]
    s = math.sqrt(var)
    return {"p90": math.exp(m - Z * s), "p50": math.exp(m), "p10": math.exp(m + Z * s), "mean": math.exp(m + var / 2), "sd_ln": s}


def main():
    ref = {"n": N, "example": {k: list(v) for k, v in EXAMPLE.items()}, "threshold": THRESHOLD, "need": NEED}
    base = draws(EXAMPLE, 1)
    ref["base"] = summary(base)
    ref["all_low"], ref["all_mid"], ref["all_high"] = at(EXAMPLE, "low"), at(EXAMPLE, "mid"), at(EXAMPLE, "high")
    ref["below_all_low"] = float((base < ref["all_low"]).mean() * 100)
    ref["above_all_high"] = float((base > ref["all_high"]).mean() * 100)
    ref["tornado"] = tornado(EXAMPLE)
    ref["known"] = known(EXAMPLE, 100)
    ref["curve"] = [float(x) for x in np.percentile(base, [1, 5, 10, 25, 50, 75, 90, 95, 99])]
    ref["links"] = {
        "por_sw_-0.5": summary(draws(EXAMPLE, 2, rho_ps=-0.5)),
        "por_sw_-0.8": summary(draws(EXAMPLE, 3, rho_ps=-0.8)),
        "area_pay_0.5": summary(draws(EXAMPLE, 4, rho_ah=0.5)),
        "area_pay_0.8": summary(draws(EXAMPLE, 5, rho_ah=0.8)),
        "both_0.5": summary(draws(EXAMPLE, 6, rho_ps=-0.5, rho_ah=0.5)),
    }
    ref["known_area_pay_0.5"] = known(EXAMPLE, 300, rho_ah=0.5)
    ref["breakeven"] = breakeven(EXAMPLE, 400)
    ref["area_at_p50"] = summary(draws(EXAMPLE, 500, fixed=("area", 0.0)))
    ref["widen"] = {str(w): summary(draws(EXAMPLE, 20 + i, widen=w)) for i, w in enumerate((1.25, 1.5, 2.0))}
    # a case with an exact answer: the three fraction inputs taken as lognormal instead of normal
    LOGN = {k: (v[0], v[1], "lognormal") for k, v in EXAMPLE.items()}
    LOGN["sw"] = (0.30, 0.30, "lognormal")        # Sw fixed, so that (1 - Sw) is a plain number
    ref["lognormal_case"] = {"spec": {k: list(v) for k, v in LOGN.items()}, "exact": exact_lognormal_fixed_sw(LOGN),
                             "exact_area_pay_0.5": exact_lognormal_fixed_sw(LOGN, rho_ah=0.5),
                             "draws": summary(draws(LOGN, 7)), "draws_area_pay_0.5": summary(draws(LOGN, 8, rho_ah=0.5))}
    # million m3 instead of million barrels
    ref["metric"] = summary(draws(EXAMPLE, 1) / C_BBL, THRESHOLD / C_BBL)
    out = Path(__file__).resolve().parent / "ref_values.json"
    out.write_text(json.dumps(ref, indent=1), encoding="utf-8")
    for k in ("base", "all_low", "all_mid", "all_high", "below_all_low", "above_all_high", "tornado", "known", "links", "widen", "lognormal_case", "breakeven", "area_at_p50", "known_area_pay_0.5"):
        print(k, json.dumps(ref[k]))


def exact_lognormal_fixed_sw(spec, rho_ah=0.0):
    """exact_lognormal for a case where Sw is one fixed number: the factor (1 - Sw) is a constant."""
    sw = spec["sw"][0]
    e = exact_lognormal({**spec, "sw": (1.0, 1.0, "lognormal")}, c=C_BBL * (1 - sw), rho_ah=rho_ah)
    return e


if __name__ == "__main__":
    main()
