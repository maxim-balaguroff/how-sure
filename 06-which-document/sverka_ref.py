# -*- coding: utf-8 -*-
"""Independent check of tool 06 "Which document is right?".

Reads example.json (the documents the page shows) and answer_key.json (what was planted, from make_example.py),
finds the discrepancies with its own code (written apart from the page's JavaScript, sharing none of it),
and compares: every planted discrepancy found, of the right type, in the right document, and nothing else.
Also runs the clean copy (no planted errors: must give nothing) and writes ref_values.json for the page's checks.
TVD here is integrated numerically along the arc (numpy, 1 cm steps), not by the minimum-curvature formula.
Usage: python -I sverka_ref.py
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
FT = 0.3048
EXPLAINED = {"crs", "swap", "zone", "datum", "feet", "magnetic", "flip", "elev"}
LOW_INC = 3.0      # degrees: below this an azimuth is not compared


# ---------------------------------------------------------------- helpers
def one_digit(a, b, min_gap=0.0):
    """True if a and b, written with one decimal, differ in one digit, by two neighbouring digits swapped,
    or by one digit missing; and differ by at least min_gap (10 for lengths: smaller is a re-measurement as often)."""
    if (a < 0) != (b < 0) or abs(a - b) < min_gap - 1e-9:
        return False
    sa, sb = f"{abs(a):.1f}", f"{abs(b):.1f}"
    if sa == sb:
        return False
    if abs(len(sa) - len(sb)) == 1:
        lo, sh = (sa, sb) if len(sa) > len(sb) else (sb, sa)
        return any(lo[:i] + lo[i + 1:] == sh for i in range(len(lo)))
    if len(sa) != len(sb):
        return False
    diff = [k for k in range(len(sa)) if sa[k] != sb[k]]
    if len(diff) == 1:
        return True
    return len(diff) == 2 and diff[1] == diff[0] + 1 and sa[diff[0]] == sb[diff[1]] and sa[diff[1]] == sb[diff[0]]


def angle_gap(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def unit(inc, az):
    i, a = math.radians(inc), math.radians(az)
    return np.array([math.sin(i) * math.cos(a), math.sin(i) * math.sin(a), math.cos(i)])


def tvd_numeric(survey, md, step=0.01):
    """TVD at md: integrate the vertical part of the hole direction, which turns along a great circle between stations."""
    st = [(0.0, 0.0, 0.0)] + [tuple(map(float, s)) for s in survey]
    total = 0.0
    for (m1, i1, a1), (m2, i2, a2) in zip(st, st[1:]):
        if md <= m1:
            return total
        if m2 <= m1:                                      # two stations at one depth: no length between them
            continue
        end = min(md, m2)
        t1, t2 = unit(i1, a1), unit(i2, a2)
        om = math.acos(float(np.clip(t1 @ t2, -1, 1)))
        n = max(1, int(round((end - m1) / step)))
        s = m1 + (np.arange(n) + 0.5) * (end - m1) / n           # midpoints
        f = (s - m1) / (m2 - m1)
        if om < 1e-12:
            v = np.full(n, t1[2])
        else:
            v = (np.sin((1 - f) * om) * t1[2] + np.sin(f * om) * t2[2]) / math.sin(om)
            # renormalise: slerp of unit vectors is already unit; kept for safety
        total += float(v.sum() * (end - m1) / n)
        if md <= m2:
            return total
    return total + (md - st[-1][0]) * math.cos(math.radians(st[-1][1]))


class Setup:
    def __init__(self, s):
        self.__dict__.update(s)

    def convert(self, x, y, frm, to):
        """Plane four-parameter transformation between crs_a and crs_b, either way."""
        if frm == to:
            return x, y
        t, s = math.radians(self.rot), self.scale
        if frm == self.crs_a and to == self.crs_b:
            return self.dx + s * (x * math.cos(t) - y * math.sin(t)), self.dy + s * (x * math.sin(t) + y * math.cos(t))
        if frm == self.crs_b and to == self.crs_a:
            u, w = x - self.dx, y - self.dy
            return (u * math.cos(t) + w * math.sin(t)) / s, (-u * math.sin(t) + w * math.cos(t)) / s
        return None


def rank_of(d, k):
    """Order of priority, 1 first: given, or from the name (drilling report, then well file, then summary table)."""
    if d.get("rank") is not None:
        return d["rank"]
    s = str(d.get("kind") or "").lower()
    for word, r in (("drill", 1), ("бурени", 1), ("well file", 2), ("дело", 2), ("summary", 3), ("table", 3), ("свод", 3)):
        if word in s:
            return r
    return k + 1


def majority(entries, same, rank=None):
    """entries: list of (doc, value). Returns (reference, docs that disagree with it, no_majority).
    Two that agree give the reference; with none agreeing, the document first in the order of priority."""
    for a in range(len(entries)):
        for b in range(a + 1, len(entries)):
            if same(entries[a][1], entries[b][1]):
                ref = entries[a]
                return ref, [e for e in entries if not same(e[1], ref[1])], False
    if len(entries) >= 2:
        ref = min(entries, key=lambda e: (rank(e[0]) if rank else 0, entries.index(e)))
        return ref, [e for e in entries if e is not ref], True
    return None, [], False


def survey_at(survey, md):
    """Inclination and azimuth at md, interpolated in a straight line between the document's own stations;
    None above the first and below the last. A different method from the page's (which follows the arc)."""
    st = [tuple(map(float, s)) for s in survey]
    if md < st[0][0] - 1e-9 or md > st[-1][0] + 1e-9:     # above the first station the path is not known
        return None
    if len(st) == 1:
        return list(st[0])
    for (m1, i1, a1), (m2, i2, a2) in zip(st, st[1:]):
        if md <= m2 + 1e-9:
            f = (md - m1) / (m2 - m1) if m2 > m1 else 1.0
            da = (a2 - a1 + 180.0) % 360.0 - 180.0
            return [md, i1 + f * (i2 - i1), (a1 + f * da) % 360.0]
    return None


