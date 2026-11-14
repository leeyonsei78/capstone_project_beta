"""
RQ1 baseline: how much does the tier-1 (automatic) path let through, and what can simple
deterministic rules catch? No LLM calls.

  python paper/eval/review/rules_baseline.py
  python paper/eval/review/rules_baseline.py --review-cost 15 --loss-fraction 1.0 --prevalence 0.03 --small-share 0.85

Reads cases/cases_*.json (from gen_cases.py). When a case has an `expert_label`, it overrides the
planted first-pass `label`.

IMPORTANT -- placeholders: review-cost, loss-fraction, prevalence and small-share are NOT
measured. They are explicit assumptions the domain expert must replace with company figures, and
the shape of the threshold curve depends on the synthetic claim-to-limit ratio distribution.
The report prints them so they cannot be mistaken for results.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
CASES = HERE / "cases"
RESULTS = HERE / "results"
THRESHOLDS = [0.05, 0.10, 0.20, 0.30, 0.50]


def load(name):
    return json.loads((CASES / name).read_text(encoding="utf-8"))


def lab(c):
    return c.get("expert_label") or c["label"]


def is_anom(c):
    return lab(c) == "investigate"


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


# ── Claims: threshold sweep ──────────────────────────────────────────────────

def auto_pays(c, thr):
    """Contract rule generalised to a threshold: pay at once if amount <= thr x coverage limit."""
    return c["claim"]["amount"] <= thr * c["policy"]["coverage_limit"]


def sweep_row(cases, thr):
    auto = [c for c in cases if auto_pays(c, thr)]
    anom = [c for c in cases if is_anom(c)]
    leaked = [c for c in auto if is_anom(c)]
    return {
        "threshold": thr, "n": len(cases), "n_auto": len(auto), "auto_rate": len(auto) / len(cases),
        "n_human": len(cases) - len(auto), "n_anomalous": len(anom), "n_leaked": len(leaked),
        "leakage_rate": len(leaked) / len(anom) if anom else 0.0,
        "leaked_amount": sum(c["claim"]["amount"] for c in leaked),
    }


def expected_cost(cases, thr, review_cost, loss_fraction, prevalence, small_share, n=1000):
    """Population-level cost per `n` claims, re-weighting the enriched evaluation set:
    strata = small/large (population share small_share), anomaly prevalence `prevalence`."""
    share = {"small": small_share, "large": 1 - small_share}

    def strat(pred, value):
        total = 0.0
        for g, s in share.items():
            sub = [c for c in cases if c["group"] == g and pred(c)]
            total += s * mean(value(c) for c in sub)
        return total

    p_a = strat(is_anom, lambda c: 1.0 if auto_pays(c, thr) else 0.0)
    p_c = strat(lambda c: not is_anom(c), lambda c: 1.0 if auto_pays(c, thr) else 0.0)
    leak_amt = strat(is_anom, lambda c: c["claim"]["amount"] if auto_pays(c, thr) else 0.0)
    auto_rate = prevalence * p_a + (1 - prevalence) * p_c
    human = n * (1 - auto_rate)
    return {
        "threshold": thr, "auto_rate": auto_rate, "human_cases": human,
        "leaked_cases": n * prevalence * p_a, "review_cost": human * review_cost,
        "leak_loss": n * prevalence * leak_amt * loss_fraction,
        "total_cost": human * review_cost + n * prevalence * leak_amt * loss_fraction,
    }


# ── Claims: deterministic detectors (need the rich evidence) ─────────────────

def detectors(c, db_max):
    cl, p, hist = c["claim"], c["policy"], c["history"]
    code, amt, limit = cl["treatment_code"], cl["amount"], p["coverage_limit"]
    flags = set()
    if code not in db_max or amt > db_max[code]:
        flags.add("R1_amount_cap")
    if any(h["code"] == code and h["days_ago"] <= 14 for h in hist):
        flags.add("R2_duplicate")
    sib = [h for h in hist if h["code"] == code and h["days_ago"] <= 7]
    if sib and amt + sum(h["amount"] for h in sib) > AUTO_PCT * limit:
        flags.add("R3_split")
    if p["policy_age_days"] <= 14 and amt >= 0.5 * db_max.get(code, 1e9):
        flags.add("R4_early")
    return flags


AUTO_PCT = 0.20
RULES = ["R1_amount_cap", "R2_duplicate", "R3_split", "R4_early"]


def detector_table(cases, db_max):
    by_type = {}
    for c in cases:
        by_type.setdefault(c["anomaly"] if is_anom(c) else "clean", []).append(c)
    rows = []
    for t, cs in sorted(by_type.items()):
        fl = [detectors(c, db_max) for c in cs]
        row = {"type": t, "n": len(cs)}
        for r in RULES:
            row[r] = sum(1 for f in fl if r in f) / len(cs)
        row["any_rule"] = sum(1 for f in fl if f) / len(cs)
        rows.append(row)
    return rows


# ── Applications ─────────────────────────────────────────────────────────────

def app_tier1(apps):
    auto = [a for a in apps if a["group"] == "auto"]
    anom = [a for a in auto if is_anom(a)]
    return {"n_auto_tier": len(auto), "n_anomalous": len(anom),
            "leakage_rate": len(anom) / len(auto) if auto else 0.0,
            "by_type": {t: sum(1 for a in anom if a["anomaly"] == t) for t in sorted({a["anomaly"] for a in anom})}}


def app_score_gate(apps, max_score):
    """Sensitivity: auto-approve only when the (advisory) contract risk score <= max_score and there is no
    prior rejection in the history; everything else goes to a human."""
    auto = [a for a in apps if a["group"] == "auto"]
    passed = [a for a in auto if a["applicant"]["risk_score"] <= max_score
              and not any(h["status"] == "rejected" for h in a["history"])]
    leaked = [a for a in passed if is_anom(a)]
    anom = [a for a in auto if is_anom(a)]
    clean_blocked = [a for a in auto if not is_anom(a) and a not in passed]
    return {"max_score": max_score, "auto_rate": len(passed) / len(auto) if auto else 0.0,
            "leakage_rate": len(leaked) / len(anom) if anom else 0.0,
            "clean_sent_to_human": len(clean_blocked)}


# ── Report ───────────────────────────────────────────────────────────────────

def pct(x):
    return f"{x * 100:.0f}%"


def build_report(claims, apps, args, db_max):
    out = ["# RQ1 rules baseline (no LLM)", "",
           "> **Assumptions, not results:** "
           f"review-cost=${args.review_cost}/case, loss-fraction={args.loss_fraction}, "
           f"prevalence={args.prevalence}, small-share={args.small_share}. Replace with company figures. "
           "Curve shapes depend on the synthetic claim-to-limit ratio distribution.", ""]
    n_anom = sum(1 for c in claims if is_anom(c))
    out += [f"Claims: {len(claims)} cases, {n_anom} anomalous (evaluation set is enriched; real prevalence is far lower).", "",
            "## Claims: threshold sweep (evaluation set)", "",
            "| threshold | auto-paid | auto rate | to human | anomalous auto-paid | leakage rate | leaked $ |",
            "|---|---|---|---|---|---|---|"]
    for thr in THRESHOLDS:
        r = sweep_row(claims, thr)
        out.append(f"| {pct(thr)} | {r['n_auto']} | {pct(r['auto_rate'])} | {r['n_human']} | "
                   f"{r['n_leaked']}/{r['n_anomalous']} | {pct(r['leakage_rate'])} | ${r['leaked_amount']:,.0f} |")
    out += ["", f"## Claims: expected cost per 1,000 claims (prevalence {args.prevalence}, small-share {args.small_share})", "",
            "| threshold | auto rate | human cases | leaked cases | review cost $ | leak loss $ | total $ |",
            "|---|---|---|---|---|---|---|"]
    for thr in THRESHOLDS:
        e = expected_cost(claims, thr, args.review_cost, args.loss_fraction, args.prevalence, args.small_share)
        out.append(f"| {pct(thr)} | {pct(e['auto_rate'])} | {e['human_cases']:.0f} | {e['leaked_cases']:.1f} | "
                   f"{e['review_cost']:,.0f} | {e['leak_loss']:,.0f} | {e['total_cost']:,.0f} |")
    out += ["", "## Claims: what simple deterministic rules catch (needs the rich evidence)", "",
            "Rows are anomaly types (`clean` = false-alarm rate). Text mismatch (A2) is deliberately not covered:",
            "free-text checks are the open question for the LLM.", "",
            "| type | n | " + " | ".join(RULES) + " | any rule |", "|---|---|" + "---|" * (len(RULES) + 1)]
    for row in detector_table(claims, db_max):
        out.append(f"| {row['type']} | {row['n']} | " + " | ".join(pct(row[r]) for r in RULES) +
                   f" | {pct(row['any_rule'])} |")
    t1 = app_tier1(apps)
    out += ["", "## Applications: tier-1 (rule auto-approve at exactly 2 coverages)", "",
            f"{t1['n_auto_tier']} auto-approved cases, {t1['n_anomalous']} anomalous -> leakage "
            f"{pct(t1['leakage_rate'])}; by type {t1['by_type']}. The contract's risk score is advisory only.", "",
            "Sensitivity: auto-approve only if risk score <= X and no prior rejection.", "",
            "| max score | auto rate | leakage rate | clean sent to human |", "|---|---|---|---|"]
    for ms in (0, 15, 25, 40, 100):
        g = app_score_gate(apps, ms)
        out.append(f"| {ms} | {pct(g['auto_rate'])} | {pct(g['leakage_rate'])} | {g['clean_sent_to_human']} |")
    return "\n".join(out) + "\n"


def main():
    sys.path.insert(0, str(HERE))
    from gen_cases import load_treatment_db
    ap = argparse.ArgumentParser()
    ap.add_argument("--review-cost", type=float, default=15.0)
    ap.add_argument("--loss-fraction", type=float, default=1.0)
    ap.add_argument("--prevalence", type=float, default=0.03)
    ap.add_argument("--small-share", type=float, default=0.85)
    args = ap.parse_args()
    claims, apps = load("cases_claims.json"), load("cases_apps.json")
    db_max = {c: v["max_usd"] for c, v in load_treatment_db().items()}
    text = build_report(claims, apps, args, db_max)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "rules_baseline.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
