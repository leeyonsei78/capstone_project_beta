"""Supplementary AI opinions and readable reports; no access to planted labels."""
import argparse
import csv
import hashlib
import json
import statistics
import time
import urllib.request
from collections import Counter
from itertools import combinations

from run_ai_blind_raters import OUT, chat, inputs, run, validate_labels, write_json

SUPPLEMENT = """보험 심사 실험에 대한 AI 대리 검토 의견을 작성하세요. 사람 전문가 경력이나 실증값을 주장하지 마세요.
다른 심사자 의견과 생성 정답은 제공되지 않습니다. 한국어로 간결하게 JSON 객체만 반환하세요.
assumptions_review 객체의 키는 review_cost_15, loss_fraction_1, prevalence_003, small_share_085, required_company_data, sensitivity_plan 입니다.
각 값은 검토 의견 한 문장입니다. 가정은 건당 사람 검토비용 $15, 부적정 지급 손실비율 1.0, 이상청구 비율 3%, 한도대비 20% 이하 소액청구 비중 85%입니다. 모두 자리표시 값입니다. 실제 회사 수치는 없으며 만들어내면 안 됩니다.
realism_review: 합성 사례가 외부 타당성을 갖추려면 필요한 검증을 한 문장.
limitations: AI 심사와 인간 전문가 검증의 차이를 한 문장.
authored: 완전히 새로 만든 가상 사례 두 개(청구 하나, 청약 하나) 배열. 가상 약관을 스스로 명시하여 판정 가능한 사례를 만드세요. 실제 사건으로 주장하지 마세요.
각 사례의 키: n(1 또는 2), type(claim 또는 app), contract(상품·담보·한도·가입 경과), facts(이번 건 사실), narrative(3문장 이내), clause(가상 약관), history(치료이력 또는 고지 답변), label(approve 또는 investigate), action(지급/보완요청/계약인수 등), rationale(판단근거), why_rules_fail(금액·건수 규칙으로 판단 못하는 이유), evidence_level(narrative 또는 detail), difficulty(1~5 정수), realism(1~5 정수), provenance(반드시 fictional), seconds(null).
최소한 하나는 investigate로 하세요. 한 항목마다 짧게 쓰되 정보가 서로 모순되지 않게 하세요."""


def supplement(rater, model):
    path = OUT / "audit" / rater / "supplement.json"
    if path.exists():
        record = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = {"model": model, "stream": False, "think": False, "format": "json", "keep_alive": "30m",
                   "options": {"temperature": 0, "seed": 20261119, "num_ctx": 4096, "num_predict": 2400},
                   "messages": [{"role": "user", "content": SUPPLEMENT}]}
        start = time.perf_counter()
        answer = chat(payload)
        record = {"request": payload, "response": answer, "elapsed_seconds": time.perf_counter() - start}
        write_json(path, record)
    result = json.loads(record["response"]["message"]["content"])
    assert len(result["authored"]) == 2
    assert {x["type"] for x in result["authored"]} == {"claim", "app"}
    required = {"n", "type", "contract", "facts", "narrative", "clause", "history", "label", "action", "rationale",
                "why_rules_fail", "evidence_level", "difficulty", "realism", "provenance", "seconds"}
    for x in result["authored"]:
        assert required <= x.keys()
        assert x["label"] in ("approve", "investigate") and x["provenance"] == "fictional" and x["seconds"] is None
    write_json(OUT / "audit" / f"{rater}_supplement.json", result)
    print(f"{rater}: supplementary opinion saved", flush=True)