# ---------------------------------------------------------------- the check of one well
def check_well(docs, S):
    found = []                        # (doc, type, field)
    small = 0                         # differences inside the tolerance that are left alone

    def hit(doc, typ, field):
        found.append((doc, typ, field))

    n = len(docs)
    rk = [rank_of(d, k) for k, d in enumerate(docs)]
    acc = {}                          # the accepted value of each field, for the export: as the majority sets it

    def keep(key, entries, r, odd, pair):
        if len(entries) == 1:
            acc[key] = {"v": entries[0][1], "k": entries[0][0], "docs": [entries[0][0]], "n": 1, "all": list(entries)}
        elif r is not None:
            acc[key] = {"v": r[1], "k": r[0], "docs": [k for k, v in entries if (k, v) not in odd], "n": len(entries), "all": list(entries)}
    # ---- coordinates
    # only documents with both coordinates; a document that names no system is read in the common one
    with_xy = [k for k, d in enumerate(docs) if d.get("x") is not None and d.get("y") is not None]
    crs_count = Counter(docs[k].get("crs") or "" for k in with_xy)
    top_n = max(crs_count.values()) if with_xy else 0
    common = next((docs[k].get("crs") or "" for k in with_xy if crs_count[docs[k].get("crs") or ""] == top_n), "")
    own_crs = lambda k: docs[k].get("crs") or common
    conv = []
    for k in with_xy:
        d = docs[k]
        c = S.convert(d["x"], d["y"], own_crs(k), common)
        conv.append((k, c))
    known = [e for e in conv if e[1] is not None]
    close = lambda p, q: abs(p[0] - q[0]) <= S.tol_xy and abs(p[1] - q[1]) <= S.tol_xy
    ref, odd, xy_pair = majority(known, close, lambda k: rk[k])
    keep("xy", known, ref, odd, xy_pair)
    for k, c in known:
        if ref and k != ref[0] and (k, c) not in odd and own_crs(k) == own_crs(ref[0]):
            for f in (0, 1):
                if 0 < abs(c[f] - ref[1][f]) <= S.tol_xy:
                    small += 1
    for k, c in conv:
        d = docs[k]
        if ref is None or k == ref[0]:
            continue
        if c is None:
            hit(k, "crs_unknown", "x"); hit(k, "crs_unknown", "y"); continue
        if (k, c) not in odd:
            if own_crs(k) != own_crs(ref[0]):
                hit(k, "crs", "x"); hit(k, "crs", "y")
            continue
        rx, ry = S.convert(ref[1][0], ref[1][1], common, own_crs(k))
        if abs(d["x"] - ry) <= S.tol_xy and abs(d["y"] - rx) <= S.tol_xy:
            hit(k, "swap", "x"); hit(k, "swap", "y"); continue
        # zone number of the Gauss-Krueger zone in front of the easting, or left out: whole millions of metres
        zd = d["y"] - ry
        zn = round(zd / 1e6)
        if abs(d["x"] - rx) <= S.tol_xy and zn != 0 and abs(zn) <= 60 and abs(zd - zn * 1e6) <= S.tol_xy:
            hit(k, "zone", "y"); continue
        ox, oy = abs(d["x"] - rx) <= S.tol_xy, abs(d["y"] - ry) <= S.tol_xy
        if ox and one_digit(d["y"], round(ry, 1), 10):
            hit(k, "typo", "y"); continue
        if oy and one_digit(d["x"], round(rx, 1), 10):
            hit(k, "typo", "x"); continue
        hit(k, "other", "x"); hit(k, "other", "y")

    # ---- KB and GL: reference now, the odd ones judged at the end (feet? own KB? second bore?)
    elev_ref, elev_odd = {}, []
    for f in ("kb", "gl"):
        ent = [(k, d[f]) for k, d in enumerate(docs) if d.get(f) is not None]
        same = lambda p, q: abs(p - q) <= S.tol_elev
        r, odd, el_pair = majority(ent, same, lambda k: rk[k])
        keep(f, ent, r, odd, el_pair)
        elev_ref[f] = r[1] if r else (ent[0][1] if ent else None)
        for k, v in ent:
            if r and (k, v) not in odd and 0 < abs(v - r[1]) <= S.tol_elev:
                small += 1
        elev_odd += [(k, f, v, r[1]) for k, v in odd]
    h = (elev_ref["kb"] - elev_ref["gl"]) if elev_ref["kb"] is not None and elev_ref["gl"] is not None else 0.0
    kb = elev_ref["kb"]

    # ---- depth values of each document (TD, tops, core; stations are lined up by depth further down)
    def flat(d):
        out = {} if d["td"] is None else {"td": d["td"]}
        for i, v in enumerate(d["tops"]):
            if v is not None:
                out[f"top{i}"] = v
        for i, (a, b) in enumerate(d["core"]):
            out[f"core{i}t"], out[f"core{i}b"] = a, b
        return out
    raw = [flat(d) for d in docs]
    shift = [None] * n                # "GL", "GLs" (stated), "ft", "shift" (one other amount) or "KBk" (the document's own KB)
    by = [0.0] * n                    # the amount of a shift: document value minus the other document's
    for k, d in enumerate(docs):
        if d.get("datum") == "GL" and h > 0:
            shift[k] = "GLs"
    base = [{key: (v + h if shift[k] == "GLs" else v) for key, v in raw[k].items()} for k in range(n)]
    for j in range(n):
        if shift[j]:
            continue
        agrees, ft_ok, gl_ok = False, False, False
        for i in range(n):
            if i == j:
                continue
            keys = [q for q in raw[j] if q in base[i] and base[i][q] >= 0 and raw[j][q] >= 0]
            if len(keys) < 3:
                continue
            m = len(keys)
            if sum(abs(raw[j][q] - base[i][q]) <= S.tol_depth for q in keys) / m >= 0.8:
                agrees = True
            if sum(abs(raw[j][q] * FT - base[i][q]) <= S.tol_depth for q in keys) / m >= 0.8:
                ft_ok = True
            if h > S.tol_depth and sum(abs(raw[j][q] + h - base[i][q]) <= S.tol_depth for q in keys) / m >= 0.8:
                gl_ok = True
        if not agrees:
            shift[j] = "ft" if ft_ok else ("GL" if gl_ok else None)
    # second pass, with feet and ground level converted: one other amount for every depth of a document
    conv0 = [{q: (v * FT if shift[k] == "ft" else v + h if shift[k] in ("GL", "GLs") else v) for q, v in raw[k].items()} for k in range(n)]
    for j in range(n):
        if shift[j]:
            continue
        agrees, other = False, None
        for i in range(n):
            if i == j:
                continue
            keys = [q for q in raw[j] if q in conv0[i] and conv0[i][q] >= 0 and raw[j][q] >= 0]
            if len(keys) < 3:
                continue
            diffs = [raw[j][q] - conv0[i][q] for q in keys]
            if sum(abs(x) <= S.tol_depth for x in diffs) / len(diffs) >= 0.8:
                agrees = True
            # the most common difference, found by counting how many others it fits
            best = max(diffs, key=lambda c: sum(abs(x - c) <= S.tol_depth for x in diffs))
            if other is None and abs(best) > S.tol_depth and sum(abs(x - best) <= S.tol_depth for x in diffs) / len(diffs) >= 0.8:
                other = best
        if not agrees and other is not None:
            own = docs[j].get("kb")
            from_own_kb = own is not None and kb is not None and abs(own - kb) > S.tol_elev and abs(other - (own - kb)) <= S.tol_depth
            shift[j], by[j] = ("KBk" if from_own_kb else "shift"), other

    def to_m(k, v):
        if shift[k] == "ft":
            return v * FT
        if shift[k] in ("shift", "KBk"):
            return v - by[k]
        return v + h if shift[k] in ("GL", "GLs") else v

    def from_m(k, v):
        if shift[k] == "ft":
            return v / FT
        if shift[k] in ("shift", "KBk"):
            return v + by[k]
        return v - h if shift[k] in ("GL", "GLs") else v

    conv_type = lambda k: "feet" if shift[k] == "ft" else ("shift" if shift[k] == "shift" else "datum")

    # ---- surveys: depths in metres from the reference KB, azimuths corrected where magnetic or turned
    sv = [None] * n
    for k, d in enumerate(docs):
        if d["survey"]:
            sv[k] = [[to_m(k, m), inc, az] for m, inc, az in d["survey"]]

    def value_at(i, md):
        """(value, own station index or -1) of document i at md, or None."""
        if not sv[i]:
            return None
        for s, st in enumerate(sv[i]):
            if abs(st[0] - md) <= S.tol_depth:
                return st, s
        v = survey_at(sv[i], md)
        return (v, -1) if v else None

    mag = [False] * n
    for k, d in enumerate(docs):
        if sv[k] and d.get("azref") == "magnetic":
            mag[k] = True
    stated = list(mag)
    az_off = [0.0] * n

    def az_pairs(j, i, corr_i):
        out = []
        for st in sv[j]:
            o = value_at(i, st[0])
            if o and st[1] >= LOW_INC and o[0][1] >= LOW_INC:
                out.append((st[2], (o[0][2] + corr_i) % 360))
        return out
    for j in range(n):
        if not sv[j] or mag[j]:
            continue
        agrees, mag_ok = False, False
        for i in range(n):
            if i == j or not sv[i]:
                continue
            ai = az_pairs(j, i, S.decl if stated[i] else 0)
            if len(ai) < 3:
                continue
            if sum(angle_gap(a, b) <= S.tol_az for a, b in ai) / len(ai) >= 0.8:
                agrees = True
            if sum(angle_gap(a + S.decl, b) <= S.tol_az for a, b in ai) / len(ai) >= 0.8:
                mag_ok = True
        mag[j] = (not agrees) and mag_ok
    # second pass, with magnetic surveys corrected: one other angle at every station.
    # Lower-priority documents first, and a survey already turned is compared turned (two surveys: only the lower is flagged)
    wrap = lambda t: (t + 180.0) % 360.0 - 180.0
    for j in sorted(range(n), key=lambda q: (-rk[q], q)):
        if not sv[j] or mag[j]:
            continue
        agrees, off = False, None
        for i in range(n):
            if i == j or not sv[i]:
                continue
            ai = az_pairs(j, i, S.decl if mag[i] else az_off[i])
            if len(ai) < 3:
                continue
            turns = [wrap(b - a) for a, b in ai]
            if sum(abs(t) <= S.tol_az for t in turns) / len(turns) >= 0.8:
                agrees = True
            best = max(turns, key=lambda c: sum(abs(wrap(t - c)) <= S.tol_az for t in turns))
            if off is None and abs(best) > S.tol_az and sum(abs(wrap(t - best)) <= S.tol_az for t in turns) / len(turns) >= 0.8:
                off = best
        if not agrees and off is not None:
            az_off[j] = off
    corr = lambda k: S.decl if mag[k] else az_off[k]
    for k in range(n):
        if sv[k] and (mag[k] or az_off[k]):
            sv[k] = [[m, inc, (az + corr(k)) % 360] for m, inc, az in sv[k]]

    # angles only: depths are lined up first
    st_same = lambda p, q: abs(p[1] - q[1]) <= S.tol_inc and (max(p[1], q[1]) < LOW_INC or angle_gap(p[2], q[2]) <= S.tol_az)
    # depth points: every station of every document; stations of different documents within the depth tolerance are one point
    stations = sorted(((st[0], k, s) for k in range(n) if sv[k] for s, st in enumerate(sv[k])), key=lambda t: t[0])
    points = []
    for m, k, s in stations:
        if points and m - points[-1]["m"] <= S.tol_depth and k not in points[-1]["own"]:
            points[-1]["own"][k] = s
        else:
            points.append({"m": m, "own": {k: s}})

    def entries_at(p):
        out = []
        for k in range(n):
            if not sv[k]:
                continue
            if k in p["own"]:
                out.append((k, sv[k][p["own"][k]], p["own"][k]))
            else:
                v = survey_at(sv[k], p["m"])
                if v:
                    out.append((k, v, -1))
        return out

    td_m = [(k, to_m(k, d["td"])) for k, d in enumerate(docs) if d["td"] is not None]
    tdr, td_odd, td_nomaj = majority(td_m, lambda p, q: abs(p - q) <= S.tol_depth, lambda k: rk[k])
    td_ref = tdr[1] if tdr and not td_nomaj else None

    # ---- a second bore under the same number
    side = {}                          # doc -> depth below which it is another bore
    for j in range(n):
        for i in range(j):
            if not sv[i] or not sv[j] or docs[i]["td"] is None or docs[j]["td"] is None:
                continue
            both = []
            for p in points:
                e = {k: (v, own) for k, v, own in entries_at(p)}
                if i in e and j in e and (e[i][1] >= 0 or e[j][1] >= 0):
                    both.append((p["m"], st_same(e[i][0], e[j][0])))
            lead = 0
            while lead < len(both) and both[lead][1]:
                lead += 1
            tds_differ = abs(to_m(i, docs[i]["td"]) - to_m(j, docs[j]["td"])) > S.tol_depth
            if 1 <= lead < len(both) and tds_differ:
                odd_docs = [] if td_nomaj else [k for k, _ in td_odd if k in (i, j)]
                s = odd_docs[0] if len(odd_docs) == 1 else (i if rk[i] > rk[j] else j)
                side[s] = both[lead - 1][0]

    # reference survey for TVD: the first in the order of priority that is not the second bore
    cands = [k for k in range(n) if sv[k] and k not in side]
    ref_k = min(cands, key=lambda k: rk[k]) if cands else -1
    ref_sv = sv[ref_k] if cands else None
    tvd = (lambda md: tvd_numeric(ref_sv, md)) if ref_sv else (lambda md: md)
    rank_side = lambda k: 99 if k in side else rk[k]

    # ---- survey stations, point by point
    for p in points:
        ent = entries_at(p)
        if len(ent) < 2:
            continue
        r, odd, nomaj = majority([(k, v) for k, v, _ in ent], st_same, rank_side)
        if r is None:
            continue
        own = {k: o for k, _, o in ent}
        odd_k = {k for k, _ in odd}
        if not nomaj:
            agreeing = [k for k, _, _ in ent if k not in odd_k]
            for k in agreeing:
                if own[k] < 0:
                    continue
                raw_md = docs[k]["survey"][own[k]][0]
                others = [q for q in agreeing if q != k]
                if not others:
                    continue
                if shift[k] and abs(raw_md - sv[k][own[k]][0]) > S.tol_depth:
                    hit(k, conv_type(k), f"st{own[k]}")
                elif mag[k] and any(not mag[q] for q in others):
                    hit(k, "magnetic", f"st{own[k]}")
                elif az_off[k] and any(not az_off[q] for q in others):
                    hit(k, "flip" if abs(abs(az_off[k]) - 180.0) <= S.tol_az else "azoff", f"st{own[k]}")
        for k, v in odd:
            if own[k] < 0:
                continue
            if k in side and p["m"] > side[k] + S.tol_depth:
                hit(k, "sidetrack", f"st{own[k]}"); continue
            ov = docs[k]["survey"][own[k]]
            rv = [ov[0], r[1][1], (r[1][2] - corr(k)) % 360]
            diffs = [c for c in (1, 2) if (angle_gap(ov[c], rv[c]) if c == 2 else abs(ov[c] - rv[c])) > (S.tol_inc if c == 1 else S.tol_az)]
            hit(k, "typo" if len(diffs) == 1 and one_digit(ov[diffs[0]], round(rv[diffs[0]], 1)) else "other", f"st{own[k]}")

    # ---- value by value
    def judge(key, entries, same, kind, elev=()):
        """elev: tops written as elevations, (doc, -1e9); they take no part in the vote and are judged against it."""
        nonlocal small
        elev = list(elev)
        if len(entries) >= 2:
            r, odd, pair = majority(entries, same, rank_side)
        else:
            r, odd, pair = (entries[0] if entries else None), [], True
        if r is not None or len(entries) + len(elev) == 1:
            odd = odd + elev
        if kind != "core":
            keep(key, entries + elev, r, odd, pair)
        if r is None or len(entries) + len(elev) < 2:
            return
        odd_k = {k for k, _ in odd}
        if not pair:
            for k, v in entries:
                if k == r[0] or k in odd_k:
                    continue
                # agreement after conversion: which conversion made the raw value differ
                rv_raw, ov_raw = raw_of(r[0], key), raw_of(k, key)
                vals_o = ov_raw if isinstance(ov_raw, list) else [ov_raw]
                vals_r = rv_raw if isinstance(rv_raw, list) else [rv_raw]
                if any(abs(a - b) > S.tol_depth for a, b in zip(vals_o, vals_r)):
                    if shift[k] or shift[r[0]]:
                        who = k if shift[k] else r[0]
                        hit(who, conv_type(who), key)
                elif not shift[k] and not shift[r[0]]:
                    small += sum(0 < abs(a - b) <= S.tol_depth for a, b in zip(vals_o, vals_r))
        for k, v in odd:
            ref_v = r[1]
            depth_here = v[0] if isinstance(v, (list, tuple)) else v
            if k in side and depth_here > side[k] + S.tol_depth:
                hit(k, "sidetrack", key); continue
            if kind == "td":
                hit(k, "typo" if one_digit(docs[k]["td"], round(from_m(k, ref_v), 1), 10) else "other", key)
            elif kind == "top":
                rawv = docs[k]["tops"][int(key[3:])]
                if pair and raw_of(r[0], key) < 0 <= rawv:
                    k, rawv, ref_v = r[0], raw_of(r[0], key), v
                t = tvd(ref_v)
                deviated = abs(ref_v - t) > S.tol_depth
                written_as = []                       # what else a top can be written as, besides measured depth
                if kb is not None:
                    written_as += [kb - t, t - kb]
                    if deviated:
                        written_as.append(kb - ref_v)                 # elevation from measured depth
                if deviated:
                    written_as.append(t)                              # TVD
                if elev_ref["gl"] is not None and h > S.tol_depth:
                    written_as.append(elev_ref["gl"] - t)            # elevation from ground level
                if any(abs(rawv - w) <= S.tol_depth for w in written_as):
                    hit(k, "elev", key)
                elif abs(to_m(k, rawv) - ref_v) <= S.window:
                    hit(k, "pick", key)
                elif one_digit(rawv, round(from_m(k, ref_v), 1), 10):
                    hit(k, "typo", key)
                else:
                    hit(k, "other", key)
            elif kind == "core":
                lim = td_ref if td_ref is not None else to_m(k, docs[k]["td"])
                if v[1] > lim + S.tol_depth or v[0] > lim + S.tol_depth:
                    hit(k, "core", key)
                else:
                    ra, rb = from_m(k, ref_v[0]), from_m(k, ref_v[1])
                    oa, ob = docs[k]["core"][int(key[4:])]
                    ty = (abs(oa - ra) <= S.tol_depth and one_digit(ob, round(rb, 1), 10)) or (abs(ob - rb) <= S.tol_depth and one_digit(oa, round(ra, 1), 10))
                    hit(k, "typo" if ty else "other", key)

    def raw_of(k, key):
        d = docs[k]
        if key == "td":
            return d["td"]
        if key.startswith("top"):
            return d["tops"][int(key[3:])]
        return list(d["core"][int(key[4:])])

    judge("td", td_m, lambda p, q: abs(p - q) <= S.tol_depth, "td")
    for i in range(max(len(d["tops"]) for d in docs)):
        ent = []
        for k, d in enumerate(docs):
            if i < len(d["tops"]) and d["tops"][i] is not None:
                v = d["tops"][i]
                ent.append((k, to_m(k, v) if v >= 0 else None))
        ok = [e for e in ent if e[1] is not None]
        bad = [e for e in ent if e[1] is None]
        # tops written below zero are elevations: judged against the others
        judge(f"top{i}", ok, lambda p, q: abs(p - q) <= S.tol_depth, "top", [(k, -1e9) for k, _ in bad])
    for i in range(max(len(d["core"]) for d in docs)):
        ent = [(k, [to_m(k, d["core"][i][0]), to_m(k, d["core"][i][1])]) for k, d in enumerate(docs) if i < len(d["core"])]
        judge(f"core{i}", ent, lambda p, q: abs(p[0] - q[0]) <= S.tol_depth and abs(p[1] - q[1]) <= S.tol_depth, "core")

    # ---- the odd elevations, now that units, datum and bore are known
    for k, f, v, ref_e in elev_odd:
        if shift[k] == "ft" and abs(v * FT - ref_e) <= S.tol_elev:
            hit(k, "feet", f)
        elif f == "kb" and shift[k] == "KBk":
            hit(k, "datum", f)
        elif f == "kb" and k in side:
            hit(k, "sidetrack", f)
        else:
            hit(k, "typo" if one_digit(v, ref_e, 10) else "other", f)

    return found, small, {"shift": shift, "shift_by": by, "magnetic": mag, "az_offset": az_off, "sidetrack": side, "kb_minus_gl": h, "rank": rk,
                          "acc": acc, "sv": sv, "ref_k": ref_k, "common": common, "to_m": to_m}


