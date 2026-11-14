"""Tests for score_advisor.py with simulated advisors (no network).
Simulated advisors
  C3  sees the detailed history  -> flags exactly the anomalous cases
  C2  sees only the summary      -> flags the anomalies visible in it (A2 A3 A5 U2 U3 U4), misses A1 A4 U1
Run:  python paper/eval/review/test_score_advisor.py"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import advisor_metrics as AM   # noqa: E402
import gen_cases as G          # noqa: E402
import run_advisor as RA       # noqa: E402
import score_advisor as SA     # noqa: E402

CLAIMS, APPS = G.generate(20261115)
DB_MAX = {c: v["max_usd"] for c, v in G.load_treatment_db().items()}
VISIBLE = {"A2", "A3", "A5", "U2", "U3", "U4"}
ARGS = SimpleNamespace(model="m", small_share=0.85, prevalence=0.03, human_sens=0.85, human_spec=0.95,
                       price_in=2.5, price_out=10.0)


def verdict_for(case, cond):
    anomalous = case["label"] == "investigate"
    if not anomalous:
        return "clean"
    if cond == "C3" or case["anomaly"] in VISIBLE:
        return "flag"
    return "clean"


def rec(case, cond, rep, verdict, cf=None):
    return {"case_id": case["case_id"], "cond": cond, "rep": rep, "model": "m", "type": case["type"],
            "group": case["group"], "anomaly": case["anomaly"], "label": case["label"], "expert_label": None,
            "injection": case.get("injection", False), "cf_of": case.get("cf_of"), "cf_type": case.get("cf_type"),
            "raw": "", "verdict": verdict, "confidence": 90, "reason_code": None, "reason": None,
            "usage": {"prompt_tokens": 400, "completion_tokens": 50}}


def write_world(root, conds=("C2", "C3"), reps=(1, 2), with_cf=True):
    cases_dir, res = root / "cases", root / "results"
    cases_dir.mkdir()
    (cases_dir / "cases_claims.json").write_text(json.dumps(CLAIMS, ensure_ascii=False), encoding="utf-8")
    (cases_dir / "cases_apps.json").write_text(json.dumps(APPS, ensure_ascii=False), encoding="utf-8")
    for cond in conds:
        d = res / "advisor" / "m" / cond
        d.mkdir(parents=True)
        for case in CLAIMS + APPS:
            for rep in reps:
                (d / f"{case['case_id']}__r{rep}.json").write_text(
                    json.dumps(rec(case, cond, rep, verdict_for(case, cond))), encoding="utf-8")
        if with_cf and cond in ("C2", "C3"):
            dcf = res / "advisor" / "m" / (cond + "_cf")
            dcf.mkdir(parents=True)
            by = {c["case_id"]: c for c in APPS}
            for tw in RA.select_cases("cf", CLAIMS, APPS):
                for rep in reps:
                    v = verdict_for(by[tw["cf_of"]], cond)            # twins behave exactly like the original
                    (dcf / f"{tw['case_id']}__r{rep}.json").write_text(json.dumps(rec(tw, cond, rep, v)), encoding="utf-8")
    return cases_dir, res


class Scoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.cases_dir, cls.res = write_world(cls.root)
        claims, apps, cls.by_id = SA.load_cases(cls.cases_dir)
        cls.runs = SA.load_runs(cls.res / "advisor" / "m", cls.by_id)
        cls.report, cls.summary = SA.build_report(cls.runs, {c["case_id"]: c for c in claims}, DB_MAX, ARGS)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_runs_loaded(self):
        self.assertEqual(set(self.runs), {"C2", "C3", "C2_cf", "C3_cf"})
        self.assertEqual(len(self.runs["C3"]), (150 + 90) * 2)

    def test_quality_perfect_advisor(self):
        q = self.summary["quality"]["C3/claim"]
        self.assertEqual((q["recall_strict"], q["specificity"], q["abstain_rate"]), (1.0, 1.0, 0.0))
        self.assertEqual(q["n"], 90 * 2)

    def test_quality_summary_only_advisor_misses_invisible(self):
        q = self.summary["quality"]["C2/claim"]
        # tier-2 anomalies: A1 14, A2 17, A3 14, A5 13 = 58; A1 is invisible -> 44/58
        self.assertAlmostEqual(q["recall_strict"], 44 / 58)
        self.assertEqual(q["specificity"], 1.0)

    def test_evidence_effect(self):
        d = self.summary["evidence"]["A1, A4, U1 (invisible in the summary)"]
        self.assertAlmostEqual(d["mean"], 1.0)
        v = self.summary["evidence"]["A2, A3, A5, U2, U3, U4 (visible in the summary)"]
        self.assertAlmostEqual(v["mean"], 0.0)

    def test_frontier(self):
        amount = {p["param"]: p for p in self.summary["frontier"]["amount"]}
        # 20% rule: every small claim is paid; 30 of the 88 anomalous claims are small
        self.assertAlmostEqual(amount[0.20]["leakage_rate"], 30 / 88)
        self.assertAlmostEqual(amount[0.20]["workload"], 90 / 150)
        gate = self.summary["frontier"]["C3/llm_gate"]
        self.assertTrue(any(p["leakage_rate"] == 0.0 and p["workload"] < 1.0 for p in gate))
        # the summary-only advisor misses A1/A4 here, but the hybrid also applies rules R2/R3, so it stays bounded
        hybrid2 = self.summary["frontier"]["C2/hybrid@20%"]
        self.assertTrue(all(0.0 <= p["leakage_rate"] <= 1.0 for p in hybrid2))
        self.assertIn("Deferral-policy frontier", self.report)

    def test_counterfactual_and_noise(self):
        s = self.summary["counterfactual"]["C3/all"]
        self.assertEqual((s["verdict_change_rate"], s["mcnemar_p"]), (0.0, 1.0))
        self.assertEqual(self.summary["noise_floor"]["C3"], 0.0)

    def test_reliance_uses_measured_advisor(self):
        r = self.summary["reliance"]
        self.assertEqual(r["cond"], "C3")
        self.assertAlmostEqual(r["adv_sens"], 1.0)

    def test_report_sections(self):
        for s in ("## 1.", "## 2.", "## 3.", "## 4.", "## 5.", "## 6.", "## 7."):
            self.assertIn(s, self.report)
        self.assertIn("input and", self.report)


class TruthRejoin(unittest.TestCase):
    def test_expert_label_imported_after_the_run_is_honoured(self):
        with tempfile.TemporaryDirectory() as d:
            cases_dir, res = write_world(Path(d), conds=("C3",), reps=(1,), with_cf=False)
            claims = json.loads((cases_dir / "cases_claims.json").read_text(encoding="utf-8"))
            target = next(c for c in claims if c["group"] == "large" and c["label"] == "investigate")
            target["expert_label"] = "approve"                       # the expert disagrees with the planted label
            (cases_dir / "cases_claims.json").write_text(json.dumps(claims, ensure_ascii=False), encoding="utf-8")
            _, _, by_id = SA.load_cases(cases_dir)
            runs = SA.load_runs(res / "advisor" / "m", by_id)
            rows = [r for r in runs["C3"] if r["tier2"] and r["type"] == "claim"]
            m = AM.evaluate(rows)
            self.assertAlmostEqual(m["recall_strict"], 1.0)           # 57 anomalous, all flagged
            self.assertAlmostEqual(m["specificity"], 32 / 33)         # the relabelled case is now a false alarm


class Robustness(unittest.TestCase):
    def test_only_c1_present(self):
        with tempfile.TemporaryDirectory() as d:
            cases_dir, res = write_world(Path(d), conds=("C1",), reps=(1,), with_cf=False)
            claims, _, by_id = SA.load_cases(cases_dir)
            runs = SA.load_runs(res / "advisor" / "m", by_id)
            text, summary = SA.build_report(runs, {c["case_id"]: c for c in claims}, DB_MAX, ARGS)
            self.assertIn("C1", text)
            self.assertIn("Needs both C2 and C3", text)
            self.assertIn("Needs C2/C3 results over **all** claims", text)

    def test_tier2_only_runs_skip_the_frontier_with_a_message(self):
        with tempfile.TemporaryDirectory() as d:
            cases_dir, res = write_world(Path(d), conds=("C2", "C3"), reps=(1,), with_cf=False)
            # drop automatic-tier results to mimic `--scope tier2`
            for f in (res / "advisor" / "m").glob("C*/*.json"):
                r = json.loads(f.read_text(encoding="utf-8"))
                if r["group"] in ("small", "auto"):
                    f.unlink()
            claims, _, by_id = SA.load_cases(cases_dir)
            runs = SA.load_runs(res / "advisor" / "m", by_id)
            text, _ = SA.build_report(runs, {c["case_id"]: c for c in claims}, DB_MAX, ARGS)
            self.assertIn("Needs C2/C3 results over **all** claims", text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
