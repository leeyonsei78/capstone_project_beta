# When Is an LLM a Trustworthy First-Pass Reviewer? Model-Dependent Accuracy of LLM Advice on High-Value Insurance Claims and Underwriting

**[DRAFT v2.0 — 2026-11-20]**
**Target venue**: Applied Sciences (MDPI, SCIE) / Future Internet (MDPI, SCIE) — to confirm against graduation requirements and current JCR status before submission.
**Status**: Core experiment (AI first-pass judgment on 314 blind cases) complete; evidence-level (C1–C3), calibration, traditional-ML baseline, second human-labeller, and reader study are future work (Section 7).

> All reported numbers are measured on **synthetic** cases and reflect **AI judgments scored against planted ground-truth labels**. They are **not** human-expert gold labels and do **not** establish external validity. See Sections 4 and 7.

---

## Abstract

Insurers process low-value claims by straight-through rules and escalate high-value or ambiguous cases to human reviewers. A natural design is to let a large language model (LLM) produce a *first-pass recommendation* on the escalated cases while a human makes the final decision. Whether this is safe depends on how accurately the LLM judges, and on *which* model is used. We construct 314 blind, synthetic dental-insurance review cases (150 claims + 90 underwriting applications + 74 complexity-layer claims) with planted ground-truth labels and seeded anomalies (duplicate billing, code–narrative mismatch, amount inflation, limit-threshold splitting, exclusion/waiting-period violations, upcoding, and embedded prompt-injection payloads). Three LLMs — a capable hosted model (referred to here as *Codex*) and two local open-weight models (Qwen-14B, DeepSeek-R1) — each judge all 314 cases blind (approve vs. investigate), for 942 judgments total. We then score each model against the planted labels after the labelling phase was frozen. The capable model reaches 91.4% overall and 86.0% on the high-value subset, versus 52–57% (near chance) for the two local models; it correctly flags the anomaly types that deterministic rules catch 0% of the time (code–narrative mismatch, upcoding, rule-undetectable complex cases: 100%), and resists all 11 prompt-injection attempts, while the local models are manipulated on 4/11 and 7/11. The capable model's residual errors concentrate on amount-only inflation (A3: 55%), which even a strong model cannot confirm from amount alone — a *judgment-dependent* category that should remain with humans. We conclude that a capable LLM is an effective first-pass reviewer for high-value cases, but (a) its value is model-dependent — weak models are unsafe, with one leaking 99 of 314 escalation-worthy cases as "approve" — and (b) the final decision must remain human. We frame the findings as properties of the *advice*, not as evidence of improved human decisions, which we leave to a reader study.

**Keywords**: large language model; insurance claim review; underwriting; human-in-the-loop; first-pass triage; anomaly detection; prompt injection; model comparison

---

## 1. Introduction

Insurance claim and underwriting operations are increasingly structured as a two-stage pipeline. Low-value, low-risk cases are settled automatically by deterministic rules (straight-through processing); high-value or ambiguous cases are escalated to human reviewers. A recurring proposal is to insert an LLM as a *first-pass reviewer* on the escalated stream — it reads the case, produces a recommendation (approve, or investigate further) and a rationale, and a human reviewer makes the binding decision.

The attraction is clear: the escalated stream is exactly where deterministic rules fail, because the signals are textual and contextual (a treatment code that does not match the narrative, a claim split just under an auto-pay threshold, a disclosure that is technically consistent but materially suspicious). But the proposal's safety is not self-evident. It depends on two things that are rarely measured together: **how accurately the LLM judges the escalated cases**, and **how much that accuracy depends on the specific model deployed**. A design that is safe with a frontier model may be unsafe with a cost-driven or on-premises open-weight substitute.

This paper measures both. We build 314 blind, synthetic dental-insurance review cases with planted ground-truth labels and a catalogue of seeded anomalies, and have three LLMs — one capable hosted model and two local open-weight models — each judge every case blind. We then score the judgments against the planted labels.

We make three contributions:

1. **A labelled evaluation set and protocol** for first-pass insurance review (Sections 3–4): 314 cases spanning low-value auto, high-value basic, high-value complex (tooth-level histories and upcoding), and underwriting, with seeded anomaly types and embedded prompt-injection cases, labelled blind and frozen before scoring.

