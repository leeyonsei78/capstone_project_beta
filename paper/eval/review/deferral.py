"""
Deferral-policy frontier (improvement 1): which cases are paid or approved automatically and which go to
a human, and how much anomalous volume slips through at a given human workload.

A *policy* maps a case row to True (automatic) or False (send to a human). Compared families:
  amount     auto iff amount <= threshold x coverage limit        (today's rule at 20%)
  rules      auto iff no deterministic rule fires                  (R1-R4, rules_baseline.py)
  llm_gate   auto iff advisor says clean with confidence >= tau and no rule fires
  hybrid     amount rule AND llm_gate                              (the amount rule stays the outer fence)

Framing follows cost-sensitive learning-to-defer under a workload constraint (Alves et al., TMLR 2024):
the frontier is the best leakage achievable for each human workload.

Rows are dicts: case_id, group, anomalous (bool), amount, limit, verdict, confidence (0-100),
rule_flags (list). One row per (case, repetition); bootstraps resample whole cases.
"""
import random

THRESHOLDS = [0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 0.75, 1.00]
TAUS = [0, 50, 60, 70, 80, 90, 95, 99, 101]     # 101 = never auto (all to human)


# ── Policies ─────────────────────────────────────────────────────────────────

def amount_policy(thr):
    return lambda r: r["amount"] <= thr * r["limit"]


def rules_policy():
    return lambda r: not r.get("rule_flags")


def llm_gate_policy(tau, use_rules=True):
    def decide(r):
        if r.get("verdict") != "clean":
            return False
        conf = r.get("confidence")
        if conf is None or conf < tau:
            return False
        return not (use_rules and r.get("rule_flags"))
    return decide


def hybrid_policy(thr, tau, use_rules=True):
    a, g = amount_policy(thr), llm_gate_policy(tau, use_rules)
    return lambda r: a(r) and g(r)


# ── Metrics ──────────────────────────────────────────────────────────────────

def _mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def metrics(rows, decide, prevalence=None, shares=None):
    """Evaluation-set metrics; with `prevalence` and `shares` (group -> population share) also a
    population-adjusted human workload (the evaluation set is enriched with anomalies)."""
    auto = [r for r in rows if decide(r)]
    anom = [r for r in rows if r["anomalous"]]
    clean = [r for r in rows if not r["anomalous"]]
    leaked = [r for r in auto if r["anomalous"]]
    out = {
        "n": len(rows), "auto_rate": len(auto) / len(rows) if rows else 0.0,
        "workload": 1 - len(auto) / len(rows) if rows else 0.0,
        "leakage_rate": len(leaked) / len(anom) if anom else 0.0,
        # dollars that left automatically per repetition (rows hold one entry per case x repetition)
        "leaked_amount": sum(r.get("amount", 0) for r in leaked) / max(1.0, len(rows) / max(1, len({r["case_id"] for r in rows}))),
        "false_hold_rate": sum(1 for r in clean if not decide(r)) / len(clean) if clean else 0.0,
    }
    if prevalence is not None and shares:
        def p_auto(subset_pred):
            tot = 0.0
            for g, w in shares.items():
                sub = [r for r in rows if r["group"] == g and subset_pred(r)]
                tot += w * _mean(1.0 if decide(r) else 0.0 for r in sub)
            return tot
        p_a, p_c = p_auto(lambda r: r["anomalous"]), p_auto(lambda r: not r["anomalous"])
        out["workload_population"] = 1 - (prevalence * p_a + (1 - prevalence) * p_c)
    return out


def frontier(rows, family, prevalence=None, shares=None):
    """family: list of (param, decide) -> list of metric dicts including the param."""
    pts = []
    for param, decide in family:
        m = metrics(rows, decide, prevalence, shares)
        m["param"] = param
        pts.append(m)
    return pts


def amount_family():
    return [(t, amount_policy(t)) for t in THRESHOLDS]


def amount_family_fine():
    """1% steps. Use this (not the coarse grid) as the baseline when comparing at equal workload:
    a coarse grid forces the baseline onto a lower-workload, higher-leakage point and so overstates
    the improvement of any competing policy."""
    return [(t / 100, amount_policy(t / 100)) for t in range(1, 101)]


def llm_gate_family(use_rules=True):
    return [(t, llm_gate_policy(t, use_rules)) for t in TAUS]


def hybrid_family(thr=0.20, use_rules=True):
    return [(t, hybrid_policy(thr, t, use_rules)) for t in TAUS]


def pareto(points, workload_key="workload"):
    """Non-dominated points: strictly lower leakage than every point with lower or equal workload."""
    best, keep = float("inf"), []
    for p in sorted(points, key=lambda p: (p[workload_key], p["leakage_rate"])):
        if p["leakage_rate"] < best:
            keep.append(p)
            best = p["leakage_rate"]
    return keep


def leakage_at_workload(points, workload, workload_key="workload"):
    """Lowest leakage among points whose workload does not exceed `workload` (no interpolation)."""
    c = [p["leakage_rate"] for p in points if p[workload_key] <= workload + 1e-12]
    return min(c) if c else None


def paired_bootstrap(rows, decide_a, decide_b, metric="leakage_rate", n=1000, seed=0):
    """CI for metric(a) - metric(b). Resamples whole cases within each group (repetitions of a case
    stay together), so repeated runs do not masquerade as independent evidence."""
    rng = random.Random(seed)
    by_group = {}
    for r in rows:
        by_group.setdefault(r["group"], {}).setdefault(r["case_id"], []).append(r)
    diffs = []
    for _ in range(n):
        sample = []
        for cases in by_group.values():
            ids = list(cases)
            for _ in ids:
                sample.extend(cases[ids[rng.randrange(len(ids))]])
        diffs.append(metrics(sample, decide_a)[metric] - metrics(sample, decide_b)[metric])
    diffs.sort()
    return {"mean": sum(diffs) / n, "lo": diffs[int(0.025 * n)], "hi": diffs[int(0.975 * n) - 1], "n_boot": n}
