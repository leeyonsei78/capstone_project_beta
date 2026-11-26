# Reproducible capable-model re-run (gpt-5.5, 2026-11-27)

Replaces the non-reproducible "Codex" session slot of ai_proxy_20261119 for Experiment 1.
- Capable model: `gpt-5.5-2026-04-23` via OpenAI API, neutral blind single-case prompt
  (same SYSTEM prompt and same frozen blind sheet, dataset `aa25553d314f`, as the local models).
- qwen / deepseek rater files copied unchanged from ai_proxy_20261119 (same frozen sheet).
- 314/314 judged, 0 unparsed. Scored by score_vs_ground_truth.py (validated to reproduce the
  committed ai_proxy report on the session-Codex slot).

Key difference from the session-Codex number: gpt-5.5 under a truly blind, per-call protocol is
high-recall on anomalies (A2 95%, A5/X3/text-only 100%, injection 0/11 obeyed) but low-specificity
on clean cases (~52%), so it over-investigates (safe direction). Overall 72.3% (A3-excluded 72.4%),
vs the session-Codex 91.4% — the gap is almost entirely clean-case specificity, consistent with the
session model having seen project context (not fully blind; see ai_proxy README).
