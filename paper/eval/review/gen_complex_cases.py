"""
Complexity layer for the dental review experiment (adds cases; never touches the 240 base cases).

  python paper/eval/review/gen_complex_cases.py [--seed 20261116]

Why a separate file: gen_cases.py output (and the blind sheets the expert may already be filling in) must stay
byte-identical, so the new cases get their own generator, their own seed and their own files:
  cases/cases_claims_complex.json      full cases, group="complex" (so no existing analysis picks them up)
  cases/review_claims_complex_blind.csv + blind_key_complex.json   neutral ids, planted label hidden

Complexity levels (claims above the 20% auto-pay line only, i.e. what a human reviewer would see):
  L1  base set (gen_cases.py): single-claim consistency (code vs description vs amount, short history)
  L2  tooth-level history reasoning. The same code on a *different* tooth is legitimate, on the *same* tooth it
      is a duplicate; a crown cannot follow an extraction of that tooth; a second implant on the same site within
      a year needs an explanation. The count-only summary used in production hides the tooth, so these cases
      cannot be separated under C2 -- only the detailed history (C3) can.
  L3  same-family upcoding: the description matches a cheaper sibling code (1-surface filling vs 3-surface, 1-3
      teeth periodontal vs wide, simple extraction vs bony impaction) while the billed code is the expensive one.
      The amount stays inside the billed code's own ceiling, so no amount rule fires; it needs knowledge of what
      the code means and a careful reading of the text. The prompt only gives the code number, not its name.

rule_detectable (what a *structured* rule engine could do with the same data):
  tooth_rule  a rule over (tooth, code, date) catches it -> the LLM adds little beyond a well-built rule
  text_only   needs code semantics + free text -> the part where an LLM could add value over rules
  none        legitimate case

Planted labels are first-pass only; the expert may override (e.g. a second implant on the same site can be a
legitimate redo after a failed first one). Synthetic data: amounts, teeth and wording are invented, and the
dental code table is the CDT-style one in mock-provider.js, not the Korean fee schedule.
"""
import argparse
import csv
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import gen_cases as G  # noqa: E402

OUT = G.OUT
SEED = 20261116

PLAN = {          # kind -> count
    "X1clean": 10, "X1anom": 10, "X2clean": 10, "X2anomCrown": 10, "X2anomImplant": 10,   # L2 (50)
    "X3clean": 12, "X3anom": 12,                                                          # L3 (24)
}
LEVEL = {"X1clean": "L2", "X1anom": "L2", "X2clean": "L2", "X2anomCrown": "L2", "X2anomImplant": "L2",
         "X3clean": "L3", "X3anom": "L3"}
ANOMALY = {"X1anom": "X1", "X2anomCrown": "X2a", "X2anomImplant": "X2b", "X3anom": "X3"}
RULE = {"X1anom": "tooth_rule", "X2anomCrown": "tooth_rule", "X2anomImplant": "tooth_rule", "X3anom": "text_only"}

FAMILIES = [("D2140", "D2160"), ("D4341", "D4342"), ("D7140", "D7240")]   # (cheaper sibling, expensive sibling)
UPPER = [11, 12, 13, 14, 15, 16, 17, 21, 22, 23, 24, 25, 26, 27]
LOWER = [31, 32, 33, 34, 35, 36, 37, 41, 42, 43, 44, 45, 46, 47]


def tooth_label(t):
    jaw = "위" if t // 10 in (1, 2) else "아래"
    side = "오른쪽" if t // 10 in (1, 4) else "왼쪽"
    kind = {1: "앞니", 2: "앞니", 3: "송곳니", 4: "작은어금니", 5: "작은어금니", 6: "큰어금니", 7: "큰어금니"}[t % 10]
    return f"{jaw} {side} {kind}({t}번)"


def pick_teeth(rng, n=2, molar=False):
    pool = [t for t in UPPER + LOWER if (t % 10 >= 4 if molar else True)]
    return rng.sample(pool, n)


def rich_evidence(history, db):
    if not history:
        return "과거 청구 없음."
    lines = [f"- {h['days_ago']}일 전 | {h['code']} {db[h['code']]['name']} | {tooth_label(h['tooth'])} | "
             f"${h['amount']:.2f} | {h['status']}" for h in sorted(history, key=lambda x: x["days_ago"])]
    return "과거 청구 상세:\n" + "\n".join(lines)


def describe_tooth(code, tooth, rng, text=None):
    return f"{tooth_label(tooth)} - " + (text or G.describe(code, rng))


