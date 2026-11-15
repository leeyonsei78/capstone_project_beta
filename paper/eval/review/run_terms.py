"""
Run the clause-conditioned claim review (see gen_terms_cases.py / terms_profiles.py).

  python paper/eval/review/run_terms.py --cond all --dry-run --limit 2          # print prompts, no API call
  python paper/eval/review/run_terms.py --cond all --model gpt-4o-mini --reps 3
  python paper/eval/review/run_terms.py --cond T1 --model qwen2.5:7b --base-url http://localhost:11434/v1

Conditions
  T0  facts only; the model is told the insurer's terms apply but is not shown them (what it can do from general
      knowledge alone: it cannot know which of the three profiles it is looking at)
  T1  facts + the clause excerpt of the case's profile (terms_profiles.render_clause)
Results: results/terms/<model>/<cond>/<case_id>__r<rep>.json (existing files are skipped; --force to redo).
Output of the model: JSON {decision: 지급|감액지급|부지급|근거부족, reason_code, confidence, reason}.
"""
import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import run_advisor as RA      # noqa: E402  (client + call_model with the --base-url handling)
import terms_profiles as TP   # noqa: E402

CASES = HERE / "cases" / "cases_terms.json"
RESULTS = HERE / "results" / "terms"
REASONS = ("excluded_kind", "waiting", "pre_start", "annual_cap", "reduced", "none")

SYSTEM = (
    "당신은 치과보험 보험금 지급 심사를 보조하는 AI입니다. 청구 사실관계를 보고 이 청구에 대해 지급, 감액지급(50%), 부지급 "
    "중 무엇이 맞는지 판정하세요. 당신의 의견은 참고용이며 최종 결정은 심사자가 합니다. "
    "반드시 JSON 객체 하나만 출력하세요. 키: decision(\"지급\" | \"감액지급\" | \"부지급\" | \"근거부족\"), "
    "reason_code(\"excluded_kind\"=지급 제외 사유, \"waiting\"=면책기간, \"pre_start\"=보장개시일 이전 발치, "
    "\"annual_cap\"=개수 한도 초과, \"reduced\"=감액기간, \"none\"=문제 없음), confidence(0~100 정수), reason(한 문장). "
    "제공된 정보만으로 판단하기 어려우면 추측하지 말고 decision을 \"근거부족\"으로 하세요."
)
COV = {"crown": "크라운", "implant": "임플란트", "bridge": "브릿지"}
KIND = {"normal": "충치·잇몸질환(또는 상해)으로 보존할 수 없어 발치", "wisdom": "사랑니(제3대구치) 발치",
        "impacted": "매복된 치아 발치", "ortho": "교정·위치이상 목적의 발치", "prep": "다른 보철 치료를 준비하기 위한 발치"}


def facts_text(case):
    f = case["facts"]
    lines = [f"청구 ID: {case['case_id']}", f"청구 담보: {COV[f['coverage']]}",
             f"원인: {'질병(충치·잇몸질환)' if f['cause'] == 'disease' else '상해(사고)'}",
             f"치료일: 계약일로부터 {f['event_day']}일째"]
    if f["coverage"] in TP.PROSTHETIC:
        lines.append(f"영구치 발치일: 계약일로부터 {f['extraction_day']}일째 ({KIND[f['extraction_kind']]})")
        lines.append(f"이번 계약연도에 이미 지급된 같은 담보({COV[f['coverage']]}) 건수: {f['count_this_year']}건")
    return "\n".join(lines)


def build_prompt(case, cond):
    user = facts_text(case) + "\n\n"
    if cond == "T1":
        user += TP.render_clause(TP.PROFILES[case["profile"]]) + "\n\n"
    else:
        user += "이 청구에는 해당 보험사의 치아보험 약관이 적용됩니다(약관 내용은 제시되지 않았습니다).\n\n"
    return SYSTEM, user + "위 정보를 근거로 판정하세요."


def normalize_decision(s):
    s = (s or "").replace(" ", "")
    if "부지급" in s or "지급불가" in s or "거절" in s:
        return "부지급"
    if "감액" in s:
        return "감액지급"
    if "근거부족" in s or "판단불가" in s:
        return "근거부족"
    if "지급" in s or "전액" in s:
        return "지급"
    return "unparsed"


def parse(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return {"decision": "unparsed", "reason_code": None, "confidence": None, "reason": None}
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"decision": "unparsed", "reason_code": None, "confidence": None, "reason": None}
    conf = d.get("confidence")
    conf = int(conf) if isinstance(conf, (int, float)) else None
    rc = d.get("reason_code")
    return {"decision": normalize_decision(str(d.get("decision", ""))), "reason_code": rc if rc in REASONS else None,
            "confidence": conf, "reason": d.get("reason")}


def run_one(client, model, case, cond, rep, out_dir, force):
    f = out_dir / f"{case['case_id']}__r{rep}.json"
    if f.exists() and not force:
        return "skipped"
    system, user = build_prompt(case, cond)
    text, usage = RA.call_model(client, model, system, user, True)
    rec = {"case_id": case["case_id"], "scenario": case["scenario"], "profile": case["profile"], "cond": cond,
           "rep": rep, "model": model, "expected": case["expected"], "raw": text, **parse(text), "usage": usage}
    f.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    return "done"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cond", choices=["T0", "T1", "all"], default="all")
    ap.add_argument("--model", default="gpt-4o")
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--api-key-env", default="OPENAI_API_KEY")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    if args.limit:
        cases = cases[:args.limit]
    conds = ["T0", "T1"] if args.cond == "all" else [args.cond]
    print(f"{len(cases) * len(conds) * args.reps} calls: conds={conds} reps={args.reps} model={args.model}")
    if args.dry_run:
        for cond in conds:
            s, u = build_prompt(cases[0], cond)
            print(f"\n--- {cond} {cases[0]['case_id']} expected={cases[0]['expected']} ---\n[system] {s}\n[user]\n{u}")
        return
    client = RA.get_client(args.base_url, args.api_key_env)
    t0, done = time.time(), 0
    for cond in conds:
        out_dir = RESULTS / args.model.replace("/", "-") / cond
        out_dir.mkdir(parents=True, exist_ok=True)
        jobs = [(c, r) for c in cases for r in range(1, args.reps + 1)]
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            for st in ex.map(lambda a: run_one(client, args.model, a[0], cond, a[1], out_dir, args.force), jobs):
                done += st == "done"
        print(f"{cond}: {len(jobs)} jobs -> {out_dir}")
    print(f"finished {done} new calls in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
