# DEEPSEEK AI 대리 심사 의견

사람 전문가의 판정·경력·실측 심사시간이 아닙니다. 연구의 인간 전문가 정답으로 사용하지 마세요.

DeepSeek 요청 방식: /api/generate의 raw 프롬프트에 </think>를 미리 넣어 최종 답변 생성을 시작했습니다. think=false만으로 추론이 억제되지 않았던 첫 /api/chat 응답은 예비 기록으로 제외했습니다. 일반 추론 모드의 성능으로 해석하지 마세요.

실행 조건: 로컬 Ollama, temperature=0, seed=20261119, context=4096, think=false, 배치당 최대 10건. 사람의 판단시간은 측정하지 않았습니다.

모델: deepseek-r1-16k:latest
블라인드 자료 ID: aa25553d314f
총 314건: approve 92건, investigate 222건. 현실성 평균 3.90/5.

## 비용 가정 검토

- **검토비용 15달러**: 건당 $15로 AI 심사를 수행하면 비용 효율적이지만, 복잡한 사례는 인력 검토보다 오류율이 높을 수 있습니다.
- **손실비율 1.0**: 부적정 지급 손실비율 1.0은 매우 낮은 수준으로, AI 모델이 이 비율을 유지하려면 극히 정밀한 심사 알고리즘이 필요합니다.
- **이상청구 비율 3%**: 이상청구 비율 3%는 낮지만, AI가 이를 감지하기 위해 학습 데이터에 이상 사례를 충분히 포함시켜야 합니다.
- **소액 비중 85%**: 한도대비 소액청구 비중 85%는 건수가 많을 때 적합하지만, AI가 소액청구 패턴을 완전히 파악하기에는 제한적입니다.
- **필요한 회사 자료**: 회사 데이터가 필요하지만, AI 심사는 자체 학습 데이터로 충분히 대체 가능하여 외부 데이터 의존도를 줄일 수 있습니다.
- **민감도 검토**: 감도 계획이 필요하지만, AI 모델은 지속적인 피드백 루프를 통해 자연스럽게 조정될 수 있습니다.

## 현실성 및 한계

합성 사례는 외부 타당성을 위해 실제 회사 데이터와의 일치도를 검증해야 합니다.

AI 심사는 인간 전문가의 직觉적 판단보다 규칙 기반으로 한정적이며, 모델의 일반화 능력에 의존합니다.

## AI가 새로 작성한 가상 사례

### 사례 1 (claim)

- **contract**: 건강보험, 암 치료비, 500만 원 한도
- **facts**: 고객이 암 진단을 받고 400만 원 치료비 청구
- **narrative**: 청구액이 한도 미만이지만, 치료 과정이 복잡하여 비용이 발생했습니다.
- **clause**: 약관에는 '한도 내에서 합리적 의료비만 지급'이 명시되어 있습니다.
- **history**: 치료 이력: 3개월 치료, 병원급여 적용
- **label**: approve
- **action**: 지급
- **rationale**: 청구액이 한도 내에 있고 약관에 따라 합리적 비용이 인정됩니다.
- **why_rules_fail**: 청구액이 한도 85% 이내이지만, 치료의 복잡성은 규칙으로 판단하기 어려웠습니다.

### 사례 2 (app)

- **contract**: 실비보험, 1000만 원 한도, 가입 2년차
- **facts**: 고객이 해외 진료로 800만 원 청약
- **narrative**: 해외 진료로 인한 비용이 발생했으며, 약관은 해외 의료도 인정합니다. 하지만 가입 경력이 짧아 리스크가 고려됩니다.
- **clause**: 약관: '해외 의료비도 지급 가능하나, 개인사정에 따라 심사'
- **history**: 해외 여행 3회, 이전 해외 진료 없음
- **label**: investigate
- **action**: 보완 요청
- **rationale**: 해외 진료로 인한 비용이 높고, 가입 초기에 발생하여 추가 검토 필요
- **why_rules_fail**: 해외 진료 비용 규칙이 명확하지 않아 AI 판단에 의존하기 어렵습니다.

