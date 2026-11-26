# A Terms-Grounded Cascade for Insurance Review: Where Deterministic Rules End and LLM Judgment Begins

**[DRAFT v3.0 — 2026-11-26]**
**Target venue**: domestic conference (short version) → KCI journal (full version); SCIE (Applied Sciences / Future Internet, MDPI) as a later target. Confirm indexing/JCR before submission.
**Status**: Both experiments complete on synthetic cases scored against planted, terms-derived ground truth. The Experiment-1 capable model is now a **reproducible API model (gpt-5.5-2026-04-23)**, replacing an earlier non-reproducible assistant-session result (Section 4.1); human-expert validation is optional future work (Section 8).

> All numbers are measured on **synthetic** cases and scored against **planted ground-truth labels that are derived from each product's terms**, not from human-expert opinion. See Sections 3 and 8 for what this does and does not establish.

---

## Abstract

Insurers settle low-value, structurally clean cases automatically and escalate the rest to human reviewers. We study a **cascade**: a deterministic rule engine makes the objective, terms-derived first pass, and a large language model (LLM) handles only the **residual that rules cannot encode** — free-text anomalies and natural-language policy clauses — producing an approve / investigate / reject recommendation that a human reviewer confirms. Because, in a fixed-benefit (non-indemnity) dental product, every eligibility decision is **determined by the product's terms**, the ground truth is objective by construction and does not require human gold labels; different insurers' terms yield different-but-objective answers, which we model as three insurer rule profiles. We run two experiments on synthetic cases with planted, terms-derived labels. **Experiment 1** (314 blind cases; amount-adequacy cases excluded as out-of-scope for a fixed-benefit product, leaving 294) measures whether a *reproducible* capable model (gpt-5.5, called per-case via API under a neutral blind prompt) covers the free-text residual that rules miss. It catches the anomaly types deterministic rules catch **0%** of at high recall — **code–narrative mismatch 95%, upcoding and text-only complex cases 100%, exclusion/waiting-period 100%** — and **resists all 11 prompt-injection attempts (0 obeyed)**, but it is **conservative on clean cases (≈52% specificity)**, so it over-investigates: overall accuracy is **72.4%** with errors overwhelmingly in the **safe direction** (over-investigation 70 vs. dangerous leakage 11). Two local open-weight models sit near chance (53–54%) and fail dangerously (one leaks 88 investigate-worthy cases, the other obeys 7/11 injections). A notable methodological result: an earlier non-blind assistant-session run of a capable model reported 91% accuracy, but under a truly blind per-call protocol the reproducible number is 72% — the gap is almost entirely clean-case specificity, a caution about session-based LLM evaluation. **Experiment 2** (180 cases = 60 scenarios × 3 insurer profiles, reproducible gpt-4o) measures whether an LLM can apply the actual terms: accuracy swings from **37% with no terms to 88% with a clean clause excerpt to 69% with verbatim policy text**, and small models collapse toward chance — so terms grounding is essential and format-sensitive. We conclude that the objective, structured decision belongs to a deterministic rule engine; the LLM's defensible role is the terms-grounded textual residual, where a *capable* model is a high-recall, safe-direction filter and a weak one is unsafe; and the final decision stays human. The design needs no human gold labels to be evaluated, because correctness is defined by the terms.

**Keywords**: large language model; insurance claim review; underwriting; terms-grounded decision; deterministic cascade; human-in-the-loop; anomaly detection; prompt injection; model comparison

---

## 1. Introduction

Claim and underwriting operations run as a two-stage pipeline: low-value, structurally clean cases are settled automatically by rules (straight-through processing), and the rest are escalated to human reviewers. A recurring proposal is to insert an LLM into the escalated stream. The question this paper answers is **where** the LLM belongs, and **under what conditions** it is safe.

Our starting observation is that an insurance eligibility decision is not a matter of taste. For a **fixed-benefit** dental product — where the payout is a fixed amount per covered procedure, not a reimbursement of an actual bill — every decision (is this treatment covered? is it inside a waiting/reduction period? was there a disclosure breach?) is **determined by the product's terms and the case facts**. This has two consequences that shape the whole study:

