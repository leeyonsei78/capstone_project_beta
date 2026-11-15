# Clause-conditioned review report (synthetic, 60 scenarios x 3 profiles)

T0 = facts only, T1 = facts + the profile's clause excerpt. CI over scenarios. See the metric definitions in score_terms.py. Profiles come from public product summaries and are simplified (terms_profiles.py).

| model | cond | n | accuracy | on-disagree | adaptation | overpay | underpay | abstain | A / B / C |
|---|---|---|---|---|---|---|---|---|---|
| gpt-4o | T0 | 180 | 42% [36,51] | 40% [31,49] | 0% [0,0] | 43% | 13% | 1% | 37% / 47% / 43% |
| gpt-4o | T1 | 180 | 84% [78,89] | 85% [79,91] | 58% [38,80] | 4% | 11% | 0% | 95% / 82% / 75% |
| gpt-4o-mini | T0 | 540 | 30% [23,38] | 27% [20,35] | 1% [0,3] | 19% | 37% | 14% | 34% / 29% / 27% |
| gpt-4o-mini | T1 | 540 | 54% [46,62] | 67% [59,74] | 29% [11,50] | 0% | 46% | 0% | 64% / 33% / 64% |