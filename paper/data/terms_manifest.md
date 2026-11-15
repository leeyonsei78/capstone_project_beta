# Collected dental-insurance terms and dispute sources (2026-11-15)

Raw PDFs are in `terms_raw/` and extracted text (UTF-8) in `terms_txt/`. Do not commit them to the public repo
(third-party documents, large files); cite the URL and the clause instead.

## Terms (약관) status
| Insurer | Product / version | File | Status |
|---|---|---|---|
| Samsung Fire (손보) | 덴탈파트너 자동갱신형 2304.9 (2023-04) | samsungfire_dental_2023-04.pdf | complete, text extracted |
| Samsung Fire (손보) | 치아보험 재가입형 (2018-01) | samsungfire_dental_2018-01.pdf | complete, text extracted (old version) |
| Samsung Fire | product leaflet | samsungfire_leaflet.pdf | leaflet only, not terms |
| Hana Insurance (손보) | 하나더퍼스트 / 가득담은 치아보험 요약서 | hana_summary_*.retry.pdf | downloaded, but no extractable text (probably image PDF; needs OCR) |
| AXA (손보) | 치아보험(갱신형) 2604 | - | server returns an HTML error page to scripted downloads; fetch in a browser |
| KB Insurance | The드림치아안심보험 (2019-01, discontinued) | - | server resets the connection mid-download (2 attempts); retry later |
| Lina Life (생보) | 건강한치아보험 V | - | only a cafe-post link found, unverified; get from the Lina disclosure page |
| Hyundai Marine, DB, Meritz, Hanwha | - | - | not found in search; download from each insurer's 상품공시실 |

## Parameters actually present in Samsung Fire 2023-04 (summary pages 8-9; verify against the clause text)
- Waiting period: 90 days after first enrollment/reinstatement, for most coverages (none for accident-caused treatment).
- Reduction: crown 50% (100% after 1 year); implant/denture 50% (100% after 2 years); bridge 25% (50% after 2 years);
  accident-caused treatment exempt from the reduction.
- Limits: crown 3 per year (variant), implant-related annual limits, prosthesis claims tied to extracted permanent teeth.
Insurers differ on every one of these numbers, which is why a per-insurer clause condition is a real experiment.

## Dispute sources (read with a subagent; verify originals before citing)
- Daejeon District Court 2023나209036 (2024-01-16, appeal): policyholder's heir sued for 11.14M KRW periodontal
  prosthetic treatment; DISMISSED. The court read a past dental chart with an extraction/implant plan as a diagnosis that
  surgery was needed, so answering "no" on the pre-contract question was a breach; insurer rescinded. (An earlier search
  summary said the opposite; the full judgment text on casenote.kr says dismissed.)
- Changwon District Court appeal 2024나109*21 (about 2025-05-29, from a news article only): implants/bridge after 13
  extractions for chronic periodontitis; pre-contract condition exclusion upheld; bridge not payable (treatment not
  finished). Case number is partly masked in the article; get the judgment.
- FSS dispute-committee case (2023-02-15, via a secondary AI-rewritten article, original not seen): implant after residual-
  root removal denied because a residual root is not "loss of a natural tooth". Verify against the FSS decision.
- FSS press release 2025-06-24 (reported by several outlets): annual prosthesis limit counted by extracted permanent
  teeth (5 treated, 3 paid), self-extraction not paid, wisdom-tooth/orthodontic extraction and pre-start diagnosed decay
  excluded. The PDF copy at kiri.or.kr was not readable by the fetcher.
- Not dental-insurance disputes: Uijeongbu 2018가단19200 (medical malpractice), Korea Consumer Agency implant cases.
