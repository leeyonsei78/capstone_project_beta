"""
Write the template the domain expert fills in to author/vet UNSTRUCTURED cases -- the layer where
deterministic rules cannot decide and an advisor might add information (disclosure breaches, exclusion /
reduction clauses, causality, narrative-vs-code mismatch).

  python paper/eval/review/make_expert_template.py

Writes cases/expert_cases_template.csv (UTF-8 with BOM so Excel shows Korean correctly) with two worked
EXAMPLE rows (clearly marked, delete them before use) and an empty body. Nothing here is imported into the
experiment yet: once the expert confirms the column set is workable, a loader will map these rows onto the
case JSON schema (cases_claims.json / cases_apps.json) so run_advisor.py can score them like the others.

Rules for the expert:
  * Use fictional or fully de-identified content. Do not paste real policyholder names, IDs, hospital names
    or anything from company systems; check your company's policy before adapting a real case.
  * Decide the label FIRST from the facts as written, then fill the reasoning columns.
  * The advisor sees only the columns marked [ADVISOR SEES]. Gold columns are never shown to it.
"""
import csv
from pathlib import Path

OUT = Path(__file__).parent / "cases"

COLUMNS = [
    ("case_no", "U001 형식 일련번호"),
    ("type", "claim(청구) / app(청약)"),
    # ---- [ADVISOR SEES] ----
    ("[ADVISOR SEES] 상품·담보 요약", "담보명, 보장한도, 가입 경과일, 면책/감액 기간 등 판단에 필요한 계약 사실"),
    ("[ADVISOR SEES] 이번 건 사실", "청구: 치료코드·명, 청구액 / 청약: 연령, 월보험료, 담보 수"),
    ("[ADVISOR SEES] 서술(비정형)", "진단서 요지, 치료 경위, 고지사항 답변, 청구 사유 등 자유 서술 (3~8문장)"),
    ("[ADVISOR SEES] 관련 약관 발췌", "판단에 쓰이는 약관 조항을 짧게 (없으면 공란)"),
    ("[ADVISOR SEES] 과거 이력", "날짜(며칠 전)·코드·금액·처리상태를 줄 단위로 / 없으면 '없음'"),
    # ---- gold (never shown) ----
    ("정답(approve/investigate)", "approve = 그대로 처리 가능, investigate = 심사자가 추가 조사/보완 필요"),
    ("세부처리", "지급 / 부분지급 / 부지급 / 보완요청 / 계약인수 / 조건부인수 / 거절 중 해당 값 (참고용)"),
    ("판단근거", "정답을 낸 핵심 이유 한두 문장"),
    ("규칙으로 못 잡는 이유", "예: 서술과 코드의 의미 불일치, 고지의무 해석, 면책 요건 해당 여부 등"),
    ("필요한 근거 수준", "summary(이력 요약만으로 판단 가능) / detail(이력 상세 필요) / narrative(서술 해석 필요)"),
    ("난이도(1-5)", "담당자 입장에서 실제로 판단하기 어려운 정도"),
    ("현실성(1-5)", "실무에서 나올 법한 사례인가"),
    ("실제 건 변형 여부", "fictional(완전 가상) / adapted(실제 건을 익명화·변형, 사내 규정 확인함)"),
    ("소요시간(초)", "정답을 내리기까지 직접 잰 시간"),
    ("메모", "자유 기입"),
]

EXAMPLES = [
    ["EXAMPLE-1 (삭제할 것)", "claim",
     "치아보험 임플란트 담보, 보장한도 $2,000, 가입 후 95일, 가입 후 180일 미만 감액(50%) 조항",
     "D6010 임플란트 식립, 청구액 $1,800",
     "환자는 3년 전 발치 후 방치하다 최근 임플란트를 시행했다고 서술. 진료기록상 발치일은 가입 전.",
     "제12조: 가입 후 180일 이내 보철 치료는 보험금의 50%만 지급한다.",
     "없음",
     "investigate", "부분지급",
     "감액 기간에 해당하나 청구액은 전액으로 접수됨. 발치가 가입 전이어도 임플란트 치료일은 가입 후라 감액 대상.",
     "금액·이력 규칙으로는 정상 범위, 약관 감액 조항 적용 여부는 서술과 계약일 해석이 필요",
     "narrative", "3", "4", "fictional", "", "예시 행"],
    ["EXAMPLE-2 (삭제할 것)", "app",
     "치아보험 보철 담보 포함, 보장한도 $3,000, 월 보험료 $60",
     "42세, 담보 2개(임플란트·크라운), 활성 증권 0건",
     "고지사항: 최근 5년간 치과 치료 경험 '없음'으로 답변. 첨부 설문에 '최근 잇몸 치료를 위해 병원을 다닌 적 있다'는 자유 기재.",
     "고지의무: 중요 사항을 사실과 다르게 알린 경우 계약을 해지하거나 보장을 제한할 수 있다.",
     "과거 청약 없음",
     "investigate", "조건부인수",
     "정형 항목('경험 없음')과 자유 기재가 모순. 규칙상 담보 2개라 자동승인되지만 고지 위반 가능성이 있음.",
     "규칙은 담보 개수만 보므로 자동승인, 두 문장의 모순은 서술 해석이 필요",
     "narrative", "4", "4", "fictional", "", "예시 행"],
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "expert_cases_template.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([c for c, _ in COLUMNS])
        w.writerow([d for _, d in COLUMNS])     # row 2: how to fill each column
        w.writerows(EXAMPLES)
    print(f"wrote {path} ({len(COLUMNS)} columns, {len(EXAMPLES)} example rows)")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
