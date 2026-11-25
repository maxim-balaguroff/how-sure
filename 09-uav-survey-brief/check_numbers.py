# -*- coding: utf-8 -*-
"""Check of every computed number in the filled example of the UAV survey brief (position 09).

Source of truth: tool 02 page `magnetic-survey-check.html` on its made-up example, as rendered
in a browser on 21.11.2026 (values copied below as PAGE). This script recomputes them with the
closed form the page documents (anomaly of a vertical dyke in a vertical field is proportional to
the angle its top subtends at the sensor) and the independent dipole sum in tool 02
`_sborka/physics_ref.py` (ref value at h = 360 m). Then it derives the few numbers the brief adds
(thresholds, line-km) and prints them. Exit code 1 if any check fails.
"""
import math
import sys

k, F = 0.02, 55000.0          # susceptibility contrast, SI; Earth's field, nT (page example)
w, depth = 20.0, 300.0        # dyke width, m; depth to top below ground, m
noise = 0.5                   # final-data noise, nT RMS
sep = 300.0                   # second dyke, m
C = k * F / (2 * math.pi)

def peak(sensor_height):
    h = depth + sensor_height
    return 2 * C * math.atan((w / 2) / h)

# Values shown by the page (table "The same body at other heights" and the result panel)
PAGE = {
    2: (302, 11.6, 23),
    30: (330, 10.6, 21),
    40: (340, 10.3, 21),
    80: (380, 9.21, 18),
    150: (450, 7.78, 16),
}
PAGE_MAX_HEIGHT = 1100       # "highest sensor height for a clear signal, m"
PAGE_SPLIT_AT_80 = 440       # "they split beyond about 1.15 x h, here 440 m"
PAGE_GROWTH_150_TO_2 = 1.49

fails = []
def check(name, got, want, tol):
    ok = abs(got - want) <= tol
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {got:.4g} vs {want} (+/-{tol})")
    if not ok:
        fails.append(name)

for hs, (h, pk, ratio) in PAGE.items():
    check(f"h at sensor {hs} m", depth + hs, h, 0)
    check(f"peak at sensor {hs} m, nT", peak(hs), pk, 0.05 if pk < 10 else 0.05)
    check(f"peak/noise at sensor {hs} m", round(peak(hs) / noise), ratio, 0)

# independent dipole sum from tool 02 (physics_ref.py, h = 360 m): 9.72363499063359 nT
check("closed form vs dipole sum at h = 360 m", peak(60), 9.72363499063359, 1e-3)

# highest sensor height for 5 x noise
h_needed = (w / 2) / math.tan(5 * noise / (2 * C))
check("highest sensor height for a clear signal, m", h_needed - depth, PAGE_MAX_HEIGHT, 5)
check("split distance at 80 m, m", 2 / math.sqrt(3) * 380, PAGE_SPLIT_AT_80, 5)
check("growth from 150 m to 2 m", peak(2) / peak(150), PAGE_GROWTH_150_TO_2, 0.005)

print("\nDerived for the brief (sensor 30 m above ground):")
p30 = peak(30)
split30 = 2 / math.sqrt(3) * 330
print(f"  peak {p30:.3f} nT; peak/noise {p30 / noise:.1f}")
print(f"  two thin dykes split beyond {split30:.0f} m; separation {sep:.0f} m -> {'two' if sep > split30 else 'one'} anomaly")
print(f"  ... on the ground (h = 302 m) split beyond {2 / math.sqrt(3) * 302:.0f} m -> still one")
# half-width at half peak for the 20 m dyke at h = 330
def prof(x, h=330.0):
    return C * (math.atan((x + w / 2) / h) - math.atan((x - w / 2) / h))
pk = prof(0.0)
lo, hi = 0.0, 2000.0
for _ in range(80):
    mid = (lo + hi) / 2
    if prof(mid) > pk / 2:
        lo = mid
    else:
        hi = mid
