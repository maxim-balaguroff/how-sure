# -*- coding: utf-8 -*-
"""Independent calculation for tool 07 "Is the answer on the page it cites?".

Shares no code with the page or the workbook. Reads the made-up run (questions.json), counts the grades,
works out the exact binomial (Clopper-Pearson) ranges two ways (scipy's beta quantile and a bisection on the
binomial tail written out here), applies the acceptance rule and writes ref_values.json.

Usage: python acceptance_ref.py            (writes ref_values.json next to this file)
"""
import json
import math
from pathlib import Path

from scipy.stats import beta

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))

ANSWERED = ("right-page", "right-nopage", "partly", "wrong", "refused", "madeup")   # grades that fit a question with an answer
NOANSWER = ("refused", "madeup")                                                      # grades that fit a question without one
MIN_NON = 10                     # questions with no answer needed before a run may accept (default)


# ---------- the exact binomial range, two ways ----------
def cp_scipy(x, n, conf):
    a = 1 - conf
    lo = 0.0 if x == 0 else float(beta.ppf(a / 2, x, n - x + 1))
    hi = 1.0 if x == n else float(beta.ppf(1 - a / 2, x + 1, n - x))
    return lo, hi


def tail_ge(x, n, p):            # P(X >= x) for X ~ Binomial(n, p), summed term by term
    return sum(math.comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(x, n + 1))


def cp_bisect(x, n, conf):
    """The lower end is the p at which getting x or more right has chance a/2; the upper end mirrors it."""
    a = 1 - conf

    def solve(f):                 # f rises with p; find f(p) = 0 on (0, 1)
        lo, hi = 0.0, 1.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if f(mid) < 0:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    low = 0.0 if x == 0 else solve(lambda p: tail_ge(x, n, p) - a / 2)
    # upper end: the p at which getting x or fewer right has chance a/2 (that chance falls as p rises)
    high = 1.0 if x == n else solve(lambda p: a / 2 - (1 - tail_ge(x + 1, n, p)))
    return low, high


def cp(x, n, conf):
    s, b = cp_scipy(x, n, conf), cp_bisect(x, n, conf)
    assert abs(s[0] - b[0]) < 1e-9 and abs(s[1] - b[1]) < 1e-9, (x, n, conf, s, b)
    return s


# ---------- the run ----------
def summarise(rows, bar=0.80, conf=0.90, allowed=0, min_non=MIN_NON):
    """rows: list of (type code, grade code). Returns every number the page and the workbook show."""
    bad = [i for i, (t, g) in enumerate(rows) if not g or (t == "noanswer" and g not in NOANSWER) or (t != "noanswer" and g not in ANSWERED)]
    ok = [r for i, r in enumerate(rows) if i not in bad]
    ans = [g for t, g in ok if t != "noanswer"]
    non = [g for t, g in ok if t == "noanswer"]
    n, k = len(ans), len(non)
    rr = ans.count("right-page")
    out = {
        "rows": len(rows), "bad": len(bad), "n": n, "k": k, "rr": rr, "rn": ans.count("right-nopage"),
        "partly": ans.count("partly"), "wrong": ans.count("wrong"), "overrefused": ans.count("refused"),
        "refused": non.count("refused"), "madeup": non.count("madeup") + ans.count("madeup"),
        "madeup_ans": ans.count("madeup"),
    }
    out["a"] = rr / n if n else None
    out["a_any"] = (rr + out["rn"]) / n if n else None
    out["a_lo"], out["a_hi"] = cp(rr, n, conf) if n else (None, None)
    out["b"] = out["refused"] / k if k else None
    out["b_lo"], out["b_hi"] = cp(out["refused"], k, conf) if k else (None, None)
    per = {}
    for t in [x["code"] for x in DATA["types"]]:
        gs = [g for tt, g in ok if tt == t]
        good = gs.count("refused") if t == "noanswer" else gs.count("right-page")
        per[t] = [good, len(gs)]
    out["per_type"] = per
    # the rule
    if out["bad"]:
        v = "notready"
    elif out["madeup"] > allowed:
        v = "rejected-madeup"
    elif n and out["a_hi"] < bar:
        v = "rejected-share"
    elif not n:
        v = "notproven-empty"
    elif out["a_lo"] < bar:
        v = "notproven"                      # the bar is inside the range
    elif k < min_non:
        v = "notproven-noanswer"             # the share is proven, but too few questions tested what it does without an answer
    else:
        v = "accepted"
    out["verdict"] = v
    out["more"] = more_questions(rr, n, bar, conf) if v == "notproven" else None
    out["line"] = one_line(out)
    return out


