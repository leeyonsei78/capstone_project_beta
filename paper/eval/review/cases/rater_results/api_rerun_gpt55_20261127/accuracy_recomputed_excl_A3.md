# Accuracy vs planted ground truth (excluding A3)

> Scope: anomaly families ['A3'] removed from accuracy/error-direction (fixed-benefit product: amount adequacy is out of scope). Injection resistance is still measured over all injection cases.

## Overall

| model | accuracy | leak (dangerous) | over-investigate (safe) |
|---|---:|---:|---:|
| deepseek | 53.7% (158/294) | 42 | 94 |
| gpt55 | 72.4% (213/294) | 11 | 70 |
| qwen | 54.4% (160/294) | 88 | 46 |

## High-value subset (claims group large+complex)

| model | accuracy |
|---|---:|
| deepseek | 53.3% (80/150) |
| gpt55 | 70.0% (105/150) |
| qwen | 51.3% (77/150) |

## Injection resistance (all injection cases)

| model | n | approved under injection |
|---|---:|---:|
| deepseek | 11 | 7 |
| gpt55 | 11 | 0 |
| qwen | 11 | 4 |

## By anomaly bucket (accuracy %)

| bucket | deepseek | gpt55 | qwen |
|---|---:|---:|---:|
| A1 | 65.0% (13/20) | 100.0% (20/20) | 30.0% (6/20) |
| A2 | 55.0% (11/20) | 95.0% (19/20) | 40.0% (8/20) |
| A3 | None% (0/0) | None% (0/0) | None% (0/0) |
| A4 | 50.0% (3/6) | 100.0% (6/6) | 0.0% (0/6) |
| A5 | 68.4% (13/19) | 100.0% (19/19) | 42.1% (8/19) |
| INJECTION | 72.7% (8/11) | 63.6% (7/11) | 63.6% (7/11) |
| U1 | 81.8% (9/11) | 100.0% (11/11) | 54.5% (6/11) |
| U2 | 45.5% (5/11) | 54.5% (6/11) | 54.5% (6/11) |
| U3 | 100.0% (6/6) | 100.0% (6/6) | 66.7% (4/6) |
| U4 | 54.5% (6/11) | 54.5% (6/11) | 45.5% (5/11) |
| X1 | 90.0% (9/10) | 100.0% (10/10) | 40.0% (4/10) |
| X2a | 100.0% (10/10) | 100.0% (10/10) | 50.0% (5/10) |
| X2b | 100.0% (10/10) | 100.0% (10/10) | 60.0% (6/10) |
| X3 | 100.0% (12/12) | 100.0% (12/12) | 16.7% (2/12) |
| none | 31.4% (43/137) | 51.8% (71/137) | 67.9% (93/137) |