def one_doc_flags(d, tol):
    """The check of one document on its own: order and ranges. Returns the fields that take part in a failed check."""
    bad = set()
    if d.get("kb") is not None and d.get("gl") is not None and d["kb"] <= d["gl"]:
        bad |= {"kb", "gl"}
    td = d["td"]
    sv = d["survey"] or []
    for i, (m, inc, az) in enumerate(sv):
        if not (0 <= inc <= 90) or not (0 <= az < 360):
            bad.add(f"st{i}")
        if i and m <= sv[i - 1][0]:
            bad |= {f"st{i}", f"st{i - 1}"}
        if td is not None and m > td + tol:
            bad |= {f"st{i}", "td"}
    tops = [v for v in d["tops"] if v is not None]
    if tops and all(v >= 0 for v in tops):
        for i in range(1, len(tops)):
            if tops[i] <= tops[i - 1]:
                bad |= {f"top{i}", f"top{i - 1}"}
        for i, v in enumerate(tops):
            if td is not None and v > td + tol:
                bad |= {f"top{i}", "td"}
    elif tops and all(v < 0 for v in tops):
        for i in range(1, len(tops)):
            if tops[i] >= tops[i - 1]:
                bad |= {f"top{i}", f"top{i - 1}"}
    elif tops:
        bad |= {f"top{i}" for i in range(len(tops))}
    for i, (a, b) in enumerate(d["core"]):
        if a >= b:
            bad.add(f"core{i}")
        if td is not None and b > td + tol:
            bad |= {f"core{i}", "td"}
    return bad


