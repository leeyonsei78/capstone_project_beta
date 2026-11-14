"""
Verdict parsing and advisor-quality metrics (RQ2).

Three verdicts are used everywhere:
  clean         the advisor sees nothing wrong (claims: 정상 / applications: 승인)
  flag          the advisor raises a concern    (claims: 주의 필요 / applications: 거절)
  insufficient  the advisor says the evidence is not enough to decide
                (structured prompt: 근거부족 / production application prompt: 보류)

"insufficient" matters because language models tend to answer even when the context cannot support
an answer (see related_work_notes.md). It is counted as "defer to a human", never as clean.

Ground truth per case: `expert_label` if the domain expert set one, else the planted `label`
("approve" = legitimate, "investigate" = anomalous).
"""
import json
import re

# ── Parsing ──────────────────────────────────────────────────────────────────


def parse_production_claim(text):
    """Production claim prompt answers '검토 의견: (정상/주의 필요) - 이유'."""
    if not text:
        return "unparsed"
    m = re.search(r"검토\s*의견\s*[:：]\s*(정상|주의\s*필요)", text)
    if m:
        return "clean" if m.group(1) == "정상" else "flag"
    i_flag, i_ok = text.find("주의"), text.find("정상")
    if i_flag == -1 and i_ok == -1:
        return "unparsed"
    if i_flag == -1:
        return "clean"
    if i_ok == -1:
        return "flag"
    return "flag" if i_flag < i_ok else "clean"


def parse_production_app(text):
    """Production application prompt answers '권고: (승인/거절/보류) - 이유'."""
    m = re.search(r"권고\s*[:：]\s*(승인|거절|보류)", text or "")
    if not m:
        return "unparsed"
    return {"승인": "clean", "거절": "flag", "보류": "insufficient"}[m.group(1)]


_STRUCT = {"정상": "clean", "주의": "flag", "근거부족": "insufficient", "근거 부족": "insufficient"}


def parse_structured(text):
    d = None
    try:
        d = json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text or "", re.S)
        if m:
            try:
                d = json.loads(m.group(0))
            except Exception:
                d = None
    if not isinstance(d, dict):
        return {"verdict": "unparsed", "confidence": None, "reason_code": None, "reason": None}
    try:
        conf = max(0, min(100, int(round(float(d.get("confidence"))))))
    except (TypeError, ValueError):
        conf = None
    return {"verdict": _STRUCT.get(str(d.get("verdict", "")).strip(), "unparsed"),
            "confidence": conf, "reason_code": d.get("reason_code"), "reason": d.get("reason")}


# ── Metrics ──────────────────────────────────────────────────────────────────


def truth_is_anomalous(row):
    return (row.get("expert_label") or row["label"]) == "investigate"


def ece(confs, correct, bins=10):
    """Expected calibration error. confs in [0,1]; correct in {0,1}."""
    n = len(confs)
    if n == 0:
        return None
    total = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, c in enumerate(confs) if lo <= c < hi or (b == bins - 1 and c == 1.0)]
        if idx:
            acc = sum(correct[i] for i in idx) / len(idx)
            conf = sum(confs[i] for i in idx) / len(idx)
            total += len(idx) / n * abs(acc - conf)
    return total


def brier(confs, correct):
    return sum((c - y) ** 2 for c, y in zip(confs, correct)) / len(confs) if confs else None


def _ratio(a, b):
    return a / b if b else None


def evaluate(rows):
    """rows: dicts with label/expert_label, verdict, confidence (0-100 or None), reason_code, anomaly.
    Returns a flat dict of metrics. Rates are None when the denominator is empty."""
    parsed = [r for r in rows if r["verdict"] != "unparsed"]
    anom = [r for r in parsed if truth_is_anomalous(r)]
    legit = [r for r in parsed if not truth_is_anomalous(r)]
    held = lambda r: r["verdict"] in ("flag", "insufficient")      # sent to a human
    tp = sum(1 for r in anom if r["verdict"] == "flag")
    fp = sum(1 for r in legit if r["verdict"] == "flag")

    decided = [r for r in parsed if r["verdict"] in ("clean", "flag") and r.get("confidence") is not None]
    correct = [1 if (r["verdict"] == "flag") == truth_is_anomalous(r) else 0 for r in decided]
    confs = [r["confidence"] / 100.0 for r in decided]

    flagged_anom = [r for r in anom if r["verdict"] == "flag" and r.get("reason_code")]
    return {
        "n": len(rows), "unparsed": len(rows) - len(parsed),
        "abstain_rate": _ratio(sum(1 for r in parsed if r["verdict"] == "insufficient"), len(parsed)),
        "flag_rate": _ratio(sum(1 for r in parsed if r["verdict"] == "flag"), len(parsed)),
        "recall_strict": _ratio(tp, len(anom)),                      # anomalous flagged
        "recall_deferral": _ratio(sum(1 for r in anom if held(r)), len(anom)),   # flagged or deferred
        "specificity": _ratio(sum(1 for r in legit if r["verdict"] == "clean"), len(legit)),
        "false_hold_rate": _ratio(sum(1 for r in legit if held(r)), len(legit)),
        "precision": _ratio(tp, tp + fp),
        "accuracy_decided": _ratio(sum(correct), len(correct)),
        "ece": ece(confs, correct), "brier": brier(confs, correct), "n_calibration": len(decided),
        "reason_accuracy": _ratio(sum(1 for r in flagged_anom if r["reason_code"] == r.get("anomaly")),
                                  len(flagged_anom)),
        "clean_confidence_on_anomalous": _ratio(
            sum(r["confidence"] for r in anom if r["verdict"] == "clean" and r.get("confidence") is not None),
            sum(1 for r in anom if r["verdict"] == "clean" and r.get("confidence") is not None)),
    }


def prevalence_adjusted_ppv(recall, specificity, prevalence):
    """PPV at an assumed real-world prevalence (the evaluation set is enriched)."""
    if recall is None or specificity is None:
        return None
    tp = prevalence * recall
    fp = (1 - prevalence) * (1 - specificity)
    return tp / (tp + fp) if (tp + fp) else None
