"""
Import the domain expert's labels from the review CSVs back into the case JSON files.

  python paper/eval/review/import_expert_labels.py

Reads cases/review_claims.csv and cases/review_apps.csv (UTF-8 with BOM, as written by gen_cases.py).
Fill the column '전문가라벨(approve/investigate)' with approve or investigate (anything else is rejected;
blank keeps the planted label). Writes `expert_label` and `expert_note` into cases_*.json and reports
how often the expert overrode the planted label -- that agreement rate is itself a result (it measures
how realistic the construction is) and goes into the paper.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
CASES = HERE / "cases"
LABEL_COL = "전문가라벨(approve/investigate)"
NOTE_COL = "전문가메모"
REAL_COL = "현실성(1-5)"
TIME_COL = "소요시간(초)"
VALID = {"approve", "investigate"}


def apply(csv_name, json_name):
    blind = csv_name.replace(".csv", "_blind.csv")
    key = None
    if (CASES / blind).exists():                       # prefer the blind sheet the expert filled in
        csv_name = blind
        key = json.loads((CASES / "blind_key.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader(open(CASES / csv_name, encoding="utf-8-sig", newline="")))
    if key is not None:
        for r in rows:
            r["case_id"] = key[r["blind_id"]]
    cases = json.loads((CASES / json_name).read_text(encoding="utf-8"))
    by_id = {c["case_id"]: c for c in cases}
    stats = Counter()
    realism = []
    times = []
    for r in rows:
        cid = r["case_id"]
        if cid not in by_id:
            raise SystemExit(f"{csv_name}: unknown case_id {cid}")
        lab = (r.get(LABEL_COL) or "").strip().lower()
        c = by_id[cid]
        if lab:
            if lab not in VALID:
                raise SystemExit(f"{csv_name} {cid}: label must be approve/investigate, got '{lab}'")
            c["expert_label"] = lab
            stats["labelled"] += 1
            stats["agree" if lab == c["label"] else "override"] += 1
            if lab != c["label"]:
                stats[f"override_{c['anomaly']}"] += 1
        note = (r.get(NOTE_COL) or "").strip()
        if note:
            c["expert_note"] = note
        try:
            realism.append(int(r.get(REAL_COL) or ""))
        except ValueError:
            pass
        try:
            sec = float(r.get(TIME_COL) or "")
            if sec > 0:
                c["expert_time_sec"] = sec
                times.append(sec)
        except ValueError:
            pass
    (CASES / json_name).write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(rows), stats, realism, times


def main():
    for csv_name, json_name in (("review_claims.csv", "cases_claims.json"), ("review_apps.csv", "cases_apps.json")):
        n, st, realism, times = apply(csv_name, json_name)
        lab = st["labelled"]
        print(f"{json_name}: {n} cases, labelled {lab}, agree {st['agree']}, override {st['override']}"
              + (f" (agreement {st['agree'] / lab:.0%})" if lab else ""))
        for k, v in sorted(st.items()):
            if k.startswith("override_"):
                print(f"   overrides on planted {k[9:]}: {v}")
        if realism:
            print(f"   mean realism rating {sum(realism) / len(realism):.2f} (n={len(realism)})")
        if times:
            s = sorted(times)
            print(f"   expert time per case: median {s[len(s) // 2]:.0f}s, mean {sum(s) / len(s):.0f}s (n={len(s)})")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