def run(data):
    S = Setup(data["settings"])
    groups = {}
    small_total = 0
    info = {}
    for w in data["wells"]:
        found, small, inf = check_well(w["docs"], S)
        small_total += small
        info[w["name"]] = inf
        for doc, typ, field in found:
            groups.setdefault((w["name"], doc, typ), []).append(field)
    seen = 0
    for (well, doc, typ), fields in groups.items():
        d = next(x for x in data["wells"] if x["name"] == well)["docs"][doc]
        fl = one_doc_flags(d, S.tol_depth)
        base = {f[:-1] if f.startswith("core") and f[-1] in "tb" else f for f in fields}
        if any(f in fl or (f.startswith("core") and any(g.startswith(f) for g in fl)) for f in base):
            seen += 1
    return groups, small_total, seen, info


# ---------------------------------------------------------------- the export of accepted values
SEVER = ["needs a choice", "converted", "one document", "agreed", "tie point"]


def path_numeric(survey, step=0.01):
    """(md, inc, az, TVD, DX east, DY north) at each station, from a vertical start at the datum: the direction
    turns along a great circle between stations and is integrated in 1 cm steps (not the minimum-curvature formula)."""
    st = [(0.0, 0.0, 0.0)] + [tuple(map(float, s)) for s in survey]
    pos = np.zeros(3)                                   # north, east, down
    out = []
    for (m1, i1, a1), (m2, i2, a2) in zip(st, st[1:]):
        t1, t2 = unit(i1, a1), unit(i2, a2)
        om = math.acos(float(np.clip(t1 @ t2, -1, 1)))
        n = max(1, int(round((m2 - m1) / step)))
        f = (np.arange(n) + 0.5) / n
        v = np.tile(t1, (n, 1)) if om < 1e-12 else (np.outer(np.sin((1 - f) * om), t1) + np.outer(np.sin(f * om), t2)) / math.sin(om)
        pos = pos + v.sum(axis=0) * (m2 - m1) / n
        out.append((m2, i2, a2, float(pos[2]), float(pos[1]), float(pos[0])))
    return out


