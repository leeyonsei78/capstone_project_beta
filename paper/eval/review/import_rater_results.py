"""
Merge the JSON files exported from cases/review_blind.html (one per rater) into the case files.

  python paper/eval/review/import_rater_results.py [dir_with_rater_json]      (default: cases/rater_results/)

For every case it stores
  expert_labels      {rater_id: label}
  expert_label       the majority label (left unset on a tie -> listed for adjudication)
  expert_times       {rater_id: seconds to first decision}   (falls back to total viewed seconds)
  expert_time_sec    median of those
  expert_note        memos joined as "[R01] ..."
and writes results/rater_agreement.md: per-rater coverage and speed, pairwise Cohen's kappa, Fleiss' kappa on the
cases every rater labelled, agreement of each rater and of the consensus with the PLANTED label (a measure of how
realistic the construction is), and the list of ties. Rater-authored unstructured cases are collected into
cases/expert_authored.json (a loader that turns them into runnable cases is a separate, later step).

Only the latest export per rater code is used. Exports made from a different version of the sheet (dataset_id
mismatch) are refused.
"""
import csv
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).parent
CASES = HERE / "cases"
RESULTS = HERE / "results"
VALID = {"approve", "investigate"}


def dataset_id(cases_dir):
    raw = (cases_dir / "review_claims_blind.csv").read_bytes() + (cases_dir / "review_apps_blind.csv").read_bytes()
    return hashlib.sha256(raw).hexdigest()[:12]


def cohen_kappa(a, b):
    """a, b: dicts case->label on any cases; uses their intersection. None if undefined."""
    common = sorted(set(a) & set(b))
    n = len(common)
    if n == 0:
        return None, 0
    po = sum(a[c] == b[c] for c in common) / n
    pe = sum((sum(a[c] == k for c in common) / n) * (sum(b[c] == k for c in common) / n) for k in VALID)
    if pe == 1:
        return (1.0 if po == 1 else None), n
    return (po - pe) / (1 - pe), n


def fleiss_kappa(items):
    """items: list of Counter(label->count), every item rated by the same number of raters (>=2)."""
    if not items:
        return None
    n = sum(items[0].values())
    N = len(items)
    if n < 2:
        return None
    p_j = {k: sum(it[k] for it in items) / (N * n) for k in VALID}
    P_i = [(sum(it[k] ** 2 for k in VALID) - n) / (n * (n - 1)) for it in items]
    Pbar, Pe = sum(P_i) / N, sum(v * v for v in p_j.values())
    if Pe == 1:
        return 1.0 if Pbar == 1 else None
    return (Pbar - Pe) / (1 - Pe)


def consensus(labels):
    """labels: {rater: label} -> majority label or None on a tie."""
    c = Counter(labels.values()).most_common()
    if not c:
        return None
    if len(c) > 1 and c[0][1] == c[1][1]:
        return None
    return c[0][0]


def load_exports(src, ds_id):
    latest = {}
    for p in sorted(Path(src).glob("*.json")):
        o = json.loads(p.read_text(encoding="utf-8"))
        if o.get("format") != "review_rater_v1":
            raise SystemExit(f"{p.name}: not a review_rater_v1 export")
        if o.get("dataset_id") != ds_id:
            raise SystemExit(f"{p.name}: dataset_id {o.get('dataset_id')} != current sheet {ds_id} "
                             "(exported from a different version of the sheet)")
        rid = o["rater"]["id"]
        if rid not in latest or o["exported_at"] > latest[rid]["exported_at"]:
            latest[rid] = o
    return latest


