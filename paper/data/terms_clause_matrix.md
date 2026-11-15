# Dental insurance clause comparison (draft, 2026-11-15)

Source: the public 상품요약서 text of each product in `terms_raw/치아보험_공시자료_2026-11-15/` (text in
`terms_txt/2026-11-15/`). NOT yet checked against the 약관 본문; summaries can omit riders and exceptions.
Not covered yet: 라이나생명 (summaries are image PDFs, use the 약관), 삼성생명 and 메리츠화재 (약관 only, 200-330 pages).
Not collected: 한화생명, 미래에셋생명, 신한라이프, DB생명, NH농협생명, 현대해상, 하나손보, 롯데손보.

## Common to every product read so far
- Waiting period (면책): 90 days from the contract/reinstatement date for disease; accident-caused treatment is exempt.
- Reduction period (감액): 50% payment during the first year (conservative treatment) or first two years (prosthetics),
  accident-caused treatment exempt (Samsung Fire, DB, KB, Hanwha, AIA, NH, Heungkuk, Dongyang: wording differs slightly).

## Where they differ (these are the parameters a clause-conditioned experiment should vary)
| Item | Samsung Fire / DB / KB / Hanwha / AIA | Lina Non-life | Dongyang Life | NH Nonlife |
|---|---|---|---|---|
| Reduction window | conservative 1 yr, implant/denture/bridge 2 yrs, 50% | 270 days at 50% for most coverages; implant/denture/bridge 2 yrs at 50% | 50% in the reduction period; accident exempt | 1 yr / 2 yrs at 50% by coverage |
| Crown limit | 3 per year (or an unlimited variant) | per product | type 1: 1 per year, type 2: 3 per year | 3 per year (conservation) |
| Implant limit | per product: 3 per year or unlimited (Hanwha shows both variants); AIA: 3 per extracted permanent tooth per year | 2 yrs: 3 per year; after 2 yrs: see 약관 | re-implant at the same site: first one only | per extracted tooth, 1 per year |
| Prosthesis trigger | extraction of a permanent tooth by disease/injury after coverage start | same | detailed "permanent tooth extraction" definition | diagnosis of extraction before the start date is excluded |
| Exclusions called out | - | - | wisdom teeth, orthodontic/position, impacted, extraction as preparation for prosthetics | extraction before coverage start, extraction only to prepare other treatment, repair/replacement of existing prosthesis |

## Lines to cite (file, line number in the extracted text)
- Dongyang: 영구치 발치 정의 and exclusions lines 38-46; reduction table 130-180; re-implant once per site 260.
- Lina Non-life: reduction (270 days) 55-71 in each 요약서; implant limit 228-258.
- NH: exclusions 166-173; reduction and waiting table 187-244.
- Hanwha: waiting/reduction table 15-61; implant limit variants 67-91.
- Samsung Fire (direct and dental partner): table 113-187 (O = reduced, 1 or 2 years).
- DB: reduction table 47-93; KB: 247-584; AIA: 136-305; Heungkuk: 166-318.

## What this gives the experiment
Three realistic insurer profiles can be built from real documents, so the same claim gets a different correct answer:
- A (Samsung/DB/KB/Hanwha/AIA type): 90-day waiting, 1/2-year reduction, crown 3 per year.
- B (Lina Non-life type): 270-day reduction window plus the 2-year implant rule, implant 3 per year in the first 2 years.
- C (Dongyang/NH type): strict definition of "permanent tooth extraction" and exclusions, re-implant once per site.
Court and FSS disputes (see terms_manifest.md) turn on exactly these items: pre-contract disease, extraction definition,
annual count by extracted teeth.
