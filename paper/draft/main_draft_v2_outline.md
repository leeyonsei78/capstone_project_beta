# 논문 골격 v2 (2026-11-15) — 고액 심사에서 LLM 권고의 증분 가치와 신뢰 조건

> 이 파일은 `main_draft.md`(v0.2, 블록체인 조회 챗봇의 오류 분류체계 중심)를 **대체할 새 방향의 골격**이다.
> 기존 초안은 삭제하지 않았다. 아래 "7. 기존 초안 재활용"에서 무엇을 어디로 옮길지 정한다.
> 숫자는 전부 `[TBD]`다. 실험이 끝나기 전에는 어떤 성능 수치도 쓰지 않는다.

## 0. 한 문장 주장

> 규칙으로 결정되지 않는 고액 보험 청구·청약에서, LLM 권고는 규칙·전통 ML 기준선에 **어떤 조건에서 증분 정보를 더하는가**,
> 그 권고는 **얼마나 믿을 수 있는가**(보정·기권·강건성).

**쓰지 않는 표현:** "LLM이 고액을 판정한다", "심사를 효율화한다"(사람 효과 미검증), "블록체인이 ○○를 보장한다".
**쓰는 표현:** "권고(advice)의 품질", "증분 가치", "신뢰 조건", "자동화율 대 누수의 민감도 분석".

## 1. 가제와 초록 초안

**가제 (영문):** *When Does an LLM Advisor Add Value? Incremental Evidence, Calibration, and Robustness in High-Value Insurance Claim and Underwriting Review*

**초록 초안 (수치는 결과 후 채움):**

Insurers route low-value claims to straight-through processing and escalate high-value or ambiguous cases to human reviewers.
Whether a large language model (LLM) can usefully advise reviewers on the escalated cases is rarely tested against strong non-LLM baselines.
We evaluate LLM advice on [TBD: N] expert-labelled synthetic claim and underwriting cases, including a stratum of
[TBD: n] unstructured cases (disclosure breaches, exclusion clauses, narrative–code mismatch) authored and vetted by an insurance underwriter,
in which deterministic rules and a structured-feature classifier cannot decide.
We compare rules, a classifier, the LLM, and rule∧LLM agreement; vary the evidence given to the LLM (operational summary vs. itemised history vs. history plus policy text);
and report calibration, abstention ("insufficient evidence"), and robustness to prompt injection, history tampering, and counterfactual name/age changes.
Results: [TBD: incremental recall over the best baseline at matched precision, with 95% case-level bootstrap CIs; effect of evidence level; ECE; robustness].
The advisor adds value mainly when [TBD]; with summary-only evidence it [TBD].
All data are synthetic and labelled by a single expert (with a [TBD]% second-rater subsample), and we do not measure the effect of advice on human reviewers;
we therefore frame the findings as properties of the advice, not as evidence of improved human decisions.
We release the cases, labels, and scoring code [TBD: after privacy and permission checks].

## 2. 연구 질문 (v2)

| | 질문 | 주 지표 | 설계서 대응 |
|---|---|---|---|
| **RQ1** | 규칙·ML이 못 푸는 층(비정형)에서 LLM 권고가 **증분 정보**를 주는가? | 같은 정밀도에서의 재현율 차이, 기준선이 틀린 사례 중 LLM이 맞힌 비율 | RQ2 확장 + 기준선 신설 |
| **RQ2** | 근거 수준(요약 / 상세 / 상세+약관)이 권고 품질을 얼마나 좌우하는가? | 유형별 재현율 변화(C1→C2→C3). **편입(2026-11-16 결정): 약관 조건부 실험(T0→T1→T2)을 RQ2의 "근거의 형식" 축으로 포함** — 근거의 양뿐 아니라 제시 형식(정리된 조항 vs 실제 원문)이 정확도를 좌우하는지, 모델 크기별로 | 5.2, 5.9 |
| **RQ3** | 권고는 **믿을 만한가**? (보정, 기권, 근거 없이 확신하는 정도) | ECE, Brier, 기권률, 이상 건에 "정상"이라 답한 평균 확신도 | 6장 |
| **RQ4** | 권고는 **강건한가**? (인젝션, 이력 변조, 이름·연령 변경) | 판정 변경률, McNemar, 변조 전후 놓침 비율 | 5.3, 5.6 |
| 맥락 | 소액 자동 처리의 누수와 임계값 민감도 | 자동화율 대 누수 곡선 | 5.1 (맥락 설명으로 축소) |