1. **The ground truth is objective by construction.** We do not need a panel of human reviewers to define the correct answer; the terms define it. Different insurers have different terms, so they reach different answers — but each is objective relative to its own terms, not a disagreement of opinion. We model this directly with three insurer rule profiles.
2. **The right tool for the structured part is a deterministic rule engine, not an LLM.** If a decision is fixed by arithmetic over structured fields (amount vs. limit, age, coverage count, elapsed days against a waiting period) a Python rule engine produces it objectively, auditably, and for free. Putting an LLM there only adds cost and variance.

The LLM therefore earns its place **only on the residual that rules cannot encode**:
- **(a) Free text → facts.** A treatment code that contradicts the free-text narrative, or an upcoded procedure, is invisible to any structured rule because no field encodes the contradiction.
- **(b) Natural-language terms.** Clauses an insurer has not hand-coded into rules — read directly from the 약관 / product summary and applied to the case.

We call this a **terms-grounded cascade**: deterministic rules first, LLM for the terms-grounded textual residual, human confirmation last. We make four contributions:

1. **An objectivity argument and evaluation protocol** that needs no human gold labels: ground truth is the terms-derived label, and cross-insurer variation is modeled as distinct rule profiles (Section 3).
2. **A measured division of labor** (Section 6.1): what a deterministic engine settles objectively, and the exact residual it cannot (code–narrative mismatch caught 0% by rules).
3. **A model-dependence result on the residual** (Section 6.2): a reproducible capable model (gpt-5.5) covers the residual at high recall (code–narrative mismatch 95%, upcoding/text-only 100%) with total injection resistance and only safe-direction errors, but is conservative on clean cases (overall 72%); weak local models are near chance and unsafe. We also report that a non-blind session run of a capable model overstated accuracy by ~19 points, a reproducibility caution.
4. **A terms-grounding result** (Section 6.3): the same objective answer is reached 37% / 88% / 69% of the time given no terms / a clean clause / verbatim policy text, and small models cannot use real policy text — so grounding is essential and presentation-sensitive.

We deliberately exclude **amount adequacy** from scope: in a fixed-benefit product the payout is set by the terms, so "is the claimed amount excessive?" does not arise (Section 3.3). We also scope our claims to the *quality of the recommendation*; we do not measure its effect on human reviewers, which needs a reader study.

---

## 2. Related Work

**LLMs for insurance claims and fraud.** Islayem et al. [1] apply LLMs with retrieval over blockchain-stored health-insurance claims to fraud analysis, reporting up to 99% on 100 author-written synthetic claims whose narratives state the inconsistency in prose, with a human making the final call. Our setting differs: cases are *structured* review inputs, we separate the anomalies deterministic rules already catch from those they do not, we model cross-insurer variation as explicit rule profiles, and we test weak local models to probe deployment sensitivity. Other LLM claim-automation and underwriting-agent proposals [2,3] keep a human in the loop and are evaluated on the downstream decision rather than on where the LLM's value actually lies.

**Deferral and human–AI collaboration.** Learning-to-defer and cost-sensitive triage frame the automation boundary as a policy under a cost or workload constraint [4]. We adopt the view that the model should escalate when evidence is insufficient, and we report the *direction* of errors (dangerous leakage vs. safe over-investigation), not accuracy alone. Automation-bias work [5] warns that confident, explained output can increase over-reliance; lacking a human study, we report error direction and injection robustness as deployment-risk proxies.

**Prompt injection.** Tool- and document-grounded LLM agents obey instructions embedded in their inputs [6]. We include injection-bearing cases so robustness is on the same scale as accuracy.

> *Citation discipline:* Only [1] has been read in full. [2–6] are cited from abstracts/summaries and must be verified against primary text, with venue/indexing confirmed, before submission; unverifiable entries will be removed.

---

## 3. System, Objectivity, and Scope

