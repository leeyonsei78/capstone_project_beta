"""
Evaluation harness for:
  "Error Taxonomy and Mitigation Strategies for LLM Agents Querying
   Blockchain-Based Insurance Data"

Usage:
  python harness.py --phase before           # run before-mitigation queries
  python harness.py --phase after            # run after-mitigation queries
  python harness.py --phase before --all-queries  # run all 80 queries (paired design)
  python harness.py --phase both             # run all
  python harness.py --error-type E1_array_truncation  # filter by error type
  python harness.py --query-id E1-01        # run single query
  python harness.py --model gpt-4o-mini     # override model label (default: gpt-4o)
  python harness.py --report                 # generate summary report from results/
  python harness.py --report --model gpt-4o-mini  # report for specific model

Requirements (must be running):
  - insurance_agent web server: http://localhost:5000
  - Hardhat node: http://localhost:8545  (for ground-truth extraction)
  - node blockchain-dental/scripts/query-policy.js <wallet> (auto-called)

Output: results/{model}/{phase}/{query_id}.json
  Multi-model comparison: run twice with different --model labels after
  configuring the chatbot's LLM. Results are stored per model so runs
  do not overwrite each other.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))  # needed under `python -I`
import scorers  # noqa: E402

# Windows console (cp949) cannot encode the check/cross marks used in progress output.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ── Config ───────────────────────────────────────────────────────────────────
CHATBOT_URL   = "http://localhost:5000/api/chat"
STREAM_URL    = "http://localhost:5000/api/chat/stream"
QUERY_JS      = str(Path(__file__).parent.parent.parent /
                    "blockchain-dental" / "scripts" / "query-policy.js")
QUERIES_FILE  = Path(__file__).parent / "queries.json"
RESULTS_DIR   = Path(__file__).parent / "results"
WALLET        = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"  # Hardhat Account #1

SESSION_ID_PREFIX = "eval-harness"
MODEL             = "gpt-4o"   # default; override via --model CLI flag

# ── Scorer: simple string-based correctness ──────────────────────────────────
SCORING_RUBRIC = {
    # (error_type, check_key): lambda llm_text, ground_truth -> (score, note)
}

def score_response(query: dict, llm_text: str, ground_truth: dict,
                   sse_flags: dict) -> dict:
    """
    Returns a scoring dict:
      correct (bool): main answer correctness
      no_news (bool): news section absent (required for blockchain queries)
      no_bad_buttons (bool): no insurance comparison buttons on crypto/blockchain tables
      flags_ok (bool): SSE used_blockchain_tool / used_crypto_tool correct
      score (0-3): sum of above booleans (max 3 for blockchain queries, 2 for baseline)
      notes (str): evaluator notes
    """
    et = query["error_type"]
    text_lower = llm_text.lower()

    correct      = None   # set by error-type-specific logic below
    notes        = ""
    no_news      = "관련 보험 뉴스" not in llm_text and "최신 보험 뉴스" not in llm_text
    flags_ok     = True   # default pass for baseline

    # ── E1 / E2 / E4: scored by field-aware scorers (see scorers.py) ───────────
    if et in ("E1_array_truncation", "E2_temporal_reasoning", "E4_timezone_ambiguity"):
        if not ground_truth or ground_truth.get("ok") is False:
            correct, notes = None, "unscorable: ground truth unavailable"
        else:
            correct, notes = scorers.score_content(
                et, query["ground_truth_field"], llm_text, ground_truth)

    # ── E3: Stale tool reuse ──────────────────────────────────────────────────
    elif et == "E3_stale_tool_reuse":
        # Main check: no news section in blockchain-related follow-up
        correct = True  # Content usually correct; the error is the news section
        if query.get("turn", 1) > 1:
            # In follow-up turns, news section must not appear
            correct = "관련 보험 뉴스" not in llm_text

    # ── E5: Expression variability ────────────────────────────────────────────
    elif et == "E5_expression_variability":
        # SSE flag must be present and correct
        flags_ok = sse_flags.get("used_crypto_tool", False)
        correct = True  # Content itself is typically correct; UI behavior is the error

    # ── E6: Conditional logic failure ─────────────────────────────────────────
    elif et == "E6_conditional_logic_failure":
        # Accept either blockchain or crypto flag — some E6 queries use crypto tool
        flags_ok = (sse_flags.get("used_blockchain_tool", False) or
                    sse_flags.get("used_crypto_tool", False))
        correct = True

    # ── Baseline control ──────────────────────────────────────────────────────
    elif et == "baseline_control":
        correct = True
        no_news = True  # don't penalize baselines for news
        flags_ok = True

    score_max = 3 if et != "baseline_control" else 1
    # correct is None -> unscorable; excluded from accuracy denominators (never "correct").
    score = None if correct is None else sum([
        1 if correct else 0,
        1 if no_news else 0,
        1 if flags_ok else 0,
    ])

    return {
        "correct": correct,
        "no_news": no_news,
        "flags_ok": flags_ok,
        "score": None if score is None else min(score, score_max),
        "score_max": score_max,
        "notes": notes,
    }


# ── Ground truth extraction ───────────────────────────────────────────────────
GT_SCRIPTS = {   # key in merged dict -> script (all take the wallet as argv[1])
    "policy":     "query-policy.js",       # policies, claims, queriedAt (merged at top level)
    "altinvest":  "query-altinvest.js",    # -> gt["altinvest"]["positions"]
    "parametric": "query-parametric.js",   # -> gt["parametric"]["coverages"]
}


def _run_gt_script(script: str, wallet: str) -> dict:
    path = Path(QUERY_JS).parent / script
    try:
        r = subprocess.run(["node", str(path), wallet], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30,
                           cwd=str(path.parent.parent))
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception as e:
        print(f"  [warn] ground truth ({script}) failed: {e}")
    return {}


def get_ground_truth(wallet: str) -> dict:
    """Merged on-chain ground truth. Called before EVERY query so relative-time
    strings reflect the chain clock at question time."""
    gt = _run_gt_script(GT_SCRIPTS["policy"], wallet)
    if not gt.get("ok"):
        return gt
    gt["altinvest"] = _run_gt_script(GT_SCRIPTS["altinvest"], wallet)
    gt["parametric"] = _run_gt_script(GT_SCRIPTS["parametric"], wallet)
    return gt


# ── Chatbot call ──────────────────────────────────────────────────────────────
WALLET_URL = "http://localhost:5000/api/blockchain/wallet"


def register_wallet(session_id: str) -> bool:
    """Register the evaluation wallet for this chatbot session.

    Without this the chatbot answers "no wallet registered" and never calls the
    on-chain query tool, which would make every blockchain query meaningless.
    """
    try:
        r = requests.post(WALLET_URL, json={"session_id": session_id,
                                            "wallet_address": WALLET}, timeout=15)
        return r.ok and not r.json().get("error")
    except Exception as e:
        print(f"  [warn] wallet registration failed: {e}")
        return False


def call_chatbot(user_message: str, session_id: str = None) -> tuple[str, dict]:
    """Returns (llm_text, sse_flags)."""
    payload = {
        "message": user_message,
        "session_id": session_id or f"{SESSION_ID_PREFIX}-default",
        "mode": "live",
    }
    try:
        resp = requests.post(CHATBOT_URL, json=payload, timeout=60)
        data = resp.json()
        text = data.get("response", "")
        sse_flags = {
            "used_blockchain_tool": data.get("used_blockchain_tool", False),
            "used_crypto_tool": data.get("used_crypto_tool", False),
        }
        return text, sse_flags
    except Exception as e:
        return f"ERROR: {e}", {}


def call_chatbot_stream(user_message: str, session_id: str = None) -> tuple[str, dict]:
    """SSE streaming call. Returns (full_text, sse_flags)."""
    payload = {
        "message": user_message,
        "session_id": session_id or f"{SESSION_ID_PREFIX}-default",
        "mode": "live",
    }
    full_text = []
    sse_flags = {}
    done_text = ""
    try:
        with requests.post(STREAM_URL, json=payload, stream=True, timeout=90) as r:
            # Decode bytes as UTF-8 explicitly: the server sends text/event-stream without
            # a charset, and requests would otherwise fall back to ISO-8859-1 (mojibake).
            for raw_line in r.iter_lines():
                line = raw_line.decode("utf-8", errors="replace") if raw_line else ""
                if not line or not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                try:
                    ev = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                # The server streams body text as {"type": "token"} events and finishes
                # with {"type": "done", "full_text": ..., "used_crypto_tool": ...}.
                # ("content" is accepted too for backward compatibility.)
                if ev.get("type") in ("token", "content"):
                    full_text.append(ev.get("text", ""))
                elif ev.get("type") == "done":
                    done_text = ev.get("full_text", "")
                    sse_flags["used_blockchain_tool"] = ev.get("used_blockchain_tool", False)
                    sse_flags["used_crypto_tool"]    = ev.get("used_crypto_tool", False)
    except Exception as e:
        return f"ERROR: {e}", {}
    # Prefer the server's final full_text (it includes any post-processing such as
    # the appended news section); fall back to the concatenated tokens.
    return (done_text or "".join(full_text)), sse_flags


# ── Run one query ─────────────────────────────────────────────────────────────
def run_query(query: dict, ground_truth: dict, phase: str, rep: int = 1) -> dict:
    qid = query["id"]
    turn = query.get("turn", 1)

    print(f"  [{qid}] {query['error_type']} | turn={turn}")

    # Use a per-query session to prevent cross-query history pollution.
    # Multi-turn queries share the same session within themselves (turn 1 + turn 2),
    # but different query IDs are always isolated from each other.
    session_id = f"{SESSION_ID_PREFIX}-{qid}"
    if not register_wallet(session_id):
        print("    [warn] wallet not registered for this session; results may be invalid")

    # For multi-turn queries, run turn 1 silently first (same session)
    if turn == 2:
        prev_q = query.get("user_query_turn1", "블록체인 보험 현황 알려줘.")
        call_chatbot_stream(prev_q, session_id=session_id)
        time.sleep(1)

    start = time.time()
    text, sse_flags = call_chatbot_stream(query["user_query"], session_id=session_id)
    elapsed = time.time() - start

    scoring = score_response(query, text, ground_truth, sse_flags)

    result = {
        "query_id": qid,
        "error_type": query["error_type"],
        "phase": phase,
        "rep": rep,
        "model": MODEL,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "user_query": query["user_query"],
        "llm_response": text,
        "sse_flags": sse_flags,
        "ground_truth_field": query.get("ground_truth_field"),
        "elapsed_sec": round(elapsed, 2),
        "scoring": scoring,
        "ground_truth_snapshot": {k: ground_truth.get(k) for k in
                                  ("queriedAt", "policies", "claims", "altinvest", "parametric")},
        "mitigation": query.get("mitigation"),
        "expected_behavior": query.get("expected_behavior"),
        "failure_mode": query.get("failure_mode"),
    }
    icon = "?" if scoring["correct"] is None else ("✓" if scoring["correct"] else "✗")
    print(f"    {icon} score={scoring['score']}/{scoring['score_max']} "
          f"correct={scoring['correct']} no_news={scoring['no_news']} "
          f"flags={scoring['flags_ok']} [{elapsed:.1f}s] {scoring['notes']}")
    return result


# ── Report generation ─────────────────────────────────────────────────────────
def _rate(items):
    """(correct, scorable, unscorable). Unscorable (correct is None) never counts as
    correct and is excluded from the denominator."""
    scorable = [x for x in items if x["scoring"]["correct"] is not None]
    return sum(1 for x in scorable if x["scoring"]["correct"]), len(scorable), len(items) - len(scorable)


def _fmt(k, n):
    return f"{k}/{n} = {k / n:.0%}" if n else "n/a (no scorable trials)"


def generate_report(model_filter: str = None):
    """
    Print evaluation report. If model_filter is set, restrict to that model's
    results directory; otherwise aggregate all models found under RESULTS_DIR.
    """
    rows = []
    if model_filter:
        search_dirs = [RESULTS_DIR / _model_slug(model_filter)]
    else:
        # Find all model subdirs (directories that contain at least one phase subdir)
        candidates = [d for d in RESULTS_DIR.iterdir() if d.is_dir()] if RESULTS_DIR.exists() else []
        # If no model subdirs exist, fall back to flat layout (backward compat)
        if not candidates:
            search_dirs = [RESULTS_DIR]
        else:
            search_dirs = candidates

    for search_dir in search_dirs:
        for f in sorted(search_dir.glob("**/*.json")):
            try:
                rows.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                continue

    if not rows:
        print("No result files found.")
        return

    # Group by (model, error_type, phase)
    by_model_et_phase: dict = {}
    for r in rows:
        model_key = r.get("model", "unknown")
        key = (model_key, r["error_type"], r["phase"])
        by_model_et_phase.setdefault(key, []).append(r)

    models_found = sorted(set(k[0] for k in by_model_et_phase))

    for model_key in models_found:
        print("\n" + "=" * 72)
        print(f"EVALUATION REPORT  |  model={model_key}")
        print("=" * 72)

        by_et_phase = {(et, ph): v
                       for (m, et, ph), v in by_model_et_phase.items()
                       if m == model_key}

        for (et, phase), items in sorted(by_et_phase.items()):
            k, n, unsc = _rate(items)
            scorable = [x for x in items if x["scoring"]["correct"] is not None]
            no_news = sum(1 for x in scorable if x["scoring"]["no_news"])
            flags = sum(1 for x in scorable if x["scoring"]["flags_ok"])
            print(f"\n{et} [{phase}]  trials={len(items)}  scorable={n}  unscorable={unsc}")
            print(f"  Correct      : {_fmt(k, n)}")
            print(f"  No news      : {_fmt(no_news, n)}")
            print(f"  Flags ok     : {_fmt(flags, n)}")

        print("\n" + "-" * 72)
        print("BEFORE vs AFTER (correctness rate)")
        for et in sorted(set(k[0] for k in by_et_phase)):
            before = by_et_phase.get((et, "before_mitigation"), [])
            after  = by_et_phase.get((et, "after_mitigation"), [])
            if before and after:
                bk, bn, _ = _rate(before)
                ak, an, _ = _rate(after)
                if bn and an:
                    print(f"  {et:<35} {bk/bn:.0%} (n={bn}) -> {ak/an:.0%} (n={an})  d={ak/an - bk/bn:+.0%}")
                else:
                    print(f"  {et:<35} n/a (no scorable trials)")
        print("=" * 72)

    # Cross-model comparison when multiple models present
    if len(models_found) > 1:
        print("\n" + "=" * 72)
        print("CROSS-MODEL COMPARISON (after_mitigation, correctness rate)")
        print("=" * 72)
        et_set = sorted(set(k[1] for k in by_model_et_phase))
        header = f"{'Error type':<35}" + "".join(f"  {m[:12]:>12}" for m in models_found)
        print(header)
        for et in et_set:
            row = f"{et:<35}"
            for m in models_found:
                items = by_model_et_phase.get((m, et, "after_mitigation"), [])
                k, n, _ = _rate(items)
                if n:
                    row += f"  {k / n:>11.0%} "
                else:
                    row += f"  {'N/A':>12}"
            print(row)
        print("=" * 72)


def _model_slug(model: str) -> str:
    """Convert model name to a filesystem-safe slug."""
    return model.replace("/", "-").replace(":", "-").replace(" ", "_")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    global MODEL

    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["before", "after", "both", "all"],
                        default="both")
    parser.add_argument("--error-type", default=None)
    parser.add_argument("--query-id", default=None)
    parser.add_argument("--model", default=MODEL,
                        help="Model label for result grouping (default: gpt-4o). "
                             "Change the chatbot's LLM config before running with "
                             "a different label for multi-model comparison.")
    parser.add_argument("--all-queries", action="store_true",
                        help="Ignore each query's phase tag and run all queries in the "
                             "selected phase, so before/after use the identical query set "
                             "(paired comparison). Results are still labelled by --phase.")
    parser.add_argument("--reps", type=int, default=1,
                        help="Repeat every query N times (LLM output is non-deterministic).")
    parser.add_argument("--rep-start", type=int, default=1,
                        help="First repetition number to run (e.g. --rep-start 2 --reps 3 adds reps 2 and 3 "
                             "to an earlier --reps 1 run without overwriting rep 1).")
    parser.add_argument("--base-url", default="http://localhost:5000",
                        help="Chatbot server to test (http://localhost:5001 for the "
                             "before-mitigation worktree).")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--no-gt", action="store_true",
                        help="Skip ground-truth extraction (blockchain node not running)")
    args = parser.parse_args()

    MODEL = args.model  # propagate to module-level so run_query picks it up
    global CHATBOT_URL, STREAM_URL, WALLET_URL
    base = args.base_url.rstrip("/")
    CHATBOT_URL, STREAM_URL, WALLET_URL = (f"{base}/api/chat", f"{base}/api/chat/stream",
                                           f"{base}/api/blockchain/wallet")

    if args.report:
        generate_report(model_filter=args.model if args.model != "gpt-4o" else None)
        return

    queries_data = json.loads(QUERIES_FILE.read_text(encoding="utf-8"))
    all_queries = queries_data["queries"]

    # Filter
    if args.query_id:
        all_queries = [q for q in all_queries if q["id"] == args.query_id]
    if args.error_type:
        all_queries = [q for q in all_queries if q["error_type"] == args.error_type]
    if args.phase in ("before", "after") and not args.all_queries:
        phase_key = f"{args.phase}_mitigation"
        all_queries = [q for q in all_queries
                       if q.get("phase") in (phase_key, "both", "all")]

    # Ground truth is fetched per query (inside the loop); check availability once here.
    if not args.no_gt:
        print(f"Checking ground truth for wallet {WALLET} ...")
        probe = get_ground_truth(WALLET)
        if not probe.get("ok"):
            print(f"  [warn] Ground truth not available: {probe.get('error', 'unknown')}")
            print("  Run with --no-gt to skip, or start the blockchain node first.")
        else:
            print(f"  policies={len(probe.get('policies', []))} claims={len(probe.get('claims', []))} "
                  f"positions={len((probe.get('altinvest') or {}).get('positions', []))} "
                  f"coverages={len((probe.get('parametric') or {}).get('coverages', []))}")
    else:
        print("[--no-gt] Ground truth extraction skipped.")

    # Store results with the same phase labels that queries.json uses ("before_mitigation",
    # "after_mitigation", "both") so generate_report()'s dict lookups match without
    # needing translation.
    if args.phase in ("before", "after"):
        phase_label = f"{args.phase}_mitigation"
    elif args.phase == "all":
        phase_label = "both"
    else:
        phase_label = args.phase  # "both"

    out_dir = RESULTS_DIR / _model_slug(MODEL) / phase_label
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nRunning {len(all_queries)} queries x {args.reps} rep(s) "
          f"(phase={phase_label}, model={MODEL}, server={base}) ...\n")
    for rep_no in range(args.rep_start, args.reps + 1):
        for q in all_queries:
            gt_q = {} if args.no_gt else get_ground_truth(WALLET)
            result = run_query(q, gt_q, phase_label, rep_no)
            out_file = out_dir / f"{q['id']}__r{rep_no}.json"
            out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                encoding="utf-8")
            time.sleep(2)  # rate-limit courtesy

    print(f"\nResults saved to {out_dir}")
    print("Run with --report to see summary.")


if __name__ == "__main__":
    main()
