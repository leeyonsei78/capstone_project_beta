"""
Complexity-layer report: how advisor quality changes from L2 (tooth-level history) to L3 (same-family
upcoding), per model and per condition. Compares models side by side so the "does a small model still
work?" question is answered on the same cases.

  python paper/eval/review/score_complexity.py --models gpt-4o gpt-4o-mini qwen2.5-7b

Reads  results/advisor/<model>/<C1|C2|C3>_cx/*.json  and  cases/cases_claims_complex.json
(truth is re-joined from the case file: expert_label wins over the planted label).
Writes results/complexity_report.md. All numbers come from synthetic cases: wide CIs, report as such.
"""
import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import advisor_metrics as AM  # noqa: E402

RESULTS = HERE / "results"
CASES = HERE / "cases" / "cases_claims_complex.json"
BOOT = 400


def load_rows(model, cases):
    out = defaultdict(list)           # cond -> rows
    for cond in ("C1", "C2", "C3"):
        d = RESULTS / "advisor" / model.replace("/", "-") / f"{cond}_cx"
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            r = json.loads(f.read_text(encoding="utf-8"))
            c = cases.get(r["case_id"])
            if c is None:
                continue
            r.update(label=c["label"], expert_label=c.get("expert_label"), anomaly=c["anomaly"],
                     complexity=c["complexity"], kind=c["kind"], rule_detectable=c["rule_detectable"])
            out[cond].append(r)
    return out


def ci(rows, key, n=BOOT, seed=0):
    """Case-clustered bootstrap CI for metric `key` of AM.evaluate."""
    point = AM.evaluate(rows)[key]
    by = defaultdict(list)
    for r in rows:
        by[r["case_id"]].append(r)
    ids, rng, vals = list(by), random.Random(seed), []
    for _ in range(n if len(ids) > 1 else 0):
        s = [x for _ in ids for x in by[ids[rng.randrange(len(ids))]]]
        v = AM.evaluate(s)[key]
        if v is not None:
            vals.append(v)
    vals.sort()
    lo = vals[int(.025 * len(vals))] if len(vals) >= 20 else None
    hi = vals[int(.975 * len(vals)) - 1] if len(vals) >= 20 else None
    return point, lo, hi


def fmt(t):
    p, lo, hi = t
    if p is None:
        return "n/a"
    return f"{p * 100:.0f}%" + (f" [{lo * 100:.0f},{hi * 100:.0f}]" if lo is not None else "")


def build(models):
    cases = {c["case_id"]: c for c in json.loads(CASES.read_text(encoding="utf-8"))}
    lines = [f"# Complexity layer report (synthetic, {len(cases)} cases)", "",
             "Recall = planted anomalies flagged; specificity = legitimate cases passed as clean "
             "(abstentions count as neither). 95% CI over cases. L2 = tooth-level history, "
             "L3 = same-family upcoding (text + code meaning).", ""]
    for model in models:
        runs = load_rows(model, cases)
        if not runs:
            lines += [f"## {model}", "", "_no results_", ""]
            continue
        lines += [f"## {model}", "", "| cond | level | n | recall | specificity | abstain | ECE |",
                  "|---|---|---|---|---|---|---|"]
        for cond in ("C1", "C2", "C3"):
            for lvl in ("L2", "L3", "all"):
                rows = [r for r in runs.get(cond, []) if lvl == "all" or r["complexity"] == lvl]
                if not rows:
                    continue
                m = AM.evaluate(rows)
                ece = "n/a" if m["ece"] is None else format(m["ece"], ".2f")
                lines.append(f"| {cond} | {lvl} | {m['n']} | {fmt(ci(rows, 'recall_strict'))} | "
                             f"{fmt(ci(rows, 'specificity'))} | {fmt((m['abstain_rate'], None, None))} | {ece} |")
        lines += ["", "By kind (C3 if present, else C2):", "",
                  "| kind | rule-detectable by | n | flagged | clean |", "|---|---|---|---|---|"]
        rows = runs.get("C3") or runs.get("C2") or []
        for kind in sorted({r["kind"] for r in rows}):
            kr = [r for r in rows if r["kind"] == kind]
            n = len(kr)
            lines.append(f"| {kind} | {kr[0]['rule_detectable']} | {n} | "
                         f"{sum(r['verdict'] == 'flag' for r in kr) / n * 100:.0f}% | "
                         f"{sum(r['verdict'] == 'clean' for r in kr) / n * 100:.0f}% |")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    args = ap.parse_args()
    md = build(args.models)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "complexity_report.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