**범위 밖(가정 또는 향후 과제):** 법적 허용, 스테이블코인의 존재, 사람 심사자에 대한 권고의 효과(IRB 필요), 실거래 정산, 블록체인의 필요성(데이터 원천은 변수로만 취급).

## 3. 사전 가설 (결과 보기 전에 고정 — 날짜 2026-11-15)

- **H1.** 상세 근거(C3)는 중복(A1)·분할(A4)에서 요약 근거(C2)보다 재현율이 높다.
- **H2.** 요약 근거에서는 A1·A4에서 재현율이 우연 수준에 가깝고, 그럼에도 "정상"에 높은 확신을 보인다(근거 없이 확신).
- **H3.** 인젝션이 판정을 바꾸는 비율은 작지만 0은 아니다.
- **H4.** 이력 변조는 이상을 놓치는 비율을 높인다.
- **H5.** (신규) 비정형 층에서 LLM은 규칙·분류기보다 재현율이 높지만, 정상 건을 조사로 보내는 비율(거짓 보류)도 높다.
- **H6.** (신규) 규칙∧LLM 합의 정책은 정밀도가 가장 높고 재현율은 가장 낮다(보수적 정책).
- **H7.** (신규) 모델 확신도는 비정형 층에서 과신 방향으로 보정이 나쁘다(ECE가 구조화 층보다 크다).
- **H8.** (RQ2 편입, 결과 확인 후 기록 — 사후 서술임을 명시) 같은 정보라도 실제 원문(T2)은 정리된 조항(T1)보다 정확도가 낮고, 작은 모델일수록 하락 폭이 크다. 관찰: gpt-4o −19pp, gpt-4o-mini −32pp, qwen14b −15pp(1회). 크기 순서는 qwen이 어긋남. 사전 가설 H11(T1에서 모델 격차 축소)은 반대로 틀렸고 그대로 보고.

> 어느 가설이 틀려도 그대로 보고한다. 보류 세트와 프롬프트는 본 실행 전에 동결한다.

## 4. 기여 (예상, 결과에 따라 조정)

1. **평가 자원:** 전문가가 검수한 고액 청구·청약 사례(구조화 + 비정형 층), 난이도 평정, 채점 코드.
2. **증분 가치의 위치 특정:** 규칙·분류기와 비교해 LLM이 이득을 주는 층과 주지 못하는 층.
3. **근거 수준 효과:** 운영 코드가 보내는 요약만으로는 판단할 수 없는 유형이 있음을 정량화.
4. **신뢰 조건:** 보정, 기권, 강건성을 한 틀에서 보고.

## 5. 논문 구성

| 절 | 내용 | 비고 |
|---|---|---|
| 1. Introduction | 소액 자동 처리, 고액 에스컬레이션, 문제 제기, 기여 | 선행연구와의 차별점은 "증분 가치·근거 수준·신뢰 조건" |
| 2. Related Work | (a) 보험 심사·사기 탐지의 LLM, (b) 기권·learning-to-defer, (c) 자동화 편향, (d) 인젝션·공정성 | 원문 정독한 것만 인용. 아래 8장 참조 |
| 3. Setting and Cases | 단계 구조, 청구·청약 규칙, 사례 설계, 비정형 층 작성 절차, 라벨링(블라인드, 두 번째 라벨러, κ) | 합성임을 3장에서 명시 |
| 4. Methods | 기준선(규칙·분류기), LLM 조건 C1~C3, 정책(규칙∧LLM), 지표, 통계 | 설계서 5·6장 |
| 5. Results | RQ1~RQ4 순서. RQ2 안에 5.2.1 근거의 양(C1→C3), 5.2.2 근거의 형식(약관 T0→T1→T2, 3개 모델) | 표: 기준선 대비, 근거 수준별, 보정, 강건성 |
| 6. Discussion | 어디서 이득이 있고 어디서 없는가, 실무 설계 함의 | 사람 효과는 미검증이라고 명시 |
| 7. Limitations | 합성, 라벨러 1~2인, 단일 벤더 중심, 사람 실험 없음, 가정치 | 설계서 10장 |
| 8. Conclusion | | |
| Appendix | 프롬프트 원문, 사례 예시, 오류 유형 표, 제시 신뢰성 보조 실험(E1~E4) | |

