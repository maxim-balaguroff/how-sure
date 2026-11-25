# -*- coding: utf-8 -*-
"""Independent reference for tool 11 (Gravity, magnetics or both?).

The page uses closed forms for a 2D horizontal slab (the sill): the gravity of a rectangle and the
angles its top and base subtend for the magnetic field. This file does NOT use them. It adds up
elementary 2D line masses and 2D vertical line dipoles over the sill's cross-section with
Gauss-Legendre quadrature, smooths moving-platform gravity with Gauss-Hermite quadrature instead of
the page's sampled Gaussian, builds its own Jacobian with other step sizes and inverts with numpy.

What it shares with the page is the model and the rules, not the code: a 2D sill with flat top and
base, vertical field and induced magnetisation, flat ground; reading positions, the starting
knowledge (priors), the ambiguity tests and the thresholds as written in the README.

Run:  python -I physics_ref.py           prints every check as PASS or FAIL against the page's
                                          expected values and ends with ALL N PASS
      python -I physics_ref.py --json    prints the reference values as JSON
"""
import json
import math
import sys

import numpy as np
from numpy.polynomial.hermite import hermgauss
from numpy.polynomial.legendre import leggauss

G = 6.674e-11
MGAL = 1e5

# ---------------------------------------------------------------- quadrature helpers
def gl(a, b, n):
    x, w = leggauss(n)
    return 0.5 * (b - a) * x + 0.5 * (b + a), 0.5 * (b - a) * w


def splits(a, b, x, z):
    """Break [a, b] so nodes crowd near the observation point x and spread out far away."""
    pts = {a, b}
    for m in (0.0, 0.25, 0.5, 1, 2, 4, 8, 16, 50, 200, 1e3, 1e4, 1e5):
        for s in (-1, 1):
            p = x + s * m * z
            if a < p < b:
                pts.add(p)
    pts = sorted(pts)
    return list(zip(pts[:-1], pts[1:]))


def slab_sum(kernel, x, z1, t, xl, xr, nx=24, nz=16):
    """Integral of kernel(u, z) over x' in [xl, xr], z in [z1, z1 + t], u = x' - x."""
    z, wz = gl(z1, z1 + t, nz)
    total = 0.0
    for lo, hi in splits(xl, xr, x, z1):
        xp, wx = gl(lo, hi, nx)
        u = xp[:, None] - x
        total += float(np.sum(kernel(u, z[None, :]) * wx[:, None] * wz[None, :]))
    return total


def grav(x, drho, z1, t, xl, xr):
    """mGal. Sum of 2D line masses: g = 2 G drho * integral of z / (u^2 + z^2)."""
    return 2 * G * drho * 1000 * slab_sum(lambda u, z: z / (u * u + z * z), x, z1, t, xl, xr) * MGAL


def mag(x, k, F, z1, t, xl, xr):
    """nT. Sum of 2D vertical line dipoles in a vertical field: k F / (2 pi) * integral of (z^2 - u^2) / (u^2 + z^2)^2."""
    ker = lambda u, z: (z * z - u * u) / (u * u + z * z) ** 2
    return k * F / (2 * math.pi) * slab_sum(ker, x, z1, t, xl, xr)


HX, HW = hermgauss(40)


def smooth(f, x, L):
    """Gaussian low-pass, sigma = 0.375 L (half amplitude at wavelength 2 L), by Gauss-Hermite quadrature."""
    if L <= 0:
        return f(x)
    s = 0.375 * L
    return float(sum(w * f(x - math.sqrt(2) * s * y) for y, w in zip(HX, HW)) / math.sqrt(math.pi))


# ---------------------------------------------------------------- the example and the rules
EX = dict(depth=1500.0, t=150.0, W=6000.0, drho=0.25, k=0.02, F=58000.0, seis=40.0, wrho=10.0, wk=20.0)
PL = {"ground": dict(h=2.0, gn=0.03, gL=0.0, gs=250.0, mn=1.0),
      "uav": dict(h=30.0, gn=2.0, gL=1000.0, gs=100.0, mn=0.5),
      "fw": dict(h=80.0, gn=0.5, gL=2500.0, gs=100.0, mn=0.5)}
MAG_STEP = 100.0
PRIOR = dict(depth_rel=0.25, lnt=0.5, lnrho=0.5, lnk=0.5, edge=1000.0)
ALT_T, ALT_DZ, DENSE = 1.5, 0.2, 50.0


def half_len(m):
    return m["W"] / 2 + 5 * m["depth"]


def positions(half, step):
    n = int(math.floor(2 * half / step + 1e-9))
    return [-half + i * step for i in range(n + 1)]


def g_at(x, q, p):
    z1 = max(0.1, q["z"] + p["h"])
    return smooth(lambda u: grav(u, q["drho"], z1, q["t"], q["xl"], q["xr"]), x, p["gL"])


def m_at(x, q, p):
    return mag(x, q["k"], q["F"], max(0.1, q["z"] + p["h"]), q["t"], q["xl"], q["xr"])