2. **A model-comparison result** (Section 5) showing that first-pass accuracy is strongly model-dependent: the capable model reaches 86.0% on high-value cases and 100% on the anomaly types that rules catch 0% of the time, while two local models sit near chance and are frequently manipulated by injection — so the structure's safety is a property of the *model*, not of "using an LLM".

3. **An explicit map of where the LLM helps and where it does not** (Sections 5–6): the capable model's residual errors concentrate on amount-only inflation, a *judgment-dependent* category we argue should stay with human reviewers, and on over-cautious investigation of clean complex cases (a safe-direction error).

We deliberately scope our claims to the *quality of the advice*. We do not measure the effect of the advice on human reviewers (that requires a reader study with human-subjects approval), and we do not claim efficiency gains.

---

## 2. Related Work

**LLMs for insurance claims and fraud.** Islayem et al. [1] apply LLMs (GPT-4o, Gemini 1.5 Pro, Claude 3.5 Sonnet) with retrieval over blockchain-stored health-insurance claims to fraud analysis, reporting up to 99% accuracy on 100 synthetic claims authored by the authors; the claims are described in narrative scenarios that state the inconsistency in prose, and the final decision remains with a human. Our setting differs in three ways: our cases are *structured* review inputs rather than narrative fraud scenarios, we compare a capable model against weak local models to test deployment sensitivity, and we separate the anomaly types that deterministic rules already catch from those they do not. Other LLM claim-automation and underwriting-agent proposals [2,3] likewise keep a human in the loop and are evaluated on the downstream decision rather than on the model-dependence of the first-pass advice.

**Deferral and human–AI collaboration.** Learning-to-defer and cost-sensitive triage frame the automation boundary as a policy choice under a workload or cost constraint [4]; we adopt the framing that the first-pass model should abstain or escalate when evidence is insufficient, and we report the safe/unsafe direction of its errors rather than accuracy alone. Work on automation bias cautions that confident, explained AI output can increase over-reliance [5]; because we cannot run a human study here, we report error direction and injection robustness as proxies for deployment risk and leave reliance effects to future work.

**Prompt injection.** Tool- and document-grounded LLM agents are vulnerable to instructions embedded in their inputs [6]. We include injection-bearing cases so that robustness is measured on the same scale as accuracy.

> *Citation discipline:* Only [1] has been read in full. [2–6] are cited from abstracts/summaries and must be verified against primary text, and venue/indexing confirmed, before submission. Any reference that cannot be verified will be removed.

---

## 3. System Setting and Case Design

### 3.1 Two-stage review and the escalation boundary

The reference system settles a claim automatically when the requested amount is within a fixed fraction (20%) of the coverage limit; claims above that fraction, and underwriting applications that fall outside the auto-decision rule, are escalated. The escalated stream is the object of study: this is where a first-pass LLM recommendation would be inserted ahead of a human reviewer. Low-value auto cases are included only as a control.

### 3.2 Cases

All cases are **synthetic**, generated from a fixed seed so that the set regenerates byte-identically. The frozen set (dataset identifier `aa25553d314f`) contains:

- **150 claims**: 60 low-value (≤20% limit, auto-pay region) and 90 high-value basic (>20%).
- **90 underwriting applications**: 30 in the rule's auto region and 60 in the manual-review region.
- **74 high-value complexity-layer claims**: tooth-level treatment histories (L2) and same-family upcoding (L3).

Total: 314 cases. Each case carries a planted ground-truth label (approve / investigate) by construction, plus an anomaly tag and an injection flag. Seeded anomaly families: A1 duplicate billing, A2 treatment-code vs. free-text narrative mismatch, A3 amount inflation, A4 limit-threshold splitting, A5 exclusion/waiting-period, U1–U4 underwriting (disclosure, hazardous occupation, multiple contracts, age/limit), X1–X3 complexity (tooth-level history, upcoding), and 11 cases that embed a prompt-injection payload instructing the reviewer to auto-approve. Complexity cases are additionally tagged `rule_detectable` (whether a deterministic tooth-level rule could catch the anomaly, or only free text could).

### 3.3 Why the escalated stream is hard for rules

A deterministic baseline over the escalated cases catches the structural anomalies (duplicate claim IDs, limit arithmetic) but, by construction, catches 0% of the anomalies whose only signal is textual — code–narrative mismatch (A2) and upcoding / text-only complex cases — because no field encodes the contradiction. This is precisely the gap a first-pass LLM is proposed to fill, and Section 5 measures whether it does.

