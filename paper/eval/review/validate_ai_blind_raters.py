"""Validate AI review artifacts against frozen blind inputs and raw responses.

Does not load generated answers, blind keys, or human-label case files.
"""
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone

from run_ai_blind_raters import OUT, SYSTEM, inputs, transport_request, validate_labels, write_json


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate():
    dataset, rows, hashes = inputs()
    ids = {row["id"] for row in rows}
    manifest = read(OUT / "audit" / "manifest.json")
    assert hashlib.sha256((OUT / "audit" / "codex_decisions.tsv").read_bytes()).hexdigest() == manifest["codex_decisions_sha256"]
    report = {"validated_at": datetime.now(timezone.utc).isoformat(),
              "dataset_id": dataset, "inputs_sha256": hashes,
              "human_expert_validation": False, "raters": {}}
    exports = {}
    for rater in ("codex", "qwen", "deepseek"):
        obj = read(OUT / f"rater_{rater}.json")
        assert obj["dataset_id"] == dataset
        assert obj["provenance"]["inputs_sha256"] == hashes
        assert obj["provenance"]["complete"] is True
        assert obj["provenance"]["human_expert"] is False
        assert obj["provenance"]["ground_truth_validated"] is False
        assert obj["rater"]["kind"] == "ai_proxy" and obj["rater"]["years"] is None
        assert not (obj["labels"].keys() & obj["complex_labels"].keys())
        labels = {**obj["labels"], **obj["complex_labels"]}
        validate_labels([{"id": k, **v} for k, v in labels.items()], ids)
        assert len(obj["labels"]) == 240 and len(obj["complex_labels"]) == 74
        assert all(v["seconds"] is None and v["first_seconds"] is None for v in labels.values())
        assert len(obj["authored"]) == 2
        assert {v["type"] for v in obj["authored"]} == {"claim", "app"}
        for case in obj["authored"]:
            assert case["provenance"] == "fictional" and case["seconds"] is None
            assert case["label"] in ("approve", "investigate")
            assert type(case["difficulty"]) is int and 1 <= case["difficulty"] <= 5
            assert type(case["realism"]) is int and 1 <= case["realism"] <= 5
        assumptions = obj["assumptions_review"]
        required_assumptions = ("review_cost_15", "loss_fraction_1", "prevalence_003",
                                "required_company_data", "sensitivity_plan")
        assert all(isinstance(assumptions[k], str) and assumptions[k].strip() for k in required_assumptions)
        small_share_key = "small_share_085" if "small_share_085" in assumptions else "small_share_0085"
        assert rater == "deepseek" or small_share_key == "small_share_085"
        assert isinstance(assumptions[small_share_key], str) and assumptions[small_share_key].strip()
        stats = {"labels": len(labels), "counts": dict(Counter(v["label"] for v in labels.values())),
                 "fictional_cases": len(obj["authored"])}
        backup_path = OUT / "audit" / "resume_20261120" / f"rater_{rater}.json"
        if backup_path.exists():
            backup = read(backup_path)
            old_labels = {**backup["labels"], **backup["complex_labels"]}
            pilot_ids = set()
            for pilot in (OUT / "audit" / rater / "pilot").glob("batch_*.json"):
                pilot_ids.update(row["id"] for row in json.loads(read(pilot)["request"]["messages"][-1]["content"]))
            preserved = old_labels.keys() - pilot_ids
            assert all(labels[k] == old_labels[k] for k in preserved)
            stats["previous_final_labels_preserved"] = len(preserved)
            stats["pilot_labels_replaced"] = len(old_labels.keys() & pilot_ids)
        if rater != "codex":
            seen = set()
            batches = sorted((OUT / "audit" / rater).glob("batch_*.json"))
            assert len(batches) == 32
            for path in batches:
                raw = read(path)
                request, response = raw["request"], raw["response"]
                assert raw["inputs_sha256"] == hashes
                assert request["model"] == obj["rater"]["model"]
                assert request["messages"][0] == {"role": "system", "content": SYSTEM}
                assert request["options"] == {"temperature": 0, "seed": 20261119,
                                              "num_ctx": 4096, "num_predict": 1600}
                assert request["think"] is False
                assert response["done"] is True and response.get("done_reason") == "stop"
                if rater == "deepseek":
                    endpoint, actual = transport_request(request)
                    assert response["transport"] == {"endpoint": endpoint, "request": actual}
                    assert "keyed by each supplied case ID" in actual["prompt"]
                    assert response["response"] == response["message"]["content"]
                    assert not response.get("thinking")
                batch_rows = json.loads(request["messages"][1]["content"])
                rowmap = {row["id"]: row for row in rows}
                assert all(row == rowmap[row["id"]] for row in batch_rows)
                answers = json.loads(response["message"]["content"])["labels"]
                if isinstance(answers, dict):
                    parsed = [{"id": key, **value} for key, value in answers.items()]
                elif answers and isinstance(answers[0], list):
                    assert all(isinstance(v, list) and len(v) == 4 for v in answers)
                    parsed = [dict(zip(("id", "label", "realism", "memo"), v)) for v in answers]
                else:
                    parsed = answers
                validate_labels(parsed, {row["id"] for row in batch_rows})
                for answer in parsed:
                    key = answer["id"]
                    assert key not in seen
                    seen.add(key)
                    assert all(labels[key][field] == answer[field] for field in ("label", "realism", "memo"))
                    assert labels[key]["model_batch"] == f"audit/{rater}/{path.name}"
            assert seen == ids
            stats["raw_batches_verified"] = len(batches)
            stats["final_prompt_consistent"] = True
        with (OUT / f"rater_{rater}.csv").open(encoding="utf-8-sig", newline="") as f:
            csv_rows = list(csv.DictReader(f))
        assert len(csv_rows) == len(ids) and {v["blind_id"] for v in csv_rows} == ids
        for row in csv_rows:
            value = labels[row["blind_id"]]
            assert row["ai_label"] == value["label"] and row["ai_memo"] == value["memo"]
            assert int(row["ai_realism_1_5"]) == value["realism"] and row["human_seconds"] == ""
        assert (OUT / f"rater_{rater}.md").is_file()
        exports[rater] = labels
        report["raters"][rater] = stats
    disagreements = {k for k in ids if len({v[k]["label"] for v in exports.values()}) > 1}
    with (OUT / "comparison.csv").open(encoding="utf-8-sig", newline="") as f:
        comparison = list(csv.DictReader(f))
    assert len(comparison) == len(ids) and {r["blind_id"] for r in comparison} == ids
    for row in comparison:
        key = row["blind_id"]
        assert all(row[rater] == labels[key]["label"] for rater, labels in exports.items())
        assert row["unanimous"] == str(key not in disagreements)
        assert row["ai_majority_not_ground_truth"] == Counter(row[r] for r in exports).most_common(1)[0][0]
    with (OUT / "disagreements.csv").open(encoding="utf-8-sig", newline="") as f:
        dispute_rows = list(csv.DictReader(f))
    assert len(dispute_rows) == len(disagreements) and {r["blind_id"] for r in dispute_rows} == disagreements
    report.update(total_labels=sum(len(v) for v in exports.values()),
                  unanimous=len(ids) - len(disagreements), disagreements=len(disagreements),
                  status="passed", scope="Completeness, schema and provenance only; not correctness or external validity.")
    write_json(OUT / "audit" / "validation_report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    validate()
