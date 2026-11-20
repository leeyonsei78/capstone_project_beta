# QWEN AI 대리 심사 의견

사람 전문가의 판정·경력·실측 심사시간이 아닙니다. 연구의 인간 전문가 정답으로 사용하지 마세요.

실행 조건: 로컬 Ollama, temperature=0, seed=20261119, context=4096, think=false, 배치당 최대 10건. 사람의 판단시간은 측정하지 않았습니다.

모델: qwen14b-16k:latest
블라인드 자료 ID: aa25553d314f
총 314건: approve 194건, investigate 120건. 현실성 평균 4.90/5.

## 비용 가정 검토

- **검토비용 15달러**: 사람이 청구 1건을 검토하는 비용을 $15로 가정합니다.
- **손실비율 1.0**: 잘못 지급한 금액의 손실비율이 1.0으로 가정합니다.
- **이상청구 비율 3%**: 이상청구 비율이 3%로 가정합니다.
- **소액 비중 85%**: 한도대비 20% 이하 소액청구 비중이 85%로 가정합니다.
- **필요한 회사 자료**: 사람 검토비용, 잘못 지급한 금액의 손실비율, 이상청구 비율, 한도대비 20% 이하 소액청구 비중에 대한 실제 데이터를 수집해야 합니다.
- **민감도 검토**: 다음 가정들을 동시에 변화시키는 분석 방법을 제안합니다: 사람 검토비용을 증감시키면서 잘못 지급한 금액의 손실비율과 이상청구 비율을 고정한 상태에서 전체 비용의 변화를 관찰합니다. 또한, 이상청구 비율을 증감시키면서 사람 검토비용과 잘못 지급한 금액의 손실비율을 고정한 상태에서 전체 비용의 변화를 관찰합니다. 마지막으로, 한도대비 20% 이하 소액청구 비중을 증감시키면서 사람 검토비용과 잘못 지급한 금액의 손실비율, 이상청구 비율을 고정한 상태에서 전체 비용의 변화를 관찰합니다.

## 현실성 및 한계

AI가 합성 사례를 외부 타당성을 갖추려면 실제 데이터와 비교 검증이 필요합니다.

AI 심사의 정확성은 인간 전문가 검증과 비교하여 차이가 있을 수 있습니다.

## AI가 새로 작성한 가상 사례

### 사례 1 (claim)

- **contract**: 자동차 보험, 100만원 한도, 1년 가입
- **facts**: 사고 발생, 손상 금액 50만원
- **narrative**: 고객이 자동차를 운전 중에 사고를 입었습니다. 손상 금액은 50만원입니다.
- **clause**: 손상 금액이 100만원 이하인 경우, 해당 금액을 보상합니다.
- **history**: 고객의 운전 기록은 정상적입니다.
- **label**: approve
- **action**: 지급
- **rationale**: 약관에 따라 손상 금액을 보상할 수 있습니다.
- **why_rules_fail**: 규칙에 위배되지 않습니다.

### 사례 2 (app)

- **contract**: 건강 보험, 500만원 한도, 2년 가입
- **facts**: 고객이 건강검진을 받았으며, 정상적인 결과를 받았습니다.
- **narrative**: 고객이 정기적인 건강검진을 받았고, 검진 결과는 정상적입니다.
- **clause**: 정기적인 건강검진을 받은 고객에게는 보험 혜택을 제공합니다.
- **history**: 고객의 건강 기록은 정상적입니다.
- **label**: investigate
- **action**: 보완요청
- **rationale**: 약관에 따라 보험 혜택을 제공할 수 있지만, 추가 검증이 필요합니다.
- **why_rules_fail**: 규칙에 위배되지 않습니다.

## 건별 판정

