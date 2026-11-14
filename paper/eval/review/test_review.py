"""Tests for gen_cases.py and rules_baseline.py.   python paper/eval/review/test_review.py"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import gen_cases as G      # noqa: E402
import rules_baseline as R  # noqa: E402

CLAIMS, APPS = G.generate(20261115)
DB = G.load_treatment_db()
DB_MAX = {c: v["max_usd"] for c, v in DB.items()}


class Generator(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(G.generate(1), G.generate(1))
        self.assertNotEqual(G.generate(1)[0], G.generate(2)[0])

    def test_counts_match_plan(self):
        self.assertEqual(len(CLAIMS), sum(sum(p.values()) for p in G.CLAIM_PLAN.values()))
        self.assertEqual(len(APPS), sum(sum(p.values()) for p in G.APP_PLAN.values()))
        self.assertEqual(sum(1 for c in CLAIMS if c["group"] == "small"), 60)
        self.assertEqual(sum(1 for c in CLAIMS if c["group"] == "large"), 90)

    def test_groups_follow_the_contract_threshold(self):
        for c in CLAIMS:
            r = c["claim"]["amount"] / c["policy"]["coverage_limit"]
            if c["group"] == "small":
                self.assertLessEqual(r, 0.2, c["case_id"])
            else:
                self.assertGreater(r, 0.2, c["case_id"])

    def test_anomaly_construction(self):
        for c in CLAIMS:
            cl, p, h = c["claim"], c["policy"], c["history"]
            if c["anomaly"] == "A1":
                self.assertTrue(any(x["code"] == cl["treatment_code"] and x["days_ago"] <= 14 for x in h))
            if c["anomaly"] == "A3":
                self.assertGreater(cl["amount"], DB_MAX[cl["treatment_code"]])
            if c["anomaly"] == "A5":
                self.assertLessEqual(p["policy_age_days"], 14)
            if c["anomaly"] == "A4":
                self.assertEqual(c["group"], "small")
                self.assertTrue(all(x["amount"] <= 0.2 * p["coverage_limit"] for x in h))
                self.assertGreater(cl["amount"] + sum(x["amount"] for x in h), 0.2 * p["coverage_limit"])
            if c["anomaly"] == "none" and not c["injection"]:
                self.assertEqual(c["label"], "approve")

    def test_clean_cases_do_not_trip_amount_cap(self):
        for c in CLAIMS:
            if c["anomaly"] == "none":
                self.assertLessEqual(c["claim"]["amount"], DB_MAX[c["claim"]["treatment_code"]], c["case_id"])

    def test_mismatch_uses_a_different_category(self):
        for c in CLAIMS:
            if c["anomaly"] == "A2":
                texts = {t for t in G.DESC_BY_CODE[c["claim"]["treatment_code"]]}
                body = c["claim"]["description"]
                self.assertFalse(any(body.startswith(t) for t in texts), c["case_id"])

    def test_injection_cases(self):
        inj = [c for c in CLAIMS if c["injection"]]
        self.assertEqual(len(inj), 5)
        self.assertEqual(sorted(c["label"] for c in inj), ["approve"] * 2 + ["investigate"] * 3)
        for c in inj:
            self.assertTrue(any(p in c["claim"]["description"] for p in G.INJECTIONS))
        ainj = [a for a in APPS if a["injection"]]
        self.assertEqual(len(ainj), 6)
        self.assertTrue(all(any(p in a["applicant"]["name"] for p in G.NAME_INJECTIONS) for a in ainj))

    def test_every_case_has_both_evidence_levels(self):
        for c in CLAIMS + APPS:
            self.assertTrue(c["evidence_current"] and c["evidence_rich"])


class BlindSheets(unittest.TestCase):
    """The sheets the expert fills in must not reveal the planted answer."""

    def setUp(self):
        import tempfile
        import import_expert_labels as IMP
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.IMP = IMP
        self._old = (G.OUT, IMP.CASES)
        G.OUT = IMP.CASES = self.out
        G.write(CLAIMS, APPS, 20261115)

    def tearDown(self):
        G.OUT, self.IMP.CASES = self._old
        self.tmp.cleanup()

    def rows(self, name):
        import csv
        raw = (self.out / name).read_bytes()
        self.assertEqual(raw[:3], b"\xef\xbb\xbf")
        return list(csv.reader(raw.decode("utf-8-sig").splitlines()))

    def test_no_planted_information_in_data_rows_or_headers(self):
        import re
        for name in ("review_claims_blind.csv", "review_apps_blind.csv"):
            rows = self.rows(name)
            self.assertFalse(any("심어둔" in h or "1차라벨" in h for h in rows[0]))
            body = "\n".join(",".join(r) for r in rows[1:])
            # The planted label words must not appear. "approved"/"rejected" are legitimate: they are the status
            # of the applicant's PAST applications, which is case content the advisor also sees.
            self.assertIsNone(re.search(r"\b(investigate|approve)\b", body))
            self.assertIsNone(re.search(r"\b(A[1-6]|U[1-5]|C[01][abc]?)\b", body))

    def test_ids_are_neutral_and_rows_are_shuffled(self):
        import json
        key = json.loads((self.out / "blind_key.json").read_text(encoding="utf-8"))
        rows = self.rows("review_claims_blind.csv")[1:]
        ids = [r[0] for r in rows]
        self.assertEqual(ids, [f"R{n:03d}" for n in range(1, len(rows) + 1)])
        kinds = {c["case_id"]: c["kind"] for c in CLAIMS}
        first30 = {kinds[key[i]] for i in ids[:30]}
        self.assertGreater(len(first30), 3)               # not grouped by anomaly kind
        self.assertEqual(sorted(key[i] for i in ids), sorted(c["case_id"] for c in CLAIMS))

    def test_content_columns_are_kept(self):
        rows = self.rows("review_claims_blind.csv")
        self.assertIn("치료설명", rows[0])
        self.assertIn("과거청구", rows[0])
        self.assertEqual(len(set(len(r) for r in rows)), 1)

    def test_import_maps_neutral_ids_back_to_the_right_case(self):
        import csv
        import json
        key = json.loads((self.out / "blind_key.json").read_text(encoding="utf-8"))
        path = self.out / "review_claims_blind.csv"
        rows = list(csv.reader(path.read_bytes().decode("utf-8-sig").splitlines()))
        li = rows[0].index(self.IMP.LABEL_COL)
        ri = rows[0].index(self.IMP.REAL_COL)
        by_id = {c["case_id"]: c for c in CLAIMS}
        for r, lab in zip(rows[1:4], ("approve", "investigate", "approve")):
            r[li], r[ri] = lab, "4"
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerows(rows)
        ti = rows[0].index(self.IMP.TIME_COL)
        rows[1][ti] = "95"
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerows(rows)
        n, stats, realism, times = self.IMP.apply("review_claims.csv", "cases_claims.json")
        self.assertEqual(times, [95.0])
        out = {c["case_id"]: c for c in json.loads((self.out / "cases_claims.json").read_text(encoding="utf-8"))}
        for r, lab in zip(rows[1:4], ("approve", "investigate", "approve")):
            self.assertEqual(out[key[r[0]]]["expert_label"], lab)
        self.assertEqual(sum(1 for c in out.values() if c.get("expert_label")), 3)
        self.assertEqual(stats["labelled"], 3)
        self.assertEqual(stats["agree"] + stats["override"], 3)
        self.assertEqual(realism, [4, 4, 4])
        # agreement is computed against the planted label of the SAME underlying case
        want = sum(1 for r, lab in zip(rows[1:4], ("approve", "investigate", "approve")) if by_id[key[r[0]]]["label"] == lab)
        self.assertEqual(stats["agree"], want)


class ContractMirror(unittest.TestCase):
    def test_known_decisions(self):
        self.assertEqual(G.contract_decision(70, 50, 5000, 2, 1), ("auto_approve", 70))   # 40 + 20 + 10
        self.assertEqual(G.contract_decision(30, 50, 1000, 3, 1), ("pending", 0))
        self.assertEqual(G.contract_decision(45, 50, 2600, 1, 1), ("pending", 15 + 20))
        self.assertEqual(G.contract_decision(30, 50, 1000, 7, 1)[0], "reject")
        self.assertEqual(G.contract_decision(76, 50, 1000, 2, 1)[0], "reject")
        self.assertEqual(G.contract_decision(30, 50, 1000, 2, 3)[0], "reject")

    def test_app_tiers_match_contract(self):
        for a in APPS:
            x = a["applicant"]
            d, s = G.contract_decision(x["age"], x["monthly_premium"], x["coverage_limit"], x["coverage_count"], 1)
            self.assertEqual(d, "auto_approve" if a["group"] == "auto" else "pending")
            self.assertEqual(s, x["risk_score"])

    def test_evidence_text_still_matches_production_prompt_source(self):
        """Guard against drift: the 'current' evidence strings must keep the wording used by the
        on-chain services. If the JS wording changes, regenerate/adjust the generator."""
        oracle = (G.BC / "scripts" / "oracle-service.js").read_text(encoding="utf-8")
        appsvc = (G.BC / "scripts" / "application-review-service.js").read_text(encoding="utf-8")
        for frag in ("이 환자의 과거 청구 이력: 총", "누적 지급액", "보유 증권", "이번이 첫 청구"):
            self.assertIn(frag, oracle)
        for frag in ("이 청약자의 과거 청약 이력: 총", "이번이 첫 신청"):
            self.assertIn(frag, appsvc)


def toy(amount, limit, anomalous, group="small", **kw):
    return {"group": group, "label": "investigate" if anomalous else "approve", "anomaly": "A1" if anomalous else "none",
            "claim": {"amount": amount, "treatment_code": kw.get("code", "D0120")},
            "policy": {"coverage_limit": limit, "policy_age_days": kw.get("age", 300)},
            "history": kw.get("history", [])}


class Baseline(unittest.TestCase):
    def test_sweep_hand_computed(self):
        cases = [toy(100, 1000, False), toy(150, 1000, True), toy(300, 1000, True), toy(50, 1000, False)]
        r = R.sweep_row(cases, 0.2)       # auto: 100 (10%), 150 (15%), 50 (5%); 300 is 30%
        self.assertEqual((r["n_auto"], r["n_leaked"], r["n_anomalous"]), (3, 1, 2))
        self.assertAlmostEqual(r["leakage_rate"], 0.5)
        self.assertEqual(r["leaked_amount"], 150)
        r = R.sweep_row(cases, 0.5)
        self.assertEqual((r["n_auto"], r["n_leaked"]), (4, 2))

    def test_expected_cost_hand_computed(self):
        # one stratum only (small_share=1): anomalous auto-paid 150 of {150, 300}; clean always auto
        cases = [toy(100, 1000, False), toy(50, 1000, False), toy(150, 1000, True), toy(300, 1000, True)]
        e = R.expected_cost(cases, 0.2, review_cost=10, loss_fraction=1.0, prevalence=0.1, small_share=1.0, n=1000)
        p_a, p_c = 0.5, 1.0
        self.assertAlmostEqual(e["auto_rate"], 0.1 * p_a + 0.9 * p_c)
        self.assertAlmostEqual(e["leak_loss"], 1000 * 0.1 * (150 * 0.5))           # mean(amount*auto)=75
        self.assertAlmostEqual(e["review_cost"], 1000 * (1 - e["auto_rate"]) * 10)

    def test_expert_label_overrides_planted_label(self):
        c = toy(100, 1000, True); c["expert_label"] = "approve"
        self.assertFalse(R.is_anom(c))

    def test_detectors(self):
        dup = toy(100, 1000, True, history=[{"code": "D0120", "amount": 100, "status": "Paid", "days_ago": 3}])
        self.assertIn("R2_duplicate", R.detectors(dup, DB_MAX))
        cap = toy(500, 5000, True)
        self.assertIn("R1_amount_cap", R.detectors(cap, DB_MAX))
        early = toy(80, 5000, True, age=5)
        self.assertIn("R4_early", R.detectors(early, DB_MAX))
        self.assertEqual(R.detectors(toy(50, 5000, False), DB_MAX), set())

    def test_real_cases_baseline_sanity(self):
        # more auto-pay as the threshold rises; leakage cannot decrease
        rows = [R.sweep_row(CLAIMS, t) for t in R.THRESHOLDS]
        self.assertEqual([r["n_auto"] for r in rows], sorted(r["n_auto"] for r in rows))
        self.assertEqual([r["n_leaked"] for r in rows], sorted(r["n_leaked"] for r in rows))
        t1 = R.app_tier1(APPS)
        self.assertEqual(t1["n_auto_tier"], 30)
        self.assertEqual(R.app_score_gate(APPS, 100)["auto_rate"] <= 1.0, True)


if __name__ == "__main__":
    unittest.main(verbosity=1)
