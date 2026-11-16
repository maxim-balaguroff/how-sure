# -*- coding: utf-8 -*-
"""Independent reference for tool 02 (magnetic survey check).

The page uses closed forms (angle / solid angle the top of the body subtends at the sensor).
This file does NOT use them: it adds up elementary dipoles over the body's cross-section or volume
with Gauss-Legendre quadrature. Agreement between the two is the first check; the hand-derived
textbook answers (half-widths, merge distances) are the second.

Conventions (same as the page): vertical inducing field F (nT), vertical induced magnetisation,
susceptibility contrast k (SI), no remanence, flat ground. h = depth to top below ground + sensor height.
Output: expected values for the page's Checks panel, printed as JSON.
"""
import json
import math

import numpy as np
from numpy.polynomial.legendre import leggauss


def gl(a, b, n):
    x, w = leggauss(n)
    return 0.5 * (b - a) * x + 0.5 * (b + a), 0.5 * (b - a) * w


def depth_nodes(h, n=200):
    # z from h to infinity via z = h / tau, tau in (0, 1]; dz = h / tau^2 dtau
    tau, wt = gl(0.0, 1.0, n)
    return h / tau, wt * h / tau**2


def segments(a, b, x, h):
    """Split [a, b] so quadrature nodes crowd near the observation point x and spread out far away."""
    pts = {a, b}
    for m in (0.0, 0.5, 1, 2, 5, 10, 30, 100, 1e3, 1e4, 1e5, 1e6, 1e7):
        for s in (-1, 1):
            p = x + s * m * h
            if a < p < b:
                pts.add(p)
    pts = sorted(pts)
    return list(zip(pts[:-1], pts[1:]))


def strip_sum(x, a, b, z, wz, h, n=120):
    total = 0.0
    for lo, hi in segments(a, b, x, h):
        x0, wx = gl(lo, hi, n)
        u = x - x0[:, None]
        zz = z[None, :]
        ker = (zz**2 - u**2) / (u**2 + zz**2) ** 2
        total += float(np.sum(ker * wx[:, None] * wz[None, :]))
    return total


def dyke_2d(x, k, F, w, h, n=200):
    """Vertical prism, width w, top at h, infinite depth. Sum of 2D vertical line dipoles."""
    z, wz = depth_nodes(h, n)
    return k * F / (2 * math.pi) * strip_sum(x, -w / 2, w / 2, z, wz, h)


def sill_edge_2d(x, k, F, t, h, xmax=1e10):
    """Horizontal sheet, thickness t, top at h, from x0 = 0 to +inf (edge at 0); tail past 1e10 m is nil."""
    z, wz = gl(h, h + t, 40)
    return k * F / (2 * math.pi) * strip_sum(x, 0.0, xmax, z, wz, h)


def plug_3d(r, k, F, R, h, nr=60, nphi=128, nz=80):
    """Vertical cylinder radius R, top at h, infinite depth. Sum of 3D vertical dipoles."""
    rr, wr = gl(0.0, R, nr)
    phi, wp = gl(0.0, 2 * math.pi, nphi)
    z, wz = depth_nodes(h, nz)
    X = rr[:, None] * np.cos(phi)[None, :]
    Y = rr[:, None] * np.sin(phi)[None, :]
    dA = (rr[:, None] * wr[:, None]) * wp[None, :]
    d2 = (r - X) ** 2 + Y**2
    total = 0.0
    for zi, wzi in zip(z, wz):
        rho2 = d2 + zi**2
        ker = (2 * zi**2 - d2) / rho2**2.5
        total += float(np.sum(ker * dA)) * wzi
    return k * F / (4 * math.pi) * total


def half_width(f, peak, lo, hi):
    target = peak / 2
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if f(mid) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


out = {}
k, F = 0.02, 55000.0

# Example: dyke 20 m wide, top 300 m below ground, sensor 60 m above ground
out["dyke_example_peak"] = dyke_2d(0.0, k, F, 20.0, 360.0)
out["dyke_example_x200"] = dyke_2d(200.0, k, F, 20.0, 360.0)
# thin dyke half-width at half maximum, h = 100 -> expect 100
thin = lambda x: dyke_2d(x, k, F, 1.0, 100.0)
out["thin_dyke_halfwidth_h100"] = half_width(thin, thin(0.0), 0.0, 400.0)
# very wide dyke -> kF/2
out["dyke_w2e4_h100_peak"] = dyke_2d(0.0, k, F, 2e4, 100.0)  # wide body; the half-space limit kF/2 is a hand answer

# Sill edge: t = 50, h = 200
for x in (223.6068, 100.0, -223.6068, 1000.0):
    out[f"sill_t50_h200_x{x:g}"] = sill_edge_2d(x, k, F, 50.0, 200.0)

# Plug: R = 50, h = 200, on axis and at r = 200; R = 100, h = 10, r = 50 (inside the disc projection)
out["plug_R50_h200_r0"] = plug_3d(0.0, k, F, 50.0, 200.0)
out["plug_R50_h200_r200"] = plug_3d(200.0, k, F, 50.0, 200.0)
out["plug_R100_h10_r50"] = plug_3d(50.0, k, F, 100.0, 10.0, nr=200, nphi=256, nz=120)
small = lambda r: plug_3d(r, k, F, 1.0, 100.0, nr=12, nphi=32, nz=60)
out["small_plug_halfwidth_h100"] = half_width(small, small(0.0), 0.0, 400.0)

# Textbook answers derived by hand (see README "Checked against known answers")
out["hand_thin_dyke_merge_ratio"] = 2 / math.sqrt(3)      # two thin dykes merge if s < 1.1547 h
out["hand_small_plug_merge_ratio"] = 1.0                   # two small plugs merge if s < h
out["hand_small_plug_halfwidth_ratio"] = math.sqrt(2 ** (2 / 3) - 1)
out["hand_lines_L_eq_h"] = (1 / 1.25) ** 1.5               # plug midway between lines spaced h
out["hand_lines_L_eq_2h"] = 0.5 ** 1.5
out["hand_sill_extreme_x"] = math.sqrt(200 * 250)
out["hand_plug_axis"] = k * F / 2 * (1 - 200 / math.hypot(200, 50))
# max sensor height for the example dyke to stay at 5 x 0.5 nT noise
C = k * F / (2 * math.pi)
h_needed = 10.0 / math.tan(2.5 / (2 * C))
out["hand_dyke_max_sensor_height"] = h_needed - 300.0

print(json.dumps(out, indent=1))
