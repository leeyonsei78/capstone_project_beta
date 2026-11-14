"""
Generate Figure 2: before/after correctness-rate bar chart for the paper.

Usage (after running harness.py --phase before and --phase after):
  python paper/draft/figures/gen_fig2.py
  python paper/draft/figures/gen_fig2.py --model gpt-4o-mini

Reads:  paper/eval/results/{model}/{before_mitigation,after_mitigation}/*.json
Writes: paper/draft/figures/fig2_before_after[_{model}].png  (300 DPI)

If --model is omitted, uses the first model directory found (or the flat
legacy layout results/{phase}/*.json for backward compatibility).
"""

import argparse
import json
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = Path(__file__).parent.parent.parent / "eval" / "results"
OUT_FILE    = Path(__file__).parent / "fig2_before_after.png"

# Error-type groups to plot (exclude MX/BL/ST from primary chart)
PRIMARY = ["E1_array_truncation", "E2_temporal_reasoning",
           "E3_stale_tool_reuse", "E4_timezone_ambiguity",
           "E5_expression_variability", "E6_conditional_logic_failure"]

LABELS = {
    "E1_array_truncation":        "E1\nArray\nTruncation",
    "E2_temporal_reasoning":      "E2\nTemporal\nArithmetic",
    "E3_stale_tool_reuse":        "E3\nStale\nReuse",
    "E4_timezone_ambiguity":      "E4\nTimezone\nAmbiguity",
    "E5_expression_variability":  "E5\nExpression\nVariability",
    "E6_conditional_logic_failure":"E6\nConditional\nLogic",
}

COLORS = {"before_mitigation": "#ef4444", "after_mitigation": "#22c55e"}


def _resolve_model_dir(model_slug: str = None) -> Path:
    """Return the base directory for a model's results."""
    if model_slug:
        return RESULTS_DIR / model_slug
    # Auto-detect: prefer model subdirs over flat layout
    if RESULTS_DIR.exists():
        subdirs = [d for d in RESULTS_DIR.iterdir() if d.is_dir()
                   and not d.name.endswith("_mitigation")]
        if subdirs:
            return subdirs[0]
    return RESULTS_DIR  # flat legacy layout


def load_phase(phase: str, base_dir: Path) -> dict:
    """Returns {error_type: correctness_rate}."""
    phase_dir = base_dir / phase
    if not phase_dir.exists():
        print(f"[warn] {phase_dir} not found — using placeholder 0.0")
        return {et: 0.0 for et in PRIMARY}
    rates = {}
    for et in PRIMARY:
        items = []
        for f in phase_dir.glob("*.json"):
            try:
                r = json.loads(f.read_text(encoding="utf-8"))
                if r.get("error_type") == et:
                    items.append(r)
            except Exception:
                continue
        if items:
            correct = sum(1 for x in items if x["scoring"]["correct"])
            rates[et] = correct / len(items)
        else:
            rates[et] = 0.0
    return rates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None,
                    help="Model slug (e.g. gpt-4o-mini). Omit to auto-detect.")
    args = ap.parse_args()

    model_slug = args.model.replace("/", "-").replace(":", "-") if args.model else None
    base_dir = _resolve_model_dir(model_slug)
    print(f"Reading results from: {base_dir}")

    # Adjust output filename when a specific model is requested
    out_file = OUT_FILE
    if model_slug and model_slug != "gpt-4o":
        out_file = OUT_FILE.with_stem(f"fig2_before_after_{model_slug}")

    before = load_phase("before_mitigation", base_dir)
    after  = load_phase("after_mitigation", base_dir)

    x     = np.arange(len(PRIMARY))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))

    bars_b = ax.bar(x - width / 2,
                    [before[et] for et in PRIMARY],
                    width, label="Before mitigation",
                    color=COLORS["before_mitigation"], alpha=0.85)
    bars_a = ax.bar(x + width / 2,
                    [after[et] for et in PRIMARY],
                    width, label="After mitigation",
                    color=COLORS["after_mitigation"], alpha=0.85)

    ax.set_xlabel("Error Type", fontsize=12)
    ax.set_ylabel("Correctness Rate", fontsize=12)
    ax.set_title("Figure 2. Correctness Rate Before and After Mitigation\nby TLPE Error Class",
                 fontsize=12, pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[et] for et in PRIMARY], fontsize=9)
    ax.set_ylim(0, 1.05)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0%", "20%", "40%", "60%", "80%", "100%"])
    ax.legend(fontsize=10)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

    # Annotate bars
    for bar in bars_b:
        h = bar.get_height()
        if h > 0:
            ax.annotate(f"{h:.0%}", xy=(bar.get_x() + bar.get_width() / 2, h),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=8, color="#991b1b")
    for bar in bars_a:
        h = bar.get_height()
        if h > 0:
            ax.annotate(f"{h:.0%}", xy=(bar.get_x() + bar.get_width() / 2, h),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=8, color="#15803d")

    fig.tight_layout()
    fig.savefig(str(out_file), dpi=300, bbox_inches="tight")
    print(f"Saved: {out_file}")


if __name__ == "__main__":
    main()