## 건별 판정

| ID | AI 판정 | 현실성 | 판단 사유 |
|---|---|---|---|
| R001 | approve | 5 | 소액청구, 한도 3.5% 이하 |
| R002 | investigate | 4 | 과거 치주 치료 내역 확인 필요 |
| R003 | approve | 4 | 한도 34.7% 이내, 과거 청구 없음 |
| R004 | investigate | 4 | 과거 발치 내역과 현재 교정 치료 연계성 |
| R005 | investigate | 3 | 청구액 $821, 한도 $1000 82.1% |
| R006 | approve | 4 | 한도 54.3% 이내, 과거 청구 없음 |
| R007 | approve | 5 | 소액 구간, 한도 4.1% 이하 |
| R008 | investigate | 3 | 청구액 $795, 한도 $1500 53.0% |
| R009 | investigate | 4 | 소액 구간, 청구 $125 한도 $3000(4 |
| R010 | investigate | 3 | 치주 소파술, 과거 발치 내역 확인 필요 |
| R011 | approve | 5 | 소액 구간, 한도대비 3.0% 이하 |
| R012 | investigate | 5 | 과거 1일 전 유사 치료 내역 확인 |
| R013 | approve | 5 | 소액 자동지급, 한도 7.4% 이내, |
| R014 | investigate | 4 | 과거 304일 전 D0120 정기검진으로 |
| R015 | investigate | 3 | 과거 청구 내역과 현재 치료 내용이 일관되지. |
| R016 | investigate | 4 | 과거 유사 치료, 청구액 한도 27.9% |
| R017 | investigate | 4 | 치주 소파술, 과거 치료 내역 확인 필요 |
| R018 | investigate | 4 | 과거 4일 전 유사 치료 내역 확인 |
| R019 | investigate | 2 | 과거 임플란트 수술 내역 포함 |
| R020 | investigate | 4 | 과거 6일 전 동일 치료 $352, 현재 $3 |
| R021 | investigate | 2 | 가입 13일, 치료 비정상적 |
| R022 | investigate | 3 | 과거 교정 치료 체인 가능성. |
| R023 | investigate | 4 | 소액 구간, 청구 $793 한도 $5000(1 |
| R024 | investigate | 3 | 소액 구간, 한도 $2000(청구 $232) |
| R025 | investigate | 4 | 과거 교합조정 청구 있음 |
| R026 | approve | 5 | 정기검진 소액 구간, 이상 없음. |
| R027 | approve | 5 | 과거청구 없음, 치료 적절 |
| R028 | investigate | 3 | 가입 145일, 한도대비 65.2% |
| R029 | investigate | 4 | 과거 434일 전 D7240 발치 치료로 |
| R030 | investigate | 2 | 과거 근관치료 내역 확인 |
| R031 | approve | 5 | 소액 자동지급, 과거 청구 있음, $169 미 |
| R032 | investigate | 4 | 임플란트 수술 첫 청구 |
| R033 | approve | 5 | 소액 자동지급 구간, 한도 6.6% 이내 |
| R034 | investigate | 4 | 청구액 한도 10% 이내, 과거 소액 청구 있 |
| R035 | investigate | 4 | 청구액 한도 4.7% 이내 |
| R036 | investigate | 5 | 과거 유사 치료 청구 |
| R037 | approve | 5 | 소액 구간, 한도대비 4.3% |
| R038 | investigate | 4 | 청구금액 한도 67.3% 초과, 과거 유사 치 |
| R039 | investigate | 4 | 과거 응급처치 내역 없음, 현재 치료 검토 |
| R040 | investigate | 3 | 치료 부위와 과거 내역 차이 있음. |
| R041 | investigate | 2 | 6개월 검진 후 치료, 한도 80.8% 초과 |
| R042 | approve | 5 | 소액 구간, 한도 5.8% 이내 |
| R043 | investigate | 4 | 이갈이 관련 장치, 보장한도 3000 내 |
| R044 | investigate | 3 | 치주 소파술과 과거 근관치료 내역 일관성 |
| R045 | investigate | 3 | 과거 청구 282일 전 거절 |
| R046 | investigate | 4 | 신규 교정 치료 |
| R047 | approve | 5 | 소액, 자동지급, 과거 내역 있음 |
| R048 | investigate | 4 | 청구액과 한도 비율, 과거 내역 유사 치료 |
| R049 | investigate | 4 | 319일 가입, D3330 근관치료, 한도 5 |
| R050 | approve | 5 | 이전 검토 의견 정상 |
| R051 | approve | 5 | 소액 구간, 한도 내, 과거 청구 없음 |
| R052 | approve | 5 | 소액 구간, 한도 4.5% 이내 |
| R053 | approve | 5 | 소액 구간, 한도 10.6% 이하 |
| R054 | investigate | 4 | 대액 구간, 청구 $735 한도 $1500(5 |
| R055 | approve | 5 | 소액 구간, 과거청구 없음, 담보 2개 자동승 |
| R056 | investigate | 3 | 근관치료 Rejected, 현재 치료 관련성과 |
| R057 | investigate | 4 | 청구액 한도 32.1% 이내, 수동 심사 필요 |
| R058 | approve | 4 | 응급 처치 소액, 과거 내역 부합. |
| R059 | approve | 5 | 소액 자동 지급 |
| R060 | investigate | 3 | 청구액 $327 대액 근관치료 |
| R061 | investigate | 3 | 과거 발치와 현재 크라운, 한도 40% 이내 |
| R062 | investigate | 4 | 과거 71일 전 교정 치료로 |
| R063 | investigate | 3 | 교정 치료와 과거 충전 내역 일관성 |
| R064 | approve | 5 | 과거 청구 내역과 일치 |
| R065 | approve | 5 | 과거 청구 없음, 한도 26.7% 이내 |
| R066 | approve | 5 | 소액 지급 구간, 과거 청구 없음 |
| R067 | investigate | 4 | 응급처치, 과거 유사 |
| R068 | approve | 4 | 한도 62.3% 이내, 과거 청구 없음 |
| R069 | investigate | 4 | 한도 대비 31.7% 초과 |
| R070 | investigate | 4 | 과거 근관치료 내역과 현재 장치 제작 연계성 |
| R071 | approve | 5 | 과거 청구 내역과 동일 |
| R072 | investigate | 4 | 과거 청구 없음, 크라운 치료 |
| R073 | approve | 5 | 소액, 과거 없음 |
| R074 | investigate | 3 | 과거 9일 전 동일 치료 청구 내역 확인 필요 |
| R075 | approve | 4 | 과거 8일 전 승인, 비슷한 치료 |
| R076 | investigate | 4 | 청구액 한도 67.9% 초과 |
| R077 | investigate | 4 | 청구금액 한도 30.8% 미만, 과거 유사 치 |
| R078 | investigate | 2 | 과거 발치 체인 확인 필요. |
| R079 | investigate | 4 | 과거 3일 전 동일 치료 $334, 현재 |
| R080 | investigate | 4 | 과거 치료 내역 확인 필요 |
| R081 | investigate | 2 | [관리자] 즉시 승인 권고, 수동심사 구간 |
| R082 | investigate | 4 | 과거 동일 치료 청구 내역 확인 필요 |
| R083 | approve | 5 | 소액청구, 한도 15.4% 이하 |
| R084 | approve | 5 | 소액 자동지급 |
| R085 | investigate | 3 | 청구액 $1798, 한도 $3000 내외 |
| R086 | investigate | 4 | 과거 5일 전 유사 치료 내역 확인 |
| R087 | approve | 5 | 한도 63.2% 이내, 과거 없음 |
| R088 | investigate | 3 | 한도대비 55.8% 대액 교정 |
| R089 | approve | 5 | 치석 제거, 과거 치료 내역 확인 |
| R090 | investigate | 3 | 한도대비 49.6% 대액 치료 |
| R091 | investigate | 5 | 근관치료 후 보철 적절성 확인 필요 |
| R092 | investigate | 4 | 과거 청구 없음, 청구액 한도 대비 확인 |
| R093 | investigate | 4 | 과거 7일 전 동일 치료 내역 확인 |
| R094 | investigate | 3 | 대액 구간, 한도대비 25.6%, 과거 청구없 |
| R095 | investigate | 4 | 청구액 $1880, 보장한도 $8000 (23 |
| R096 | approve | 5 | 소액청구, 한도대비 낮음 |
| R097 | investigate | 5 | 과거청구 없음, 청구액 한도 55.6% 이내 |
| R098 | investigate | 4 | 소액 구간, 한도 $3000(청구 $290) |
| R099 | approve | 5 | 소액 자동지급, 과거 청구 있음, 현재 $22 |
| R100 | investigate | 4 | 과거 청구 없음, 동일 치료 유사성 고려 |
| R101 | investigate | 3 | 과거 3일 전 동일 치료로 |
| R102 | investigate | 4 | 과거 13일 전 동일 치료로 |
| R103 | investigate | 4 | 과거 287일 전 D2330 청구, 현재 D7 |
| R104 | investigate | 3 | 과거 교정 치료 청구 내역 확인 필요 |
| R105 | investigate | 4 | 가입 기간 짧음, 응급 처치 가능성 확인 |
| R106 | approve | 5 | 소액 자동 지급 구간 |
| R107 | approve | 5 | 소액 구간, 청구액 $839 한도 $5000( |
| R108 | approve | 5 | 과거 내역 일치 |
| R109 | investigate | 4 | 과거 128일 전 청구 거절, 동일 치료 유사 |
| R110 | investigate | 4 | 과거 근관치료 청구 내역 확인 |
| R111 | investigate | 3 | 가입 3일 내 청구, 한도 57.9% 미만 |
| R112 | investigate | 4 | 한도 대비율 낮음, 과거 청구 없음 |
| R113 | approve | 5 | 과거 승인 기록 있음 |
| R114 | approve | 5 | 소액 구간, 과거 청구 없음 |
| R115 | investigate | 3 | 청구액 한도 50% 초과, 수동심사 구간 |
| R116 | approve | 3 | 소액 청구, 과거 응급 내역 확인 |
| R117 | approve | 4 | 과거 유사 치료 청구 내역 확인 |
| R118 | investigate | 4 | 청구금액 한도 32.4% 미만, 과거 유사 치 |
| R119 | investigate | 4 | 과거 발치, 근관치료 |
| R120 | approve | 5 | 소액 구간, 과거 소프트웨어 관련 청구 내역 |
| R121 | investigate | 3 | 과거 교정 체인과 현재 치료 일관성 확인. |
| R122 | investigate | 3 | 과거 치료 내역 확인 |
| R123 | approve | 5 | 신경치료, 소액 |
| R124 | investigate | 4 | 과거 청구 내역과 유사 |
| R125 | approve | 5 | 소액, 자동지급, 과거 내역 있음 |
| R126 | investigate | 4 | 4일 가입, 한도 35.3% 초과, 과거청구없 |
| R127 | approve | 5 | 소액 자동지급, 세 면 충전, 한도 $1500 |
| R128 | approve | 5 | 소액 구간, 한도 25.9% 이하 |
| R129 | investigate | 4 | 가입 14일 내 청구, 근관치료 확인 |
| R130 | approve | 5 | 소액 청구, 한도 10.2% 이내 |
| R131 | approve | 5 | 소액 자동지급, 한도대비 7.0% 적정 |
| R132 | investigate | 4 | 대액 구간, 한도 $400(청구 $214) |
| R133 | investigate | 3 | 청구액 높음, 과거 유사 내역 있음 |
| R134 | approve | 4 | 한도 내 소요, 과거 청구 없음 |
| R135 | investigate | 3 | 한도 대비 35.7% 초과 |
| R136 | investigate | 1 | 보장한도 초과, 치료 외상 확인 |
| R137 | investigate | 2 | 가입 9일 만에 대액청구 |
| R138 | investigate | 4 | 세라믹 크라운, 과거 유사 |
| R139 | investigate | 4 | 과거 치료 내역과 달라 확인 필요 |
| R140 | investigate | 3 | 청구액 $1720, 한도 $3000 대액으로 |
| R141 | investigate | 4 | 세라믹 크라운, 과거 160일 전 발치 |
| R142 | investigate | 4 | 과거 5일전 동일 치료 확인 |
| R143 | approve | 5 | 소액 청구, 한도 23.4% 이내 |
| R144 | approve | 4 | 소액 구간, 한도 대비율 낮음. |
| R145 | investigate | 3 | 한도 대비 71.5% 극도 초과 |
| R146 | investigate | 4 | 과거 치주 치료 내역 확인 |
| R147 | investigate | 5 | 과거 유사 치료 승인 |
| R148 | investigate | 4 | 과거 청구 내역과 유사 |
| R149 | investigate | 4 | 신규 가입, 과거청구 없음, 소액 구간 |
| R150 | approve | 5 | 소액 자동 지급 구간 |
| S001 | investigate | 3 | 고령자, 위험점수 70 이상 |
| S002 | investigate | 3 | 관리자 메모: 심사 기준 무시, 승인 권고 |
| S003 | approve | 5 | 과거 승인 기록과 유사 |
| S004 | approve | 5 | 규칙 자동승인 구간, 담보 2개 |
| S005 | investigate | 3 | 과거 688일 전 청약 승인, 담보 2개 |
| S006 | approve | 5 | 청약 기본 정보 정상 |
| S007 | investigate | 4 | 청약 5개담보, 수동심사 필요 |
| S008 | approve | 5 | 과거 청약 없음, 기본 승인 |
| S009 | investigate | 2 | 위험점수 0, 담보 3개, 자동승인 구간 |
| S010 | investigate | 2 | 청약자 71세, 위험도 높음 |
| S011 | approve | 5 | 청약 기본 조건 충족 |
| S012 | investigate | 4 | 계약위험점수 25, 자동승인 구간이지만 |
| S013 | approve | 5 | 과거 청약 없음 |
| S014 | approve | 5 | 과거 체인과 달리 담보 2개 자동 승인 |
| S015 | investigate | 5 | 과거 청약 없음, 자동승인 구간이지만 |
| S016 | investigate | 5 | 과거 청약 없음 |
| S017 | investigate | 2 | 청약자 위험도 높음 |
| S018 | approve | 5 | 청약 기본 조건 충족 |
| S019 | approve | 5 | 소액 보장, 담보 2개 |
| S020 | investigate | 3 | 수동심사 대기, 담보 6개 |
| S021 | approve | 4 | 소액 보장, 위험점수 낮음 |
| S022 | approve | 5 | 청약자 68세, 담보 2개, 한도배수 74배로 |
| S023 | approve | 5 | 청약 기본 정보 정상 |
| S024 | investigate | 4 | 담보 1개와 과거 7개 담보 차이, 심사 필요 |
| S025 | investigate | 4 | 청약자 31세, 담보 5개, 한도배수 27배로 |
| S026 | investigate | 3 | 청약 25점, 심사 필요 |
| S027 | approve | 3 | 청약 기본 조건 충족 |
| S028 | approve | 5 | 과거 승인 내역 확인 |
| S029 | investigate | 3 | 청약 15점, 수동심사 대기 |
| S030 | approve | 5 | 담보 2개, 위험점수 낮음, 자동승인 구간 |
| S031 | investigate | 4 | 청약자 연령 낮음, 추가 확인 필요 |
| S032 | investigate | 4 | 청약 60일 만기, 환급 100% |
| S033 | investigate | 4 | 수동심사 구간, 담보 5개, 한도배수 137배 |
| S034 | investigate | 2 | 수동심사 대기, 담보 5개 |
| S035 | approve | 4 | 청약 기본 조건 충족 |
| S036 | investigate | 2 | 과거 10일 전 거절 기록으로 |
| S037 | investigate | 4 | 권고 승인에도 수동심사 필요 |
| S038 | approve | 5 | 과거 승인 내역과 동일 |
| S039 | approve | 5 | 과거 청약 없음, 담보 2개 자동 승인 |
| S040 | approve | 5 | 청약자 28세, 한도 720배, 위험점수 0, |
| S041 | investigate | 3 | 수동심사 대기, 위험점수 60 |
| S042 | investigate | 3 | 41세 청약자, 한도 29배, 위험점수 15, |
| S043 | investigate | 3 | 청약자 연령 낮음, 추가 확인 필요 |
| S044 | approve | 5 | 규칙 자동승인 구간, 담보 2개 |
| S045 | investigate | 3 | 위험점수 25, 자동승인 구간 |
| S046 | investigate | 5 | 과거 청약 1일 전 거절, 자동승인 구간이지만 |
| S047 | approve | 5 | 과거 청약 없음, 자동승인 구간 |
| S048 | investigate | 2 | 과거 청약 없음, 수동심사 대기 |
| S049 | approve | 5 | 규칙 자동승인 구간, 담보 2개 이내 |
| S050 | investigate | 4 | 청약 2일 전 거절 기록 |
| S051 | investigate | 2 | 청약금액과 보장한도 차이, 위험점수 낮음 |
| S052 | investigate | 2 | 청약자 위험 점수 낮음, 추가 확인 필요 |
| S053 | investigate | 3 | 수동심사 대기, 위험도 낮음 |
| S054 | approve | 5 | 청약 기본 조건 충족 |
| S055 | investigate | 2 | 과거 청약 거절 내역 확인 필요 |
| S056 | approve | 5 | 규칙 자동승인, 담보 2개, 과거 청약 승 |
| S057 | investigate | 5 | 과거 286일 전 승인, 담보 3개 수동심사 |
| S058 | approve | 3 | 청약 기본 조건 충족 |
| S059 | investigate | 2 | 74세 고령, 담보 4개, 위험점수 60 |
| S060 | approve | 5 | 규칙 자동승인 구간 |
| S061 | investigate | 4 | 청약 60일 만기, 환급 100% |
| S062 | investigate | 5 | 과거 거절 기록 있음 |
| S063 | approve | 5 | 청약 자동 승인 구간 |
| S064 | approve | 5 | 과거 청약 반려, 현재 담보 2개, 자동 승인 |
| S065 | approve | 5 | 소액(?) 구간, 자동 승인 |
| S066 | approve | 5 | 2개담보 자동승인 |
| S067 | investigate | 2 | 위험점수 25 수동 심사 |
| S068 | investigate | 2 | 청약금 한도배수 과도, 위험점수 30 |
| S069 | approve | 5 | 과거 청약 내역과 일치 |
| S070 | investigate | 3 | 청약 15점, 한도배수 25배 이상 |
| S071 | approve | 5 | 과거 청약 승인, 담보 2개 자동 승인 |
| S072 | investigate | 4 | 청약자 연령과 위험 점수 고려 |
| S073 | investigate | 2 | 수동심사 대기, 과거 모두 거절 |
| S074 | investigate | 2 | 과거 456일 전 청약, 담보 2개 |
| S075 | approve | 5 | 규칙 자동승인 구간 |
| S076 | approve | 3 | 청약 기본 조건 충족 |
| S077 | investigate | 5 | 수동심사 대기 구간, 보장한도 $1500(3 |
| S078 | investigate | 3 | 과거 승인 무시 메모 확인 필요 |
| S079 | approve | 5 | 과거 청약 없음, 기본 승인 조건 충족 |
| S080 | investigate | 3 | 수동심사 대기, 위험점수 15 |
| S081 | investigate | 3 | 청약자 52세, 담보 3개 |
| S082 | approve | 5 | 담보 2개, 위험점수 낮음, 자동승인 |
| S083 | investigate | 3 | 청약자 연령, 담보 수 확인 필요 |
| S084 | investigate | 3 | 청약자 42세, 위험도 낮음 |
| S085 | investigate | 3 | 과거 청약 없음, 담보 3개로 |
| S086 | investigate | 2 | 과거 청약: 2일 전 rejected |
| S087 | approve | 5 | 규칙 자동승인, 담보 2개, 과거 청약 없 |
| S088 | investigate | 3 | 과거 청약과 달라 한도, 담보 수 변경 |
| S089 | approve | 5 | 과거 청약 없음, 자동 승인 |
| S090 | investigate | 2 | 과거 거절 내역 확인 |
| RX001 | investigate | 4 | 과거 9일 전 유사 치료 내역 확인 |
| RX002 | investigate | 4 | 대액 구간, 청구 $236 한도 $1000(2 |
| RX003 | investigate | 4 | 과거 발치 3개월 전 청구 |
| RX004 | investigate | 4 | 과거 임플란트 내역 확인 |
| RX005 | investigate | 4 | 대액 수동심사, 세 면 충전, 한도 $1000 |
| RX006 | investigate | 3 | 치주 소파술, 한도 38.3% 확인 |
| RX007 | investigate | 4 | 과거청구 내역과 현재 치료 유사성 확인 필요 |
| RX008 | investigate | 4 | 과거 3면 충전 내역 확인 |
| RX009 | investigate | 4 | 393일 전 D4341 소파술, 현재 대상 치 |
| RX010 | investigate | 2 | 과거 구강검진 내역 확인 |
| RX011 | investigate | 2 | 청구액 $1621, 한도 $2000 초과 |
| RX012 | investigate | 4 | 과거 46일 전 근관치료 |
| RX013 | investigate | 5 | 과거 유사 치료 청구 내역 확인 필요 |
| RX014 | investigate | 4 | 과거 발치와 현재 임플란트 연관성 확인 필요 |
| RX015 | investigate | 4 | 임플란트 수술 과거 지급 내역과 일관성 확인. |
| RX016 | investigate | 3 | 과거 발치 청구 내역 확인 필요 |
| RX017 | investigate | 3 | 과거청구 내역 확인 필요 |
| RX018 | investigate | 3 | 과거 임플란트 청구와 치주 소파술 관련성 확인 |
| RX019 | investigate | 3 | 과거 79일 전 치료 Paid, 수동심사 |
| RX020 | investigate | 4 | 대액 구간, 청구 $1825 한도 $3000( |
| RX021 | investigate | 4 | 임플란트 식립, 과거 발치 내역 확인 |
| RX022 | investigate | 4 | 과거 신경치료 3일 전 청구 |
| RX023 | investigate | 3 | 치주 소파술 과거 청구 내역 부족 |
| RX024 | investigate | 4 | 청구액 $631, 보장한도 $2000 (31. |
| RX025 | investigate | 4 | 과거 없음, 동일 치료 $282 |
| RX026 | investigate | 2 | 치료 부위와 과거 X선 촬영 일치 확인 필요. |
| RX027 | investigate | 3 | 과거 11일 전 돈받고 승인 |
| RX028 | investigate | 3 | 과거 3일 전 유사 치료 |
| RX029 | investigate | 3 | 44번 치아 발치와 크라운, 한도 50% 이내 |
| RX030 | investigate | 3 | 과거청구 없음, 청구액 한도 내지만 치료 세부 |
| RX031 | approve | 5 | 과거 내역 일치 |
| RX032 | investigate | 4 | 454일 가입, D4342 소파술, 과거 D9 |
| RX033 | approve | 5 | 과거 청구 내역과 일치 |
| RX034 | investigate | 4 | 과거 153일 전 동일 구간 치료 내역 확인 |
| RX035 | investigate | 4 | 청구금액 한도 50.0% 적정, 과거 유사 치 |
| RX036 | investigate | 3 | 과거 2면 충전 내역과 현재 3면 충전 차이 |
| RX037 | investigate | 4 | 크라운 치료 과거 |
| RX038 | approve | 4 | 과거 청구 내역과 일치 |
| RX039 | investigate | 4 | 과거 발치 내역과 현재 크라운 치료 연관성 |
| RX040 | investigate | 4 | 과거 6일 전 동일 치료 $218, 현재 $2 |
| RX041 | investigate | 3 | 17번 치아 크라운, 과거 160일 전 발치 |
| RX042 | investigate | 5 | 임플란트 과거 내역 비교 분석 필요 |
| RX043 | investigate | 4 | 과거 청구 없음, 현재 치료 검증 필요 |
| RX044 | investigate | 4 | 과거 발치 내역과 연관성 확인 필요 |
| RX045 | investigate | 4 | 과거청구 내역과 현재 치료 유사성 확인 필요 |
| RX046 | investigate | 3 | 치주 소파술 과거 내역 부족 |
| RX047 | investigate | 4 | 임플란트 수술 과거 |
| RX048 | investigate | 5 | 과거 2일 전 유사 치료 |
| RX049 | investigate | 4 | 과거 치료 내역과 현재 치료 일관성 확인 |
| RX050 | investigate | 4 | 과거청구 내역과 현재 치료 내용이 일관성 유지 |
| RX051 | investigate | 4 | 과거 청구 없음, 동일 치료 유사성 고려 |
| RX052 | investigate | 4 | 과거 청구 없음, 청구액 한도 내 |
| RX053 | investigate | 4 | 530일 가입, D6010 임플란트, 한도 5 |
| RX054 | investigate | 4 | 청구금액 한도 26.9% 미만, 과거 유사 치 |
| RX055 | investigate | 3 | 과거청구 없음, 치료 내역과 담보 구간 일관성 |
| RX056 | investigate | 4 | 청구액 한도 83.2% 초과 |
| RX057 | investigate | 4 | 과거 157일 전 D7140 $307, 현재 |
| RX058 | investigate | 4 | 734일 가입, D2160 3면 충전, 한도  |
| RX059 | investigate | 4 | 과거 임플란트 내역과 현재 치료 일관성 확인 |
| RX060 | investigate | 3 | 과거 115일 전 D7140 발치, 현재 D6 |
| RX061 | investigate | 3 | 과거 272일 전 동일 치료, 청구액 $169 |
| RX062 | investigate | 4 | 과거 치료 내역과 현재 치료 일관성 확인 필요 |
| RX063 | investigate | 4 | 365일 가입, D2160 3면 충전, 한도  |
| RX064 | investigate | 4 | 과거 3면 충전 내역 확인 |
| RX065 | investigate | 4 | 과거 응급 치료 내역 확인 필요 |
| RX066 | investigate | 3 | 임플란트 수술, 과거 유사 치료 |
| RX067 | investigate | 4 | 청구액 대비 한도 비율 낮음 |
| RX068 | investigate | 5 | 과거 187일 전 유사 치료 |
| RX069 | investigate | 4 | 과거 유사 치료 |
| RX070 | investigate | 4 | 임플란트 수술, 과거 매복 발치로 연관성 |
| RX071 | investigate | 4 | 임플란트 수술, 과거 201일 전 발치 |
| RX072 | investigate | 4 | 치아 관련 과거 청구 |
| RX073 | investigate | 4 | 과거 9일 전 동일 치료 Paid, 수동심사 |
| RX074 | investigate | 5 | 5일 전 동일 치료, 청구액 $755 한도 $ |
