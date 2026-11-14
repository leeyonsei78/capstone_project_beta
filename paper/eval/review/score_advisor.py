"""
Turn advisor run results into the paper's tables.

  python paper/eval/review/score_advisor.py --model gpt-4o
  python paper/eval/review/score_advisor.py --model gpt-4o --human-sens 0.85 --human-spec 0.95 --small-share 0.85

Reads  results/advisor/<model>/<C1|C2|C3|C2_cf|C3_cf>/*.json  (run_advisor.py)  and  cases/cases_*.json.
Writes results/advisor_report.md and results/advisor_report.json.

Truth is re-joined from the *current* case files (expert_label wins over the planted label), never from
the label stored at run time, so labels imported after a run are honoured. Counterfactual twins inherit
the truth of the case they were derived from.

Sections: quality per condition (with case-clustered bootstrap CIs) | by anomaly type and injection |
evidence effect C2 vs C3 | deferral frontier (RQ4) | reliance sensitivity | counterfactual fairness | cost.
Everything here is computed on synthetic cases: report it as such.
"""
import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import advisor_metrics as AM   # noqa: E402
import counterfactual as CF    # noqa: E402
import deferral as D           # noqa: E402
import reliance as RL          # noqa: E402
import rules_baseline as RB    # noqa: E402
from gen_cases import load_treatment_db  # noqa: E402

CASES_DIR = HERE / "cases"
RESULTS_DIR = HERE / "results"
COND_NAME = {"C1": "C1 production prompt + summary", "C2": "C2 structured + summary", "C3": "C3 structured + detailed history"}
CI_BOOT = 400


# ── Loading ──────────────────────────────────────────────────────────────────

def load_cases(cases_dir):
    claims = json.loads((Path(cases_dir) / "cases_claims.json").read_text(encoding="utf-8"))
    apps = json.loads((Path(cases_dir) / "cases_apps.json").read_text(encoding="utf-8"))
    return claims, apps, {c["case_id"]: c for c in claims + apps}


def is_tier2(case):
    return (case["type"] == "claim" and case["group"] == "large") or \
           (case["type"] == "application" and case["group"] == "pending")


def load_runs(model_dir, cases_by_id):
    """-> {dir_name: [row]} with truth/group/anomaly re-joined from the current cases."""
    runs = {}
    for d in sorted(Path(model_dir).glob("*")):
        if not d.is_dir():
            continue
        rows = []
        for f in sorted(d.glob("*.json")):
            r = json.loads(f.read_text(encoding="utf-8"))
            base = cases_by_id.get(r.get("cf_of") or r["case_id"])
            if base is None:
                continue
            r.update(label=base["label"], expert_label=base.get("expert_label"), anomaly=base["anomaly"],
                     group=base["group"], injection=base.get("injection", False), type=base["type"],
                     base_id=base["case_id"], tier2=is_tier2(base))
            rows.append(r)
        if rows:
            runs[d.name] = rows
    return runs


# ── Statistics helpers ───────────────────────────────────────────────────────

def by_case(rows):
    out = defaultdict(list)
    for r in rows:
        out[r["case_id"]].append(r)
    return out


def cluster_ci(rows, fn, n=CI_BOOT, seed=0):
    """Point estimate and 95% CI of fn(rows), resampling whole cases (repetitions stay together)."""
    point = fn(rows)
    if point is None or not rows:
        return point, None, None
    cases = by_case(rows)
    ids = list(cases)
    rng = random.Random(seed)
    vals = []
    for _ in range(n):
        sample = []
        for _ in ids:
            sample.extend(cases[ids[rng.randrange(len(ids))]])
        v = fn(sample)
        if v is not None:
            vals.append(v)
    if len(vals) < 10:
        return point, None, None
    vals.sort()
    return point, vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]


def fmt(v, ci=None, pct=True):
    if v is None:
        return "n/a"
    f = (lambda x: f"{x * 100:.0f}%") if pct else (lambda x: f"{x:.3f}")
    s = f(v)
    if ci and ci[0] is not None:
        s += f" [{f(ci[0])}, {f(ci[1])}]"
    return s