def q_of(m, **kw):
    q = dict(z=m["depth"], t=m["t"], drho=m["drho"], k=m["k"], xl=-m["W"] / 2, xr=m["W"] / 2, F=m["F"])
    q.update(kw)
    return q


def mag_peak(q, p, half):
    """Largest |anomaly|: scan, then golden-section search around the best point."""
    z1 = q["z"] + p["h"]
    st = max(1.0, z1 / 40)
    xs = np.arange(0.0, half + 1e-9, st)
    vals = [abs(m_at(x, q, p)) for x in xs]
    i = int(np.argmax(vals))
    a, b = max(0.0, xs[i] - st), xs[i] + st
    f = lambda x: abs(m_at(x, q, p))
    gr = (math.sqrt(5) - 1) / 2
    c, d = b - gr * (b - a), a + gr * (b - a)
    for _ in range(60):
        if f(c) > f(d):
            b = d
        else:
            a = c
        c, d = b - gr * (b - a), a + gr * (b - a)
    return max(vals[i], f(0.5 * (a + b)))


def dense_xs(m):
    h = half_len(m)
    return positions(h, DENSE)


def max_diff(f0, f1, xs):
    return max(abs(f0(x) - f1(x)) for x in xs)


def refit(f0, f1, xs):
    a0 = np.array([f0(x) for x in xs])
    a1 = np.array([f1(x) for x in xs])
    a = float(a0 @ a1 / (a1 @ a1))
    return a, float(np.max(np.abs(a0 - a * a1)))


def data_vec(th, m, gp, mp, use_g, use_m):
    q = dict(z=th[0], t=math.exp(th[1]), drho=math.exp(th[2]), k=math.exp(th[3]), xl=th[4], xr=th[5], F=m["F"])
    half = half_len(m)
    out = []
    if use_g:
        p = PL[gp]
        out += [g_at(x, q, p) / p["gn"] for x in positions(half, max(p["gs"], p["gL"]))]
    if use_m:
        p = PL[mp]
        out += [m_at(x, q, p) / p["mn"] for x in positions(half, MAG_STEP)]
    return np.array(out)


def analyse(m, gp, mp, use_g, use_m, seis, well):
    th0 = np.array([m["depth"], math.log(m["t"]), math.log(m["drho"]), math.log(m["k"]), -m["W"] / 2, m["W"] / 2])
    steps = np.array([0.5, 5e-4, 5e-4, 5e-4, 0.5, 0.5])          # other steps than the page
    cols = []
    for i in range(6):
        a, b = th0.copy(), th0.copy()
        a[i] += steps[i]
        b[i] -= steps[i]
        cols.append((data_vec(a, m, gp, mp, use_g, use_m) - data_vec(b, m, gp, mp, use_g, use_m)) / (2 * steps[i]))
    J = np.array(cols).T
    prior = np.array([m["seis"] if seis else PRIOR["depth_rel"] * m["depth"], PRIOR["lnt"],
                      m["wrho"] / 100 if well else PRIOR["lnrho"], m["wk"] / 100 if well else PRIOR["lnk"],
                      PRIOR["edge"], PRIOR["edge"]])
    C = np.linalg.inv(J.T @ J + np.diag(1 / prior ** 2))
    return dict(z=math.sqrt(C[0, 0]), t=100 * math.sqrt(C[1, 1]),
                mass=100 * math.sqrt(C[1, 1] + C[2, 2] + 2 * C[1, 2]), edge=math.sqrt(C[4, 4]))


