"""Unit tests for scorers.py (no network / chain needed).
Run:  python paper/eval/test_scorers.py
Each scorer must (a) accept a correct answer and (b) REJECT the specific error it
is meant to detect -- the old E1 scorer accepted everything."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import scorers as S  # noqa: E402

GT = {
    "queriedAt": "2026. 11. 15. 오후 2:00:00 (KST)",
    "policies": [
        {"policyId": 1, "monthlyPremium": "$50.00",  "coverageLimit": "$1000.00",
         "timeUntilMaturity": "오늘, 2시간 41분 후", "maturityDate": "2026. 11. 15. 오후 4:41:00 (KST)",
         "lastPaymentDate": "2026. 11. 15. 오후 1:30:00 (KST)", "nextDueDate": "2026. 11. 15. 오후 3:30:00 (KST)"},
        {"policyId": 2, "monthlyPremium": "$120.00", "coverageLimit": "$3000.00", "timeUntilMaturity": "3일 4시간 후"},
        {"policyId": 3, "monthlyPremium": "$90.00",  "coverageLimit": "$1500.00", "timeUntilMaturity": "7일 1시간 후"},
        {"policyId": 4, "monthlyPremium": "$150.00", "coverageLimit": "$2500.00", "timeUntilMaturity": "30일 0시간 후"},
    ],
    "claims": [
        {"claimId": 1, "policyId": 1, "amount": "$100.00", "processedAt": "2026. 11. 15. 오후 1:45:00 (KST)"},
        {"claimId": 2, "policyId": 2, "amount": "$250.00", "processedAt": "2026. 11. 15. 오후 1:50:00 (KST)"},
    ],
    "altinvest": {"positions": [
        {"fundName": "그린인프라 대체투자 펀드", "timeUntilUnlock": "89일 20시간 후",
         "unlockDate": "2027. 2. 12. 오전 9:15:00 (KST)"},
        {"fundName": "프라임오피스 리츠 펀드", "timeUntilUnlock": "179일 3시간 후",
         "unlockDate": "2027. 5. 14. 오후 12:00:00 (KST)"},
    ]},
    "parametric": {"coverages": [
        {"coverageId": 1, "productName": "항공편 지연 보장"},
        {"coverageId": 2, "productName": "폭염특보 보장"},
    ]},
}

ALL4 = "증권 4개: $50.00, $120.00, $90.00, $150.00 입니다."
MISS1 = "증권 3개: $50.00, $120.00, $150.00 입니다."


class E1(unittest.TestCase):
    def test_all_policies_listed(self):
        self.assertTrue(S.score_e1("policies.length", ALL4, GT)[0])

    def test_one_omitted_is_caught(self):
        ok, note = S.score_e1("policies.length", MISS1, GT)
        self.assertFalse(ok); self.assertIn("3/4", note)

    def test_substring_digits_do_not_count(self):
        # old scorer: '4' appears in '$150.00' / dates -> counted as mentioned
        text = "총 보험료 $50.00, $120.00, $150.00 이며 2026. 11. 14. 에 가입했습니다."
        self.assertFalse(S.score_e1("policies.length", text, GT)[0])

    def test_amount_not_matched_inside_larger_number(self):
        self.assertFalse(S.amount_present("한도 $1500.00", "$50.00"))
        self.assertTrue(S.amount_present("월 50 USDC 입니다", "$50.00"))

    def test_claims_all_vs_missing(self):
        self.assertTrue(S.score_e1("policies[*].claims.length", "청구 $100.00, $250.00", GT)[0])
        self.assertFalse(S.score_e1("policies[*].claims.length", "청구 $100.00 한 건", GT)[0])

    def test_policy1_claims_field(self):
        gt = dict(GT)
        self.assertTrue(S.score_e1("policies[1].claims", "증권 2 청구 $250.00", gt)[0])
        self.assertFalse(S.score_e1("policies[1].claims", "청구 내역이 없습니다", gt)[0])

    def test_altinvest_positions(self):
        both = "그린인프라 대체투자 펀드, 프라임오피스 리츠 펀드"
        self.assertTrue(S.score_e1("altinvest.positions.length", both, GT)[0])
        self.assertFalse(S.score_e1("altinvest.positions.length", "그린인프라 대체투자 펀드", GT)[0])

    def test_parametric(self):
        self.assertTrue(S.score_e1("parametric.coverages.length", "항공편 지연 보장, 폭염특보 보장", GT)[0])
        self.assertFalse(S.score_e1("parametric.coverages.length", "항공편 지연 보장", GT)[0])

    def test_unscorable_fields(self):
        self.assertIsNone(S.score_e1("policies[0].premiumHistory.length", "x", GT)[0])
        self.assertIsNone(S.score_e1("policies.length", "x", {"policies": []})[0])

    def test_id_fallback_when_amounts_not_unique(self):
        gt = {"policies": [{"policyId": 1, "monthlyPremium": "$50.00"},
                           {"policyId": 2, "monthlyPremium": "$50.00"}]}
        self.assertTrue(S.score_e1("policies.length", "| 1 | 김덴탈 |\n| 2 | 이치과 |", gt)[0])
        self.assertFalse(S.score_e1("policies.length", "| 1 | 김덴탈 | $50.00", gt)[0])


class E2(unittest.TestCase):
    def test_today_bucket(self):
        self.assertTrue(S.score_e2("policies[0].timeUntilMaturity", "만기는 오늘이며 약 2시간 뒤입니다.", GT)[0])

    def test_today_said_tomorrow_is_caught(self):
        self.assertFalse(S.score_e2("policies[0].timeUntilMaturity", "만기는 내일입니다.", GT)[0])

    def test_days_bucket(self):
        gt = {"policies": [{"timeUntilMaturity": "3일 4시간 후"}]}
        self.assertTrue(S.score_e2("policies[0].timeUntilMaturity", "약 3일 남았습니다", gt)[0])
        self.assertFalse(S.score_e2("policies[0].timeUntilMaturity", "내일 만기입니다", gt)[0])
        self.assertFalse(S.score_e2("policies[0].timeUntilMaturity", "5일 남았습니다", gt)[0])

    def test_altinvest_uses_its_own_field(self):
        self.assertTrue(S.score_e2("altinvest.positions[0].timeUntilUnlock", "약 89일 뒤 해제", GT)[0])
        # the old scorer demanded the word '오늘' here (policy maturity) -> false failure
        self.assertFalse(S.score_e2("altinvest.positions[0].timeUntilUnlock", "오늘 해제됩니다", GT)[0])

    def test_next_due_from_timestamps(self):
        # nextDue 15:30, now 14:00 -> 1h30 -> '오늘' bucket
        self.assertTrue(S.score_e2("policies[0].timeUntilNextDue", "오늘 1시간 30분 뒤입니다", GT)[0])
        self.assertFalse(S.score_e2("policies[0].timeUntilNextDue", "내일입니다", GT)[0])

    def test_created_at_unscorable(self):
        self.assertIsNone(S.score_e2("policies[0].createdAt", "x", GT)[0])


class E4(unittest.TestCase):
    def test_correct_kst(self):
        self.assertTrue(S.score_e4("policies[0].maturityDate_kst", "만기는 2026년 11월 15일 오후 4:41 (KST)입니다.", GT)[0])

    def test_24h_format(self):
        self.assertTrue(S.score_e4("policies[0].maturityDate_kst", "2026-11-15 16:41 KST", GT)[0])

    def test_missing_label_but_correct_time_is_accepted(self):
        ok, note = S.score_e4("policies[0].maturityDate_kst", "만기는 11월 15일 오후 4:41입니다.", GT)
        self.assertTrue(ok); self.assertIn("label_ok=False", note)

    def test_relative_day_word_counts_as_the_date(self):
        # pilot case: a correct answer said "오늘 오전 3시 51분 52초" with no calendar date and no KST label
        gt = {"queriedAt": "2026. 11. 15. 오전 12:54:13 (KST)",
              "policies": [{"maturityDate": "2026. 11. 15. 오전 3:51:52 (KST)"}]}
        self.assertTrue(S.score_e4("policies[0].maturityDate_kst", "가장 빠른 만기일은 오늘 오전 3시 51분 52초입니다.", gt)[0])
        self.assertFalse(S.score_e4("policies[0].maturityDate_kst", "가장 빠른 만기일은 내일 오전 3시 51분입니다.", gt)[0])

    def test_pilot_before_response_utc_time_is_still_caught(self):
        gt = {"queriedAt": "2026. 11. 15. 오전 12:54:13 (KST)",
              "policies": [{"maturityDate": "2026. 11. 15. 오전 3:51:52 (KST)"}]}
        utc_answer = "보험 ID 1: 만기일은 2026년 11월 14일 18시 51분 52초, 오늘 18시 51분 52초에 만기됩니다."
        self.assertFalse(S.score_e4("policies[0].maturityDate_kst", utc_answer, gt)[0])

    def test_utc_shift_is_caught(self):
        # 16:41 KST == 07:41 UTC; an answer in UTC but labelled KST must fail
        self.assertFalse(S.score_e4("policies[0].maturityDate_kst", "11월 15일 오전 7:41 (KST)", GT)[0])

    def test_claim_and_altinvest(self):
        self.assertTrue(S.score_e4("policies[0].claims[0].processedAt_kst", "11월 15일 오후 1:45 KST", GT)[0])
        self.assertTrue(S.score_e4("altinvest.positions[0].unlockDate_kst", "2027년 2월 12일 오전 9:15 한국 시간", GT)[0])

    def test_unscorable(self):
        self.assertIsNone(S.score_e4("policies[0].createdAt_kst", "x", GT)[0])
        self.assertIsNone(S.score_e4("policies[0].claims[0].processedAt_kst", "x", {"claims": []})[0])


class Parse(unittest.TestCase):
    def test_parse_kst(self):
        d = S.parse_kst("2026. 11. 14. 오후 10:45:00 (KST)")
        self.assertEqual((d.month, d.day, d.hour, d.minute), (11, 14, 22, 45))
        d = S.parse_kst("2027. 5. 14. 오후 12:00:00 (KST)"); self.assertEqual(d.hour, 12)
        d = S.parse_kst("2027. 5. 14. 오전 12:05:00 (KST)"); self.assertEqual(d.hour, 0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
