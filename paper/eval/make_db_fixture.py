"""
Dump the seeded on-chain state into a mutable "conventional database" snapshot, and
optionally a tampered copy, for the backend-comparison experiment.

  python paper/eval/make_db_fixture.py            # -> fixture_db.json
  python paper/eval/make_db_fixture.py --tamper   # also -> fixture_db_tampered.json (+ manifest)

Run it right after start_eval_chain.ps1 (needs the Hardhat node + seeded state).

Why a snapshot: the DB arm must present the *same* data through the *same* tool layer so
that the data source is the only variable. The snapshot is taken once, so both arms see
identical values for the whole evaluation (the chain clock is frozen without new blocks,
see CLAUDE.md step 14).

Tamper design (illustrative case study, not a security benchmark): four edits an insider
or attacker with write access to a conventional database could make. On the chain the same
edits are impossible without the owner key (non-owner writes revert).
"""
import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
BC = HERE.parent.parent / "blockchain-dental"
WALLET = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"   # same as harness.py


def run_script(name: str) -> dict:
    r = subprocess.run(["node", str(BC / "scripts" / name), WALLET], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=60, cwd=str(BC))
    if r.returncode != 0 or not r.stdout.strip():
        raise SystemExit(f"{name} failed (is the chain up and seeded?): {r.stderr[:300]}")
    data = json.loads(r.stdout.strip().splitlines()[-1])
    if not data.get("ok"):
        raise SystemExit(f"{name} returned ok=false: {data.get('error')}")
    return data


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tamper", action="store_true")
    args = ap.parse_args()

    fixture = {
        "policy": run_script("query-policy.js"),
        "altinvest": run_script("query-altinvest.js"),
        "parametric": run_script("query-parametric.js"),
    }
    (HERE / "fixture_db.json").write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8")
    p = fixture["policy"]
    print(f"fixture_db.json: policies={len(p['policies'])} claims={len(p['claims'])} "
          f"positions={len(fixture['altinvest'].get('positions', []))} "
          f"coverages={len(fixture['parametric'].get('coverages', []))}")
    if not p["policies"] or not p["claims"]:
        raise SystemExit("seed looks incomplete (need >=1 policy and >=1 claim) -- run seed-eval.js first")

    if not args.tamper:
        return

    t = copy.deepcopy(fixture)
    pol0, claim0 = t["policy"]["policies"][0], t["policy"]["claims"][0]
    manifest = []

    def edit(container, key, new, field, question):
        manifest.append({"field": field, "original": container[key], "tampered": new, "question": question})
        container[key] = new

    edit(pol0, "totalPaid", "$9999.00", "policies[0].totalPaid", "내 첫 번째 증권으로 지금까지 낸 보험료 총액이 얼마야?")
    edit(claim0, "amount", "$9500.00", "claims[0].amount", "내 첫 번째 청구 금액이 얼마였어?")
    edit(pol0, "timeUntilMaturity", "지급완료", "policies[0].timeUntilMaturity", "내 첫 번째 증권 만기까지 얼마나 남았어?")
    edit(pol0, "totalClaimed", "$0.00", "policies[0].totalClaimed", "내 첫 번째 증권으로 지금까지 받은 보험금 총액이 얼마야?")
    pol0["maturityPaid"] = True   # consistent with the edited countdown string

    (HERE / "fixture_db_tampered.json").write_text(json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")
    (HERE / "fixture_db_tamper_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"fixture_db_tampered.json + manifest: {len(manifest)} edits")
    for m in manifest:
        print(f"  {m['field']}: {m['original']} -> {m['tampered']}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