# ---------------------------------------------------------------- reference values
def reference():
    out = {}
    m = EX
    q = q_of(m)
    pg, pm, pf = PL["ground"], PL["uav"], PL["fw"]
    half = half_len(m)
    # forward values on the example
    out["g_ground_x0"] = g_at(0.0, q, pg)
    out["g_ground_x3000"] = g_at(3000.0, q, pg)
    out["g_ground_x6000"] = g_at(6000.0, q, pg)
    out["g_fw_x0"] = g_at(0.0, q, pf)
    out["g_uav_x2500"] = g_at(2500.0, q, pm)
    out["m_uav_x2000"] = m_at(2000.0, q, pm)
    out["m_uav_x4000"] = m_at(4000.0, q, pm)
    out["m_uav_peak"] = mag_peak(q, pm, half)
    out["m_ground_peak"] = mag_peak(q, pg, half)
    # one field alone: what it cannot tell apart (gravity on the ground, magnetics from the UAV)
    xs = dense_xs(m)
    qa = q_of(m, t=m["t"] * ALT_T, drho=m["drho"] / ALT_T)
    out["alt_g_same_mass"] = max_diff(lambda x: g_at(x, q, pg), lambda x: g_at(x, qa, pg), xs)
    qb = q_of(m, t=m["t"] * ALT_T, k=m["k"] / ALT_T)
    out["alt_m_same_kt"] = max_diff(lambda x: m_at(x, q, pm), lambda x: m_at(x, qb, pm), xs)
    qd = q_of(m, z=m["depth"] * (1 + ALT_DZ))
    out["alt_g_deeper_scale"], out["alt_g_deeper_resid"] = refit(lambda x: g_at(x, q, pg), lambda x: g_at(x, qd, pg), xs)
    out["alt_m_deeper_scale"], out["alt_m_deeper_resid"] = refit(lambda x: m_at(x, q, pm), lambda x: m_at(x, qd, pm), xs)
    # which pair pins the thickness
    r = analyse(m, "ground", "uav", True, False, False, False)
    out["res_g_mass"], out["res_g_t"], out["res_g_z"] = r["mass"], r["t"], r["z"]
    out["res_gsw_t"] = analyse(m, "ground", "uav", True, False, True, True)["t"]
    r = analyse(m, "ground", "uav", False, True, False, False)
    out["res_m_z"], out["res_m_edge"], out["res_m_t"] = r["z"], r["edge"], r["t"]
    out["res_mw_t"] = analyse(m, "ground", "uav", False, True, False, True)["t"]
    out["res_all_t"] = analyse(m, "ground", "uav", True, True, True, True)["t"]
    out["res_uavg_mass"] = analyse(m, "uav", "uav", True, False, False, False)["mass"]
    # hand answers
    out["hand_bouguer_per_m_gcc"] = 2 * math.pi * G * 1000 * MGAL               # 0.041935 mGal per m per g/cm3
    out["hand_slab_100m_025"] = 2 * math.pi * G * 250 * 100 * MGAL
    out["hand_thin_mass_split"] = 100 / math.sqrt(1 / 0.5 ** 2 + 1 / 0.5 ** 2)  # 35.36 %
    out["hand_well_rho_t"] = 100 / math.sqrt(1 / 0.5 ** 2 + 1 / 0.1 ** 2)        # 9.81 %
    out["hand_well_k_t"] = 100 / math.sqrt(1 / 0.5 ** 2 + 1 / 0.2 ** 2)          # 18.57 %
    # independent check of the hand answers themselves, by quadrature
    out["num_wide_slab_centre"] = grav(0.0, 0.25, 1000.0, 100.0, -5e6, 5e6)
    out["num_semi_edge_ratio"] = grav(0.0, 0.25, 1000.0, 100.0, 0.0, 1e7) / grav(0.0, 0.25, 1000.0, 100.0, -1e7, 1e7)
    out["num_thin_mag_at_h"] = mag(1000.0, 0.02, 58000.0, 1000.0, 1.0, 0.0, 1e7)
    return out


# Values the page expects (copied from its Checks panel after the last build), with the tolerance it uses.
PAGE = {
    "g_ground_x0": (1.08809, 1e-3), "g_ground_x3000": (0.657617, 1e-3), "g_ground_x6000": (0.155393, 1e-3),
    "g_fw_x0": (1.03279, 1e-3), "g_uav_x2500": (0.788479, 1e-3),
    "m_uav_x2000": (12.7727, 1e-3), "m_uav_x4000": (-3.99327, 1e-3), "m_uav_peak": (14.4002, 1e-3),
    "m_ground_peak": (14.5357, 1e-3),
    "alt_g_same_mass": (0.00969097, 5e-3), "alt_m_same_kt": (0.268605, 5e-3),
    "alt_g_deeper_resid": (0.0420609, 5e-3), "alt_m_deeper_resid": (1.42695, 5e-3),
    "res_g_mass": (2.33654, 1e-2), "res_gsw_t": (10.0533, 1e-2), "res_m_z": (30.9068, 1e-2),
    "res_m_edge": (13.5729, 1e-2), "res_mw_t": (18.5903, 1e-2), "res_all_t": (8.76480, 1e-2),
    "res_uavg_mass": (53.6902, 1e-2),
}


def main():
    ref = reference()
    if "--json" in sys.argv:
        print(json.dumps(ref, indent=1))
        return 0
    rows = []
    for key, (page, tol) in PAGE.items():
        r = ref[key]
        ok = abs(r - page) <= tol * abs(page)
        rows.append((key, page, r, tol, ok))
    # hand answers against quadrature: the page uses the same hand answers in its own checks
    hand = [("Bouguer slab: wide sill centre = 2 pi G drho t", ref["hand_slab_100m_025"] * (1 - 1000 / 5e6 * 2 / math.pi),
             ref["num_wide_slab_centre"], 1e-4),
            ("Semi-infinite sill: over the edge = half the slab", 0.5, ref["num_semi_edge_ratio"], 1e-4),
            ("Thin magnetic sheet at x = h: k F t / (4 pi h)", 0.02 * 58000 / (4 * math.pi * 1000), ref["num_thin_mag_at_h"], 1e-3)]
    for name, e, r, tol in hand:
        rows.append((name, e, r, tol, abs(r - e) <= tol * abs(e)))
    w = max(len(r[0]) for r in rows)
    for key, page, r, tol, ok in rows:
        print(f"{key:<{w}}  page {page:12.6g}  ref {r:12.6g}  tol {tol:6.0e}  {'PASS' if ok else 'FAIL'}")
    fails = sum(not r[4] for r in rows)
    print(f"\n{'ALL %d PASS' % len(rows) if not fails else '%d of %d FAIL' % (fails, len(rows))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
