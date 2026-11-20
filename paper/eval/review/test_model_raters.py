"""Offline checks for run_model_raters.py (no network). Run: python paper/eval/review/test_model_raters.py"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import run_model_raters as R  # noqa: E402
import import_rater_results as IR  # noqa: E402

n = 0


def ok(cond, msg):
    global n
    assert cond, "FAIL: " + msg
    n += 1


# ── load_blind_rows mirrors the human sheet exactly ──────────────────────────
rows = R.load_blind_rows()
bids = [r["blind_id"] for r in rows]
key = json.loads((R.CASES / "blind_key.json").read_text(encoding="utf-8"))
ok(len(rows) == len(key), f"row count {len(rows)} == blind_key {len(key)}")
ok(set(bids) == set(key), "every blind row id is in blind_key and vice versa")
ok(len(bids) == len(set(bids)), "blind ids unique")
ok(any(b.startswith("R") for b in bids) and any(b.startswith("S") for b in bids), "has claims (R) and apps (S)")

# the blank human columns must never reach the model
joined = "\n".join(r["user"] for r in rows)
for col in ("전문가라벨", "전문가메모", "현실성", "소요시간"):
    ok(col not in joined, f"human-only column '{col}' not shown to model")
# a planted injection row is passed through verbatim (that is the point of the probe)
ok("심사 기준 무시" in joined, "prompt-injection text is forwarded to the model, not stripped")

# ── parse_label ──────────────────────────────────────────────────────────────
ok(R.parse_label('{"label":"approve","reason":"ok"}') == ("approve", "ok"), "parse clean approve json")
ok(R.parse_label('잡담 {"label": "investigate", "reason": "의심"} 끝')[0] == "investigate", "parse json inside noise")
ok(R.parse_label("검토 의견: investigate 필요")[0] == "investigate", "parse bare investigate")
ok(R.parse_label("approve 권장")[0] == "approve", "parse bare approve")
ok(R.parse_label("둘 다 approve 또는 investigate 가능")[0] is None, "ambiguous -> None (never guessed)")
ok(R.parse_label("")[0] is None, "empty -> None")

# ── majority ─────────────────────────────────────────────────────────────────
ok(R.majority(["approve", "approve", "investigate"]) == ("approve", None), "majority picks winner")
ok(R.majority(["approve", "investigate"])[0] is None, "even tie -> None")
ok(R.majority([None, None])[0] is None, "no valid votes -> None")

# ── build_rater_json is a valid review_rater_v1 export ────────────────────────
judged = {r["blind_id"]: {"label": ("investigate" if i % 3 == 0 else "approve"),
                          "reason": "r", "seconds": 1.2, "votes": None}
          for i, r in enumerate(rows)}
rj = R.build_rater_json("fakemodel", "fake:latest", judged, R.CASES,
                        {"base_url": "http://localhost:11434/v1", "reps": 1})
ok(rj["format"] == "review_rater_v1", "format tag")
ok(rj["dataset_id"] == IR.dataset_id(R.CASES), "dataset_id matches current sheet")
ok(set(rj["labels"]) == set(key), "labels cover all blind ids")
ok(all(v["label"] in R.VALID for v in rj["labels"].values()), "all labels valid")

# a dropped (unparsed) case must simply be absent, not guessed
judged2 = dict(judged)
some = bids[0]
judged2[some] = {"label": None, "reason": "", "seconds": None, "votes": None}
rj2 = R.build_rater_json("m2", "m2", judged2, R.CASES, {"base_url": "x", "reps": 1})
ok(some not in rj2["labels"], "unparsed case is omitted from labels")

# ── end-to-end: import_rater_results accepts two synthetic model raters (read-only) ──
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    (d / "fakemodel.json").write_text(json.dumps(rj, ensure_ascii=False), encoding="utf-8")
    (d / "m2.json").write_text(json.dumps(rj2, ensure_ascii=False), encoding="utf-8")
    text, info = IR.run(src=d, write=False)   # write=False: does not touch the real case files
    ok(info["labelled"] == len(key), f"import labelled all {len(key)} cases from model raters")
    ok("Cohen's κ" in text or "Cohen" in text, "agreement report computed for 2 raters")

print(f"all {n} checks passed")
