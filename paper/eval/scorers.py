"""
Field-aware scorers for the TLPE evaluation (error classes E1-E4 are LLM-origin
and are scored against on-chain ground truth; E5/E6/baseline are flag-only).

Design rules
------------
* Every scorer reads the ground-truth field that the query names in
  ``ground_truth_field`` -- not a hard-coded key.
* A scorer returns ``(correct, notes)``. ``correct is None`` means the query is
  *unscorable* (the tool never exposes that field, or the fixture has no data to
  discriminate). Unscorable items are excluded from accuracy denominators and
  reported separately -- they must never silently count as correct.
* Pure functions, no network: unit-tested in ``test_scorers.py``.

Known limits (state these in the paper)
---------------------------------------
* Matching is string/number based, so an answer that is correct but phrased in an
  unexpected format can be marked wrong; a ~20% human audit estimates this rate.
* E4 correctness is the displayed time value (relative day words accepted); the explicit timezone label is
  only a secondary measure.
* E3 (stale tool reuse) is measured operationally as "no stale news attachment on
  follow-up turns" because a static chain fixture cannot distinguish a fresh answer
  from a reused one.
"""

import datetime
import re

# ── Generic helpers ───────────────────────────────────────────────────────────

_KST_RE = re.compile(
    r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(오전|오후)\s*(\d{1,2}):(\d{2}):(\d{2})"
)


def parse_kst(s):
    """Parse the ko-KR string produced by query-*.js, e.g.
    '2026. 11. 14. 오후 10:45:00 (KST)'. Returns a naive datetime (KST wall clock)
    or None."""
    if not s:
        return None
    m = _KST_RE.search(s)
    if not m:
        return None
    y, mo, d, ap, h, mi, se = m.groups()
    h = int(h) % 12 + (12 if ap == "오후" else 0)
    return datetime.datetime(int(y), int(mo), int(d), h, int(mi), int(se))


def _amount_value(formatted):
    """'$50.00' -> 50.0 ; '₩70,000' -> 70000.0"""
    if formatted is None:
        return None
    digits = re.sub(r"[^\d.]", "", str(formatted))
    try:
        return float(digits)
    except ValueError:
        return None


def amount_present(text, formatted):
    """True if the numeric amount appears in ``text`` as a standalone number
    (so '50' does not match inside '150' or '50.5')."""
    v = _amount_value(formatted)
    if v is None:
        return False
    cands = {f"{v:,.2f}", f"{v:.2f}"}
    if v == int(v):
        cands |= {f"{int(v):,}", f"{int(v)}"}
    for c in sorted(cands, key=len, reverse=True):
        if re.search(r"(?<![\d.,])" + re.escape(c) + r"(?!\d|[.,]\d)", text):
            return True
    return False


def id_present(text, ident):
    """True if an item id is referenced the way a table/list would ('| 3 |',
    '#3', 'ID 3', '3번', '증권 3')."""
    i = re.escape(str(ident))
    pats = [
        r"(?:#|ID\s*[:：]?\s*|증권\s*(?:ID|번호)?\s*#?\s*|청구\s*(?:ID|번호)?\s*#?\s*|번호\s*[:：]?\s*)" + i + r"(?!\d)",
        r"\|\s*" + i + r"\s*\|",
        r"(?<![\d.,$₩])" + i + r"\s*번(?!째)",
    ]
    return any(re.search(p, text) for p in pats)


def _unique(values):
    vals = [v for v in values if v is not None]
    return len(vals) == len(set(vals)) and len(vals) > 0


def _mentioned_count(items, text, amount_key, id_key):
    """How many of ``items`` appear in ``text``. Uses the item's amount when the
    amounts are distinct across items (robust), otherwise falls back to ids."""
    amounts = [i.get(amount_key) for i in items]
    use_amount = _unique(amounts)
    hit = 0
    for it in items:
        ok = amount_present(text, it.get(amount_key)) if use_amount else id_present(text, it.get(id_key))
        hit += 1 if ok else 0
    return hit, ("amount" if use_amount else "id")


# ── E1: array truncation ──────────────────────────────────────────────────────

