"""Tests for the HTML review sheet builder and the multi-rater importer."""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import import_rater_results as IR
import make_review_html as MH

HERE = Path(__file__).parent
REAL = HERE / "cases"


def stage():
    """Copy the generated case files into a temp dir so tests never touch the real ones."""
    tmp = tempfile.TemporaryDirectory()
    d = Path(tmp.name)
    for n in ("cases_claims.json", "cases_apps.json", "blind_key.json", "review_claims_blind.csv", "review_apps_blind.csv"):
        shutil.copy(REAL / n, d / n)
    return tmp, d


def export(rater, ds, labels, authored=None, when="2026-11-16T00:00:00Z"):
    return {"format": "review_rater_v1", "dataset_id": ds, "exported_at": when, "rater": {"id": rater, "years": 5, "field": "둘 다"},
            "labels": {b: {"label": l, "memo": m, "realism": 4, "seconds": s, "first_seconds": s, "changes": 0}
                       for b, (l, m, s) in labels.items()}, "authored": authored or []}


class HtmlBuilder(unittest.TestCase):
    def setUp(self):
        self.tmp, self.d = stage()
        self.html, self.ds = MH.build(self.d)

    def tearDown(self):
        self.tmp.cleanup()

    def test_contains_all_cases_and_no_answers(self):
        key = json.loads((self.d / "blind_key.json").read_text(encoding="utf-8"))
        for bid in key:
            self.assertIn(f'"{bid}"', self.html)
        claims = json.loads((self.d / "cases_claims.json").read_text(encoding="utf-8"))
        apps = json.loads((self.d / "cases_apps.json").read_text(encoding="utf-8"))
        for c in claims + apps:
            self.assertNotIn(c["case_id"], self.html)            # original ids encode the anomaly kind
        for banned in ("심어둔", "1차라벨", "anomaly", "blind_key", "evidence_rich"):
            self.assertNotIn(banned, self.html)
        # the planted label must not appear next to any case: only the two UI option words exist
        self.assertEqual(len(re.findall(r'"label"\s*:\s*"(?:approve|investigate)"', self.html)), 0)

    def test_rater_entry_columns_are_not_shown_as_case_fields(self):
        data = json.loads(re.search(r"const DATA = (.*?);\n", self.html, re.S).group(1).replace("<\\/", "</"))
        for t in ("claims", "apps"):
            self.assertFalse(any("전문가" in c or "소요시간" in c or "현실성" in c for c in data[t]["cols"]))
            self.assertEqual(len(data[t]["rows"][0]["cells"]), len(data[t]["cols"]))

    def test_script_has_valid_syntax(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        js = re.search(r"<script>(.*)</script>", self.html, re.S).group(1)
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "x.js"
            p.write_text(js, encoding="utf-8")
            r = subprocess.run([node, "--check", str(p)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_dataset_id_changes_with_sheet(self):
        p = self.d / "review_apps_blind.csv"
        raw = p.read_bytes()
        p.write_bytes(raw.replace(b",", b",.", 1))          # change one cell, keep the row structure
        self.assertNotEqual(MH.build(self.d)[1], self.ds)


class Stats(unittest.TestCase):
    def test_cohen_kappa_hand_values(self):
        a = {1: "approve", 2: "approve", 3: "investigate", 4: "investigate"}
        b = {1: "approve", 2: "investigate", 3: "investigate", 4: "investigate"}
        k, n = IR.cohen_kappa(a, b)         # po=.75, pe=.5*.25+.5*.75=.5 -> k=.5
        self.assertEqual(n, 4)
        self.assertAlmostEqual(k, 0.5)
        self.assertEqual(IR.cohen_kappa(a, a)[0], 1.0)
        self.assertIsNone(IR.cohen_kappa({}, {})[0])

    def test_fleiss_kappa_hand_values(self):
        from collections import Counter
        perfect = [Counter({"approve": 3}), Counter({"investigate": 3})]
        self.assertAlmostEqual(IR.fleiss_kappa(perfect), 1.0)
        # same four items as the Cohen example. Fleiss pools both raters' label frequencies for chance agreement,
        # so it is NOT equal to Cohen's 0.5: Pbar=(1+0+1+1)/4=.75, p_approve=3/8, Pe=(3/8)^2+(5/8)^2=.53125,
        # kappa=(.75-.53125)/(1-.53125)=7/15
        two = [Counter({"approve": 2}), Counter({"approve": 1, "investigate": 1}), Counter({"investigate": 2}), Counter({"investigate": 2})]
        self.assertAlmostEqual(IR.fleiss_kappa(two), 7 / 15)

    def test_consensus_and_ties(self):
        self.assertEqual(IR.consensus({"a": "approve", "b": "approve", "c": "investigate"}), "approve")
        self.assertIsNone(IR.consensus({"a": "approve", "b": "investigate"}))
        self.assertEqual(IR.consensus({"a": "investigate"}), "investigate")


class Importer(unittest.TestCase):
    def setUp(self):
        self.tmp, self.d = stage()
        self.ds = IR.dataset_id(self.d)
        self.src = self.d / "rater_results"
        self.src.mkdir()
        self.key = json.loads((self.d / "blind_key.json").read_text(encoding="utf-8"))
        self.ids = [b for b in self.key if b.startswith("R")][:4]

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, obj):
        (self.src / name).write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

    def test_two_raters_consensus_tie_kappa_and_times(self):
        i = self.ids
        self.write("a.json", export("R01", self.ds, {i[0]: ("approve", "ok", 30), i[1]: ("approve", "", 50),
                                                      i[2]: ("investigate", "why", 70), i[3]: ("investigate", "", 90)},
                                    authored=[{"n": 1, "type": "app", "facts": "x", "label": "investigate"}]))
        self.write("b.json", export("R02", self.ds, {i[0]: ("approve", "", 10), i[1]: ("investigate", "", 20),
                                                      i[2]: ("investigate", "", 30), i[3]: ("investigate", "", 40)}))
        text, info = IR.run(self.src, self.d, self.d / "res")
        self.assertEqual(info["labelled"], 4)
        self.assertAlmostEqual(info["pair_kappa"][("R01", "R02")][0], 0.5)
        self.assertAlmostEqual(info["fleiss"], 7 / 15)
        cid_tie = self.key[i[1]]
        self.assertEqual(info["ties"], [cid_tie])
        claims = {c["case_id"]: c for c in json.loads((self.d / "cases_claims.json").read_text(encoding="utf-8"))}
        self.assertEqual(claims[self.key[i[0]]]["expert_label"], "approve")
        self.assertNotIn("expert_label", {k for k, v in claims[cid_tie].items() if v is not None and k == "expert_label" and v})
        self.assertEqual(claims[cid_tie]["expert_labels"], {"R01": "approve", "R02": "investigate"})
        self.assertEqual(claims[self.key[i[0]]]["expert_time_sec"], 20)      # median(30, 10)
        self.assertIn("[R01] ok", claims[self.key[i[0]]]["expert_note"])
        authored = json.loads((self.d / "expert_authored.json").read_text(encoding="utf-8"))
        self.assertEqual(authored[0]["authored_id"], "X-R01-001")
        self.assertTrue((self.d / "res" / "rater_agreement.md").exists())

    def test_latest_export_per_rater_wins(self):
        i = self.ids
        self.write("old.json", export("R01", self.ds, {i[0]: ("approve", "", 5)}, when="2026-11-16T00:00:00Z"))
        self.write("new.json", export("R01", self.ds, {i[0]: ("investigate", "", 5)}, when="2026-11-17T00:00:00Z"))
        _, info = IR.run(self.src, self.d, self.d / "res")
        claims = {c["case_id"]: c for c in json.loads((self.d / "cases_claims.json").read_text(encoding="utf-8"))}
        self.assertEqual(claims[self.key[i[0]]]["expert_label"], "investigate")

    def test_wrong_dataset_version_is_refused(self):
        self.write("x.json", export("R01", "deadbeef0000", {self.ids[0]: ("approve", "", 5)}))
        with self.assertRaises(SystemExit):
            IR.run(self.src, self.d, self.d / "res")

    def test_single_rater_has_no_kappa_but_sets_labels(self):
        self.write("a.json", export("R01", self.ds, {self.ids[0]: ("approve", "", 5)}))
        text, info = IR.run(self.src, self.d, self.d / "res")
        self.assertIsNone(info["fleiss"])
        self.assertIn("계산할 수 없습니다", text)


if __name__ == "__main__":
    unittest.main()