def accepted(docs, found, info, S):
    """The accepted values of one well and the status of each: agreed, one document, converted or needs a choice;
    pending while a discrepancy touches it (no decisions here: the register is the page's)."""
    acc, side, rk = info["acc"], info["sidetrack"], info["rank"]
    rank_k = lambda k: 99 if k in side else rk[k]
    groups = defaultdict(set)
    for doc, typ, field in found:
        groups[(doc, typ)].add(field)
    on, st_hits = defaultdict(set), []
    for (doc, typ), fields in groups.items():
        for f in fields:
            if f in ("x", "y"):
                on["xy"].add((doc, typ))
            elif f in ("kb", "gl", "td") or f.startswith("top"):
                on[f].add((doc, typ))
            elif f.startswith("st"):
                st_hits.append((info["to_m"](doc, docs[doc]["survey"][int(f[2:])][0]), (doc, typ)))
            elif typ == "core":                         # core below TD: either the core or the TD is wrong
                on["td"].add((doc, typ))

    def status(gs, n):
        if not gs:
            return ("agreed" if n >= 2 else "one document"), False
        return ("converted" if all(t in EXPLAINED for _, t in gs) else "needs a choice"), True

    shift = info["shift"]

    def converted(key, k):                              # did the document's value need a conversion to agree
        if key == "xy":
            return (docs[k].get("crs") or info["common"]) != info["common"]
        if key in ("kb", "gl"):
            return shift[k] == "ft"
        return bool(shift[k])

    def pick(key):
        """Of the documents that hold the accepted value: one that needed no conversion, then priority. A second bore
        gives a value only when no other document has one; a top written as an elevation never."""
        a = acc.get(key)
        if not a:
            return None
        is_md = lambda e: not (isinstance(e[1], (int, float)) and e[1] <= -1e8)
        order = lambda e: (converted(key, e[0]), rank_k(e[0]), e[0])
        hold = sorted((e for e in a["all"] if e[0] in a["docs"] and is_md(e) and e[0] not in side), key=order)
        if hold:
            return hold[0]
        ok = sorted((e for e in a["all"] if is_md(e) and e[0] not in side), key=order) or \
            sorted((e for e in a["all"] if is_md(e)), key=order)
        return ok[0] if ok else None

    def elev(f):
        p = pick(f)
        return None if p is None else (p[1] * FT if info["shift"][p[0]] == "ft" else p[1])
    kb, gl, xy, td = elev("kb"), elev("gl"), pick("xy"), pick("td")
    fields = {f: status(on[f], acc[f]["n"]) for f in ("xy", "kb", "gl", "td") if f in acc}
    worst = min(fields.values(), key=lambda s: SEVER.index(s[0]))[0] if fields else ""
    pend = "; ".join(nm for f, nm in (("xy", "N/E"), ("kb", "KB"), ("gl", "GL"), ("td", "TD")) if f in fields and fields[f][1])
    head = {"crs": info["common"] if xy else "", "n": xy[1][0] if xy else None, "e": xy[1][1] if xy else None,
            "kb": kb, "gl": gl, "td": td[1] if td else None, "status": worst, "pending": pend}
    # the exported survey: not a second bore; one that needed no conversion first, then the order of priority
    sv = info["sv"]
    cands = sorted((k for k in range(len(docs)) if sv[k] and k not in side),
                   key=lambda k: (bool(shift[k] or info["magnetic"][k] or info["az_offset"][k]), rank_k(k), k))
    traj, K = [], (cands[0] if cands else -1)
    ref_sv = sv[K] if K >= 0 else None
    if ref_sv:
        P = path_numeric(ref_sv)
        at = [set() for _ in P]
        for m, g in st_hits:
            if g[1] == "sidetrack" and g[0] in side:    # below the depth where the surveys part, every station is in question
                for j, p in enumerate(P):
                    if p[0] > side[g[0]] + S.tol_depth + 1e-9:
                        at[j].add(g)
                continue
            j = min(range(len(P)), key=lambda i: (abs(P[i][0] - m) - 1e-9 * i, -i))   # the nearest station, the deeper one on a tie
            at[j].add(g)
        if abs(P[0][0]) > 1e-9:                         # a survey that starts at MD 0 is its own tie point
            traj.append([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "tie point", "no"])
        for j, (md, inc, az, t, dx, dy) in enumerate(P):
            n = sum(1 for s in info["sv"] if s and (any(abs(x[0] - md) <= S.tol_depth for x in s) or survey_at(s, md)))
            s_ = status(at[j], n)
            traj.append([md, inc, az, t, dx, dy, s_[0], "yes" if s_[1] else "no"])
    # a top waits for a decision on its own value, on the KB its TVDSS is worked out from, or on a station its TVD uses
    kb_pending = "kb" in fields and fields["kb"][1]
    pend_md = [r[0] for r in traj if r[7] == "yes"]
    st_md = [r[0] for r in traj]
    tops = []
    for i in range(max(len(d["tops"]) for d in docs)):
        p = pick(f"top{i}")
        if p is None:
            continue
        t = tvd_numeric(ref_sv, p[1]) if ref_sv else None          # no survey: TVD not known
        s_ = status(on[f"top{i}"], acc[f"top{i}"]["n"])
        below = [m for m in st_md if m >= p[1] - 1e-9]
        uses = [m for m in st_md if m <= p[1] + 1e-9] + below[:1]
        wait = s_[1] or (kb_pending and t is not None) or any(m in pend_md for m in uses)
        tops.append([i, p[1], t, None if kb is None or t is None else t - kb, s_[0], "yes" if wait else "no"])
    return {"head": head, "traj": traj, "tops": tops}