def score_e1(field, text, gt):
    policies = gt.get("policies", []) or []
    claims = gt.get("claims", []) or []
    positions = (gt.get("altinvest") or {}).get("positions", []) or []
    coverages = (gt.get("parametric") or {}).get("coverages", []) or []

    if "premiumHistory" in field:
        return None, "unscorable: tool does not expose premium history"

    parts = []   # (label, expected, mentioned)

    def policies_part():
        hit, how = _mentioned_count(policies, text, "monthlyPremium", "policyId")
        parts.append((f"policies[{how}]", len(policies), hit))

    def claims_part(cl):
        hit, how = _mentioned_count(cl, text, "amount", "claimId")
        parts.append((f"claims[{how}]", len(cl), hit))

    if field in ("policies.length",):
        policies_part()
    elif field == "policies[*].claims.length":
        claims_part(claims)
    elif field == "policies.length + policies[*].claims.length":
        policies_part(); claims_part(claims)
    elif field == "policies[1].claims":
        if len(policies) < 2:
            return None, "unscorable: fixture has fewer than 2 policies"
        pid = policies[1].get("policyId")
        claims_part([c for c in claims if c.get("policyId") == pid])
    elif field == "full_status":
        policies_part()
        if claims:
            claims_part(claims)
    elif field == "altinvest.positions.length":
        hit = sum(1 for p in positions
                  if re.sub(r"\s+", "", p.get("fundName", "")) in re.sub(r"\s+", "", text))
        parts.append(("positions[name]", len(positions), hit))
    elif field == "parametric.coverages.length":
        names = [c.get("productName") for c in coverages]
        if _unique(names):
            hit = sum(1 for n in names if n and re.sub(r"\s+", "", n) in re.sub(r"\s+", "", text))
            how = "name"
        else:
            hit = sum(1 for c in coverages if id_present(text, c.get("coverageId")))
            how = "id"
        parts.append((f"coverages[{how}]", len(coverages), hit))
    else:
        return None, f"unscorable: no E1 rule for field '{field}'"

    expected = sum(p[1] for p in parts)
    if expected == 0:
        return None, "unscorable: fixture has no items of this kind (cannot discriminate)"
    ok = all(m == e for _, e, m in parts)
    note = "; ".join(f"{lbl} {m}/{e}" for lbl, e, m in parts)
    if sum(1 for p in parts if p[1] == 1) == len(parts) and expected == 1:
        note += " (single item: weak discrimination)"
    return ok, note


# ── E2: temporal reasoning ────────────────────────────────────────────────────

_DONE_WORDS = ("해제", "완료", "도달", "이미", "지났", "만료", "도래", "가능")


def relative_ok(pre, text):
    """Check the answer against a pre-computed relative-time string such as
    '오늘, 2시간 41분 후', '3일 4시간 후' or '잠금 해제됨'."""
    if not pre:
        return None, "unscorable: empty relative string"
    if pre.startswith("오늘"):
        ok = ("오늘" in text) and ("내일" not in text)
        return ok, f"expect today-bucket ('{pre}')"
    m = re.match(r"(\d+)일", pre)
    if m:
        n = int(m.group(1))
        wrong_tomorrow = ("내일" in text) and n != 1
        ok = (f"{n}일" in text or (n == 1 and "내일" in text)) and not wrong_tomorrow
        return ok, f"expect {n}일 ('{pre}')"
    if any(w in pre for w in ("해제", "지급완료", "도달")):
        return any(w in text for w in _DONE_WORDS), f"expect already-done ('{pre}')"
    return None, f"unscorable: unrecognised relative string '{pre}'"


