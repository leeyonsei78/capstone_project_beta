import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import terms_profiles as TP     # noqa: E402
import gen_terms_cases as GT    # noqa: E402
import run_terms as RT          # noqa: E402
import score_terms as ST        # noqa: E402

A, B, C = (TP.PROFILES[k] for k in "ABC")


def S(cov="implant", cause="disease", ev=300, ex=200, kind="normal", cnt=0):
    return {"coverage": cov, "cause": cause, "event_day": ev,
            "extraction_day": ex if cov in TP.PROSTHETIC else None,
            "extraction_kind": kind if cov in TP.PROSTHETIC else None, "count_this_year": cnt}


class Engine(unittest.TestCase):
    def test_profile_A(self):
        self.assertEqual(TP.decide(A, S(ev=100, ex=50)), (.5, "reduced"))
        self.assertEqual(TP.decide(A, S(ev=800, ex=700)), (1.0, "none"))
        self.assertEqual(TP.decide(A, S(ev=60, ex=20)), (0.0, "waiting"))
        self.assertEqual(TP.decide(A, S(cause="accident", ev=10, ex=5)), (1.0, "none"))
        self.assertEqual(TP.decide(A, S(ev=800, ex=700, cnt=9)), (1.0, "none"))          # no implant cap

    def test_profile_A_crown_boundary(self):
        self.assertEqual(TP.decide(A, S(cov="crown", ev=300)), (.5, "reduced"))
        self.assertEqual(TP.decide(A, S(cov="crown", ev=420)), (1.0, "none"))

    def test_profile_B(self):
        self.assertEqual(TP.decide(B, S(ev=150, ex=60)), (0.0, "waiting"))              # implant waits 180
        self.assertEqual(TP.decide(B, S(ev=200, ex=100)), (.5, "reduced"))
        self.assertEqual(TP.decide(B, S(ev=200, ex=100, cnt=3)), (0.0, "annual_cap"))
        self.assertEqual(TP.decide(B, S(ev=800, ex=700, cnt=5)), (1.0, "none"))          # cap lifted after 730
        self.assertEqual(TP.decide(B, S(cov="crown", ev=100)), (.5, "reduced"))          # crown reduction 270
        self.assertEqual(TP.decide(B, S(cov="crown", ev=300)), (1.0, "none"))

    def test_profile_C(self):
        self.assertEqual(TP.decide(C, S(ev=800, ex=600)), (.5, "reduced"))               # extraction basis
        self.assertEqual(TP.decide(A, S(ev=800, ex=600)), (1.0, "none"))                 # same facts, other terms
        self.assertEqual(TP.decide(C, S(ev=800, ex=700, kind="wisdom")), (0.0, "excluded_kind"))
        self.assertEqual(TP.decide(A, S(ev=800, ex=700, kind="wisdom")), (1.0, "none"))
        self.assertEqual(TP.decide(C, S(ev=200, ex=60)), (0.0, "pre_start"))
        self.assertEqual(TP.decide(C, S(ev=800, ex=700, cnt=3)), (0.0, "annual_cap"))
        self.assertEqual(TP.decide(C, S(cause="accident", ev=20, ex=5)), (1.0, "none"))
        self.assertEqual(TP.decide(C, S(cov="crown", ev=500)), (.5, "reduced"))          # crown reduction 730

    def test_priority_exclusion_before_waiting(self):
        self.assertEqual(TP.decide(C, S(ev=40, ex=10, kind="ortho")), (0.0, "excluded_kind"))