print(f"  half-width at half peak {lo:.1f} m; full width at half peak {2 * lo:.0f} m (rule: about h = 330 m)")
check("half-width at half peak at h = 330 m, m", lo, 330, 1)
print(f"  noise for 5 x (clear): {p30 / 5:.2f} nT; for 2 x (lost below): {p30 / 2:.2f} nT")
print(f"  2 h at 30 m (map breaks into beads beyond): {2 * 330} m; planned spacing 200 m")
print(f"  repeat-line difference allowed, sqrt(2) x {noise}: {math.sqrt(2) * noise:.2f} nT RMS")
# dyke ending 1 km below its top: factor (1 - h/b), b = base below the sensor
b = 330 + 1000
print(f"  dyke ending 1 km below its top: x{1 - 330 / b:.3f} -> {p30 * (1 - 330 / b):.1f} nT, {p30 * (1 - 330 / b) / noise:.0f} x noise")
check("dyke ending 1 km deep stays clear (>= 5 x noise)", p30 * (1 - 330 / b) / noise >= 5, True, 0)

# after the two readings (21.11): the pair of dykes, the low case, other heights, inclination
def pair(x, h=330.0):
    return prof(x - sep / 2, h) + prof(x + sep / 2, h)
xs = [i * 1.0 for i in range(-1000, 1001)]
vals = [pair(x) for x in xs]
pmax = max(vals)
print(f"\n  pair of dykes 300 m apart at 30 m: peak {pmax:.1f} nT at x = {xs[vals.index(pmax)]:.0f} m (midpoint); dip in the middle: {'no' if abs(xs[vals.index(pmax)]) < 1 else 'yes'}")
check("pair peak at the midpoint, nT", pmax, 17.6, 0.05)
# half-width of the pair anomaly
lo, hi = 0.0, 3000.0
for _ in range(80):
    mid = (lo + hi) / 2
    if pair(mid) > pmax / 2:
        lo = mid
    else:
        hi = mid
print(f"  pair: full width at half peak {2 * lo:.0f} m")
k_low = 0.002   # altered dolerite, ten times weaker (page note)
p_low = 2 * k_low * F / (2 * math.pi) * math.atan((w / 2) / 330)
print(f"  low case k = {k_low} SI: one dyke {p_low:.2f} nT = {p_low / noise:.1f} x noise")
check("low case is under 5 x noise", p_low / noise < 5, True, 0)
print(f"  sensor 50 m: peak {peak(50):.2f} nT, {peak(50) / noise:.0f} x noise")
I = math.radians(80)
print(f"  inclination 80 deg, north-striking dyke: factor sin2 I = {math.sin(I) ** 2:.3f}")
# one dyke edge 160 m from the centre line of the pair (half separation + half width)
print(f"  centre line to the outer edge of a dyke: {sep / 2 + w / 2:.0f} m; 500 m to a dyke + 50 m accuracy = {500 + sep / 2 + w / 2 + 50:.0f} m to the centre line")
check("distance rule on the centre line, m", 500 + sep / 2 + w / 2 + 50, 710, 0)
print(f"  anomaly crossing time at 7.5 m/s: {2 * 330 / 7.5:.0f} s; sample distance at 10 Hz and 8 m/s: {8 / 10:.1f} m")
check("crossing time about 90 s", 2 * 330 / 7.5, 90, 3)
# first vertical derivative of two thin dykes (shape (h^2 - x^2)/(x^2 + h^2)^2): dip at the midpoint
def vd(x, h=330.0):
    return (h * h - x * x) / (x * x + h * h) ** 2
vd_pair = [vd(x - sep / 2) + vd(x + sep / 2) for x in xs]
dip = 1 - vd_pair[xs.index(0.0)] / max(vd_pair)
print(f"  first vertical derivative of the pair: dip at the midpoint {dip * 100:.1f} % of the peak")
check("derivative dip is small (under 3 %)", dip < 0.03, True, 0)

# survey quantities (made-up block added for the brief)
L_ew, L_ns, spacing, tie = 6000.0, 4000.0, 200.0, 1000.0
n_trav = int(L_ns / spacing) + 1
n_tie = int(L_ew / tie) + 1
km_trav = n_trav * L_ew / 1000
km_tie = n_tie * L_ns / 1000
print(f"\nBlock {L_ew/1000:.0f} x {L_ns/1000:.0f} km = {L_ew*L_ns/1e6:.0f} km2")
print(f"  traverse lines E-W at {spacing:.0f} m: {n_trav} x {L_ew/1000:.0f} km = {km_trav:.0f} line-km")
print(f"  tie lines N-S at {tie:.0f} m: {n_tie} x {L_ns/1000:.0f} km = {km_tie:.0f} line-km")
print(f"  total {km_trav + km_tie:.0f} line-km, without repeat lines")
check("traverse line-km", km_trav, 126, 0)
check("tie line-km", km_tie, 28, 0)
check("total line-km", km_trav + km_tie, 154, 0)
# v4 (v1.6): grid cell one fifth of the line spacing as flown (GA Record 2023/04, Attachment 1C)
for s, want in ((200, 40), (400, 80)):
    print(f"  grid cell at {s} m spacing: {s / 5:.0f} m")
    check(f"grid cell 1/5 of {s} m spacing, m", s / 5, want, 0)