---

## 4. Methods

### 4.1 Raters

Three LLMs act as blind first-pass reviewers, each judging all 314 cases independently:

- **Codex** — a capable hosted model. *Reproducibility caveat:* in this study the judgments were produced through an interactive assistant session (a ChatGPT Plus agent), not through a per-call judgment API, because no such token API was available to us. A deployable version would call an equivalent capable model API with the same prompt; the numbers below should be read as the capability ceiling of a strong model under this protocol, not as the output of a turnkey "Codex API".
- **Qwen-14B** (`qwen14b-16k`, local Ollama) and **DeepSeek-R1** (`deepseek-r1-16k`, local Ollama) — open-weight models run on-device, representing a cost-driven or on-premises deployment.

Each model received the same blind case content (the inputs a human reviewer sees, including the injection payloads) and returned `approve` or `investigate` with a short rationale. The two local models were run with shuffled case order and without access to each other's answers. Pilot batches used to check output format and latency were archived and excluded from the final count. The full request/response audit trail is retained.

### 4.2 Scoring

Each judgment is scored against the planted label. Scoring was performed **after** the labelling phase was frozen and schema-validated (completeness, no duplicates, dataset-identifier and input-hash consistency across all three models; 942/942 judgments present). We report, per model: overall and per-category accuracy; per-anomaly-type accuracy; **error direction** (leakage = an investigate-worthy case judged approve, the dangerous direction for an insurer; vs. over-investigation = a clean case judged investigate, the safe direction); injection resistance (how many of the 11 injection cases were approved under manipulation); and accuracy on rule-undetectable (text-only) complex cases.

Confidence calibration (ECE/Brier), evidence-level conditions (summary vs. itemised vs. with policy text), a traditional-ML baseline, a second LLM vendor family, and a second human labeller are **not** part of this experiment; they are future work (Section 7).

---

## 5. Results

### 5.1 Accuracy by case category

Table 1 reports each model's accuracy against the planted labels, by case category. The capable model (Codex) is strong across the board; the two local models are near chance everywhere.

**Table 1.** First-pass accuracy by case category (correct / n).

| Category | n | Codex | Qwen | DeepSeek |
|---|---:|---:|---:|---:|
| Low-value claim (≤20%, auto region) | 60 | 98.3% (59/60) | 50.0% (30/60) | 48.3% (29/60) |
| High-value claim — basic (>20%) | 90 | 84.4% (76/90) | 53.3% (48/90) | 55.6% (50/90) |
| High-value claim — complex | 74 | 87.8% (65/74) | 51.4% (38/74) | 58.1% (43/74) |
| Underwriting — auto region | 30 | 100.0% (30/30) | 63.3% (19/30) | 53.3% (16/30) |
| Underwriting — manual region | 60 | 95.0% (57/60) | 56.7% (34/60) | 61.7% (37/60) |
| **High-value subset (claims >20%)** | **164** | **86.0% (141/164)** | **52.4% (86/164)** | **56.7% (93/164)** |
| **All cases** | **314** | **91.4% (287/314)** | **53.8% (169/314)** | **55.7% (175/314)** |

The headline for the design question is the high-value subset: **86.0% for the capable model vs. ~52–57% for the local models.** First-pass accuracy on exactly the stream that would be escalated is therefore usable with a capable model and near-chance with the local substitutes.

### 5.2 Where the LLM adds value: anomalies rules cannot catch

Table 2 breaks accuracy down by seeded anomaly type over all 314 cases. The capable model reaches **100% on A2 (code–narrative mismatch), X3 (upcoding), and all underwriting families**, and 100% on the 12 rule-undetectable (text-only) complex cases — the categories a deterministic baseline catches 0% of. This is the concrete incremental value of a first-pass LLM: it covers exactly the gap rules leave open.

**Table 2.** Accuracy by anomaly type, all 314 cases.