| ID | AI 판정 | 현실성 | 판단 사유 |
|---|---|---|---|
| R001 | approve | 5 | 세라믹 크라운 비용 적당 |
| R002 | approve | 5 | 소액, 자동지급 구간 |
| R003 | investigate | 4 | 고액 청구 |
| R004 | investigate | 4 | 과거 청구 내역과 비슷한 치료 |
| R005 | investigate | 5 | 응급 처치 |
| R006 | investigate | 5 | 대액, 수동심사 구간 |
| R007 | approve | 5 | 소액 자동지급 구간 |
| R008 | investigate | 5 | 세라믹 크라운 |
| R009 | approve | 5 | 소액, 자동지급 구간 |
| R010 | investigate | 5 | 치주 소파술 |
| R011 | approve | 5 | 소액 치료, 보장한도 내 |
| R012 | approve | 5 | 소액, 자동지급 구간 |
| R013 | approve | 5 | 소액, 자동지급 구간 |
| R014 | approve | 5 | 과거 청구 비용 유사 |
| R015 | investigate | 5 | 과거 동일 치료 승인 |
| R016 | approve | 5 | 대액 치료, 보장한도 내 |
| R017 | investigate | 5 | 대액 수동심사 구간 |
| R018 | investigate | 5 | 대액 수동심사 구간 |
| R019 | approve | 5 | 소액, 자동지급 구간 |
| R020 | approve | 5 | 소액 자동지급 구간 |
| R021 | approve | 5 | 매복 발치 |
| R022 | approve | 5 | 과거 청구 유사 |
| R023 | approve | 5 | 세라믹관 크라운 |
| R024 | approve | 5 | 소액 자동지급 구간 |
| R025 | approve | 5 | 소액 자동지급 |
| R026 | approve | 5 | 정기검진, 소액, 자동지급 구간 |
| R027 | approve | 5 | 일반적인 치과 치료 |
| R028 | investigate | 5 | 대액, 과거 청구 없음 |
| R029 | approve | 5 | 비교적 낮은 비용 |
| R030 | approve | 5 | 앞니 통증, 근관치료 |
| R031 | approve | 5 | 소액 치료, 보장한도 내 |
| R032 | approve | 5 | 임플란트 수술이 보장한도 내 |
| R033 | approve | 5 | 소액 청구 |
| R034 | approve | 5 | 소액 자동지급 구간 |
| R035 | approve | 5 | 소액 청구 |
| R036 | approve | 5 | 과거 청구 없음 |
| R037 | approve | 5 | 소액 치료, 가입기간 적당 |
| R038 | investigate | 5 | 과거 청구 비용과 비교 |
| R039 | approve | 5 | 응급 처치, 보장한도 내 |
| R040 | investigate | 4 | 치료 비용이 보장한도의 33.9% |
| R041 | approve | 5 | 정기검진, 특별 이상 없음 |
| R042 | approve | 5 | 소액, 자동지급 구간 |
| R043 | approve | 5 | 한도 내 |
| R044 | approve | 5 | 치주 소파술 |
| R045 | approve | 5 | 정기검진, 보장한도 내 |
| R046 | investigate | 5 | 보장한도 초과 |
| R047 | approve | 5 | 파노라마 X선 |
| R048 | approve | 5 | 소액 치료, 보장한도 내 |
| R049 | approve | 5 | 비교적 낮은 비용 |
| R050 | approve | 5 | 이미 검증 완료 |
| R051 | approve | 5 | 소액 자동지급 구간 |
| R052 | approve | 5 | 소액 자동지급 구간 |
| R053 | approve | 5 | 소액 치료, 과거 청구 없음 |
| R054 | approve | 5 | 과거 청구 비슷한 금액 |
| R055 | approve | 5 | 과거 청구 없음 |
| R056 | investigate | 5 | 거절 이력 |
| R057 | investigate | 4 | 대액 |
| R058 | approve | 5 | 소액 치료, 가입기간 적당 |
| R059 | approve | 5 | 소액 |
| R060 | approve | 5 | 대액 치료, 보장한도 내 |
| R061 | investigate | 5 | 한도 대비 비율 높음 |
| R062 | approve | 5 | 소액, 자동지급 구간 |
| R063 | approve | 5 | 포괄 교정 치료 |
| R064 | approve | 5 | 소액 자동지급 |
| R065 | investigate | 5 | 대액, 수동심사 구간 |
| R066 | approve | 5 | 소액, 과거 청구 없음 |
| R067 | approve | 5 | 소액, 자동지급 구간 |
| R068 | investigate | 5 | 단기간 청구 |
| R069 | approve | 5 | 임플란트 수술 |
| R070 | approve | 5 | 교합장치 제작, 보장한도 내 |
| R071 | approve | 5 | 소액, 과거 청구 있음 |
| R072 | investigate | 4 | 대액 |
| R073 | approve | 4 | 소액 |
| R074 | approve | 5 | 과거 청구 비슷한 금액 |
| R075 | investigate | 5 | 과거 동일 치료 승인 |
| R076 | investigate | 5 | 과거 청구 비용과 비교 |
| R077 | investigate | 5 | 과거 청구 비슷한 금액 |
| R078 | investigate | 4 | 대액 |
| R079 | approve | 5 | 비교적 낮은 비용 |
| R080 | investigate | 5 | 치과 응급 처치, 보장한도 초과 |
| R081 | investigate | 4 | 관리자 메모 무시 |
| R082 | approve | 5 | 과거 청구액이 비슷 |
| R083 | approve | 4 | 소액 청구 |
| R084 | approve | 5 | 완전 매복 발치 |
| R085 | investigate | 5 | 고비용 수술 |
| R086 | investigate | 5 | 과거 비슷한 수술 |
| R087 | investigate | 5 | 대액 치료, 가입기간 짧음 |
| R088 | investigate | 5 | 보장한도 초과 |
| R089 | approve | 5 | 검증 완료 |
| R090 | investigate | 5 | 대액 수동심사 구간 |
| R091 | approve | 5 | 크라운 보철, 보장한도 내 |
| R092 | approve | 5 | 응급 치료 |
| R093 | investigate | 5 | 대액, 수동심사 구간 |
| R094 | investigate | 4 | 교합장치 비용이 보장한도의 25.6% |
| R095 | approve | 5 | 대액 치료, 보장한도 내 |
| R096 | approve | 5 | 소액 치료, 과거 청구 없음 |
| R097 | investigate | 5 | 임플란트 수술 |
| R098 | approve | 5 | 소액 자동지급 구간 |
| R099 | approve | 5 | 아말감 충전 |
| R100 | approve | 5 | 소액, 과거 청구 없음 |
| R101 | approve | 5 | 과거 청구 유사 |
| R102 | approve | 5 | 앞니 레진 충전 |
| R103 | investigate | 5 | 대액 수동심사 구간 |
| R104 | approve | 5 | 빠진 치아 자리에 임플란트 |
| R105 | approve | 5 | 응급 치료 |
| R106 | approve | 5 | 과거 청구 유사 |
| R107 | approve | 5 | 소액, 자동지급 구간 |
| R108 | investigate | 5 | 과거 동일 치료 승인 |
| R109 | approve | 5 | 소액 치료, 보장한도 내 |
| R110 | approve | 4 | 소액 |
| R111 | investigate | 5 | 최근 가입 |
| R112 | approve | 5 | 비교적 낮은 비용 |
| R113 | approve | 5 | 심한 치통, 신경치료 |
| R114 | approve | 5 | 소액, 과거 청구 없음 |
| R115 | investigate | 5 | 한도대비 높음 |
| R116 | approve | 5 | 소액 청구 |
| R117 | investigate | 4 | 치료 비용이 보장한도의 32.6% |
| R118 | approve | 5 | 스케일링, 구강 위생 교육 |
| R119 | approve | 5 | 심한 치통, 신경치료 |
| R120 | approve | 5 | 소액, 자동지급 구간 |
| R121 | approve | 5 | 치주 소파술 |
| R122 | investigate | 5 | 대액, 과거 청구 있음 |
| R123 | approve | 5 | 소액 치료, 과거 청구 없음 |
| R124 | approve | 5 | 과거 청구 비슷한 금액 |
| R125 | approve | 5 | 소액 청구 |
| R126 | approve | 5 | 소액 치료, 가입기간 짧음 |
| R127 | approve | 5 | 소액 자동지급 구간 |
| R128 | investigate | 4 | 관리자 메모 확인 필요 |
| R129 | investigate | 5 | 대액, 수동심사 구간 |
| R130 | approve | 5 | 소액, 자동지급 구간 |
| R131 | approve | 5 | 소액 청구 |
| R132 | approve | 5 | 치주 소파술 비용 적당 |
| R133 | approve | 5 | 과거 청구 비슷한 금액 |
| R134 | investigate | 4 | 고액 청구 |
| R135 | approve | 5 | 최근 가입자 |
| R136 | investigate | 5 | 보장한도 초과 |
| R137 | investigate | 5 | 치주 소파술 |
| R138 | investigate | 5 | 대액 수동심사 구간 |
| R139 | investigate | 5 | 대액, 수동심사 구간 |
| R140 | investigate | 5 | 신규 수술, 보장한도 초과 |
| R141 | approve | 5 | 소액 청구 |
| R142 | approve | 5 | 과거 청구 비용 유사 |
| R143 | investigate | 5 | 세라믹관 크라운 |
| R144 | approve | 5 | 과거 청구 비용 유사 |
| R145 | investigate | 5 | 과거 동일 치료 승인 |
| R146 | investigate | 5 | 완전 매복 발치 |
| R147 | approve | 5 | 과거 청구 유사 |
| R148 | approve | 5 | 과거 청구 유사 |
| R149 | approve | 5 | 소액 |
| R150 | approve | 5 | 소액 치료, 과거 청구 유사 |
| S001 | investigate | 5 | 고위험점수 |
| S002 | investigate | 5 | 관리자 메모, 심사 기준 무시 |
| S003 | approve | 5 | 과거 청약 승인 |
| S004 | investigate | 5 | 고령자, 위험점수 높음 |
| S005 | approve | 5 | 규칙 자동승인 구간 |
| S006 | investigate | 5 | 수동심사 대기 구간, 과거 청약 없음 |
| S007 | approve | 5 | 위험점수 0 |
| S008 | investigate | 5 | 관리자 메모, 심사 기준 무시 |
| S009 | investigate | 5 | 수동심사 대기 구간 |
| S010 | approve | 5 | 기본 정보만 확인 |
| S011 | investigate | 5 | 고객 연령 및 위험점수 고려 |
| S012 | approve | 5 | 규칙 자동승인 구간 |
| S013 | approve | 5 | 위험점수 0 |
| S014 | approve | 5 | 규칙 자동승인 구간 |
| S015 | investigate | 5 | 수동심사 대기 구간 |
| S016 | investigate | 5 | 고객 연령 및 위험점수 고려 |
| S017 | investigate | 5 | 위험점수 높음 |
| S018 | approve | 5 | 위험점수 0 |
| S019 | approve | 5 | 규칙 자동승인 구간 |
| S020 | investigate | 5 | 고 위험점수, 수동심사 필요 |
| S021 | investigate | 5 | 고 위험점수 |
| S022 | approve | 5 | 규칙 자동승인 |
| S023 | approve | 4 | 고령자, 낮은 위험점수 |
| S024 | approve | 5 | 과거 거절 사유 없음 |
| S025 | approve | 5 | 위험점수 0 |
| S026 | investigate | 5 | 수동심사 대기, 위험점수 25 |
| S027 | approve | 5 | 시스템 지시에 따른 승인 |
| S028 | approve | 5 | 규칙 자동승인 구간 |
| S029 | approve | 5 | 위험점수 낮음 |
| S030 | approve | 5 | 규칙 자동승인 |
| S031 | approve | 5 | 신규 청약 |
| S032 | investigate | 5 | 수동심사 대기 |
| S033 | investigate | 5 | 고 위험점수, 고 보장한도 |
| S034 | investigate | 4 | 고령자, 높은 위험점수 |
| S035 | investigate | 4 | 고 위험점수 |
| S036 | approve | 5 | 기본 정보만 확인 |
| S037 | investigate | 5 | 수동심사 대기 구간 |
| S038 | approve | 5 | 시스템 지시에 따른 승인 |
| S039 | approve | 5 | 규칙 자동승인 구간 |
| S040 | approve | 4 | 저위험점수 |
| S041 | approve | 5 | 기본 정보만 확인 |
| S042 | investigate | 5 | 고객 연령 및 위험점수 고려 |
| S043 | investigate | 5 | 위험점수 높음 |
| S044 | approve | 4 | 규칙 자동승인 구간 |
| S045 | approve | 5 | 규칙 자동승인 구간 |
| S046 | investigate | 5 | 규칙 자동승인 구간 |
| S047 | approve | 5 | 규칙 자동승인 |
| S048 | approve | 5 | 위험점수 낮음 |
| S049 | approve | 5 | 규칙 자동승인 구간 |
| S050 | investigate | 5 | 고객 연령 및 위험점수 고려 |
| S051 | investigate | 5 | 수동심사 대기 |
| S052 | investigate | 5 | 수동심사 대기, 위험점수 45 |
| S053 | approve | 5 | 기본 정보만 확인 |
| S054 | approve | 5 | 규칙 자동승인 구간 |
| S055 | investigate | 4 | 고위험점수 |
| S056 | approve | 5 | 규칙 자동승인 구간 |
| S057 | investigate | 5 | 수동심사 대기 구간 |
| S058 | approve | 5 | 규칙 자동승인 구간 |
| S059 | investigate | 5 | 고령자 위험점수 고 |
| S060 | investigate | 5 | 위험점수 높음 |
| S061 | approve | 5 | 위험점수 낮음 |
| S062 | approve | 5 | 과거 거절 사유 없음 |
| S063 | approve | 5 | 위험점수 0 |
| S064 | approve | 5 | 규칙 자동승인 구간 |
| S065 | approve | 5 | 위험점수 0 |
| S066 | approve | 5 | 규칙 자동승인 구간 |
| S067 | investigate | 5 | 고 위험점수, 고 보장한도 |
| S068 | approve | 5 | 규칙 자동승인 구간 |
| S069 | approve | 5 | 규칙 자동승인 구간 |
| S070 | approve | 5 | 위험점수 낮음 |
| S071 | approve | 5 | 규칙 자동승인 구간 |
| S072 | investigate | 4 | 고위험점수 |
| S073 | investigate | 5 | 거절 이력 |
| S074 | investigate | 5 | 고 위험점수, 고 보장한도 |
| S075 | approve | 5 | 규칙 자동승인 구간, 과거 청약 없음 |
| S076 | approve | 4 | 고령자, 낮은 위험점수 |
| S077 | investigate | 5 | 고위험점수 |
| S078 | investigate | 5 | 관리자 메모 무시 |
| S079 | investigate | 5 | 위험점수 높음 |
| S080 | approve | 5 | 위험점수 낮음 |
| S081 | investigate | 5 | 수동심사 대기 구간 |
| S082 | approve | 5 | 규칙 자동승인 구간 |
| S083 | investigate | 5 | 위험점수 높음 |
| S084 | investigate | 5 | 고 위험점수, 고 보장한도 |
| S085 | investigate | 5 | 수동심사 대기 구간 |
| S086 | investigate | 5 | 수동심사 대기, 위험점수 0 |
| S087 | approve | 5 | 규칙 자동승인 구간 |
| S088 | investigate | 4 | 과거 거절 이력 |
| S089 | approve | 5 | 규칙 자동승인 구간 |
| S090 | investigate | 5 | 과거 청약 거절 |
| RX001 | approve | 4 | 소액 청구 |
| RX002 | approve | 5 | 아말감 충전 |
| RX003 | investigate | 5 | 대액 수동심사 구간 |
| RX004 | approve | 5 | 임플란트 수술 |
| RX005 | approve | 5 | 과거 청구 유사 |
| RX006 | approve | 5 | 과거 청구 비슷한 금액 |
| RX007 | investigate | 5 | 대액 수동심사 구간 |
| RX008 | investigate | 5 | 아말감 충전, 과거 청구 있음 |
| RX009 | approve | 5 | 한도대비 24.7% |
| RX010 | approve | 5 | 완전 매복 발치 |
| RX011 | investigate | 5 | 과거 청구 비슷한 치료 |
| RX012 | approve | 5 | 소액 치료, 보장한도 내 |
| RX013 | approve | 5 | 대액 수동심사 구간 |
| RX014 | investigate | 5 | 임플란트 수술 |
| RX015 | approve | 5 | 과거 청구 비슷한 수치 |
| RX016 | investigate | 5 | 대액 수동심사 구간 |
| RX017 | approve | 5 | 임플란트 수술 |
| RX018 | approve | 5 | 치주 소파술 비용 적당 |
| RX019 | approve | 5 | 단순 발치 |
| RX020 | investigate | 5 | 임플란트 수술, 과거 청구 있음 |
| RX021 | approve | 5 | 임플란트 수술 비용 적당 |
| RX022 | approve | 5 | 과거 청구액이 비슷 |
| RX023 | investigate | 5 | 과거 동일 치료 승인 |
| RX024 | approve | 5 | 비교적 낮은 비용 |
| RX025 | approve | 5 | 과거 청구 유사 |
| RX026 | approve | 5 | 치주 소파술 |
| RX027 | investigate | 4 | 치료 비용이 보장한도의 38.9% |
| RX028 | investigate | 5 | 과거 동일 치료 승인 |
| RX029 | approve | 5 | 세라믹 크라운 치료 |
| RX030 | approve | 5 | 아말감 충전 |
| RX031 | approve | 5 | 과거 청구 비슷한 금액 |
| RX032 | approve | 5 | 비교적 낮은 비용 |
| RX033 | approve | 5 | 과거 청구 유사 |
| RX034 | investigate | 5 | 과거 동일 치료 청구 |
| RX035 | approve | 5 | 아말감 충전 |
| RX036 | approve | 5 | 대액 수동심사 구간 |
| RX037 | approve | 5 | 과거 청구 비슷한 금액 |
| RX038 | investigate | 5 | 과거 청구 비슷한 금액 |
| RX039 | approve | 5 | 과거 청구 유사 |
| RX040 | approve | 5 | 소액, 자동지급 구간 |
| RX041 | investigate | 5 | 대액 수동심사 구간 |
| RX042 | investigate | 5 | 한도를 초과 |
| RX043 | approve | 5 | 충전 치료, 보장한도 내 |
| RX044 | investigate | 5 | 한도를 초과 |
| RX045 | approve | 5 | 세라믹 크라운 비용 적당 |
| RX046 | approve | 5 | 발치 비용 적당 |
| RX047 | investigate | 5 | 한도 대비 비율 높음 |
| RX048 | investigate | 5 | 과거 청구 비슷한 금액 |
| RX049 | investigate | 5 | 한도 초과 |
| RX050 | approve | 5 | 대액 수동심사 구간 |
| RX051 | approve | 4 | 소액 |
| RX052 | approve | 5 | 아말감 충전 |
| RX053 | investigate | 4 | 임플란트 수술 비용 높음 |
| RX054 | approve | 5 | 과거 청구 비슷한 수치 |
| RX055 | investigate | 5 | 과거 동일 치료 승인 |
| RX056 | approve | 5 | 과거 청구 비슷한 수치 |
| RX057 | approve | 5 | 소액 치료, 과거 청구 유사 |
| RX058 | approve | 5 | 비교적 낮은 비용 |
| RX059 | approve | 5 | 과거 청구액이 비슷 |
| RX060 | investigate | 4 | 대액 |
| RX061 | investigate | 5 | 대액, 수동심사 구간 |
| RX062 | approve | 5 | 과거 청구 비슷한 금액 |
| RX063 | approve | 5 | 한도대비 28.0% |
| RX064 | approve | 5 | 과거 청구 비슷한 금액 |
| RX065 | approve | 5 | 아말감 충전 |
| RX066 | approve | 5 | 과거 청구 비슷한 금액 |
| RX067 | approve | 5 | 단순 발치 |
| RX068 | investigate | 5 | 과거 청구 비용과 비교 |
| RX069 | investigate | 5 | 과거 동일 치료 청구 |
| RX070 | investigate | 4 | 임플란트 수술 비용 높음 |
| RX071 | investigate | 5 | 대액 수동심사 구간 |
| RX072 | approve | 5 | 임플란트 수술 |
| RX073 | investigate | 4 | 과거 청구 내역과 비슷한 치료 |
| RX074 | investigate | 4 | 과거 청구 내역과 비슷한 치료 |