def export_set(data):
    """Accepted values of every well; wellheads in the system most wells use, converted where the transformation is given."""
    S = Setup(data["settings"])
    out = {}
    for w in data["wells"]:
        found, _, inf = check_well(w["docs"], S)
        out[w["name"]] = accepted(w["docs"], found, inf, S)
    systems = Counter(x["head"]["crs"] for x in out.values() if x["head"]["crs"])
    OUT = max(systems, key=lambda c: (systems[c], -list(systems).index(c))) if systems else ""
    for x in out.values():
        h = x["head"]
        if h["crs"] and h["crs"] != OUT:
            c = S.convert(h["n"], h["e"], h["crs"], OUT)
            if c:
                h["n"], h["e"], h["crs"] = c[0], c[1], OUT
    return out, OUT


def main():
    data = json.loads((HERE / "example.json").read_text(encoding="utf-8"))
    key = json.loads((HERE / "answer_key.json").read_text(encoding="utf-8"))
    clean = json.loads((HERE / "example_clean.json").read_text(encoding="utf-8"))
    S = Setup(data["settings"])
    results = []

    def check(what, ok, detail=""):
        results.append(ok)
        print(("PASS " if ok else "FAIL ") + what + (f"  [{detail}]" if detail else ""))

    groups, small, seen, info = run(data)
    found = {(w, d, t) for (w, d, t) in groups}
    planted = {(k["well"], k["doc"], k["type"]) for k in key}
    check("every planted discrepancy found", planted <= found, f"missed {sorted(planted - found)}")
    check("no false discrepancies", found <= planted, f"false {sorted(found - planted)}")
    check("17 discrepancies in the key", len(planted) == 17)
    by_type = Counter(t for (_, _, t) in groups)
    for t, c in sorted(Counter(k["type"] for k in key).items()):
        check(f"type {t}: {c} found", by_type[t] == c, f"got {by_type[t]}")
    nvals = sum(len(v) for v in groups.values())
    # a survey station and a core run count as one value each; core ends are reported once per run
    def count_values(fields):
        return len({f[:-1] if f.startswith("core") and f[-1] in "tb" else f for f in fields})
    nvals = sum(count_values(v) for v in groups.values())
    check("64 values differ between the documents", nvals == 64, f"got {nvals}")
    expl = sum(1 for (_, _, t) in groups if t in EXPLAINED)
    check("11 systematic, 6 need a choice", expl == 11 and len(groups) - expl == 6, f"{expl}/{len(groups) - expl}")
    check("a check of each document on its own sees 2 of 17", seen == 2, f"got {seen}")
    check("5 differences inside the tolerance are left alone", small == 5, f"got {small}")
    docs_hit = len({(w, d) for (w, d, _) in groups})
    check("14 of 18 documents carry at least one discrepancy", docs_hit == 14, f"got {docs_hit}")
    check("W-06: the second bore leaves the first below 1200 m", info["W-06"]["sidetrack"] == {1: 1200.0}, str(info["W-06"]["sidetrack"]))
    check("W-02 drilling report: depths from ground level, 6.4 m", info["W-02"]["shift"][1] == "GLs" and abs(info["W-02"]["kb_minus_gl"] - 6.4) < 1e-9)
    check("W-06 summary table: depths from ground level although it says KB", info["W-06"]["shift"][2] == "GL")
    check("W-04 drilling report: depths in feet", info["W-04"]["shift"][1] == "ft")
    check("W-04 drilling report: KB and GL in feet too, in the same discrepancy",
          {"kb", "gl"} <= set(groups.get(("W-04", 1, "feet"), [])), str(groups.get(("W-04", 1, "feet"))))
    check("W-06 drilling report of the sidetrack: its rig's own KB belongs to the sidetrack",
          "kb" in groups.get(("W-06", 1, "sidetrack"), []), str(groups.get(("W-06", 1, "sidetrack"))))
    check("W-03 and W-05 well files: magnetic azimuths", info["W-03"]["magnetic"][0] and info["W-05"]["magnetic"][0])
    g2, s2, seen2, _ = run(clean)
    check("clean copy of the six wells: nothing found", not g2 and s2 == 0, str(sorted(g2)))
    check("clean copy: a check of each document on its own finds nothing", seen2 == 0)
    # one planted change at a time on the clean copy: exactly that one must be found, nothing else
    import copy
    alone_ok = 0
    for k in key:
        case = copy.deepcopy(clean)
        src = next(w for w in data["wells"] if w["name"] == k["well"])["docs"][k["doc"]]
        dst = next(w for w in case["wells"] if w["name"] == k["well"])["docs"][k["doc"]]
        for f in k["fields"]:
            if f in ("x", "y"):
                dst[f] = src[f]; dst["crs"] = src["crs"]
            elif f.startswith("top:"):
                i = data["horizons"].index(f[4:]); dst["tops"][i] = src["tops"][i]
            elif f.startswith("core:"):
                i = int(f[5:]) - 1; dst["core"][i] = list(src["core"][i])
            else:
                dst[f] = copy.deepcopy(src[f]); dst["datum"] = src["datum"]; dst["azref"] = src["azref"]
        g, _, _, _ = run(case)
        alone_ok += set(g) == {(k["well"], k["doc"], k["type"])}
        if set(g) != {(k["well"], k["doc"], k["type"])}:
            print("   alone:", k["well"], k["doc"], k["type"], "->", sorted(g))
    check("each planted change on its own, on the clean copy: found alone, 17 of 17", alone_ok == 17, f"{alone_ok}")

    # rules added after the geologist's reading, on a small made-up well of three agreeing documents
    def tiny(change, steep=False, n=3, kinds=None):
        sv0 = [[300.0, 10.0, 10.0], [600.0, 20.0, 20.0], [900.0, 30.0, 30.0]] if steep else [[300.0, 3.0, 10.0], [600.0, 5.0, 20.0], [900.0, 10.0, 30.0]]
        d0 = {"crs": S.crs_a, "x": 1000.0, "y": 2000.0, "kb": 100.0, "gl": 94.0, "datum": "KB", "azref": "true", "td": 1000.0,
              "survey": sv0, "tops": [700.0, 800.0, 900.0], "core": [[810.0, 818.0]]}
        ds = [copy.deepcopy(d0) for _ in range(n)]
        for d, kd in zip(ds, kinds or []):
            d["kind"] = kd
        change(ds)
        f, _, _ = check_well(ds, S)
        return sorted({(d, t) for d, t, _ in f})

    def deeper(d, by):
        d["td"] += by
        d["survey"] = [[m + by, i, a] for m, i, a in d["survey"]]
        d["tops"] = [v + by for v in d["tops"]]
        d["core"] = [[a + by, b + by] for a, b in d["core"]]
    check("small well: every depth 3 m deeper is a constant shift", tiny(lambda ds: deeper(ds[1], 3.0)) == [(1, "shift")])
    check("small well: TD 3 m deeper is no rule, not a typing error", tiny(lambda ds: ds[2].update(td=1003.0)) == [(2, "other")])
    check("small well: a document without a TD is read, and nothing is found",
          tiny(lambda ds: ds[2].update(td=None)) == [] and tiny(lambda ds: ds[1].update(td=None), n=2) == [])
    check("small well: TD 1985 against 985 written with a digit missing is a typing error",
          tiny(lambda ds: [d.update(td=1985.0) for d in ds[:2]] and ds[2].update(td=985.0)) == [(2, "typo")])
    check("small well: every azimuth 4 degrees larger is a constant offset",
          tiny(lambda ds: ds[0].update(survey=[[m, i, a + 4.0] for m, i, a in ds[0]["survey"]])) == [(0, "azoff")])
    check("small well: every azimuth 180 degrees off is a survey written in the opposite direction",
          tiny(lambda ds: ds[0].update(survey=[[m, i, (a + 180.0) % 360] for m, i, a in ds[0]["survey"]])) == [(0, "flip")])
    check("small well, two surveys only: the well file 180 degrees off is the one flagged",
          tiny(lambda ds: ds[0].update(survey=[[m, i, (a + 180.0) % 360] for m, i, a in ds[0]["survey"]]), n=2, kinds=["Well file", "Drilling report"]) == [(0, "flip")])
    check("small well: zone number 8 in front of Y (8 002 000 for 2 000) is the zone rule",
          tiny(lambda ds: ds[2].update(y=8002000.0)) == [(2, "zone")])
    check("small well: azimuths 20 degrees apart at 1 degree inclination are not compared",
          tiny(lambda ds: [d["survey"][0].__setitem__(1, 1.0) for d in ds] and ds[2]["survey"][0].__setitem__(2, 30.0)) == [])
    check("small well: tops written as TVD are read as such",
          tiny(lambda ds: ds[2].update(tops=[round(tvd_numeric(ds[0]["survey"], v), 1) for v in ds[0]["tops"]]), steep=True) == [(2, "elev")])
    check("small well: elevations from measured depth (KB - MD) are read as such",
          tiny(lambda ds: ds[2].update(tops=[100.0 - v for v in ds[0]["tops"]]), steep=True) == [(2, "elev")])

    # rules added on the second round: which document is the record, survey by depth, own KB, elevations in feet
    two = ["Well file", "Drilling report"]
    check("two documents that differ: the drilling report is the record, the well file is flagged",
          tiny(lambda ds: ds[0].update(td=1003.0), n=2, kinds=two) == [(0, "other")]
          and tiny(lambda ds: ds[1].update(td=1003.0), n=2, kinds=two) == [(0, "other")])
    check("two documents, priority given by hand, the second first: the first is flagged",
          tiny(lambda ds: [ds[0].update(rank=2), ds[1].update(rank=1, td=1003.0)], n=2) == [(0, "other")])
    check("small well: stations at other depths on the same path are not discrepancies",
          tiny(lambda ds: ds[2].update(survey=[survey_at(ds[0]["survey"], m) for m in (450.0, 750.0, 900.0)])) == [])
    check("small well: a survey that starts at its tie-in is compared below it only",
          tiny(lambda ds: ds[2].update(survey=ds[2]["survey"][1:])) == [])
    check("small well: depths from the document's own KB, 2 m higher, are a datum shift",
          tiny(lambda ds: [ds[1].update(kb=102.0), deeper(ds[1], 2.0)]) == [(1, "datum")])

    def in_feet(d):
        for f in ("kb", "gl", "td"):
            d[f] = round(d[f] / FT, 1)
        d["survey"] = [[round(m / FT, 1), i, a] for m, i, a in d["survey"]]
        d["tops"] = [round(v / FT, 1) for v in d["tops"]]
        d["core"] = [[round(a / FT, 1), round(b / FT, 1)] for a, b in d["core"]]
    check("small well: KB and GL in feet with the depths are one discrepancy, feet",
          tiny(lambda ds: in_feet(ds[1])) == [(1, "feet")])
    el = lambda ds, k: ds[k].update(tops=[round(100.0 - tvd_numeric(ds[0]["survey"], v), 1) for v in ds[0]["tops"]])
    check("small well: two documents with tops as elevations, one in measured depth: both elevations flagged",
          tiny(lambda ds: [el(ds, 1), el(ds, 2)]) == [(1, "elev"), (2, "elev")])

    # the export on small wells: the cases the example does not hold
    def tiny_acc(change, n=3):
        d0 = {"crs": S.crs_a, "x": 1000.0, "y": 2000.0, "kb": 100.0, "gl": 94.0, "datum": "KB", "azref": "true", "td": 1000.0,
              "survey": [[300.0, 3.0, 10.0], [600.0, 5.0, 20.0], [900.0, 10.0, 30.0]], "tops": [700.0, 800.0, 900.0], "core": [[810.0, 818.0]]}
        ds = [copy.deepcopy(d0) for _ in range(n)]
        change(ds)
        f, _, inf = check_well(ds, S)
        return accepted(ds, f, inf, S)
    def side_kb(ds):
        ds[0]["kb"] = None
        ds[1].update(kb=102.3, td=1040.0, tops=[715.0, 822.0, 931.0], core=[[832.0, 840.0]])
        ds[1]["survey"][2] = [920.0, 18.0, 70.0]
    check("export, small well: the second bore's KB is not taken where another document gives one",
          abs(tiny_acc(side_kb)["head"]["kb"] - 100.0) < 1e-9)
    ax = tiny_acc(lambda ds: [ds[k].update(tops=[-600.0, 800.0, 900.0]) for k in (0,)], n=2)
    check("export, small well: a top written as an elevation is never taken, the other document's measured depth is",
          abs(ax["tops"][0][1] - 700.0) < 1e-9)
    ax = tiny_acc(lambda ds: ds[2].update(kb=125.3))
    check("export, small well: while the KB waits for a decision, every top waits too (TVDSS uses it)",
          [t[5] for t in ax["tops"]] == ["yes"] * 3 and ax["head"]["pending"] == "KB")
    ax = tiny_acc(lambda ds: [d.update(survey=[[0.0, 0.0, 0.0]] + d["survey"]) for d in ds])
    check("export, small well: a survey that starts at MD 0 is its own tie point, no second row at 0",
          [r[0] for r in ax["traj"]] == [0.0, 300.0, 600.0, 900.0])
    check("TVD with two stations at one depth is a number", math.isfinite(tvd_numeric([[0.0, 0.5, 10.0], [100.0, 0.5, 10.0]], 50.0)))

    # the export of accepted values
    exp, OUT = export_set(data)
    q = path_numeric([[100.0, 90.0, 0.0]])[-1]
    check("export path, quarter circle of 100 m to the north: TVD and DY 200/pi, DX 0",
          abs(q[3] - 200 / math.pi) < 1e-4 and abs(q[5] - 200 / math.pi) < 1e-4 and abs(q[4]) < 1e-9, str(q))
    check("export path, the same to the east: DX 200/pi, DY 0", abs(path_numeric([[100.0, 90.0, 90.0]])[-1][4] - 200 / math.pi) < 1e-4)
    check("export: 6 wellheads, 18 tops, 36 trajectory rows with the tie point, all in FLD-75",
          len(exp) == 6 and sum(len(x["tops"]) for x in exp.values()) == 18 and sum(len(x["traj"]) for x in exp.values()) == 36 and OUT == "FLD-75")
    hd = {n: x["head"] for n, x in exp.items()}
    check("export: W-04 wellhead converted (zone, feet), pending N/E, KB, GL and TD; TD 1892.0 from a metric document",
          hd["W-04"]["status"] == "converted" and hd["W-04"]["pending"] == "N/E; KB; GL; TD" and abs(hd["W-04"]["td"] - 1892.0) < 1e-9, str(hd["W-04"]))
    check("export: TD needs a choice in W-03 (core below TD), W-05 (typed 1652) and W-06 (second bore)",
          all("TD" in hd[w]["pending"] and hd[w]["status"] == "needs a choice" for w in ("W-03", "W-05", "W-06")))
    check("export: W-01 X 14 862.0 from the drilling report, where the well file says 14 862.4 inside the tolerance", abs(hd["W-01"]["n"] - 14862.0) < 1e-9)
    st06 = [(r[0], r[6]) for r in exp["W-06"]["traj"]]
    check("export: W-06 trajectory from the well file, the stations below 1200 m need a choice",
          [s for m, s in st06 if m > 1200.5] == ["needs a choice"] * 2 and [s for m, s in st06 if 0 < m <= 1200.5] == ["agreed"] * 3, str(st06))
    pend_rows = sum(r[-1] == "yes" for x in exp.values() for r in x["traj"] + x["tops"]) + sum(bool(h["pending"]) for h in hd.values())
    nr = lambda v: None if v is None else round(v, 4)
    export_ref = {"out": OUT, "pending_rows": pend_rows, "wells": {n: {
        "head": [nr(x["head"][k]) for k in ("n", "e", "kb", "gl", "td")] + [x["head"]["status"], x["head"]["pending"]],
        "tops": [[t[0], nr(t[1]), nr(t[2]), nr(t[3]), t[4], t[5]] for t in x["tops"]],
        "traj": [[nr(v) for v in r[:6]] + r[6:] for r in x["traj"]]} for n, x in exp.items()}}

    # numbers for the page's checks
    w02 = next(w for w in data["wells"] if w["name"] == "W-02")
    sv02 = w02["docs"][0]["survey"]
    tops02 = w02["docs"][0]["tops"]
    tvd02 = [tvd_numeric(sv02, m) for m in tops02]
    back = {}
    for name in ("W-01", "W-03", "W-04"):
        d = next(w for w in data["wells"] if w["name"] == name)["docs"][2]
        back[name] = S.convert(d["x"], d["y"], S.crs_b, S.crs_a)
    quarter = tvd_numeric([[100.0, 90.0, 0.0]], 100.0)
    w05 = next(w for w in data["wells"] if w["name"] == "W-05")
    tvd05 = tvd_numeric(w05["docs"][1]["survey"], 1952.0)
    ref = {
        "tvd_w02_tops": tvd02, "elev_w02_tops": [w02["docs"][0]["kb"] - t for t in tvd02],
        "back_to_fld": back, "tvd_quarter_circle_100": quarter, "tvd_w05_td": tvd05,
        "tvd_w03_td": tvd_numeric(next(w for w in data["wells"] if w["name"] == "W-03")["docs"][1]["survey"], 1885.0),
        "groups": len(groups), "values": nvals, "explained": expl, "seen_one_doc": seen, "small": small,
        "docs_hit": docs_hit, "by_type": dict(by_type), "export": export_ref,
    }
    (HERE / "ref_values.json").write_text(json.dumps(ref, indent=1), encoding="utf-8")
    for k, v in ref.items():
        if k != "export":
            print("   ", k, v)
    print("    export: wellheads in", OUT, "; pending rows", pend_rows)
    ok = sum(results)
    print(f"ALL {len(results)} PASS" if ok == len(results) else f"{ok} of {len(results)} pass")
    sys.exit(0 if ok == len(results) else 1)


if __name__ == "__main__":
    main()