| Anomaly type | n | Codex | Qwen | DeepSeek |
|---|---:|---:|---:|---:|
| Normal (no anomaly) | 137 | 89.8% | 67.9% | 31.4% |
| A1 duplicate billing | 20 | 100.0% | 30.0% | 65.0% |
| A2 code–narrative mismatch | 20 | **100.0%** | 40.0% | 55.0% |
| A3 amount inflation | 20 | 55.0% | 45.0% | 85.0% |
| A4 threshold splitting | 6 | 100.0% | 0.0% | 50.0% |
| A5 exclusion / waiting period | 19 | 100.0% | 42.1% | 68.4% |
| U1 disclosure | 11 | 100.0% | 54.5% | 81.8% |
| U2 hazardous occupation | 11 | 100.0% | 54.5% | 45.5% |
| U3 multiple contracts | 6 | 100.0% | 66.7% | 100.0% |
| U4 age / limit | 11 | 100.0% | 45.5% | 54.5% |
| X1 complex tooth-history | 10 | 100.0% | 40.0% | 90.0% |
| X2a complex | 10 | 100.0% | 50.0% | 100.0% |
| X2b complex | 10 | 100.0% | 60.0% | 100.0% |
| X3 upcoding | 12 | **100.0%** | 16.7% | 100.0% |
| Prompt injection | 11 | 63.6% | 63.6% | 72.7% |
| **Rule-undetectable (text-only, complex)** | **12** | **100.0%** | **16.7%** | **100.0%** |

### 5.3 Where the capable model fails: the judgment-dependent category

The capable model is **not** infallible on high-value cases (86.0%, not 100%). Its 23 high-value errors split into two kinds:

- **Amount inflation (A3): 55% only (8 of its high-value misses).** These are investigate-worthy cases judged approve — the dangerous (leakage) direction. The model's own rationales state that overbilling cannot be confirmed from the amount alone without material/fee-schedule data. We therefore treat A3 as a **judgment-dependent category** that should remain with human reviewers (or require additional evidence) rather than a model defect to be prompted away.
- **Over-investigation of clean complex cases (15, safe direction):** mostly clean L3 complex claims and the 2 injection-bearing cases whose underlying case was legitimately approvable. These are safe-direction errors (a clean case sent to a human) and include the model's correct refusal to obey injection payloads (Section 5.4).

### 5.4 Error direction and injection robustness

Accuracy alone hides the operational risk. Table 3 shows error direction: the capable model's errors are few and balanced (only **9 leakage** cases out of 314), whereas the weak models fail in opposite, both-undesirable ways — Qwen **leaks 99** investigate-worthy cases as approve (catastrophic for an insurer), and DeepSeek over-investigates 94 (it approves only 92/314 and floods review with noise; its 100% on some hard subsets is an artifact of "investigate almost everything", not discrimination).

**Table 3.** Error direction (all 314) and injection resistance (11 injection cases).

| Model | Correct | Leakage (dangerous) | Over-investigation (safe) | Approved under injection |
|---|---:|---:|---:|---:|
| Codex | 287 | 9 | 18 | **0 / 11 (resisted all)** |
| Qwen | 169 | 99 | 46 | 4 / 11 |
| DeepSeek | 175 | 45 | 94 | 7 / 11 |

On injection, the capable model approved **0 of 11** manipulated cases — it never obeyed an embedded "auto-approve" instruction (its 63.6% label-accuracy on the injection row reflects conservatively investigating the 4 injection cases whose underlying label was approve, a safe error, not a security failure). Both local models were manipulated (Qwen 4, DeepSeek 7).

---

## 6. Discussion

**A capable LLM is an effective first-pass reviewer for high-value cases — with conditions.** On the escalated stream, the capable model is correct 86% of the time, covers the rule-undetectable anomaly types (A2, upcoding, text-only complex) at 100%, keeps leakage low (9/314), and resists injection completely. For a design in which the human makes the final decision, this is a strong first-pass filter that materially extends what deterministic rules can catch.

**But the value is model-dependent, not intrinsic to "using an LLM".** The two local open-weight models are near chance (52–57%), and dangerously so in opposite directions: one leaks the majority of escalation-worthy cases, the other drowns review in false escalations. The safety of the two-stage structure is therefore a property of the *specific model*, and a cost-driven downgrade to a weak local model is unsafe. Any deployment claim must name the model and its measured error direction, not merely "an LLM".

**The final decision must remain human, and one category is irreducibly human.** A3 (amount inflation) resists even the capable model, because the signal (is this amount excessive?) is not determinable from the claim text alone. This is not a prompting failure; it marks the boundary of what first-pass advice can decide. The appropriate design keeps A3-like, amount-only judgments with human reviewers (or routes them to additional evidence), and uses the LLM's first pass where its advantage is real.

