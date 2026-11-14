# RQ1 rules baseline (no LLM)

> **Assumptions, not results:** review-cost=$15.0/case, loss-fraction=1.0, prevalence=0.03, small-share=0.85. Replace with company figures. Curve shapes depend on the synthetic claim-to-limit ratio distribution.

Claims: 150 cases, 88 anomalous (evaluation set is enriched; real prevalence is far lower).

## Claims: threshold sweep (evaluation set)

| threshold | auto-paid | auto rate | to human | anomalous auto-paid | leakage rate | leaked $ |
|---|---|---|---|---|---|---|
| 5% | 16 | 11% | 134 | 5/88 | 6% | $1,354 |
| 10% | 37 | 25% | 113 | 12/88 | 14% | $4,076 |
| 20% | 60 | 40% | 90 | 30/88 | 34% | $11,101 |
| 30% | 86 | 57% | 64 | 48/88 | 55% | $19,370 |
| 50% | 120 | 80% | 30 | 70/88 | 80% | $39,700 |

## Claims: expected cost per 1,000 claims (prevalence 0.03, small-share 0.85)

| threshold | auto rate | human cases | leaked cases | review cost $ | leak loss $ | total $ |
|---|---|---|---|---|---|---|
| 5% | 31% | 693 | 4.2 | 10,402 | 1,151 | 11,552 |
| 10% | 70% | 303 | 10.2 | 4,541 | 3,465 | 8,005 |
| 20% | 85% | 150 | 25.5 | 2,250 | 9,436 | 11,686 |
| 30% | 89% | 112 | 26.9 | 1,683 | 10,077 | 11,761 |
| 50% | 94% | 56 | 28.6 | 839 | 11,655 | 12,494 |

## Claims: what simple deterministic rules catch (needs the rich evidence)

Rows are anomaly types (`clean` = false-alarm rate). Text mismatch (A2) is deliberately not covered:
free-text checks are the open question for the LLM.

| type | n | R1_amount_cap | R2_duplicate | R3_split | R4_early | any rule |
|---|---|---|---|---|---|---|
| A1 | 20 | 0% | 100% | 40% | 0% | 100% |
| A2 | 23 | 0% | 0% | 0% | 0% | 0% |
| A3 | 20 | 100% | 0% | 0% | 0% | 100% |
| A4 | 6 | 0% | 100% | 100% | 0% | 100% |
| A5 | 19 | 0% | 0% | 0% | 100% | 100% |
| clean | 62 | 0% | 0% | 0% | 0% | 0% |

## Applications: tier-1 (rule auto-approve at exactly 2 coverages)

30 auto-approved cases, 15 anomalous -> leakage 50%; by type {'U1': 5, 'U2': 5, 'U4': 5}. The contract's risk score is advisory only.

Sensitivity: auto-approve only if risk score <= X and no prior rejection.

| max score | auto rate | leakage rate | clean sent to human |
|---|---|---|---|
| 0 | 20% | 0% | 9 |
| 15 | 33% | 0% | 5 |
| 25 | 50% | 0% | 0 |
| 40 | 67% | 33% | 0 |
| 100 | 83% | 67% | 0 |
