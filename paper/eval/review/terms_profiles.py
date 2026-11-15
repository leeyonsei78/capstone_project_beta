"""
Insurer clause profiles for the clause-conditioned review experiment, and the deterministic rule engine that
decides the correct payout from (profile, event facts).

Why: the same dental claim gets a different correct answer under different insurers' terms. A rule engine has to be
re-coded per insurer; an LLM only has to read the clause. Ground truth here comes from the clause parameters, not from
a planted anomaly, so it is not circular in the way the planted-anomaly cases are.

Profiles are simplified from real public product summaries (paper/data/terms_raw/, text in terms_txt/); see
paper/data/terms_clause_matrix.md for the comparison and line references. They are NOT the full terms:
  A  "standard"  : Samsung Fire (dental partner / direct), DB, KB, Hanwha family
                   waiting 90d (disease); reduction 50% crown <365d, implant/bridge <730d; accident exempt;
                   crown capped 3 per year; implant/bridge no count cap (the unlimited variant: Hanwha also sells a
                   3-per-year variant).
  B  "Lina Non-life" 要約書 (New보철치료보장, 신크라운치료보장):
                   waiting 180d for implant/bridge, 90d for crown; reduction 50% crown <270d, implant/bridge <730d;
                   implant/bridge 3 per year while <730d, no limit afterwards.
  C  "Dongyang Life / NH" style (우리WON하는치아보험 summary, NH80튼튼치아보험 exclusions):
                   waiting 90d; reduction 50% crown <730d; implant/bridge: reduction depends on the EXTRACTION date
                   being <730d after the contract (not the treatment date); implant/bridge 3 per year; excluded:
                   wisdom/impacted tooth, orthodontic/position extraction, extraction only to prepare other work,
                   and extraction before the coverage start date.
Known simplifications: only crown / implant / bridge; dentures, scaling, bone grafts, re-implant rules and
renewal contracts are not modelled; exclusion lists are only encoded for C because only its summary was read in
detail; A and B may have exclusions in the full terms that are not modelled here. Day counts are "days since the
contract date, which is day 0"; scenarios stay at least 5 days away from any threshold so the "N days passed,
starting the next day" wording does not matter.
"""
from dataclasses import dataclass, field

COVERAGES = ("crown", "implant", "bridge")
PROSTHETIC = ("implant", "bridge")
KINDS = ("normal", "wisdom", "impacted", "ortho", "prep")
THRESHOLDS = (90, 180, 270, 365, 730)      # scenario day values stay >= MARGIN days away from these
MARGIN = 5


@dataclass(frozen=True)
class Profile:
    key: str
    label: str
    waiting: dict                       # coverage -> days (disease); accident has no waiting period
    reduction: dict                     # coverage -> (window_days, ratio) applied to disease
    reduction_basis: dict               # coverage -> "event" | "extraction"
    cap: dict                           # coverage -> list of (until_day or None, limit or None)
    excluded_kinds: frozenset = field(default_factory=frozenset)
    pre_start_extraction_excluded: bool = False


PROFILES = {
    "A": Profile(
        "A", "표준형",
        waiting={"crown": 90, "implant": 90, "bridge": 90},
        reduction={"crown": (365, .5), "implant": (730, .5), "bridge": (730, .5)},
        reduction_basis={"crown": "event", "implant": "event", "bridge": "event"},
        cap={"implant": [(None, None)], "bridge": [(None, None)]}),
    "B": Profile(
        "B", "장기 보철 면책형",
        waiting={"crown": 90, "implant": 180, "bridge": 180},
        reduction={"crown": (270, .5), "implant": (730, .5), "bridge": (730, .5)},
        reduction_basis={"crown": "event", "implant": "event", "bridge": "event"},
        cap={"implant": [(730, 3), (None, None)], "bridge": [(730, 3), (None, None)]}),
    "C": Profile(
        "C", "발치 기준·제외사유 엄격형",
        waiting={"crown": 90, "implant": 90, "bridge": 90},
        reduction={"crown": (730, .5), "implant": (730, .5), "bridge": (730, .5)},
        reduction_basis={"crown": "event", "implant": "extraction", "bridge": "extraction"},
        cap={"implant": [(None, 3)], "bridge": [(None, 3)]},
        excluded_kinds=frozenset({"wisdom", "impacted", "ortho", "prep"}),
        pre_start_extraction_excluded=True),
}

DECISION_OF_RATIO = {1.0: "지급", 0.5: "감액지급", 0.0: "부지급"}