def cost_followup(rater, model):
    prompt = """보험 실험의 비용 가정을 검토하는 AI입니다. 사람 전문가로 행세하지 마세요.
정정: 건당 $15는 AI 호출비가 아니라 사람이 청구 1건을 검토하는 비용입니다.
다음 값은 전부 실증자료가 없는 자리표시입니다: 사람 검토비용 $15, 잘못 지급한 금액의 손실비율 1.0, 이상청구 비율 3%, 한도대비 20% 이하 소액청구 비중 85%.
단순히 값을 반복하거나 '검토가 필요하다'라고 끝내지 마세요. 각 가정에 대해 (1) 무엇을 가정하는지 (2) 이 가정이 틀릴 수 있는 구체적 이유 (3) 검증에 필요한 회사 데이터를 한두 문장으로 쓰세요.
JSON 키는 review_cost_15, loss_fraction_1, prevalence_003, small_share_085, required_company_data, sensitivity_plan 입니다. 값은 한국어 문자열입니다.
sensitivity_plan에는 여러 가정을 동시에 변화시키는 구체적 분석 방법을 제안하되 실제 수치를 추정하지 마세요. required_company_data는 수집할 구체적 열을 열거하세요. JSON만 출력하세요."""
    path = OUT / "audit" / rater / "supplement_cost_followup.json"
    if path.exists():
        record = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = {"model": model, "stream": False, "think": False, "format": "json", "keep_alive": "30m",
                   "options": {"temperature": 0, "seed": 20261119, "num_ctx": 4096, "num_predict": 1800},
                   "messages": [{"role": "user", "content": prompt}]}
        start = time.perf_counter()
        response = chat(payload)
        record = {"request": payload, "response": response, "elapsed_seconds": time.perf_counter()-start}
        write_json(path, record)
    data = json.loads(record["response"]["message"]["content"])
    assert {"review_cost_15", "loss_fraction_1", "prevalence_003", "small_share_085", "required_company_data", "sensitivity_plan"} <= data.keys()
    p = OUT / "audit" / f"{rater}_supplement.json"
    s = json.loads(p.read_text(encoding="utf-8"))
    s["assumptions_review"] = data
    s["assumptions_review_source"] = f"audit/{rater}/supplement_cost_followup.json"
    write_json(p, s)
    print(f"{rater}: cost review follow-up saved", flush=True)


def kappa(a, b):
    n = len(a)
    pa, pb = Counter(a.values()), Counter(b.values())
    observed = sum(a[k] == b[k] for k in a) / n
    expected = sum(pa[x] * pb[x] for x in ("approve", "investigate")) / n**2
    return observed, (observed - expected) / (1 - expected) if expected != 1 else None


