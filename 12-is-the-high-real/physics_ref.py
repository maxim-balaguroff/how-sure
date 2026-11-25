# -*- coding: utf-8 -*-
"""Independent reference for tool 12 (Is the high real?).

The page uses closed forms for vertical rays through a fast sill:
    pull-up in two-way time      dT = 2 t (1/Vh - 1/Vs)
    pull-up in depth             dZ = t (1 - Vh/Vs)       (time converted with the host velocity)
    thickness from time          t(V) = V tau / 2
This file does NOT use them. It builds a velocity log on a fine depth grid, adds up two-way time
cell by cell, and converts time back to depth by bisection on that running sum. To test the page's
claim that the overburden cancels, the log here carries a slow overburden layer that the page does
not have.

Run:  python -I physics_ref.py           prints every check as PASS or FAIL against the page's
                                          expected values and ends with ALL N PASS
      python -I physics_ref.py --json    prints the reference values as JSON
"""
import json
import sys

import numpy as np

DZ = 0.01                       # m, grid step of the velocity log
OVER = (800.0, 2200.0)          # overburden: 0-800 m at 2200 m/s, only in this file

EX = dict(top=1500.0, t=150.0, vs=5200.0, vh=3000.0, target=2500.0, high=80.0, vlo=4500.0, vhi=6000.0, wellv=300.0)
HOSTS = {"clastic": 3000.0, "salt": 4750.0, "dolomite": 5500.0}


def overlap(z0, a, b):
    """Fraction of each cell [z0, z0 + DZ) that lies inside [a, b)."""
    return np.clip((np.minimum(z0 + DZ, b) - np.maximum(z0, a)) / DZ, 0.0, 1.0)


def log(top, t, vs, vh, zmax, over=OVER):
    """Slowness of each DZ cell from 0 to zmax, averaged where a boundary cuts a cell."""
    z0 = np.arange(0.0, zmax, DZ)
    s = np.full_like(z0, 1.0 / vh)
    if over:
        f = overlap(z0, 0.0, over[0])
        s = s * (1 - f) + f / over[1]
    if t > 0:
        f = overlap(z0, top, top + t)
        s = s * (1 - f) + f / vs
    return z0, s


def twt(z_to, top, t, vs, vh, over=OVER):
    """Two-way time from the surface to depth z_to, adding up cells (partial last cell included)."""
    z0, s = log(top, t, vs, vh, z_to + DZ, over)
    n = int(np.floor(z_to / DZ + 1e-9))
    tt = 2 * DZ * float(np.sum(s[:n]))
    rest = z_to - n * DZ
    if rest > 1e-12:
        # the last cell is cut at z_to: take its slowness over [z0, z_to] from the layers directly
        a, b = n * DZ, z_to
        sl = 1.0 / vh
        if over and a < over[0]:
            sl = 1.0 / over[1] if b <= over[0] else sl
        if t > 0 and top <= a and b <= top + t:
            sl = 1.0 / vs
        tt += 2 * rest * sl
    return tt


def depth_of(T, vh, over=OVER, zmax=20000.0):
    """Depth at which the sill-free log reaches two-way time T: bisection on the running sum."""
    lo, hi = 0.0, zmax
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if twt(mid, 0.0, 0.0, vh, vh, over) < T:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def pullup(top, t, vs, vh, target, over=OVER):
    """Pull-up at the target: in ms of two-way time and in m after converting with the sill-free log."""
    t_true = twt(target, top, t, vs, vh, over)
    t_free = twt(target, 0.0, 0.0, vh, vh, over)
    z_app = depth_of(t_true, vh, over)
    return (t_free - t_true) * 1000, target - z_app


def sill_time(top, t, vs, vh):
    """Two-way time thickness of the sill, ms, as a difference of two running sums."""
    return (twt(top + t, top, t, vs, vh) - twt(top, top, t, vs, vh)) * 1000


def thickness_from_time(tau_ms, v, top=1500.0):
    """Thickness that gives the same two-way time across the sill at velocity v: bisection, not V tau / 2."""
    lo, hi = 0.0, 5000.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if sill_time(top, mid, v, 3000.0) < tau_ms:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def reference():
    m, out = EX, {}
    dT, dZ = pullup(m["top"], m["t"], m["vs"], m["vh"], m["target"])
    out["dT_ms"], out["dZ_m"] = dT, dZ
    out["share_pct"] = 100 * dZ / m["high"]
    out["dZ_no_overburden"] = pullup(m["top"], m["t"], m["vs"], m["vh"], m["target"], over=None)[1]
    out["dZ_salt"] = pullup(m["top"], m["t"], m["vs"], HOSTS["salt"], m["target"])[1]
    out["dZ_dolomite"] = pullup(m["top"], m["t"], m["vs"], HOSTS["dolomite"], m["target"])[1]
    out["dT_salt"] = pullup(m["top"], m["t"], m["vs"], HOSTS["salt"], m["target"])[0]
    tau = sill_time(m["top"], m["t"], m["vs"], m["vh"])
    out["tau_ms"] = tau
    for key, v in (("lo", m["vlo"]), ("hi", m["vhi"])):
        tv = thickness_from_time(tau, v)
        out["t_" + key] = tv
        out["dZ_" + key] = pullup(m["top"], tv, v, m["vh"], m["target"])[1]
    # the sill is in the velocity model with the right time thickness but its velocity is off by wellv:
    # the model puts the base at top + (vs + wellv) tau / 2; convert the true time to depth through that model
    t_true = twt(m["target"], m["top"], m["t"], m["vs"], m["vh"])
    vm = m["vs"] + m["wellv"]
    tm = thickness_from_time(tau, vm)
    lo, hi = 0.0, 20000.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if twt(mid, m["top"], tm, vm, m["vh"]) < t_true:
            lo = mid
        else:
            hi = mid
    out["well_resid_m"] = m["target"] - 0.5 * (lo + hi)
    out["T0_s"] = twt(m["target"], 0.0, 0.0, m["vh"], m["vh"], over=None)
    return out


# Values the page expects (copied from its Checks panel after the last build), with the tolerance it uses.
PAGE = {
    "dT_ms": (42.3077, 1e-4), "dZ_m": (63.4615, 1e-4), "share_pct": (79.3269, 1e-4),
    "dZ_no_overburden": (63.4615, 1e-4), "dZ_salt": (12.9808, 1e-4), "dZ_dolomite": (-8.65385, 1e-4),
    "dT_salt": (5.46559, 1e-4), "tau_ms": (57.6923, 1e-4), "t_lo": (129.808, 1e-4), "t_hi": (173.077, 1e-4),
    "dZ_lo": (43.2692, 1e-4), "dZ_hi": (86.5385, 1e-4), "well_resid_m": (-8.65385, 1e-4), "T0_s": (1.66667, 1e-4),
}


def main():
    ref = reference()
    if "--json" in sys.argv:
        print(json.dumps(ref, indent=1))
        return 0
    w = max(len(k) for k in PAGE)
    fails = 0
    for key, (page, tol) in PAGE.items():
        r = ref[key]
        ok = abs(r - page) <= tol * abs(page)
        fails += not ok
        print(f"{key:<{w}}  page {page:12.6g}  ref {r:12.6g}  tol {tol:6.0e}  {'PASS' if ok else 'FAIL'}")
    n = len(PAGE)
    print(f"\n{'ALL %d PASS' % n if not fails else '%d of %d FAIL' % (fails, n)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