def cap_for(profile, coverage, event_day):
    for until, limit in profile.cap.get(coverage, []):
        if until is None or event_day < until:
            return limit
    return None


def decide(profile, s):
    """s: coverage, cause ('disease'|'accident'), event_day, extraction_day (prosthetics) , extraction_kind,
    count_this_year. Returns (ratio in {1.0, .5, 0.0}, reason_code)."""
    cov, cause, ev = s["coverage"], s["cause"], s["event_day"]
    prosthetic = cov in PROSTHETIC
    if prosthetic and s["extraction_kind"] in profile.excluded_kinds:
        return 0.0, "excluded_kind"
    start = 0 if cause == "accident" else profile.waiting[cov]
    if ev < start:
        return 0.0, "waiting"
    if prosthetic and profile.pre_start_extraction_excluded and s["extraction_day"] < start:
        return 0.0, "pre_start"
    if prosthetic:
        cap = cap_for(profile, cov, ev)
        if cap is not None and s["count_this_year"] >= cap:
            return 0.0, "annual_cap"
    if cause == "disease":
        window, ratio = profile.reduction[cov]
        basis = s["extraction_day"] if (prosthetic and profile.reduction_basis[cov] == "extraction") else ev
        if basis < window:
            return ratio, "reduced"
    return 1.0, "none"


def near_threshold(day):
    return any(abs(day - t) < MARGIN for t in THRESHOLDS)


# ── Natural-language rendering of a profile (the clause excerpt given to the model in condition T1) ──────────

def render_clause(profile):
    p = profile
    lines = [f"[약관 요약 - 상품 {p.key}] 경과일수는 계약일을 0일로 센 값입니다. 아래 조건만 적용해 판정하세요."]
    w = p.waiting
    if len({w["crown"], w["implant"], w["bridge"]}) == 1:
        lines.append(f"1. 면책: 질병은 계약일로부터 {w['crown']}일이 지나야 보장합니다(그 전에 치료받으면 부지급). 상해는 계약일부터 보장합니다.")
    else:
        lines.append(f"1. 면책: 질병은 크라운 {w['crown']}일, 임플란트·브릿지 {w['implant']}일이 지나야 보장합니다"
                     "(그 전에 치료받으면 부지급). 상해는 계약일부터 보장합니다.")
    cw, ci = p.reduction["crown"][0], p.reduction["implant"][0]
    if p.reduction_basis["implant"] == "extraction":
        lines.append(f"2. 감액: 질병으로 인한 크라운은 치료일이 계약 후 {cw}일 미만이면 50%만 지급합니다. "
                     f"임플란트·브릿지는 치료일이 아니라 '발치일'이 계약 후 {ci}일 미만이면 50%만 지급합니다. 상해는 감액하지 않습니다.")
    else:
        lines.append(f"2. 감액: 질병으로 인한 크라운은 치료일이 계약 후 {cw}일 미만, 임플란트·브릿지는 {ci}일 미만이면 50%만 지급합니다. "
                     "상해는 감액하지 않습니다.")
    cap = p.cap["implant"]
    if cap == [(None, None)]:
        lines.append("3. 개수 한도: 임플란트·브릿지는 연간 개수 한도가 없습니다.")
    elif len(cap) == 2:
        lines.append(f"3. 개수 한도: 임플란트·브릿지는 계약 후 {cap[0][0]}일 미만에는 계약연도당 {cap[0][1]}개까지만 지급하고(이미 지급된 건수가 "
                     f"{cap[0][1]}개 이상이면 부지급), {cap[0][0]}일 이후에는 제한이 없습니다.")
    else:
        lines.append(f"3. 개수 한도: 임플란트·브릿지는 계약연도당 {cap[0][1]}개까지만 지급합니다(이미 지급된 건수가 {cap[0][1]}개 이상이면 부지급).")
    if p.excluded_kinds:
        lines.append("4. 지급 제외(임플란트·브릿지): 사랑니 발치, 매복치 발치, 교정·위치이상 목적 발치, 다른 치료를 위한 준비 목적 발치. "
                     "또한 보장개시일(면책 종료일) 이전에 영구치를 발치한 경우 부지급합니다.")
    else:
        lines.append("4. 이 문제에서는 위 조건 외의 별도 제외 사유를 적용하지 않습니다.")
    lines.append("판정 우선순위: 제외 사유 → 면책 → 보장개시일 이전 발치 → 개수 한도 → 감액.")
    return "\n".join(lines)