def make(kind, idx, rng, db):
    policy_age = rng.randint(150, 900)
    hist, tooth, code, desc_text = [], None, None, None
    fam = None
    label = "investigate" if kind in ANOMALY else "approve"

    if kind in ("X1clean", "X1anom"):
        code = rng.choice(["D2150", "D2160", "D3330", "D2740", "D2750"])
        t_now, t_other = pick_teeth(rng, 2, molar=True)
        tooth = t_now
        amount = round(db[code]["max_usd"] * rng.uniform(.7, .95))
        hist = [{"code": code, "amount": round(amount * rng.uniform(.95, 1.05)), "status": "Paid",
                 "days_ago": rng.randint(1, 14), "tooth": t_other if kind == "X1clean" else t_now}]
    elif kind == "X2clean":                   # implant placed where the tooth was extracted earlier
        code = "D6010"
        tooth = rng.choice([t for t in UPPER + LOWER if t % 10 >= 4])
        amount = round(db[code]["max_usd"] * rng.uniform(.75, .95))
        hist = [{"code": rng.choice(["D7140", "D7210"]), "amount": rng.randint(100, 280), "status": "Paid",
                 "days_ago": rng.randint(70, 300), "tooth": tooth}]
    elif kind == "X2anomCrown":               # crown on a tooth that was extracted
        code = rng.choice(["D2740", "D2750"])
        tooth = rng.choice([t for t in UPPER + LOWER if t % 10 >= 4])
        amount = round(db[code]["max_usd"] * rng.uniform(.7, .95))
        hist = [{"code": rng.choice(["D7140", "D7210", "D7240"]), "amount": rng.randint(100, 400), "status": "Paid",
                 "days_ago": rng.randint(30, 200), "tooth": tooth}]
    elif kind == "X2anomImplant":             # second implant on the same site within a year
        code = "D6010"
        tooth = rng.choice([t for t in UPPER + LOWER if t % 10 >= 4])
        amount = round(db[code]["max_usd"] * rng.uniform(.75, .95))
        hist = [{"code": "D6010", "amount": round(amount * rng.uniform(.9, 1.05)), "status": "Paid",
                 "days_ago": rng.randint(90, 330), "tooth": tooth}]
    elif kind in ("X3clean", "X3anom"):
        fam = rng.choice(FAMILIES)
        cheap, dear = fam
        code = dear
        tooth = rng.choice([t for t in UPPER + LOWER if t % 10 >= 4])
        amount = round(db[dear]["max_usd"] * rng.uniform(.75, .95))
        desc_text = G.describe(cheap if kind == "X3anom" else dear, rng)
        # an unrelated, ordinary history on other teeth so the history does not give the answer away
        other = rng.choice([c for c in db if c not in fam])
        hist = [{"code": other, "amount": round(db[other]["max_usd"] * rng.uniform(.3, .8)), "status": "Paid",
                 "days_ago": rng.randint(40, min(500, policy_age - 1)),
                 "tooth": rng.choice([t for t in UPPER + LOWER if t != tooth])}] if rng.random() < .6 else []
    else:
        raise ValueError(kind)

    if hist:       # the policy must already have existed when the earlier claim was paid
        policy_age = max(policy_age, max(h["days_ago"] for h in hist) + rng.randint(20, 120))
    assert all(h["days_ago"] < policy_age for h in hist), (kind, policy_age, hist)
    lo, hi = G.ratio_band("large")
    limit = G.pick_limit(amount, lo, hi, rng)
    ratio = amount / limit
    assert ratio > G.AUTO_PCT, (kind, amount, limit)
    prem = max(10, round(limit / rng.uniform(18, 32)))
    policies_n = rng.choice([1, 1, 1, 2])
    paid_hist = sum(h["amount"] for h in hist if h["status"] == "Paid")
    desc = describe_tooth(code, tooth, rng, desc_text)
    return {
        "case_id": f"CX-{LEVEL[kind]}-{idx:03d}", "type": "claim", "group": "complex", "complexity": LEVEL[kind],
        "kind": kind, "label": label, "anomaly": ANOMALY.get(kind, "none"), "injection": False,
        "expert_label": None, "rule_detectable": RULE.get(kind, "none"),
        "policy": {"coverage_limit": limit, "monthly_premium": prem, "policy_age_days": policy_age,
                   "total_paid": prem * max(1, policy_age // 30), "total_claimed": paid_hist, "policies": policies_n},
        "claim": {"treatment_code": code, "treatment_name": db[code]["name"], "amount": amount,
                  "ratio_of_limit": round(ratio, 4), "description": desc, "tooth": tooth},
        "history": hist,
        "evidence_current": G.claim_evidence(hist, policies_n),     # count-only summary: tooth is invisible
        "evidence_rich": rich_evidence(hist, db),
    }


def generate(seed=SEED):
    rng = random.Random(seed)
    db = G.load_treatment_db()
    cases, i = [], 0
    for kind, n in PLAN.items():
        for _ in range(n):
            i += 1
            cases.append(make(kind, i, rng, db))
    return cases


def write(cases, seed=SEED):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cases_claims_complex.json").write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    rng = random.Random(seed + 1)
    order = list(range(len(cases)))
    rng.shuffle(order)
    key, rows = {}, []
    for n, i in enumerate(order, 1):
        c = cases[i]
        bid = f"RX{n:03d}"
        key[bid] = c["case_id"]
        cl, p = c["claim"], c["policy"]
        rows.append([bid, "대액(수동심사 구간)", f"{cl['treatment_code']} {cl['treatment_name']}", f"${cl['amount']}",
                     f"${p['coverage_limit']}", f"{cl['ratio_of_limit'] * 100:.1f}%", f"{p['policy_age_days']}일",
                     cl["description"], c["evidence_rich"].replace("\n", " / "), "", "", "", ""])
    with open(OUT / "review_claims_complex_blind.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["blind_id", "구간", "치료", "청구액", "보장한도", "한도대비", "가입경과", "치료설명", "과거청구",
                    "전문가라벨(approve/investigate)", "전문가메모", "현실성(1-5)", G.TIME_COL])
        w.writerows(rows)
    (OUT / "blind_key_complex.json").write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()
    cases = generate(args.seed)
    write(cases, args.seed)
    from collections import Counter
    print(f"seed={args.seed} complex claims={len(cases)} -> {OUT}")
    print(dict(Counter((c["complexity"], c["kind"]) for c in cases)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