## 6. 실험 상태와 남은 일

| 항목 | 상태 | 비고 |
|---|---|---|
| 사례 생성기, 규칙 기준선 | 완료 | `gen_cases.py`, `rules_baseline.py` |
| 권고 실행기(C1~C3), 채점기, 정책·의존도·공정성 | 완료 | 테스트 통과 |
| 블라인드 시트 + 소요시간 열 | 완료 | 사용자 기입 대기 |
| **HTML 라벨링 시트(다중 심사자)** + 가져오기(κ, 다수결, 시간) | 완료 | `cases/review_blind.html`, `import_rater_results.py` |
| 비정형 사례 템플릿 | 완료 | `cases/expert_cases_template.csv`, 사용자 작성·검수 대기 |
| **비정형 로더** | **미구현** | 템플릿 열 확정 후 작성 |
| **전통 ML 기준선(로지스틱·GBM)** | **미구현** | 구조화 특성만 사용 |
| **두 번째 LLM 벤더** | **미구현** | |
| **C3에 약관 발췌 포함 조건 추가** | **미구현** | 비정형 층 전용 |
| 두 번째 라벨러(20%) | 미정 | 사용자가 동료 섭외 |
| 회사 실수치 범위(심사 시간·단가·비중) | 사용자 제공 대기 | 비용 민감도 분석용 |
| 제시 신뢰성 보조 실험 본 실행 | 보류 | 효과 크기 확인 후 1회만 |
| **AI-proxy 1차 권고 판정(codex·qwen·deepseek, 블라인드 314건)** | **완료·검증·동결** | 11장 참조. codex 91.4%만 유효, 정답대비 채점·인젝션·text_only까지 `accuracy_vs_ground_truth.{md,json}` |
| **별도 보조 실험: 치과 약관 조건부 심사** (설계서 5.9, `run_terms.py`) | 완료(gpt-4o/mini) + T2 신규 | 세 프로파일(A/B/C)을 2026-11-15 실제 약관 원문과 대조 — B/C는 일치, A는 브릿지 규칙이 4개 중 3개사와 불일치해 수정·재생성·재실행함(`paper/data/terms_profile_verification.md`). **T2(실제 원문 발췌, 합성 요약 아님) 추가 — T1→T2에서 정확도가 크게 떨어짐**(gpt-4o 88%→69%, gpt-4o-mini 67%→35%, 거의 T0 수준으로 복귀): 같은 정보라도 제시 형식(깔끔한 요약 vs 실제 문서)에 따라 작은 모델일수록 훨씬 민감하다는, RQ2("근거 수준")와 자연스럽게 연결되는 독립 결과. 본문 위치는 **RQ2 편입으로 확정(2026-11-16, 5.2.2)**. qwen14b-16k(로컬, 1회) 완료: T0 7%(87%가 기권)→T1 48%→T2 33%, 적응(adaptation) 17%→0%, 과지급 26%→47% — T1→T2 하락 패턴이 세 모델 모두에서 재현됨(단 qwen은 1회 실행이라 CI가 넓음). |

## 7. 기존 초안(`main_draft.md`) 재활용 계획

| 기존 내용 | v2에서의 위치 |
|---|---|
| TLPE E1~E4(배열 누락, 시간 연산, 이전 결과 재사용, 타임존) | Appendix: "도구 계층이 사실을 전달할 때의 오류와 완화" — 본문은 한두 문단 요약 |
| E5(응답 표현 가변성), E6(UI 조건부 로직) | LLM 오류가 아니라 통합 로직 오류이므로 본문에서 제외, 필요하면 부록 한 줄 |
| M1~M4 완화 | 부록. 본문에서는 "사전계산 문자열을 LLM에게 주는 설계"로만 언급 |
| 블록체인 아키텍처(§3) | 사례 배경으로 축소. 블록체인은 데이터 원천일 뿐이며 결과에 변수로 넣지 않음 |
| 블록체인 대 DB 비교 | 한계 한 줄 또는 이력 변조 실험(RQ4) 안에서만 사용 |
| 참고문헌 | 보험·LLM 부분만 유지, 블록체인 부분은 배경 인용으로 축소 |

## 8. 선행연구 확인 계획 (원문을 읽은 것만 인용)