### 3.1 The cascade and the escalation boundary

The reference system settles a claim automatically when the requested amount is within a fixed fraction (20%) of the coverage limit and no structural rule fires; everything else is escalated. The escalated stream is the object of study. In the cascade, a **deterministic rule engine** makes the first pass over the escalated cases; cases it cannot resolve from structured fields pass to an **LLM second pass** that reads the free text and the terms and recommends approve / investigate / reject; a **human** confirms.

### 3.2 Objectivity without human gold labels

Each case has a ground-truth label defined by the product's terms applied to the case facts — not by human consensus. We encode three insurer **rule profiles** (A/B/C, derived from public product summaries and the 약관) so that the same scenario can be scored under three different, each-objective, term sets. Cross-insurer disagreement is thus a *controlled variable*, not label noise. This is why the evaluation does not require a human-labeled gold set: correctness is a property of the terms. (A human-expert validation subset remains useful external-validity evidence and is listed as optional future work.)

### 3.3 Why amount adequacy is out of scope

The product is **fixed-benefit**, not indemnity: the payout is a fixed amount per covered procedure set by the terms. "Is the claimed amount excessive?" (amount adequacy) therefore does not arise for claims, and underwriting premiums are set by the product's rate table, so amount adequacy does not arise there either. We exclude the amount-adequacy anomaly family (A3) from scope accordingly. Note this is distinct from **terms-defined reduction** (e.g., a bridge paid at 25% within a two-year reduction window): that is objective and terms-determined, and remains in scope. Because the displayed monetary value does not affect any in-scope decision, the currency in which amounts are shown is immaterial to correctness (it matters only for reviewer familiarity).

---

## 4. Methods

### 4.1 Experiment 1 — the free-text residual (314 cases)

**Cases.** Synthetic, fixed-seed (dataset `aa25553d314f`), regenerating byte-identically: 150 claims (60 low-value, 90 high-value basic), 90 underwriting applications (30 auto-region, 60 manual-region), and 74 high-value complexity-layer claims (tooth-level histories and upcoding). Each case carries a terms-derived planted label, an anomaly tag, and an injection flag. Anomaly families: A1 duplicate billing, A2 code–narrative mismatch, A4 limit-threshold splitting, A5 exclusion/waiting-period, U1–U4 underwriting, X1–X3 complexity, plus 11 injection-bearing cases. **Amount-adequacy (A3) cases are excluded from scoring (Section 3.3)**, leaving 294 in-scope cases; the capable model rated all cases blind and A3 is dropped at scoring time, so the exclusion is a scope decision, not data selection.

**Raters.** Three LLMs judge every case blind under the identical neutral single-case prompt: a **reproducible capable hosted model** (`gpt-5.5-2026-04-23`, called per-case via API) and two **local open-weight models** (Qwen-14B, DeepSeek-R1) representing an on-premises or cost-driven deployment. All three see the same frozen blind sheet (dataset `aa25553d314f`); the capable model judged 314/314 with 0 unparsed outputs. *Reproducibility note:* an earlier version of this experiment obtained the capable-model judgments through an interactive assistant session that had incidentally seen project context (schema/templates) and reported 91.4% accuracy; we discard that number in favour of the blind per-call API result and report the difference as a finding (Section 6.1).

**Rule baseline.** A deterministic Python engine (amount cap, duplicate-ID, split, early/waiting-period checks) is run over the same cases to establish what rules settle without any LLM.

### 4.2 Experiment 2 — applying the terms (180 cases)

60 scenarios are each scored under the three insurer profiles (A/B/C) = 180 cases, with a three-way outcome (approve / reduced / reject) defined by each profile's rules. Each is judged under three conditions: **T0** facts only (no terms given), **T1** facts + a clean synthetic clause excerpt, **T2** facts + a *verbatim* excerpt from the real 약관 / product summary. Models: a reproducible hosted API model (gpt-4o, gpt-4o-mini) and a local model (Qwen-14B). This isolates whether the model can apply terms it is given, and how sensitive that is to presentation (clean summary vs. raw document) and model size.