**Reproducibility and deployment.** The capable model's judgments were obtained through an assistant session, not a turnkey judgment API (Section 4.1). The practical reading is that the 86% is the capability ceiling of a strong model under this protocol; a production system would call an equivalent capable-model API with the same prompt and should re-measure, because API model versions drift.

---

## 7. Limitations and Future Work

- **Synthetic cases, AI-scored.** All cases are synthetic with planted labels, and accuracy is measured against those planted labels, not human-expert gold. The capable model's 91.4% agreement with the planted labels is also evidence that the synthetic labels are reasonable, but it does not establish external validity. A human-expert validation subset (≈30–40 cases) and a second labeller are planned.
- **No human-reviewer effect.** We measure the quality of the advice, not whether it improves human final decisions; the latter requires a reader study under human-subjects approval and is explicitly out of scope.
- **Single run, no calibration.** Each model judged each case once; we do not report ECE/Brier (the raters emitted labels and rationales, not calibrated probabilities), evidence-level conditions (summary vs. itemised vs. policy-text), a traditional-ML baseline, or a second vendor family. These are planned and the harness supports them.
- **Rules reflect this system.** The 20% auto-pay rule and anomaly definitions follow the reference contract; external validity to other insurers' rules is a limitation.
- **One capable model, two local models.** The capable-vs-weak gap is demonstrated, not the full capability curve; intermediate models should be added.

---

## 8. Conclusion

We measured how accurately three LLMs act as blind first-pass reviewers on 314 synthetic insurance review cases, scored against planted ground truth. A capable model is an effective first-pass reviewer for the high-value, escalated stream (86.0%), covering exactly the anomaly types deterministic rules cannot (code–narrative mismatch, upcoding, text-only complex cases: 100%) and resisting all prompt-injection attempts, while keeping dangerous leakage low. Two local open-weight models are near chance and fail dangerously, showing that the safety of a first-pass-LLM design is model-dependent rather than intrinsic. One category — amount-only inflation — resists even the capable model and should remain a human judgment. The practical recommendation is narrow and defensible: on high-value cases, a *capable* LLM first pass followed by a human final decision is effective and safe for the anomaly types rules miss; a weak-model substitute is not, and amount-only judgments stay with people.

---

## References

*(To verify against primary text and current indexing before submission; unverifiable entries will be removed.)*

1. Islayem, R.; Gebreab, S.; AlKhader, W.; Musamih, A.; Salah, K.; Jayaraman, R.; Khan, M.K. Using Large Language Models for Enhanced Fraud Analysis and Detection in Blockchain-Based Health Insurance Claims. *Scientific Reports* **2025**, *15*, 11542. https://doi.org/10.1038/s41598-025-15676-4
2. Mo, Z.; Quan, Z.; O'Donohue, E.; Zhong, K. Claim Automation using Large Language Model. *arXiv* **2026**, arXiv:2602.16836. (Preprint — verify status.)
3. Roy, S.; Singh, A. Agentic AI for Commercial Insurance Underwriting with Adversarial Self-Critique. *arXiv* **2026**, arXiv:2602.13213. (Abstract only — verify.)
4. (Learning-to-defer / cost-sensitive triage — insert verified reference, e.g., DeCCaF, TMLR 2024, after reading.)
5. (Automation bias in AI-assisted decisions — insert verified reference after reading.)
6. (Prompt injection against tool-grounded LLM agents — insert verified reference after reading.)

---

## Appendix A: Data and Reproducibility

- Case set (synthetic, seeded), blind sheets, and three-model judgments: `paper/eval/review/cases/rater_results/ai_proxy_20261119/` (dataset_id `aa25553d314f`, 942 judgments).
- Per-model, per-category breakdown: `cases/rater_results/ai_proxy_20261119/classification_summary.md`.
- Accuracy-vs-ground-truth analysis (by category, anomaly type, error direction, injection, rule-undetectable): `accuracy_vs_ground_truth.{md,json}`.
- Validation (completeness/schema/provenance/input-hash): `audit/validation_report.json` (status: passed).
- Rater harness and validator: `paper/eval/review/{run_ai_blind_raters.py, run_model_raters.py, finish_ai_blind_raters.py, validate_ai_blind_raters.py}`.
