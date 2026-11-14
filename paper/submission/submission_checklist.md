# MDPI Applied Sciences Submission Checklist

**Target deadline**: 2026-11-27
**Current draft**: v0.2 (2026-11-14)
**Venue**: Applied Sciences (MDPI, SCIE) · fallback: Future Internet (MDPI, SCIE)

---

## Before Submission

### Manuscript

- [ ] All [TBD] placeholders filled (requires experiment run)
  - [ ] Abstract: error rate percentages
  - [ ] Introduction §3 contribution point: "Results demonstrate [TBD]..."
  - [ ] Table 2 (evaluation settings): n_queries per phase filled
  - [ ] Table 3 (before/after results): correctness rates per error type
  - [ ] Figure 2 (bar chart): generated from Table 3 data
  - [ ] Section 6.3 Results: discussion paragraph
  - [ ] Section 8 Conclusion: aggregate delta %
- [ ] Word count check: Applied Sciences typically 4000–10000 words for research articles
- [ ] Figure 2 PNG file created at `paper/draft/figures/fig2_before_after.png`
- [ ] All figure captions written (Figure 1: architecture ASCII → convert to actual figure? or keep inline)
- [ ] Tables numbered sequentially and cross-referenced correctly
- [ ] Spelling/grammar check (English; paper is in English)
- [ ] Korean terms in example queries — verify they render correctly in PDF

### References

- [ ] Ref [3] (Liao et al. 2021): verify this is the best citation for "AI in conversational agents for finance" — may be too general
- [ ] Ref [17] (Mo et al., arXiv:2602.16836): **PREPRINT** — MDPI accepts preprint citations, "(Preprint)" label added ✅
- [ ] Ref [18] (Pałgan et al., 10.3390/app16094329): verify on doi.org directly before submission
- [ ] All DOIs are active hyperlinks in final PDF
- [ ] Reference [4] (OpenAI function calling): check if URL still valid at submission time

### Figures

- [ ] Figure 1 (architecture diagram): currently ASCII art in Appendix-style — consider generating an actual PNG/PDF figure for MDPI submission (required: vector or ≥300 DPI)
- [ ] Figure 2 (before/after bar chart): depends on experiment results [TBD]

### Files to Prepare for MDPI Online Submission

- [ ] `main_draft.pdf` — compiled from `main_draft.md` (convert with Pandoc or LaTeX)
- [ ] `cover_letter.pdf` — from `submission/cover_letter.md`
- [ ] `highlights.txt` — from `submission/highlights.md` (plain text, ≤85 chars/bullet)
- [ ] `author_info.md` — author names, affiliations, ORCID (fill in `submission/author_info.md`)
- [ ] `figure2.png` — from evaluation results
- [ ] `queries.json` — supplementary file (Appendix A reference)
- [ ] `harness.py` — supplementary file (Appendix B reference)

---

## Experiment Run (required to fill [TBD])

```
# Step 1: Start blockchain stack
blockchain-dental\run.bat          # Hardhat node + contracts + frontend

# Step 2: Start chatbot
start.bat                          # Flask :5000

# Step 3: Before-mitigation branch
git checkout paper/before-mitigation
cd insurance_agent
python ..\paper\eval\harness.py --phase before

# Step 4: After-mitigation branch
git checkout main
python ..\paper\eval\harness.py --phase after

# Step 5: Report
python paper\eval\harness.py --report
```

Estimated time: ~2 hours (49 queries × ~90s each at 2s rate-limit)

---

## Post-Experiment

- [ ] Fill all [TBD] in `main_draft.md` from `harness.py --report` output
- [ ] Generate Figure 2 bar chart from Table 3 data
- [ ] Review narrative in §6.3 for consistency with actual numbers
- [ ] Check if any mitigation performed unexpectedly (update §7.4 Limitations if so)
- [ ] Final read-through for consistency

---

## MDPI Submission Portal Steps

1. Register/log in at susy.mdpi.com
2. Select journal: Applied Sciences
3. Article type: Article
4. Upload files in order: manuscript → cover letter → figures → supplementary
5. Enter author details and ORCID
6. Confirm open access fee (Applied Sciences APC: CHF 2600 as of 2026; check current)
7. Verify no conflicts of interest

---

## Notes

- **Korean language**: MDPI requires the manuscript to be in English. Korean user query strings in Table 1/Appendix A are acceptable as data/examples — add English translations in brackets.
- **Data availability**: Harness and queries are in the public repo https://github.com/leeyonsei78/capstone_project_alpha under `paper/eval/`. Note in Data Availability Statement using the author_info.md template text.
- **Ethical considerations**: No human subjects experiment; blockchain data is synthetic (local testnet). No IRB required for this study design.
- **Figure 1** (ASCII architecture diagram in draft): MDPI prefers actual figure files. Consider creating a PNG version using draw.io or similar before submission.