def run(src=None, cases_dir=CASES, results_dir=RESULTS, write=True):
    src = Path(src) if src else cases_dir / "rater_results"
    ds = dataset_id(cases_dir)
    raters = load_exports(src, ds)
    if not raters:
        raise SystemExit(f"no rater exports in {src}")
    key = json.loads((cases_dir / "blind_key.json").read_text(encoding="utf-8"))
    files = {"claims": cases_dir / "cases_claims.json", "apps": cases_dir / "cases_apps.json"}
    cases = {t: json.loads(p.read_text(encoding="utf-8")) for t, p in files.items()}
    by_id = {c["case_id"]: (t, c) for t in cases for c in cases[t]}

    per_case = defaultdict(dict)      # case_id -> {rater: label}
    times = defaultdict(dict)
    notes = defaultdict(list)
    realism = defaultdict(list)
    rater_stats = {}
    for rid, o in raters.items():
        secs = []
        for bid, x in o["labels"].items():
            if bid not in key:
                raise SystemExit(f"{rid}: unknown blind id {bid}")
            if x["label"] not in VALID:
                raise SystemExit(f"{rid} {bid}: bad label {x['label']}")
            cid = key[bid]
            per_case[cid][rid] = x["label"]
            t = x.get("first_seconds") if x.get("first_seconds") is not None else x.get("seconds")
            if t:
                times[cid][rid] = float(t)
                secs.append(float(t))
            if x.get("memo"):
                notes[cid].append(f"[{rid}] {x['memo']}")
            if x.get("realism"):
                realism[rid].append(x["realism"])
        rater_stats[rid] = {"n": len(o["labels"]), "field": o["rater"].get("field", ""), "years": o["rater"].get("years", ""),
                            "median_sec": statistics.median(secs) if secs else None,
                            "realism": statistics.mean(realism[rid]) if realism[rid] else None}

    ties, set_n = [], 0
    for cid, labs in per_case.items():
        t, c = by_id[cid]
        c["expert_labels"] = labs
        lab = consensus(labs)
        if lab:
            c["expert_label"] = lab
            set_n += 1
        else:
            ties.append(cid)
        if times[cid]:
            c["expert_times"] = times[cid]
            c["expert_time_sec"] = statistics.median(times[cid].values())
        if notes[cid]:
            c["expert_note"] = " | ".join(notes[cid])
    if write:
        for t, p in files.items():
            p.write_text(json.dumps(cases[t], ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- agreement report ----
    ids = sorted(raters)
    pair_k = {}
    for a, b in combinations(ids, 2):
        la = {c: l[a] for c, l in per_case.items() if a in l}
        lb = {c: l[b] for c, l in per_case.items() if b in l}
        pair_k[(a, b)] = cohen_kappa(la, lb)
    everyone = [c for c, l in per_case.items() if all(r in l for r in ids)]
    fk = fleiss_kappa([Counter(per_case[c].values()) for c in everyone]) if len(ids) >= 2 else None
    planted = {}
    for rid in ids:
        both = [(per_case[c][rid], by_id[c][1]["label"]) for c in per_case if rid in per_case[c]]
        planted[rid] = (sum(a == b for a, b in both) / len(both), len(both)) if both else (None, 0)
    cons_pairs = [(consensus(per_case[c]), by_id[c][1]["label"]) for c in per_case if consensus(per_case[c])]
    cons_planted = (sum(a == b for a, b in cons_pairs) / len(cons_pairs), len(cons_pairs)) if cons_pairs else (None, 0)

    authored = []
    for rid, o in raters.items():
        for a in o.get("authored", []):
            authored.append({"authored_id": f"X-{rid}-{a['n']:03d}", "rater": rid, **a})
    if write:
        (cases_dir / "expert_authored.json").write_text(json.dumps(authored, ensure_ascii=False, indent=2), encoding="utf-8")

    def f(x, d=2):
        return "n/a" if x is None else f"{x:.{d}f}"

    lines = ["# 심사자 결과 요약", "", f"시트 데이터 ID: `{ds}` · 심사자 {len(ids)}명 · 라벨이 붙은 사례 {len(per_case)}건 "
             f"(다수결 라벨 확정 {set_n}건, 동수 {len(ties)}건)", "",
             "## 심사자별", "", "| 심사자 | 분야 | 경력(년) | 라벨 수 | 첫 판단까지 중앙값(초) | 현실성 평균 | 계획 라벨 일치율 |", "|---|---|---|---|---|---|---|"]
    for rid in ids:
        s = rater_stats[rid]
        pa, pn = planted[rid]
        lines.append(f"| {rid} | {s['field']} | {s['years']} | {s['n']} | {f(s['median_sec'], 0)} | {f(s['realism'])} | "
                     f"{f(pa)} (n={pn}) |")
    lines += ["", "## 심사자 간 일치도", ""]
    if len(ids) < 2:
        lines.append("심사자가 1명이라 일치도를 계산할 수 없습니다. (한계로 명시, 가능하면 20% 이상 독립 재라벨 확보)")
    else:
        lines += ["| 쌍 | 공통 사례 | Cohen's κ |", "|---|---|---|"]
        for (a, b), (k, n) in pair_k.items():
            lines.append(f"| {a} – {b} | {n} | {f(k)} |")
        lines += ["", f"Fleiss' κ (모든 심사자가 라벨한 {len(everyone)}건): {f(fk)}"]
    lines += ["", f"다수결 라벨과 계획 라벨의 일치율: {f(cons_planted[0])} (n={cons_planted[1]}) — 사례 구성이 실무 판단과 얼마나 맞는지의 증거",
              "", "## 동수라 판정이 필요한 사례", "", ", ".join(ties) if ties else "없음",
              "", f"## 심사자가 작성한 비정형 사례: {len(authored)}건 (`cases/expert_authored.json`, 아직 실행용 사례로 변환되지 않음)", ""]
    text = "\n".join(lines)
    if write:
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / "rater_agreement.md").write_text(text, encoding="utf-8")
    return text, {"ties": ties, "pair_kappa": pair_k, "fleiss": fk, "planted": planted, "cons_planted": cons_planted,
                  "authored": authored, "labelled": len(per_case)}


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else None
    text, _ = run(src)
    print(text)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