### 4.3 Scoring

Each judgment is scored against the planted, terms-derived label (scorer `score_vs_ground_truth.py` for Exp 1, `score_terms.py` for Exp 2; both validated to reproduce prior committed reports). We report overall and per-category accuracy, per-anomaly accuracy, **error direction** (leakage = investigate-worthy judged approve, the dangerous direction; vs. over-investigation, the safe direction), injection resistance over all 11 injection cases, and accuracy on rule-undetectable (text-only) cases. Confidence calibration, a second human labeller, a traditional-ML baseline, and additional model families are future work (Section 8).

---

## 5. What the deterministic first pass settles (and cannot)

Table 1 shows the Python rule engine over the escalated claims. Rules catch the structural anomalies at or near 100% but catch **0%** of code–narrative mismatch (A2), because no structured field encodes the contradiction — this is precisely the residual the LLM is for.

**Table 1.** Deterministic rule coverage by anomaly type (claims).

| Anomaly | n | amount cap | duplicate | split | early/waiting | any rule |
|---|---:|---:|---:|---:|---:|---:|
| A1 duplicate | 20 | 0% | 100% | 40% | 0% | **100%** |
| A2 code–narrative mismatch | 23 | 0% | 0% | 0% | 0% | **0%** |
| A4 threshold splitting | 6 | 0% | 100% | 100% | 0% | **100%** |
| A5 exclusion / waiting period | 19 | 0% | 0% | 0% | 100% | **100%** |
| clean | 62 | 0% | 0% | 0% | 0% | 0% (no false alarms) |

The rule engine also exposes the operating cost of a pure-rules policy: at the 20% auto-pay threshold, 34% of anomalous claims in the enriched set leak through, and tier-1 underwriting auto-approval (exactly two coverages) leaks 50% of its anomalous cases — the rule's risk score is advisory only. These are the gaps the LLM second pass must close.

---

## 6. Results

### 6.1 The LLM on the free-text residual (Experiment 1, A3 out of scope)

**Table 2.** First-pass accuracy vs. terms-derived ground truth, reproducible blind per-call runs (A3 excluded; 294 in-scope cases). Capable model = `gpt-5.5-2026-04-23`.

| Metric | Capable (gpt-5.5) | Qwen-14B | DeepSeek-R1 |
|---|---:|---:|---:|
| Overall accuracy | **72.4% (213/294)** | 54.4% (160/294) | 53.7% (158/294) |
| High-value subset | **70.0% (105/150)** | 51.3% (77/150) | 53.3% (80/150) |
| Dangerous leakage (invest.→approve) | **11** | 88 | 42 |
| Over-investigation (safe) | 70 | 46 | 94 |
| Clean-case accuracy (specificity) | **51.8%** | 67.9% | 31.4% |
| Code–narrative mismatch (A2) | **95%** | 40% | 55% |
| Upcoding (X3) | **100%** | 17% | 100%\* |
| Rule-undetectable text-only complex | **100%** | 17% | 100%\* |
| Injection obeyed (of 11) | **0** | 4 | 7 |

\* DeepSeek's high scores on some hard subsets are an artifact of near-universal "investigate" (94 over-investigations), not discrimination.

The reproducible capable model is a **high-recall, conservative** first-pass reviewer. It covers exactly the residual rules miss — **95% on code–narrative mismatch, 100% on upcoding and text-only complex cases, 100% on exclusion/waiting-period** — and **obeys 0 of 11 injection attempts**. Its weakness is specificity: it flags ≈48% of genuinely clean cases for investigation, so its errors are **70 over-investigations (safe direction) against only 11 dangerous leakages**. For an insurer this is the acceptable failure mode: a clean case sent to a human costs review time, not money. Both local models are near chance and dangerous in the opposite way: Qwen leaks 88 investigate-worthy cases as approve; DeepSeek drowns review in false escalations and obeys 7/11 injections. **The residual is coverable at high recall — but only by a capable model, and only as a conservative filter under human confirmation.**