def more_questions(rr, n, bar, conf, cap=500):
    """If the share held, how many more answerable questions until the lower end reaches the bar; -1 if never within cap."""
    p = rr / n
    if p <= bar:
        return -1
    for extra in range(1, cap + 1):
        m = n + extra
        x = math.floor(p * m + 1e-9)
        if cp(x, m, conf)[0] >= bar:
            return extra
    return -1


def one_line(o):
    s = f'{o["rr"]} of {o["n"]} answerable questions answered from the right page; refused {o["refused"]} of {o["k"]} questions that have no answer'
    if o["madeup"]:
        s += f'; made up {o["madeup"]}'
    return s + "."


def main():
    ex_rows = [(q["type"], q["grade"]) for q in DATA["questions"]]
    ex = summarise(ex_rows)
    # synthetic runs for the verdict checks
    def run(rr, rn, p, w, orf, ref, mu, mua=0):
        rows = [("fact", "right-page")] * rr + [("fact", "right-nopage")] * rn + [("table", "partly")] * p + \
               [("units", "wrong")] * w + [("figure", "refused")] * orf + [("units", "madeup")] * mua + \
               [("noanswer", "refused")] * ref + [("noanswer", "madeup")] * mu
        return rows
    cases = {
        "example": ex_rows,
        "strong": run(29, 1, 0, 0, 0, 10, 0),
        "weak": run(15, 3, 4, 3, 1, 4, 0),
        "middle": run(23, 1, 1, 1, 0, 4, 0),
        "no_noanswer": run(26, 0, 0, 0, 0, 0, 0),
        "few_noanswer": run(29, 1, 0, 0, 0, 4, 0),
        "madeup_answerable": run(29, 0, 0, 0, 0, 10, 0, 1),
        "bad_grade": [("noanswer", "right-page")] + run(25, 1, 0, 0, 0, 3, 0),
    }
    verdicts = {name: dict(summarise(rows), grades=[list(r) for r in rows]) for name, rows in cases.items()}
    # the minimum of questions with no answer, on the example with a 50 % bar and one made-up answer allowed
    verdicts_min = {str(m): summarise(ex_rows, 0.50, 0.90, 1, m)["verdict"] for m in (4, 10)}
    # the sample-size table in 00_ZAMYSEL.md and on the page
    grid = []
    for n in (20, 30, 50):
        for share in (0.7, 0.8, 0.9, 1.0):
            x = round(share * n)
            lo, hi = cp(x, n, 0.90)
            grid.append({"n": n, "x": x, "lo": lo, "hi": hi})
    need80 = {n: min(x for x in range(n + 1) if cp(x, n, 0.90)[0] >= 0.80) for n in (20, 26, 30, 50, 100)}
    # how often a system that is truly right 9 times in 10 passes (the whole range at or above 80 %), by questions with an answer
    pw = {}
    for n in range(10, 300):                 # scipy quantile only here: the bisection agreed above and is too slow for 300 sizes
        x = next((x for x in range(n + 1) if cp_scipy(x, n, 0.90)[0] >= 0.80), None)
        pw[n] = 0.0 if x is None else sum(math.comb(n, j) * 0.9 ** j * 0.1 ** (n - j) for j in range(x, n + 1))
    power90 = {n: pw[n] for n in (20, 26, 30, 40, 50, 80, 82, 90, 94, 100)}
    power_stays = next(n for n in range(10, 300) if all(pw[m] >= 0.8 for m in range(n, 300)))
    # range cases at the three confidence levels, for the page and the workbook to match
    ranges = [{"x": x, "n": n, "conf": c, "lo": cp(x, n, c)[0], "hi": cp(x, n, c)[1]}
              for (x, n) in ((20, 26), (3, 4), (4, 4), (0, 5), (1, 10), (25, 26), (45, 50), (87, 100), (199, 200))
              for c in (0.80, 0.90, 0.95)]
    out = {"example": ex, "cases": {k: {kk: vv for kk, vv in v.items()} for k, v in verdicts.items()},
           "grid": grid, "need80": need80, "power90": power90, "power_stays": power_stays, "min_non": MIN_NON, "verdicts_min": verdicts_min, "ranges": ranges}
    (HERE / "ref_values.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("example:", ex["line"], "|", ex["verdict"], f'| A {ex["a"]:.4f} [{ex["a_lo"]:.4f}, {ex["a_hi"]:.4f}]',
          f'| B {ex["b"]:.2f} [{ex["b_lo"]:.4f}, {ex["b_hi"]:.4f}]')
    for k, v in verdicts.items():
        print(f'{k:12} {v["verdict"]:20} more={v["more"]}  A={v["a"]}  lo={v["a_lo"]}')
    print("need for 80 %:", need80)
    print("power at p = 0.9:", {k: round(v, 3) for k, v in power90.items()}, "stays >= 0.8 from", power_stays)
    print("per type:", ex["per_type"])


if __name__ == "__main__":
    main()