class Generator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = GT.generate(1, 40)

    def test_shape_and_pairing(self):
        self.assertEqual(len(self.cases), 120)
        by = {}
        for c in self.cases:
            by.setdefault(c["scenario"], []).append(c)
        for cs in by.values():
            self.assertEqual({c["profile"] for c in cs}, {"A", "B", "C"})
            self.assertEqual(len({json.dumps(c["facts"], sort_keys=True) for c in cs}), 1)
            self.assertEqual(len({c["expected"] for c in cs}) > 1, cs[0]["profiles_disagree"])
        self.assertEqual(sum(1 for cs in by.values() if cs[0]["profiles_disagree"]), 24)

    def test_expected_matches_engine_and_margins(self):
        for c in self.cases:
            r, _ = TP.decide(TP.PROFILES[c["profile"]], c["facts"])
            self.assertEqual(TP.DECISION_OF_RATIO[r], c["expected"])
            f = c["facts"]
            self.assertFalse(TP.near_threshold(f["event_day"]))
            if f["extraction_day"] is not None:
                self.assertFalse(TP.near_threshold(f["extraction_day"]))
                self.assertLessEqual(f["extraction_day"], f["event_day"])

    def test_deterministic(self):
        self.assertEqual(json.dumps(GT.generate(1, 40)), json.dumps(self.cases))


class Prompts(unittest.TestCase):
    def test_t0_hides_clause_t1_shows_it(self):
        case = next(c for c in GT.generate(2, 20) if c["profile"] == "B" and c["facts"]["coverage"] == "implant")
        _, u0 = RT.build_prompt(case, "T0")
        _, u1 = RT.build_prompt(case, "T1")
        self.assertNotIn("[약관 요약", u0)
        self.assertNotIn("180일", u0)
        self.assertIn("180일", u1)
        self.assertIn("[약관 요약 - 상품 B]", u1)
        for u in (u0, u1):                       # the profile letter of the case must not leak in T0
            self.assertIn(case["case_id"], u)
        self.assertNotIn("상품 B", u0)

    def test_clause_numbers_follow_profile(self):
        self.assertIn("개수 한도가 없습니다", TP.render_clause(A))
        self.assertIn("발치일", TP.render_clause(C))
        self.assertIn("사랑니", TP.render_clause(C))
        self.assertNotIn("사랑니", TP.render_clause(A))

    def test_parser(self):
        self.assertEqual(RT.normalize_decision("부지급"), "부지급")
        self.assertEqual(RT.normalize_decision("감액 지급"), "감액지급")
        self.assertEqual(RT.normalize_decision("전액 지급"), "지급")
        self.assertEqual(RT.normalize_decision("근거부족"), "근거부족")
        p = RT.parse('```json\n{"decision":"감액지급","reason_code":"reduced","confidence":80,"reason":"x"}\n```')
        self.assertEqual((p["decision"], p["reason_code"], p["confidence"]), ("감액지급", "reduced", 80))
        self.assertEqual(RT.parse("no json")["decision"], "unparsed")


class Scorer(unittest.TestCase):
    def _write(self, d, model, cond, cases, fn):
        out = Path(d) / "terms" / model / cond
        out.mkdir(parents=True)
        for c in cases:
            (out / f"{c['case_id']}__r1.json").write_text(json.dumps(
                {"case_id": c["case_id"], "scenario": c["scenario"], "profile": c["profile"], "rep": 1,
                 "decision": fn(c)}), encoding="utf-8")

    def test_perfect_and_blind(self):
        cases = GT.generate(3, 30)
        by_id = {c["case_id"]: c for c in cases}
        old_r = ST.RESULTS
        try:
            with tempfile.TemporaryDirectory() as d:
                ST.RESULTS = Path(d)
                self._write(d, "perfect", "T1", cases, lambda c: c["expected"])
                self._write(d, "blind", "T0", cases, lambda c: "지급")
                m = ST.metrics(ST.load("perfect", by_id)["T1"])
                self.assertEqual((m["acc"], m["adapt"], m["over"], m["under"]), (1.0, 1.0, 0.0, 0.0))
                b = ST.metrics(ST.load("blind", by_id)["T0"])
                self.assertEqual(b["under"], 0.0)
                self.assertGreater(b["over"], 0.3)
                self.assertLess(b["adapt"], 1.0)
        finally:
            ST.RESULTS = old_r


if __name__ == "__main__":
    unittest.main()