**A reproducibility finding.** An earlier run of a capable model through an interactive assistant session (which had incidentally seen the project's schema and templates, i.e. was not fully blind) reported 91.4% overall and 86.0% high-value accuracy. Under the blind per-call API protocol the same-class model reaches 72.4% / 70.0%; the ~19-point gap is almost entirely clean-case specificity (89.8% → 51.8%). This is a concrete caution: **session-based LLM evaluations that leak task context overstate accuracy**, and first-pass-reviewer claims should be measured blind and per-call.

### 6.2 Can the LLM apply the terms? (Experiment 2)

**Table 3.** Accuracy of the three-way terms decision by condition (60 scenarios × 3 profiles = 180; CI over scenarios).

| Model | T0 facts only | T1 clean clause | T2 verbatim 약관 |
|---|---:|---:|---:|
| gpt-4o | 37% [29,46] | **88% [83,94]** | 69% [62,77] |
| gpt-4o-mini | 33% [26,39] | 67% [59,75] | 35% [26,43] |
| Qwen-14B | 7% [3,12] | 48% [39,56] | 33% [26,41] |

Three findings a rule engine cannot give: (1) **without the terms, the model cannot guess each insurer's rules** (37%) — grounding is necessary; (2) **given a clean clause, a capable model applies it well** (88%); (3) **given the real policy document verbatim, accuracy drops to 69%**, and the small model collapses to near its no-terms level (35%) — real terms are far harder to parse than a clean summary, and the capable-vs-weak gap *widens* with realistic input. Terms grounding is thus essential and strongly presentation- and model-sensitive.

---

## 7. Discussion

**Objectivity comes from the terms, which is why no human gold set is needed.** Correctness is defined by each product's terms applied to the facts; cross-insurer differences are different rule profiles, not disagreement. This both answers the "whose judgment is the gold standard?" objection and removes human labeling from the critical path.

**The cascade assigns each decision to the right tool.** The structured, arithmetic decision belongs to a deterministic engine — objective, auditable, free (Section 5). The LLM's defensible role is narrow and measured: the free-text residual rules cannot encode (Exp 1) and the application of natural-language terms (Exp 2). A capable model is a high-recall, safe-direction filter there — it catches the textual anomalies (95–100%), resists injection, and errs toward over-investigation rather than leakage — while a weak one is near chance and leaks. Note the capable model is not a high-precision oracle (≈52% clean-case specificity): it is useful precisely as a *conservative first pass under human confirmation*, not as an autonomous approver. Any deployment claim must name the model, its error direction, and its evaluation protocol (blind, per-call), not merely "an LLM."

**Terms-encoding fidelity is the real hard problem — and it cuts both ways.** Our rule profiles are simplified from product summaries, and during construction we found that one profile's bridge rule did not match three of four real insurers' actual 약관, which we corrected against the verbatim text. This shows (a) hand-coding real terms into rules is error-prone, motivating LLMs that read the raw 약관, yet (b) even verbatim-fed capable models reach only 69% — so an LLM is not a drop-in substitute for a correctly encoded rule. The honest position is a cascade where rules carry the encodable part and the LLM assists, under human confirmation, on the rest.

**Three-way output and the human boundary.** The second pass recommends approve / investigate(supplement) / reject, and a human makes the binding decision. We make no efficiency claim: we measure recommendation quality, not its effect on human decisions.

---

## 8. Limitations and Future Work

- **Synthetic cases, terms-derived labels.** All cases are synthetic; ground truth is objective-by-construction from the terms but external validity is not established. An optional human-expert validation subset (≈30–40 cases) would strengthen it; the pipeline folds such labels in without re-running the models.
- **Capable-model identity and drift (Exp 1).** The capable-model judgments are now from a reproducible blind per-call API model (`gpt-5.5-2026-04-23`); we discarded an earlier non-blind session run that overstated accuracy by ~19 points. A hosted API model can still be deprecated or change, so we log the dated model id, prompt, and all inputs/outputs; a single capable model (plus two local models) demonstrates the capable-vs-weak gap but not the full capability curve.
- **Simplified terms profiles.** Profiles A/B/C are simplified from product summaries; T2 uses verbatim excerpts but not full policies. Full-policy grounding and more insurers are future work.
- **No human-reviewer effect; single run; no calibration.** We measure recommendation quality, not downstream human decisions; each model judged once; ECE/Brier, a traditional-ML baseline, and more model families are planned.
- **Rules reflect this system.** The 20% threshold and anomaly definitions follow the reference contract; external validity to other insurers' operational rules is a limitation.

---

## 9. Conclusion

Insurance eligibility review in a fixed-benefit product is objectively determined by the terms, so it can be evaluated without human gold labels, and its structured part belongs to a deterministic rule engine rather than an LLM. We demarcated that boundary empirically — rules catch structural anomalies but 0% of code–narrative mismatch — and measured the LLM exactly on the residual rules cannot encode. A reproducible capable model (gpt-5.5) covers that residual at high recall (code–narrative mismatch 95%, upcoding and text-only complex 100%) with full injection resistance and only safe-direction errors, though it is conservative on clean cases (overall 72%); it applies a clean clause at 88% but reaches only 69% on verbatim policy text, and weak local models are near chance and unsafe. We also found that a non-blind session run overstated capable-model accuracy by ~19 points, a caution for how such systems are evaluated. The defensible design is a terms-grounded cascade: deterministic rules first, a *capable* LLM as a high-recall conservative filter on the terms-grounded textual residual, and a human confirming — with amount adequacy out of scope for a fixed-benefit product, and model choice treated as a safety parameter, not a detail.

---

## References

*(Verify against primary text and current indexing before submission; unverifiable entries will be removed.)*

1. Islayem, R.; Gebreab, S.; AlKhader, W.; Musamih, A.; Salah, K.; Jayaraman, R.; Khan, M.K. Using Large Language Models for Enhanced Fraud Analysis and Detection in Blockchain-Based Health Insurance Claims. *Scientific Reports* **2025**, *15*, 11542.
2. Mo, Z.; Quan, Z.; O'Donohue, E.; Zhong, K. Claim Automation using Large Language Model. *arXiv* **2026**, arXiv:2602.16836. (Preprint — verify status.)
3. Roy, S.; Singh, A. Agentic AI for Commercial Insurance Underwriting with Adversarial Self-Critique. *arXiv* **2026**, arXiv:2602.13213. (Abstract only — verify.)
4. (Learning-to-defer / cost-sensitive triage — insert verified reference after reading.)
5. (Automation bias in AI-assisted decisions — insert verified reference after reading.)
6. (Prompt injection against tool-grounded LLM agents — insert verified reference after reading.)

---

## Appendix A: Data and Reproducibility

- Experiment 1 cases and blind sheets: `paper/eval/review/cases/` (dataset `aa25553d314f`).
- Experiment 1 reproducible judgments (gpt-5.5 blind per-call + the two local models, same frozen sheet): `cases/rater_results/api_rerun_gpt55_20261127/` with `rater_gpt55.json`, `accuracy_recomputed.{md,json}`, `accuracy_recomputed_excl_A3.{md,json}`, and `README.md`. The earlier non-blind session run is retained at `cases/rater_results/ai_proxy_20261119/` for the reproducibility comparison.
- Experiment 1 runner (now covers all 314 incl. complex): `paper/eval/review/run_model_raters.py`. Scorer (validated to reproduce the committed report; supports `--exclude A3`): `paper/eval/review/score_vs_ground_truth.py`.
- Rule baseline: `paper/eval/review/rules_baseline.py` → `results/rules_baseline.md`.
- Experiment 2 (terms conditions): `paper/eval/review/run_terms.py`, `terms_profiles.py`, `terms_verbatim.py`, scorer `score_terms.py` → `results/terms_report.md`.