def _relative_from_delta(delta_sec):
    if delta_sec <= 0:
        return "이미 도래"
    d, h, m = int(delta_sec // 86400), int(delta_sec % 86400 // 3600), int(delta_sec % 3600 // 60)
    return (f"{d}일 {h}시간 후" if d > 0 else
            f"오늘, {h}시간 {m}분 후" if h > 0 else f"오늘, {m}분 후")


def score_e2(field, text, gt):
    policies = gt.get("policies", []) or []
    positions = (gt.get("altinvest") or {}).get("positions", []) or []

    if field == "policies[0].timeUntilMaturity":
        if not policies:
            return None, "unscorable: no policies"
        return relative_ok(policies[0].get("timeUntilMaturity"), text)
    if field == "altinvest.positions[0].timeUntilUnlock":
        if not positions:
            return None, "unscorable: no altinvest position"
        return relative_ok(positions[0].get("timeUntilUnlock"), text)
    if field == "policies[0].timeUntilNextDue":
        if not policies:
            return None, "unscorable: no policies"
        nxt, now = parse_kst(policies[0].get("nextDueDate")), parse_kst(gt.get("queriedAt"))
        if not nxt or not now:
            return None, "unscorable: cannot parse nextDue/queriedAt"
        return relative_ok(_relative_from_delta((nxt - now).total_seconds()), text)
    if field == "policies[0].createdAt":
        return None, "unscorable: tool does not expose createdAt"
    return None, f"unscorable: no E2 rule for field '{field}'"


# ── E4: timezone ambiguity ────────────────────────────────────────────────────

def kst_matches(text, dt, ref=None):
    """True if the answer states both the date and the time of ``dt`` (KST wall
    clock). Accepts 12h/24h and several Korean/ISO date spellings. When ``ref`` (the KST
    time the question was asked, from the ground truth) is given, a relative day word
    ('오늘', '내일', '모레') also counts as the date if it is the right day -- a correct
    answer such as '오늘 오전 3시 51분' must not be marked wrong for omitting the calendar date."""
    y, mo, d, h, mi = dt.year, dt.month, dt.day, dt.hour, dt.minute
    h12 = h % 12 or 12
    dates = [f"{mo}월 {d}일", f"{mo}월{d}일", f"{y}. {mo}. {d}", f"{y}.{mo}.{d}",
             f"{y}-{mo:02d}-{d:02d}", f"{y}/{mo}/{d}", f"{y}/{mo:02d}/{d:02d}"]
    times = [f"{h:02d}:{mi:02d}", f"{h}:{mi:02d}", f"{h12}:{mi:02d}",
             f"{h}시 {mi}분", f"{h12}시 {mi}분", f"{h}시{mi}분", f"{h12}시{mi}분"]
    if mi == 0:
        times += [f"{h}시", f"{h12}시"]
    date_ok = any(x in text for x in dates)
    if not date_ok and ref is not None:
        words = {0: ("오늘",), 1: ("내일",), 2: ("모레",)}.get((dt.date() - ref.date()).days, ())
        date_ok = any(w in text for w in words)
    return date_ok and any(x in text for x in times)


_KST_FIELDS = {
    "policies[0].maturityDate_kst":    ("policies", "maturityDate"),
    "policies[0].lastPaymentTime_kst": ("policies", "lastPaymentDate"),
    "policies[0].nextDueTime_kst":     ("policies", "nextDueDate"),
}


def score_e4(field, text, gt):
    label_ok = any(k in text for k in ("KST", "한국 시간", "한국시간", "한국 표준시"))
    dt = None
    if field in _KST_FIELDS:
        coll, key = _KST_FIELDS[field]
        items = gt.get(coll, []) or []
        if not items:
            return None, "unscorable: no policies"
        dt = parse_kst(items[0].get(key))
    elif field == "policies[0].claims[0].processedAt_kst":
        claims = gt.get("claims", []) or []
        if not claims:
            return None, "unscorable: no processed claim in fixture"
        dt = parse_kst(claims[0].get("processedAt"))
    elif field == "altinvest.positions[0].unlockDate_kst":
        pos = (gt.get("altinvest") or {}).get("positions", []) or []
        if not pos:
            return None, "unscorable: no altinvest position"
        dt = parse_kst(pos[0].get("unlockDate"))
    elif field == "policies[0].createdAt_kst":
        return None, "unscorable: tool does not expose createdAt"
    else:
        return None, f"unscorable: no E4 rule for field '{field}'"

    if dt is None:
        return None, "unscorable: ground-truth timestamp missing/unparseable"
    value_ok = kst_matches(text, dt, parse_kst(gt.get("queriedAt")))
    # Correctness = the time shown is the KST time. An explicit "KST"/"한국 시간" label is NOT required:
    # a Korean answer to a Korean question ("오늘 오전 3시 51분") is unambiguous. The label is still
    # recorded (label_ok) as a secondary measure. (The pilot showed that requiring it marked a correct
    # answer wrong.) The error this class targets is a UTC time presented as local time.
    return value_ok, f"value_ok={value_ok} label_ok={label_ok} expect={dt:%Y-%m-%d %H:%M}"


# ── Dispatcher for the four LLM-origin classes ────────────────────────────────

def score_content(error_type, field, text, gt):
    """Returns (correct, notes) for E1/E2/E4; (True, '') for others (flag-only)."""
    if error_type == "E1_array_truncation":
        return score_e1(field, text, gt)
    if error_type == "E2_temporal_reasoning":
        return score_e2(field, text, gt)
    if error_type == "E4_timezone_ambiguity":
        return score_e4(field, text, gt)
    return True, ""
