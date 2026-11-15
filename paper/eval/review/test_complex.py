import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import gen_complex_cases as GC   # noqa: E402
import gen_cases as G            # noqa: E402
import run_advisor as RA         # noqa: E402
import score_complexity as SC    # noqa: E402


class ComplexLayer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = GC.generate(1)

    def test_counts_and_isolation(self):
        self.assertEqual(len(self.cases), sum(GC.PLAN.values()))
        self.assertTrue(all(c["group"] == "complex" for c in self.cases))
        self.assertTrue(all(c["claim"]["ratio_of_limit"] > G.AUTO_PCT for c in self.cases))

    def test_deterministic(self):
        self.assertEqual(json.dumps(GC.generate(1)), json.dumps(self.cases))

    def test_summary_hides_tooth_but_rich_shows_it(self):
        for c in self.cases:
            if c["history"]:
                self.assertNotIn("번)", c["evidence_current"])
                self.assertIn("번)", c["evidence_rich"])

    def test_l2_tooth_logic(self):
        for c in self.cases:
            t, h = c["claim"]["tooth"], c["history"]
            if c["kind"] == "X1clean":
                self.assertNotEqual(h[0]["tooth"], t)
                self.assertEqual(h[0]["code"], c["claim"]["treatment_code"])
            if c["kind"] == "X1anom":
                self.assertEqual(h[0]["tooth"], t)
            if c["kind"] in ("X2clean", "X2anomCrown"):
                self.assertEqual(h[0]["tooth"], t)
                self.assertTrue(h[0]["code"].startswith("D72") or h[0]["code"] == "D7140")

    def test_l3_description_matches_cheaper_code_only_when_anomalous(self):
        for c in self.cases:
            if c["complexity"] != "L3":
                continue
            fam = next(f for f in GC.FAMILIES if f[1] == c["claim"]["treatment_code"])
            body = c["claim"]["description"].split(" - ", 1)[1]
            self.assertIn(body, G.DESC_BY_CODE[fam[0] if c["kind"] == "X3anom" else fam[1]])

    def test_not_in_existing_scopes(self):
        claims, apps = RA.load_cases()
        for scope in ("tier2", "all", "cf"):
            ids = {c["case_id"] for c in RA.select_cases(scope, claims, apps)}
            self.assertFalse([i for i in ids if i.startswith("CX-")])

    def test_scorer_reads_cx_dirs(self):
        cases = {c["case_id"]: c for c in self.cases}
        old = SC.RESULTS
        try:
            with tempfile.TemporaryDirectory() as d:
                SC.RESULTS = Path(d)
                out = Path(d) / "advisor" / "m" / "C3_cx"
                out.mkdir(parents=True)
                for c in self.cases:
                    v = "flag" if c["label"] == "investigate" else "clean"      # perfect advisor
                    (out / f"{c['case_id']}__r1.json").write_text(json.dumps(
                        {"case_id": c["case_id"], "verdict": v, "confidence": 90, "reason_code": c["anomaly"]}))
                m = SC.AM.evaluate(SC.load_rows("m", cases)["C3"])
                self.assertEqual((m["recall_strict"], m["specificity"]), (1.0, 1.0))
        finally:
            SC.RESULTS = old


if __name__ == "__main__":
    unittest.main()