- 원문 정독 완료: Islayem 외(2025, *Scientific Reports*). 한계와 비교는 `related_work_notes.md` 5절.
- 초록·요약 수준만 본 것(원문 미독, 인용 전 확인 필요): Roy & Singh(arXiv 2602.13213), UNDERWRITE(arXiv 2602.00456), ATA(arXiv 2510.16381), DeCCaF(TMLR 2024).
- **"Towards Trusted Automated Insurance"**: 같은 제목을 찾지 못함. 출처 재확인 전 인용 금지.
- 투고 전 Scopus/WoS(연세대 도서관)로 재검색해 최근 6개월 내 겹치는 논문이 없는지 확인.

## 9. 투고 후보 저널 (확인 절차)

저널 이름만 적고 **등재 여부·범위·APC는 직접 확인한 것이 아니다.** 확인 순서:
1. 학과 졸업 요건의 인정 기준(DB, 분위, 출판사 제한)을 먼저 확인한다.
2. 후보 저널을 WoS Master Journal List와 JCR에서 SCIE 등재 상태와 분위를 확인한다.
3. 최근 2년 게재 논문 중 "LLM + 보험/금융 심사" 유형이 있는지 3~5편을 훑어 범위 적합성을 본다.
4. 후보 예: *Applied Sciences*, *Future Internet*(이전 초안 대상), 그 외 금융·의사결정지원 계열 저널은 위 절차로 발굴.

## 10. 일정

| 날짜 | 작업 |
|---|---|
| ~11-18 | 사용자: 블라인드 시트 기입(소요시간 포함), 비정형 사례 작성. 나: 비정형 로더, ML 기준선 |
| 11-19~22 | 본 실행(C1~C3, 3회), 두 번째 벤더, 채점 |
| 11-23~27 | 분석, 발표 자료(설계 + 규칙 기준선 + 초기 결과, 완료/향후 구분) |
| 11-28 | 발표 |
| 12월 | 초안 작성, 저널 확인, 투고 |

## 11. 1차 결과 반영 — 고액 2단계 구조에서 LLM 1차 권고 (2026-11-20)

AI-proxy 블라인드 판정(codex·qwen·deepseek가 각 314건 = 세 LLM이 1차 권고자로서 심사)이
완료·검증·동결됐다(dataset_id `aa25553d314f`, 총 942판정). 블라인드 동결 후 심어둔 정답 대비로
채점한 결과를 아래 결론으로 정리한다. 데이터·수치: `paper/eval/review/cases/rater_results/ai_proxy_20261119/accuracy_vs_ground_truth.{md,json}`.

**결론 문구 (결과 보고용):**

> 소액(한도 20% 이하) 청구는 규칙으로 자동 지급하고, **고액(20% 초과)은 LLM이 1차 심사 권고를,
> 사람이 최종 판단**을 하는 2단계 구조를 평가했다. 이 구조의 1차 권고자로서, **규칙 기준선이 0%
> 탐지하던 판단 의존 이상(A2 코드↔설명 불일치, 업코딩, text_only)을 codex가 100% 포착**했고
> (전체 91.4%, 프롬프트 인젝션 11/11 저항), 이는 규칙-only 대비 1차 선별의 증분 가치를 실측으로 보인다.
> 다만 ⓐ 본 결과는 합성 사례·AI proxy이며, ⓑ A3(금액 과다) 55%처럼 재료·요율 없이 금액만으로는
> codex조차 확정하지 못하는 **판단 의존 범주**가 남고, ⓒ 약한 로컬 모델(qwen 53.8%·deepseek 55.7%,
> 인젝션 피격)은 near-chance로 **구조의 안전성이 모델 역량에 민감**하다. 1차 권고 품질까지가 본 실험의
> 주장 범위이며, **사람 최종 판단의 개선 효과는 reader study(IRB)로 남긴다.**

**주의(서술 규칙):** "효율화", "사람 최종 판단 개선", "codex가 고액을 판정한다"는 표현은 쓰지 않는다
(0장 규칙과 일치). ⓒ(모델 역량 민감성)는 ⑮단계 "약한 모델로도 유의미" 방향과 상충하므로, 본문에서는
"capable LLM에서 1차 선별 가치가 확인되며, 약한 모델은 안전하지 않다"로 정직하게 서술한다.
