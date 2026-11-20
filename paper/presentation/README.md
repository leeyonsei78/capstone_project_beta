# 발표자료 — InsureChain 덱에 추가한 슬라이드 (복구본)

이 폴더는 교수 발표용 Slides 아티팩트에 **이번에 추가한 슬라이드의 소스 복구본**이다.
덱 자체(97파일)는 claude.ai Slides 아티팩트에 있고, 여기엔 신규 5장 + 인덱스만 보관한다.

- **발표 아티팩트(원본, 전체 덱)**: https://claude.ai/artifact/AoVW3rbXp2UWJZHxp4pAqX
- **논문 아티팩트(2부 구조)**: https://claude.ai/artifact/P8HbAMvVrN9ryku9D8RWHQ
- 논문 본문: `paper/draft/main_draft_ko.md`(한글 2부), `paper/draft/first-pass-reviewer.html`(논문 아티팩트 소스)

## 추가한 슬laides (tech-proof 뒤 등, 2026-11-21)
- `slides/exp-proof.html` — 구현을 넘어 314건 블라인드 실험으로 입증(사업화 객관 증거)
- `slides/exp-results.html` — 실험 결과표(계약심사 96.7%·고액청구 86%·규칙0%범주 100%·인젝션 0/11)
- `slides/uw-scenario.html` — 혈압·콜레스테롤·흡연 심사 사례(자동승인 vs 수동심사). "보완요청"은 사용자 요청으로 제외.
- `slides/bc-integrity.html` — 블록체인=정확도 아닌 무결성·감사가능성
- `slides/exp-cost.html` — 건당 비용 gpt-4o $0.00106(6건 실측)·314건≈$0.33
- 각 슬라이드 각주에 "출처:" 명시(본 연구 실험 / OpenAI 공개 요율 / Islayem 2025 / 구현 코드).
- `deck.json` — 인덱스 복사본(order에 위 5개 id 삽입된 상태).

## 다음에 이어서 할 것
- ⚠️ 페이지 번호: 기존 슬라이드 "/56", 신규 "/59~/61" 불일치 → 발표 확정 시 전체 재번호.
- ★2 재현성: 메인 314건 gpt-4o 토큰 API 1회 재실행(비용 ≈$0.33, ~10분) → 실측 비용·재현 결과 확보.
  키는 `blockchain-dental/.env`의 OPENAI_API_KEY. 파일럿 스크립트 패턴은 scratchpad `pilot_cost.py`(세션 소멸),
  `run_model_raters.py`(SYSTEM+load_blind_rows)·`run_advisor.call_model`(토큰 usage) 재사용.
- 보완(★1 사람검증 30~40건, ★3 보정·ML 기준선, ★4 ClaimPilot/InsClaimBench 원문) 추후 논의.
