# -*- coding: utf-8 -*-
"""Independent calculation behind the checks of the page "When did the fault move?" (how-sure, tool 05).

The page works out every chance by formula (the distribution of a sum of independent uniform errors).
This file works the same cases another way: plain Monte Carlo with numpy, 4,000,000 draws per case,
written from the definitions and sharing no code with the page.

Definitions (the same on the page):
  A normal fault on one section. Each horizon is picked on the footwall (the upthrown side) and on the
  hanging wall (the downthrown side), as a depth in metres, youngest horizon first.
  throw at a horizon        = hanging-wall depth - footwall depth
  thickness of an interval  = depth of its base - depth of its top, on each side
  growth of an interval     = hanging-wall thickness - footwall thickness
                            = throw at its base - throw at its top
  expansion index           = hanging-wall thickness / footwall thickness
  Every pick carries its own error: the true depth lies anywhere within +/- e of the pick, with equal
  chance, independently of the other picks. An error shared by both sides of the fault (depth conversion)
  cancels in the throw and is not part of e.
  chance that the fault moved during an interval = chance that the true growth is above zero (four picks)
  chance that a horizon is offset                = chance that the true throw is above zero (two picks)
  leak window = how far the top of the seal in the hanging wall lies below the top of the reservoir in the
                footwall (two picks); above zero means the top of the footwall reservoir faces beds above the seal.

Run:  python fault_ref.py            writes ref_values.json next to this file
"""
import json
from pathlib import Path

import numpy as np

N = 4_000_000

# name, footwall depth, hanging-wall depth, pick error; then the interval below it: name, role
EXAMPLE = [
    ("H1", 900.0, 905.0, 9.0, "upper mudstone", ""),
    ("H2", 1150.0, 1162.0, 9.0, "upper sandstone", ""),
    ("H3", 1400.0, 1460.0, 12.0, "siltstone", ""),
    ("H4", 1620.0, 1725.0, 15.0, "shale", "seal"),
    ("H5", 1700.0, 1810.0, 18.0, "sandstone", "reservoir"),
    ("H6", 1950.0, 2100.0, 22.0, "", ""),
]


def draws(horizons, seed, scale=1.0):
    """True depths on both sides: (footwall, hanging wall), each an array of shape (N, number of horizons)."""
    rng = np.random.default_rng(seed)
    zf = np.array([h[1] for h in horizons])
    zh = np.array([h[2] for h in horizons])
    e = np.array([h[3] for h in horizons]) * scale
    return zf + rng.uniform(-1, 1, (N, len(horizons))) * e, zh + rng.uniform(-1, 1, (N, len(horizons))) * e


def case(horizons, seed, scale=1.0):
    f, h = draws(horizons, seed, scale)
    throw = h - f
    growth = throw[:, 1:] - throw[:, :-1]
    out = {"throw": [float(horizons[i][2] - horizons[i][1]) for i in range(len(horizons))],
           "throw_chance": [float((throw[:, i] > 0).mean() * 100) for i in range(len(horizons))],
           "growth": [float((horizons[i + 1][2] - horizons[i + 1][1]) - (horizons[i][2] - horizons[i][1])) for i in range(len(horizons) - 1)],
           "growth_chance": [float((growth[:, i] > 0).mean() * 100) for i in range(len(horizons) - 1)],
           "growth_p90": [float(np.percentile(growth[:, i], 10)) for i in range(len(horizons) - 1)],
           "growth_p10": [float(np.percentile(growth[:, i], 90)) for i in range(len(horizons) - 1)],
           "ei": [float((horizons[i + 1][2] - horizons[i][2]) / (horizons[i + 1][1] - horizons[i][1])) for i in range(len(horizons) - 1)]}
    roles = [x[5] for x in horizons]
    if "seal" in roles and "reservoir" in roles:
        s, r = roles.index("seal"), roles.index("reservoir")
        window = h[:, s] - f[:, r]                       # top of the seal in the hanging wall below the top of the footwall reservoir
        out["leak_window"] = float(horizons[s][2] - horizons[r][1])
        out["leak_chance"] = float((window > 0).mean() * 100)
        out["throw_at_seal_top_chance"] = float((throw[:, s] > 0).mean() * 100)
    return out


def main():
    ref = {"n": N, "example": [list(x) for x in EXAMPLE]}
    ref["base"] = case(EXAMPLE, 1)
    ref["half_error"] = case(EXAMPLE, 2, scale=0.5)
    ref["double_error"] = case(EXAMPLE, 3, scale=2.0)
    # how large the growth must be, in units of the pick error, to be 80, 90 and 95 % sure it is real (four equal picks)
    rng = np.random.default_rng(4)
    s = rng.uniform(-1, 1, (N, 4)).sum(axis=1)
    ref["rule_four_picks"] = {str(p): float(np.percentile(s, p)) for p in (80, 90, 95)}
    s2 = rng.uniform(-1, 1, (N, 2)).sum(axis=1)
    ref["rule_two_picks"] = {str(p): float(np.percentile(s2, p)) for p in (80, 90, 95)}
    out = Path(__file__).resolve().parent / "ref_values.json"
    out.write_text(json.dumps(ref, indent=1), encoding="utf-8")
    for k in ("base", "half_error", "double_error", "rule_four_picks", "rule_two_picks"):
        print(k, json.dumps(ref[k]))


if __name__ == "__main__":
    main()