# fourth difference at 10 samples per second: under 1 m between samples at 7-8 m/s
check("sample distance at 10 Hz and 8 m/s under 1 m", 8 / 10 < 1, True, 0)
# 25.11: fourth difference divided by 16 (the sum of its coefficients): a saw-tooth of 0.1 nT reads 0.1 nT,
# and the dyke itself stays far under the limit at 0.8 m between samples
def d4(v):
    return [(v[i] - 4 * v[i + 1] + 6 * v[i + 2] - 4 * v[i + 3] + v[i + 4]) / 16 for i in range(len(v) - 4)]
check("fourth difference / 16 of a 0.1 nT saw-tooth, nT", max(abs(x) for x in d4([0.1 * (-1) ** i for i in range(40)])), 0.1, 1e-9)
dyke_line = [prof(-1000 + 0.8 * i) for i in range(2501)]
print(f"  fourth difference / 16 of the dyke anomaly: {max(abs(x) for x in d4(dyke_line)):.1e} nT")
check("the dyke stays under 0.001 nT on it", max(abs(x) for x in d4(dyke_line)) < 0.001, True, 0)
# noise above 2.1 nT: one dyke is under 5n; at the 2.1 nT limit it still stands above 2n, so row (3) holds
check("noise limit 10.6 / 5, nT", round(p30 / 5, 1), 2.1, 0)
check("at n = 2.1 nT the dyke is above 2n", p30 > 2 * 2.1, True, 0)
# section 5: the widths of row (1) and the limits at the accepted height
def width(f):
    top, lo, hi = f(0.0), 0.0, 4000.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) > top / 2 else (lo, mid)
    return 2 * lo
def short_dyke(x):                                   # the dyke ending 1 km below its top, h = 330 m
    return prof(x) - prof(x, 1330.0)
check("width of the dyke ending 1 km below its top, m", width(short_dyke), 520, 3)
check("width of the pair, sensor at 60 m, m", width(lambda x: pair(x, 360.0)), 900, 5)
check("both widths inside 500 to 950 m", 500 < width(short_dyke) and width(lambda x: pair(x, 360.0)) < 950, True, 0)
check("noise limit at 50 m, nT", round(peak(50) / 5, 1), 2.0, 0)
p8 = 2 * C * math.atan(4.0 / 330)
print(f"  a dyke 8 m wide: {p8:.1f} nT, 2n at n = 2.1 nT is 4.2 nT -> row (3) speaks of 20 m or wider")
# short base-station window (GSC Open File 7660: 0.5 nT over 15 s) is well inside the crossing time
print(f"  15 s at 7.5 m/s: {15 * 7.5:.0f} m of line; crossing time {2 * 330 / 7.5:.0f} s")
check("15 s window is under a fifth of the crossing time", 15 < (2 * 330 / 7.5) / 5, True, 0)

# v3 (operator's final reading): rate with off-track access vs edge tracks only.
# 10-day window: mobilisation, test day, demobilisation leave 7 survey days; a 4 km repeat line each day.
survey_days = 10 - 3
print(f"\nRate check: {survey_days} survey days, 4 km repeat line each day")
reserve = {}
for rate in (45, 30):
    d = (km_trav + km_tie) / (rate - 4)
    option = 60 / (rate - 4)
    reserve[rate] = survey_days - d
    print(f"  {rate} line-km/day: lines and ties in {d:.1f} days, weather reserve {survey_days - d:.1f} days;"
          f" the 60 line-km option needs {option:.1f} more days -> {'fits' if option <= survey_days - d else 'does not fit'}")
check("reserve at 45 line-km/day about 3 days", reserve[45], 3.2, 0.3)
check("reserve at 30 line-km/day about 1 day", reserve[30], 1.1, 0.3)
check("option does not fit at 30 line-km/day", float(60 / 26 > reserve[30]), 1.0, 0)

n = len(fails)
print("\nALL PASS" if n == 0 else f"\n{n} FAIL: {fails}")
sys.exit(1 if n else 0)