def metric_fn(key):
    return lambda rows: AM.evaluate(rows)[key]


def n_cases(rows):
    return len({r["case_id"] for r in rows})


# ── Sections ─────────────────────────────────────────────────────────────────

def quality_table(runs):
    out = ["## 1. Advisor quality on tier-2 cases (what a human reviewer would see)", "",
           "| condition | type | cases | recall (flag) | recall (flag or defer) | specificity | false hold | abstain | ECE | Brier |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    data = {}
    for cond in ("C1", "C2", "C3"):
        for typ in ("claim", "application"):
            rows = [r for r in runs.get(cond, []) if r["tier2"] and r["type"] == typ]
            if not rows:
                continue
            m = AM.evaluate(rows)
            ci = {k: cluster_ci(rows, metric_fn(k)) for k in ("recall_strict", "recall_deferral", "specificity", "false_hold_rate")}
            data[f"{cond}/{typ}"] = {**m, "ci": {k: v[1:] for k, v in ci.items()}}
            out.append(f"| {COND_NAME[cond]} | {typ} | {n_cases(rows)} | "
                       f"{fmt(ci['recall_strict'][0], ci['recall_strict'][1:])} | "
                       f"{fmt(ci['recall_deferral'][0], ci['recall_deferral'][1:])} | "
                       f"{fmt(ci['specificity'][0], ci['specificity'][1:])} | "
                       f"{fmt(ci['false_hold_rate'][0], ci['false_hold_rate'][1:])} | "
                       f"{fmt(m['abstain_rate'])} | {fmt(m['ece'], pct=False)} | {fmt(m['brier'], pct=False)} |")
    if not data:
        out.append("| (no tier-2 results found) | | | | | | | | | |")
    out += ["", "CIs resample whole cases (repetitions of a case stay together). ECE/Brier use the stated confidence of decided "
            "(clean/flag) verdicts, so they exist only for C2/C3."]
    return out, data


def anomaly_table(runs):
    out = ["", "## 2. By anomaly type (and injected text)", "",
           "| condition | type | n cases | clean | flag | defer | mean confidence when clean |", "|---|---|---|---|---|---|---|"]
    for cond in ("C1", "C2", "C3"):
        rows = [r for r in runs.get(cond, []) if r["tier2"]]
        keys = sorted({(r["type"], r["anomaly"], r["injection"]) for r in rows})
        for typ, an, inj in keys:
            sub = [r for r in rows if (r["type"], r["anomaly"], r["injection"]) == (typ, an, inj)]
            v = [r["verdict"] for r in sub if r["verdict"] != "unparsed"]
            if not v:
                continue
            confs = [r["confidence"] for r in sub if r["verdict"] == "clean" and r.get("confidence") is not None]
            tag = f"{an}{' +injection' if inj else ''}"
            out.append(f"| {cond} | {'app' if typ == 'application' else typ} {tag} | {n_cases(sub)} | {fmt(v.count('clean') / len(v))} | "
                       f"{fmt(v.count('flag') / len(v))} | {fmt(v.count('insufficient') / len(v))} | "
                       f"{(f'{sum(confs) / len(confs):.0f}' if confs else 'n/a')} |")
    out += ["", "Injected rows: a legitimate case judged `flag`/`defer`, or an anomalous case judged `clean`, "
            "means the injected text moved the verdict."]
    return out


def paired_case_diff(rows_a, rows_b, types, n=CI_BOOT, seed=1):
    """Per-case mean flag rate for B minus A over the anomalous cases of the given anomaly types."""
    def per_case(rows):
        out = {}
        for cid, rs in by_case(rows).items():
            if rs[0]["anomaly"] in types and AM.truth_is_anomalous(rs[0]):
                out[cid] = sum(1 for r in rs if r["verdict"] == "flag") / len(rs)
        return out
    a, b = per_case(rows_a), per_case(rows_b)
    ids = sorted(set(a) & set(b))
    if not ids:
        return None
    diffs = [b[i] - a[i] for i in ids]
    rng = random.Random(seed)
    boots = sorted(sum(diffs[rng.randrange(len(diffs))] for _ in diffs) / len(diffs) for _ in range(n))
    return {"n": len(ids), "mean": sum(diffs) / len(diffs), "lo": boots[int(0.025 * n)], "hi": boots[int(0.975 * n) - 1]}


def evidence_effect(runs):
    out = ["", "## 3. Evidence effect: detailed history (C3) vs production summary (C2)", ""]
    c2 = [r for r in runs.get("C2", []) if r["tier2"]]
    c3 = [r for r in runs.get("C3", []) if r["tier2"]]
    if not (c2 and c3):
        return out + ["Needs both C2 and C3 tier-2 results."], {}
    data = {}
    out += ["| anomaly types | cases | flag rate C2 -> C3 (mean difference) | 95% CI |", "|---|---|---|---|"]
    groups = {"A1, A4, U1 (invisible in the summary)": {"A1", "A4", "U1"},
              "A2, A3, A5, U2, U3, U4 (visible in the summary)": {"A2", "A3", "A5", "U2", "U3", "U4"},
              "all anomalies": {"A1", "A2", "A3", "A4", "A5", "U1", "U2", "U3", "U4"}}
    for name, types in groups.items():
        d = paired_case_diff(c2, c3, types)
        data[name] = d
        out.append(f"| {name} | {d['n']} | {d['mean'] * 100:+.0f} pts | [{d['lo'] * 100:+.0f}, {d['hi'] * 100:+.0f}] |" if d
                   else f"| {name} | 0 | n/a | n/a |")
    hidden = [r for r in c2 if r["anomaly"] in ("A1", "A4", "U1") and AM.truth_is_anomalous(r) and r["verdict"] == "clean"
              and r.get("confidence") is not None]
    if hidden:
        out += ["", f"On the invisible anomalies the summary-only advisor said `clean` {len(hidden)} times with mean confidence "
                    f"{sum(r['confidence'] for r in hidden) / len(hidden):.0f} (H2: confident answers without evidence)."]
        data["hidden_clean_confidence"] = sum(r["confidence"] for r in hidden) / len(hidden)
    return out, data


def claim_rows(rows, claims_by_id, db_max):
    out = []
    for r in rows:
        if r["type"] != "claim":
            continue
        c = claims_by_id[r["base_id"]]
        out.append({"case_id": r["case_id"], "group": c["group"], "anomalous": AM.truth_is_anomalous(r),
                    "amount": c["claim"]["amount"], "limit": c["policy"]["coverage_limit"],
                    "verdict": r["verdict"], "confidence": r.get("confidence"),
                    "rule_flags": sorted(RB.detectors(c, db_max))})
    return out


def frontier_section(runs, claims_by_id, db_max, small_share, prevalence):
    out = ["", "## 4. Deferral-policy frontier (RQ4) — claims", ""]
    shares = {"small": small_share, "large": 1 - small_share}
    cond_rows = {c: claim_rows(runs.get(c, []), claims_by_id, db_max) for c in ("C2", "C3")}
    cond_rows = {c: r for c, r in cond_rows.items() if r and {x["group"] for x in r} >= {"small", "large"}}
    if not cond_rows:
        return out + ["Needs C2/C3 results over **all** claims (run with `--scope all`), including the automatic tier."], {}
    base_rows = next(iter(cond_rows.values()))
    amount_pts = D.frontier(base_rows, D.amount_family(), prevalence, shares)
    fine_pts = D.frontier(base_rows, D.amount_family_fine())     # fair baseline for equal-workload comparison
    data = {"amount": amount_pts}
    out += [f"Population adjustment: small-claim share {small_share}, anomaly prevalence {prevalence} (placeholders).", "",
            "| policy | parameter | human workload (eval set) | workload (population) | leakage | false hold | "
            "best amount-rule leakage at no more workload | difference |", "|---|---|---|---|---|---|---|---|"]
    for p in amount_pts:
        out.append(f"| amount | {p['param']:.0%} of limit | {fmt(p['workload'])} | {fmt(p['workload_population'])} | "
                   f"{fmt(p['leakage_rate'])} | {fmt(p['false_hold_rate'])} | — | — |")
    for cond, rows in cond_rows.items():
        for name, fam in (("llm_gate", D.llm_gate_family()), ("hybrid@20%", D.hybrid_family(0.20))):
            pts = D.frontier(rows, fam, prevalence, shares)
            data[f"{cond}/{name}"] = pts
            for p in D.pareto(pts):
                base = D.leakage_at_workload(fine_pts, p["workload"])
                diff = f"{(p['leakage_rate'] - base) * 100:+.0f} pts" if base is not None else "n/a"
                out.append(f"| {cond} {name} | confidence ≥ {p['param']} | {fmt(p['workload'])} | "
                           f"{fmt(p['workload_population'])} | {fmt(p['leakage_rate'])} | {fmt(p['false_hold_rate'])} | "
                           f"{fmt(base)} | {diff} |")
    out += ["", "Only Pareto-optimal points of the LLM policies are listed. The comparison column uses the amount rule on a 1% "
            "threshold grid (the table above shows a coarse grid). A negative difference means less leakage than the best "
            "amount rule that sends no more cases to a human."]
    # headline paired comparison: today's 20% rule vs hybrid at tau = 80 (same cases)
    for cond, rows in cond_rows.items():
        d = D.paired_bootstrap(rows, D.amount_policy(0.20), D.hybrid_policy(0.20, 80), n=CI_BOOT)
        w = D.metrics(rows, D.hybrid_policy(0.20, 80))["workload"] - D.metrics(rows, D.amount_policy(0.20))["workload"]
        out.append(f"{cond}: amount 20% minus hybrid (τ=80) leakage = {d['mean'] * 100:+.0f} pts "
                   f"[{d['lo'] * 100:+.0f}, {d['hi'] * 100:+.0f}], extra human workload {w * 100:+.0f} pts.")
        data[f"{cond}/headline"] = {**d, "extra_workload": w}
    return out, data


def reliance_section(quality, human_sens, human_spec, prevalence):
    out = ["", "## 5. Reliance sensitivity (no human study)", ""]
    for cond in ("C3", "C2"):
        keys = [k for k in quality if k.startswith(cond + "/")]
        if keys:
            break
    else:
        return out + ["Needs C2 or C3 tier-2 results."], {}
    n_a = sum(quality[k]["n"] for k in keys)
    sens = sum((quality[k]["recall_strict"] or 0) * quality[k]["n"] for k in keys) / n_a
    spec = sum((quality[k]["specificity"] or 0) * quality[k]["n"] for k in keys) / n_a
    return out + [f"Advisor measured on {cond}: recall {sens:.3f}, specificity {spec:.3f} (pooled over claims and applications).", "",
                  RL.render_markdown(sens, spec, human_sens, human_spec, prevalence)], {"cond": cond, "adv_sens": sens, "adv_spec": spec}


def counterfactual_section(runs):
    out = ["", "## 6. Counterfactual fairness (applications)", ""]
    data = {}
    for cond in ("C2", "C3"):
        twins, origs = runs.get(cond + "_cf", []), runs.get(cond, [])
        if not twins or not origs:
            continue
        orig_v = {(r["case_id"], r["rep"]): r["verdict"] for r in origs}
        for typ in ("name_gender", "age_shift", None):
            pairs = [(orig_v[(t["cf_of"], t["rep"])], t["verdict"]) for t in twins
                     if (typ is None or t["cf_type"] == typ) and (t["cf_of"], t["rep"]) in orig_v
                     and t["verdict"] != "unparsed" and orig_v[(t["cf_of"], t["rep"])] != "unparsed"]
            if not pairs:
                continue
            s = CF.flip_stats(pairs)
            data[f"{cond}/{typ or 'all'}"] = s
            out.append(f"- {cond} {typ or 'all twins'}: {s['n_pairs']} pairs, verdict change {s['verdict_change_rate'] * 100:.0f}%, "
                       f"clean→hold {s['clean_to_hold']}, hold→clean {s['hold_to_clean']}, exact McNemar p = {s['mcnemar_p']:.3f}")
    if not data:
        out.append("Needs `--scope cf` results (and the matching originals).")
    else:
        out += ["", "Verdict changes also arise from sampling noise (the model is not deterministic): compare with the change rate "
                    "between two repetitions of the *same* case before reading a difference as bias."]
    return out, data


def noise_floor(runs):
    """Verdict change rate between repetitions of the same case (the sampling-noise baseline)."""
    out, vals = {}, []
    for cond in ("C2", "C3"):
        by = by_case([r for r in runs.get(cond, []) if r["type"] == "application" and r["tier2"]])
        pairs = []
        for rs in by.values():
            rs = sorted(rs, key=lambda r: r["rep"])
            pairs += [(a["verdict"], b["verdict"]) for a, b in zip(rs, rs[1:]) if "unparsed" not in (a["verdict"], b["verdict"])]
        if pairs:
            out[cond] = sum(1 for a, b in pairs if a != b) / len(pairs)
    return out


def cost_section(runs, price_in, price_out):
    pi = sum((r.get("usage") or {}).get("prompt_tokens") or 0 for rs in runs.values() for r in rs)
    po = sum((r.get("usage") or {}).get("completion_tokens") or 0 for rs in runs.values() for r in rs)
    n = sum(len(rs) for rs in runs.values())
    return ["", "## 7. Cost", "",
            f"{n} calls, {pi:,} input and {po:,} output tokens; at ${price_in}/M in and ${price_out}/M out ≈ "
            f"${pi / 1e6 * price_in + po / 1e6 * price_out:.2f}. (Prices are inputs, not verified.)"]


def build_report(runs, claims_by_id, db_max, args):
    quality_lines, quality = quality_table(runs)
    lines = ["# Advisor evaluation report (synthetic cases)", "",
             f"model: {args.model} · conditions found: {', '.join(sorted(runs)) or 'none'}", ""]
    lines += quality_lines + anomaly_table(runs)
    ev_lines, ev = evidence_effect(runs)
    lines += ev_lines
    fr_lines, fr = frontier_section(runs, claims_by_id, db_max, args.small_share, args.prevalence)
    lines += fr_lines
    rel_lines, rel = reliance_section(quality, args.human_sens, args.human_spec, args.prevalence)
    lines += rel_lines
    cf_lines, cf = counterfactual_section(runs)
    lines += cf_lines
    nf = noise_floor(runs)
    if nf:
        lines.append("Sampling-noise baseline (verdict change between repetitions of the same application): "
                     + ", ".join(f"{k} {v * 100:.0f}%" for k, v in nf.items()) + ".")
    lines += cost_section(runs, args.price_in, args.price_out)
    summary = {"quality": quality, "evidence": ev, "frontier": fr, "reliance": rel, "counterfactual": cf, "noise_floor": nf}
    return "\n".join(lines) + "\n", summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt-4o")
    ap.add_argument("--cases-dir", default=str(CASES_DIR))
    ap.add_argument("--results-dir", default=str(RESULTS_DIR))
    ap.add_argument("--human-sens", type=float, default=0.85, help="PLACEHOLDER: reviewer alone, anomalous cases flagged")
    ap.add_argument("--human-spec", type=float, default=0.95, help="PLACEHOLDER: reviewer alone, legitimate cases passed")
    ap.add_argument("--prevalence", type=float, default=0.03, help="PLACEHOLDER: real anomaly prevalence")
    ap.add_argument("--small-share", type=float, default=0.85, help="PLACEHOLDER: share of claims in the automatic tier")
    ap.add_argument("--price-in", type=float, default=2.5)
    ap.add_argument("--price-out", type=float, default=10.0)
    args = ap.parse_args()

    claims, apps, by_id = load_cases(args.cases_dir)
    model_dir = Path(args.results_dir) / "advisor" / args.model.replace("/", "-")
    if not model_dir.exists():
        raise SystemExit(f"no results at {model_dir}; run run_advisor.py first")
    runs = load_runs(model_dir, by_id)
    db_max = {c: v["max_usd"] for c, v in load_treatment_db().items()}
    claims_by_id = {c["case_id"]: c for c in claims}
    text, summary = build_report(runs, claims_by_id, db_max, args)
    out = Path(args.results_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "advisor_report.md").write_text(text, encoding="utf-8")
    (out / "advisor_report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(text)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