def build(raters=("codex", "qwen", "deepseek")):
    ds, rows, hashes = inputs()
    manifest = json.loads((OUT / "audit" / "manifest.json").read_text(encoding="utf-8"))
    assert hashlib.sha256((OUT / "audit" / "codex_decisions.tsv").read_bytes()).hexdigest() == manifest["codex_decisions_sha256"]
    rowmap = {r["id"]: r for r in rows}
    all_labels, exports = {}, {}
    for rater in raters:
        path = OUT / f"rater_{rater}.json"
        o = json.loads(path.read_text(encoding="utf-8"))
        assert o["dataset_id"] == ds and o["provenance"]["inputs_sha256"] == hashes
        assert o["provenance"]["complete"] and not o["provenance"]["human_expert"]
        labels = {**o["labels"], **o["complex_labels"]}
        validate_labels([{"id": k, **v} for k, v in labels.items()], rowmap)
        assert all(v["seconds"] is None and v["first_seconds"] is None for v in labels.values())
        s = json.loads((OUT / "audit" / f"{rater}_supplement.json").read_text(encoding="utf-8"))
        o.update(s)
        write_json(path, o)
        exports[rater] = o
        all_labels[rater] = {k: v["label"] for k, v in labels.items()}
        counts = Counter(all_labels[rater].values())
        with (OUT / f"rater_{rater}.csv").open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["blind_id", "type", "ai_rater", "ai_label", "ai_realism_1_5", "ai_memo", "human_seconds"])
            for k in rowmap:
                v = labels[k]
                writer.writerow([k, rowmap[k]["type"], o["rater"]["model"], v["label"], v["realism"], v["memo"], ""])
        lines = [f"# {rater.upper()} AI 대리 심사 의견", "", "사람 전문가의 판정·경력·실측 심사시간이 아닙니다. 연구의 인간 전문가 정답으로 사용하지 마세요.", "",
                 f"모델: {o['rater']['model']}", f"블라인드 자료 ID: {ds}",
                 f"총 314건: approve {counts['approve']}건, investigate {counts['investigate']}건. 현실성 평균 {statistics.mean(v['realism'] for v in labels.values()):.2f}/5.", "",
                 "## 비용 가정 검토", ""]
        if rater == "codex":
            lines[4:4] = ["출처: 이전 Codex 세션에서 완료한 314건을 그대로 보존했습니다. 프로젝트 문맥을 접한 세션이므로 완전히 격리된 블라인드 심사가 아닙니다.", ""]
        else:
            lines[4:4] = ["실행 조건: 로컬 Ollama, temperature=0, seed=20261119, context=4096, think=false, 배치당 최대 10건. 사람의 판단시간은 측정하지 않았습니다.", ""]
            if rater == "deepseek":
                lines[4:4] = ["DeepSeek 요청 방식: /api/generate의 raw 프롬프트에 </think>를 미리 넣어 최종 답변 생성을 시작했습니다. think=false만으로 추론이 억제되지 않았던 첫 /api/chat 응답은 예비 기록으로 제외했습니다. 일반 추론 모드의 성능으로 해석하지 마세요.", ""]
        titles = {"review_cost_15": "검토비용 15달러", "loss_fraction_1": "손실비율 1.0", "prevalence_003": "이상청구 비율 3%",
                  "small_share_085": "소액 비중 85%", "required_company_data": "필요한 회사 자료", "sensitivity_plan": "민감도 검토"}
        aliases = {"small_share_085": "small_share_0085"}
        for k, title in titles.items():
            value = s["assumptions_review"].get(k, s["assumptions_review"].get(aliases.get(k, "")))
            assert value, f"Missing AI opinion field: {rater}.{k}"
            lines.extend([f"- **{title}**: {value}"])
        lines.extend(["", "## 현실성 및 한계", "", s["realism_review"], "", s["limitations"], "", "## AI가 새로 작성한 가상 사례", ""])
        for a in s["authored"]:
            lines.extend([f"### 사례 {a['n']} ({a['type']})", ""])
            for k in ("contract", "facts", "narrative", "clause", "history", "label", "action", "rationale", "why_rules_fail"):
                lines.append(f"- **{k}**: {a[k]}")
            lines.append("")
        lines.extend(["## 건별 판정", "", "| ID | AI 판정 | 현실성 | 판단 사유 |", "|---|---|---|---|"])
        for k in rowmap:
            v = labels[k]
            memo = v["memo"].replace("|", "/").replace("\n", " ")
            lines.append(f"| {k} | {v['label']} | {v['realism']} | {memo} |")
        (OUT / f"rater_{rater}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if set(exports) != {"codex", "qwen", "deepseek"}:
        print("Individual reports saved: " + ", ".join(exports))
        return
    disagreements = []
    with (OUT / "comparison.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["blind_id", "codex", "qwen", "deepseek", "ai_majority_not_ground_truth", "unanimous"])
        for k in rowmap:
            vals = [all_labels[r][k] for r in all_labels]
            unanimous = len(set(vals)) == 1
            w.writerow([k, *vals, Counter(vals).most_common(1)[0][0], unanimous])
            if not unanimous:
                disagreements.append(k)
    with (OUT / "disagreements.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["blind_id", "type", "blind_facts"] +
                   [f"{r}_{field}" for r in exports for field in ("label", "realism", "memo")])
        for k in disagreements:
            values = []
            for o in exports.values():
                v = o["labels"].get(k) or o["complex_labels"][k]
                values.extend(v[field] for field in ("label", "realism", "memo"))
            w.writerow([k, rowmap[k]["type"], json.dumps(rowmap[k]["facts"], ensure_ascii=False), *values])
    lines = ["# AI 3종 블라인드 대리 심사 결과", "", "**인간 전문가 검증이 아닌 AI 대리 라벨링입니다.** 합의 라벨과 현실성 점수도 AI 의견이며 외부 타당성 또는 확정 정답을 증명하지 않습니다.", "",
             f"기본 청구 150건 + 청약 90건 + 복잡 청구 74건 = 각 314건, 총 942개 판정. 데이터 ID `{ds}`.", "",
             "| 모델 | approve | investigate |", "|---|---:|---:|"]
    for r in all_labels:
        c = Counter(all_labels[r].values())
        lines.append(f"| {exports[r]['rater']['model']} | {c['approve']} | {c['investigate']} |")
    lines.extend(["", "| 모델 쌍 | 일치율 | Cohen κ |", "|---|---:|---:|"])
    for a, b in combinations(all_labels, 2):
        agreement, k = kappa(all_labels[a], all_labels[b])
        lines.append(f"| {a} / {b} | {agreement:.1%} | {k:.3f} |")
    lines.extend(["", f"3개 모델 전원 일치 {314-len(disagreements)}건, 불일치 {len(disagreements)}건. 다수결은 정답이 아니며 사람의 후속 검토 후보입니다.", "",
                  "## 파일", "", "- `rater_codex.md`, `rater_qwen.md`, `rater_deepseek.md`: 각 모델의 판정·비용 가정 검토·가상 사례 2개.",
                  "- 같은 이름의 JSON: 기계 처리용. `labels`는 HTML 기본 240건, `complex_labels`는 별도 CSV 74건.",
                  "- 같은 이름의 CSV: 건별 AI 판정·현실성·메모.", "- `comparison.csv`: 314건의 모델 간 비교와 AI 다수결.",
                  "- `disagreements.csv`: 불일치 사례의 블라인드 정보와 세 모델의 판단 사유·현실성 점수를 나란히 수록.",
                  "- `audit/`: 로컬 모델 요청·원문 응답·실행 설정·실측 배치 실행시간, Codex 직접 작성 판정.", "",
                  "## 재현 및 해석", "", "블라인드 HTML과 복잡 사례 CSV만을 사례 입력으로 사용했습니다. 생성 스크립트와 원본 사례 파일, 블라인드 키, 기존 실험 결과는 수정하지 않았습니다. 정답과의 일치율도 계산하지 않았습니다.",
                  "Codex는 이전 세션에서 순차적으로 읽어 판정한 결과를 보존했습니다. Codex는 프로젝트 안내·스키마·템플릿·일부 실행 코드를 접했으므로 완전히 격리된 블라인드 세션이 아니며 audit/manifest.json에 이 조건을 기록했습니다. Qwen과 DeepSeek는 localhost Ollama에 서로의 답 없이 별도 셔플 순서로 10건씩 요청했습니다. 동일 프롬프트·배치 제시는 판단 상관과 순서효과를 만들 수 있어 독립된 인간 전문가 3명과 동등하지 않습니다.",
                  "2026-11-20에 중단 지점에서 재개했습니다. 재개 전 결과는 audit/resume_20261120/에 보관했고 로컬 모델 digest가 이전 실행과 같음을 확인했습니다. Qwen은 qwen2.5-coder:14b 기반, DeepSeek는 로컬 deepseek-r1:8b 기반 사용자 정의 별칭입니다. 모델 상세와 해시는 audit/manifest.json 및 audit/resume_20261120_manifest.json을 참조하세요.",
                  "Qwen 첫 20건의 속도·출력 형식 점검 결과는 audit/qwen/pilot/에 별도 보관하고 최종 집계에서 제외했습니다. 해당 20건을 최종 설정으로 다시 요청했습니다. 두 로컬 모델에는 같은 판정 지침과 context 4096을 사용했습니다. Qwen에는 25자 이내 메모와 압축 JSON 배열을 요청하고 DeepSeek에는 ID별 누락을 막는 객체 스키마를 적용했으며, 원문 실행 요청과 응답을 audit에 보존했습니다. 중단된 미완료 요청은 판정에서 제외했습니다.",
                  "DeepSeek의 첫 /api/chat 호출은 think=false에도 thinking 필드를 반환했고 10건에 약 450초가 걸렸습니다. 이 응답은 audit/deepseek/pilot_chat_think_false/에 보존하고 최종 집계에서 제외했습니다. 최종 314건은 동일한 DeepSeek 모델의 /api/generate raw 프롬프트에서 </think>를 미리 채우고 입력 ID마다 하나의 판정을 요구하는 JSON 스키마를 적용했습니다. 이 조건은 DeepSeek의 기본 추론 모드 및 Qwen의 /api/chat 프로토콜과 다릅니다. 보충 의견 요청에도 종료 표식을 적용했습니다. 원래 API 응답 필드와 실제 전송 요청을 audit에 보존했습니다.",
                  "사람 경력과 건별 판단시간은 null입니다. 로컬 모델 배치 실행시간은 사람 심사시간으로 환산하지 않았습니다. 새 사례 6건은 모두 AI가 작성한 fictional 자료이며 외부 실무 사례가 아닙니다.",
                  "Qwen의 첫 비용 의견은 사람 검토비용을 AI 비용으로 잘못 표현하고 가정을 반복하는 수준이어서, 원문을 보관하고 비용 정의·필요 자료를 구체적으로 묻는 별도 후속 요청으로 보완했습니다. 건별 라벨은 변경하지 않았습니다.",
                  "Qwen 후속 비용 의견도 가정의 타당성을 구체적으로 검증하지 못했고, 여러 변수를 동시에 바꾼다고 표현하면서 실제로는 한 변수씩 바꾸는 방법을 설명했습니다. 원문을 임의로 개선하지 않고 보존했습니다. 모델의 의견 수준 자체도 검토 대상입니다.",
                  "DeepSeek의 비용 의견은 사람 검토비용 $15를 AI 비용으로 설명하고 손실비율 1.0을 '매우 낮다'고 반대로 해석했으며, 제시한 민감도 계획은 구체적인 변화 분석을 제공하지 않았습니다. 소액비중 키의 철자 오타는 원본 JSON에 보존했고 의견서 표시 때만 항목에 연결했습니다.",
                  "Qwen의 새 사례 2건은 why_rules_fail에 '규칙에 위배되지 않습니다'라고만 답해 비정형 판단이 필요한 이유를 설명하지 못했습니다. 이 사례들은 AI 생성 초안으로 보존하며, 외부 타당성을 뒷받침하는 실무 사례나 완성된 비정형 평가 세트로 보지 않습니다.",
                  "AI 작성 가상 사례 중 Qwen과 DeepSeek 사례는 덴탈보험 맥락을 벗어난 건강·자동차·해외진료 사례가 포함됐습니다. DeepSeek의 가상 앱 사례도 청약 판단보다 해외 진료비 지급에 가까운 사실을 다룹니다. 사례 수를 충족해도 덴탈보험 외부 타당성을 보이는 결과는 아닙니다.",
                  "기존 importer는 AI와 사람을 구별하지 않고 expert_label/expert_time_sec로 병합하므로 실행하지 않았습니다. 이 하위 폴더에 격리하여 기본 cases/rater_results/*.json 검색에 자동 포함되지 않도록 했습니다. AI 비교 실험에서는 이 파일을 별도 AI 참조 라벨로 사용하고, 인간 검증 단계는 따로 수행해야 합니다.",
                  "입력 해시는 각 JSON의 provenance.inputs_sha256에 저장됩니다. 이 폴더의 AI 결과를 review_blind.html로 다시 가져오면 인간 수기 입력과 혼합될 수 있으므로 별도 AI 분석에 사용하세요.", "",
                  "## 재개 및 파일 검증", "", "저장소 루트에서 `python -X utf8 paper/eval/review/finish_ai_blind_raters.py --resume-all`로 저장된 최종 응답을 재사용하며 이어갈 수 있습니다. 다른 판정 프로세스가 실행 중이지 않을 때만 실행하세요.",
                  "완료 결과만 다시 검증하려면 `python -X utf8 paper/eval/review/validate_ai_blind_raters.py`를 실행합니다. 검증 결과는 `audit/validation_report.json`에 저장됩니다. 이 검증은 누락·중복·형식·원문 일치·입력 해시 검증이며 판정의 정답 여부나 외부 타당성 검증은 아닙니다.", "",
                  "## 불일치 사례", "", ", ".join(disagreements), ""])
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Validated: 3 x 314 labels, 6 fictional authored cases, {len(disagreements)} disagreements.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--supplement", choices=["qwen", "deepseek"])
    ap.add_argument("--model")
    ap.add_argument("--continue-after-qwen", action="store_true")
    ap.add_argument("--resume-all", action="store_true", help="Resume saved batches sequentially, build reports and validate")
    ap.add_argument("--cost-followup", choices=["qwen", "deepseek"])
    args = ap.parse_args()
    if args.resume_all:
        run("qwen", "qwen14b-16k:latest")
        if not (OUT / "audit" / "qwen_supplement.json").exists():
            supplement("qwen", "qwen14b-16k:latest")
            chat({"model": "qwen14b-16k:latest", "messages": [], "keep_alive": 0, "stream": False})
        run("deepseek", "deepseek-r1-16k:latest")
        supplement("deepseek", "deepseek-r1-16k:latest")
        chat({"model": "deepseek-r1-16k:latest", "messages": [], "keep_alive": 0, "stream": False})
        build()
        from validate_ai_blind_raters import validate
        validate()
    elif args.continue_after_qwen:
        # Qwen is already running in a separate exec session. Do not load both
        # large models together on the small GPU. Each sleep is interruptible.
        print("Waiting for Qwen labels, supplement, and model unload.", flush=True)
        while True:
            p = OUT / "rater_qwen.json"
            s = OUT / "audit" / "qwen_supplement.json"
            try:
                ready = p.exists() and s.exists() and json.loads(p.read_text(encoding="utf-8"))["provenance"]["complete"]
            except json.JSONDecodeError:
                ready = False  # Writer may be publishing its next checkpoint.
            if ready:
                with urllib.request.urlopen("http://127.0.0.1:11434/api/ps") as response:
                    loaded = json.load(response)["models"]
                if not any(m["name"] == "qwen14b-16k:latest" for m in loaded):
                    break
            time.sleep(5)
        # Only the two archived pilot batches are missing; all other responses
        # are reused. This ensures one consistent final prompt for every case.
        run("qwen", "qwen14b-16k:latest")
        run("deepseek", "deepseek-r1-16k:latest")
        supplement("deepseek", "deepseek-r1-16k:latest")
        chat({"model": "deepseek-r1-16k:latest", "messages": [], "keep_alive": 0, "stream": False})
        build()
    elif args.cost_followup:
        cost_followup(args.cost_followup, args.model)
    elif args.supplement:
        supplement(args.supplement, args.model)
    else:
        build()
