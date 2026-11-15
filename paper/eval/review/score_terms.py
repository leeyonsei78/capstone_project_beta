"""
Score the clause-conditioned review, models side by side.

  python paper/eval/review/score_terms.py --models gpt-4o gpt-4o-mini qwen2.5-7b

Reads results/terms/<model>/<T0|T1>/*.json and cases/cases_terms.json; truth is re-joined from the case file.
Writes results/terms_report.md.

Metrics (per model and condition; 95% CI by bootstrap over scenarios, so the three profile versions of one scenario
and repeated runs stay together):
  accuracy      exact match of 지급 / 감액지급 / 부지급 (abstentions and unparsed count as wrong)
  on-disagree   accuracy on scenarios where the profiles' correct answers differ (reading the clause is required)
  adaptation    share of disagreeing scenarios where the model got ALL THREE profiles right
  overpay       predicted more generous than correct (payment that should have been reduced or refused)
  underpay      predicted less generous than correct (wrongful denial)
  abstain       "근거부족"
Overpay is the costly direction for the insurer, underpay for the customer; both are reported, none is weighted.
"""
import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
CASES = HERE / "cases" / "cases_terms.json"
RESULTS = HERE / "results"
RANK = {"부지급": 0, "감액지급": 1, "지급": 2}
BOOT = 400


def load(model, cases):
    out = defaultdict(list)
    for cond in ("T0", "T1"):
        d = RESULTS / "terms" / model.replace("/", "-") / cond
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            r = json.loads(f.read_text(encoding="utf-8"))
            c = cases.get(r["case_id"])
            if c:
                r["expected"], r["disagree"] = c["expected"], c["profiles_disagree"]
                out[cond].append(r)
    return out


def metrics(rows):
    n = len(rows)
    if not n:
        return None
    acc = sum(r["decision"] == r["expected"] for r in rows) / n
    over = sum(1 for r in rows if r["decision"] in RANK and RANK[r["decision"]] > RANK[r["expected"]]) / n
    under = sum(1 for r in rows if r["decision"] in RANK and RANK[r["decision"]] < RANK[r["expected"]]) / n
    ab = sum(r["decision"] == "근거부족" for r in rows) / n
    dis = [r for r in rows if r["disagree"]]
    on_dis = sum(r["decision"] == r["expected"] for r in dis) / len(dis) if dis else None
    # adaptation: per (scenario, rep) all three profile cases right
    groups = defaultdict(list)
    for r in dis:
        groups[(r["scenario"], r["rep"])].append(r["decision"] == r["expected"])
    full = [all(v) for v in groups.values() if len(v) == 3]
    adapt = sum(full) / len(full) if full else None
    by_profile = {k: (sum(r["decision"] == r["expected"] for r in rows if r["profile"] == k) /
                      max(1, sum(1 for r in rows if r["profile"] == k))) for k in ("A", "B", "C")}
    return {"n": n, "acc": acc, "on_dis": on_dis, "adapt": adapt, "over": over, "under": under, "abstain": ab,
            "by_profile": by_profile}


def ci(rows, key, seed=0):
    by = defaultdict(list)
    for r in rows:
        by[r["scenario"]].append(r)
    ids, rng, vals = list(by), random.Random(seed), []
    for _ in range(BOOT if len(ids) > 1 else 0):
        sample = [x for _ in ids for x in by[ids[rng.randrange(len(ids))]]]
        m = metrics(sample)
        if m and m[key] is not None:
            vals.append(m[key])
    vals.sort()
    if len(vals) < 20:
        return None, None
    return vals[int(.025 * len(vals))], vals[int(.975 * len(vals)) - 1]


def pct(v, lohi=None):
    if v is None:
        return "n/a"
    s = f"{v * 100:.0f}%"
    if lohi and lohi[0] is not None:
        s += f" [{lohi[0] * 100:.0f},{lohi[1] * 100:.0f}]"
    return s


def build(models):
    cases = {c["case_id"]: c for c in json.loads(CASES.read_text(encoding="utf-8"))}
    n_scn = len({c["scenario"] for c in cases.values()})
    lines = [f"# Clause-conditioned review report (synthetic, {n_scn} scenarios x 3 profiles)", "",
             "T0 = facts only, T1 = facts + the profile's clause excerpt. CI over scenarios. See the metric definitions in "
             "score_terms.py. Profiles come from public product summaries and are simplified (terms_profiles.py).", "",
             "| model | cond | n | accuracy | on-disagree | adaptation | overpay | underpay | abstain | A / B / C |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for model in models:
        runs = load(model, cases)
        if not runs:
            lines.append(f"| {model} | - | 0 | no results | | | | | | |")
            continue
        for cond in ("T0", "T1"):
            rows = runs.get(cond)
            if not rows:
                continue
            m = metrics(rows)
            bp = " / ".join(pct(m["by_profile"][k]) for k in ("A", "B", "C"))
            lines.append(f"| {model} | {cond} | {m['n']} | {pct(m['acc'], ci(rows, 'acc'))} | "
                         f"{pct(m['on_dis'], ci(rows, 'on_dis'))} | {pct(m['adapt'], ci(rows, 'adapt'))} | "
                         f"{pct(m['over'])} | {pct(m['under'])} | {pct(m['abstain'])} | {bp} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    a = ap.parse_args()
    md = build(a.models)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "terms_report.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
