"""
Clause-conditioned claim cases: each scenario (one set of facts) is turned into one case per insurer profile, so
the same facts have different correct answers where the profiles' terms differ.

  python paper/eval/review/gen_terms_cases.py [--seed 20261117] [--scenarios 60]

Output: cases/cases_terms.json  (180 cases = 60 scenarios x 3 profiles by default)
Each case: case_id TS-<scn>-<profile>, scenario id, profile, the facts, expected decision (지급/감액지급/부지급),
expected reason code, and whether the profiles disagree on this scenario.

Selection: a large random pool is drawn and 60% of the scenarios are taken from those where at least two profiles
give different answers (that is where reading the clause matters), 40% from scenarios where all agree (controls).
Prevalence of the three outcomes is therefore a design choice, not a real-world rate.
"""
import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import terms_profiles as TP  # noqa: E402

OUT = HERE / "cases"
SEED = 20261117
DAYS = (30, 50, 75, 110, 140, 200, 240, 300, 330, 420, 520, 640, 700, 780, 900, 1100, 1300)
KIND_W = {"normal": .55, "wisdom": .1, "impacted": .1, "ortho": .1, "prep": .15}


def draw_day(rng, lo=None, hi=None):
    for _ in range(200):
        d = rng.choice(DAYS) + rng.randint(-8, 8)
        if d >= 1 and not TP.near_threshold(d) and (lo is None or d >= lo) and (hi is None or d <= hi):
            return d
    raise RuntimeError("no day found")


def draw_scenario(rng):
    cov = rng.choice(["crown", "implant", "implant", "bridge"])
    cause = rng.choices(["disease", "accident"], [.8, .2])[0]
    ev = draw_day(rng)
    s = {"coverage": cov, "cause": cause, "event_day": ev, "extraction_day": None,
         "extraction_kind": None, "count_this_year": 0}
    if cov in TP.PROSTHETIC:
        # extraction precedes the prosthetic treatment by 2 weeks to 5 months, never on a threshold margin
        for _ in range(200):
            ex = max(1, ev - rng.randint(14, 150))
            if not TP.near_threshold(ex):
                break
        s["extraction_day"] = ex
        s["extraction_kind"] = rng.choices(list(KIND_W), list(KIND_W.values()))[0]
        s["count_this_year"] = rng.choices([0, 1, 2, 3, 4], [.3, .25, .2, .15, .1])[0]
    return s


def outcomes(s):
    return {k: TP.decide(p, s) for k, p in TP.PROFILES.items()}


def generate(seed=SEED, n=60):
    rng = random.Random(seed)
    pool = []
    for _ in range(3000):
        s = draw_scenario(rng)
        o = outcomes(s)
        pool.append((s, o, len({r for r, _ in o.values()}) > 1))
    dis = [x for x in pool if x[2]]
    agree = [x for x in pool if not x[2]]
    rng.shuffle(dis)
    rng.shuffle(agree)
    n_dis = round(n * .6)
    chosen = dis[:n_dis] + agree[:n - n_dis]
    rng.shuffle(chosen)
    cases = []
    for i, (s, o, disagree) in enumerate(chosen, 1):
        for k in TP.PROFILES:
            ratio, reason = o[k]
            cases.append({
                "case_id": f"TS-{i:03d}-{k}", "type": "terms_claim", "scenario": f"TS-{i:03d}", "profile": k,
                "facts": dict(s), "profiles_disagree": disagree,
                "expected": TP.DECISION_OF_RATIO[ratio], "expected_ratio": ratio, "expected_reason": reason,
                "all_profiles_expected": {kk: TP.DECISION_OF_RATIO[v[0]] for kk, v in o.items()},
            })
    return cases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--scenarios", type=int, default=60)
    a = ap.parse_args()
    cases = generate(a.seed, a.scenarios)
    OUT.mkdir(exist_ok=True)
    (OUT / "cases_terms.json").write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"seed={a.seed} cases={len(cases)} -> {OUT / 'cases_terms.json'}")
    print("expected:", dict(Counter(c["expected"] for c in cases)))
    print("by profile:", {k: dict(Counter(c["expected"] for c in cases if c["profile"] == k)) for k in TP.PROFILES})
    print("reasons:", dict(Counter(c["expected_reason"] for c in cases)))
    print("coverage:", dict(Counter(c["facts"]["coverage"] for c in cases if c["profile"] == "A")))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
