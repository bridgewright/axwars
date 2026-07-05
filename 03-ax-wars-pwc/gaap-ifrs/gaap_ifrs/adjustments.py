"""Layer 2: recognition/measurement adjustments.

Rules (with citations + required inputs) live in data/adjustments/*.json.
The numeric computation lives here as deterministic functions that return
balanced double-entry `entries`. If a triggered rule's required inputs are
absent, the adjustment is FLAGGED (no entries, nothing fabricated) — the
anti-hallucination guarantee.

Each computer returns (entries, note) where entries is a list of
{"account", "section", "delta"} postings.
"""
from .schema import Adjustment
from .knowledge import load_adjustment_rules


def _acc(tb, name):
    return sum(a.amount for a in tb.accounts if a.name_src == name)


def _mapped_amount(mapped, ifrs_account):
    """소스 언어와 무관하게, 특정 IFRS 계정으로 매핑된 소스 금액 합계."""
    return sum(ml.source.amount for ml in (mapped or []) if ml.ifrs_account == ifrs_account)


def compute_ecl(tb, extra, mapped=None):
    """대손충당금(발생손실) → ECL(기대신용손실), K-IFRS 1109. IFRS 계정 기준(언어무관)."""
    aging = extra["aging_schedule"]
    target = sum(b["receivable"] * b["loss_rate"] for b in aging)
    if mapped:
        existing = abs(_mapped_amount(mapped, "손실충당금"))   # US/VAS/CAS 등 어떤 명칭이든
    else:
        existing = abs(_acc(tb, "대손충당금"))                  # 매핑 미제공 시 K-GAAP 폴백
    change = existing - target                          # +면 환입(충당금 감소), -면 추가충당
    entries = [
        {"account": "손실충당금", "section": "유동자산", "delta": change},
        {"account": "이익잉여금", "section": "자본", "delta": change},
    ]
    note = f"목표 손실충당금 {target:,.0f} vs 기존 {existing:,.0f} → 조정 {change:,.0f}"
    return entries, note


def _lease_state(payments, r, elapsed):
    """리스 상각 스케줄을 돌려 elapsed년 경과 시점의 (PV, 누적감가상각, 잔여리스부채,
    누적순이익영향, 누적임차료)를 반환. 불균등 지급·다년 경과 지원."""
    n = len(payments)
    pv = sum(payments[t] / ((1 + r) ** (t + 1)) for t in range(n))
    dep = pv / n                                    # 정액 감가상각
    balance = pv
    acc_dep = cum_ni = cum_rent = 0.0
    for y in range(min(elapsed, n)):
        interest = balance * r
        principal = payments[y] - interest
        balance -= principal
        acc_dep += dep
        cum_rent += payments[y]
        cum_ni += payments[y] - dep - interest      # 각 연도 순이익 영향(전진배분이면 음수)
    return pv, acc_dep, balance, cum_ni, cum_rent


def compute_lease(tb, extra, mapped=None):
    """운용리스 → 사용권자산 + 리스부채, K-IFRS 1116.

    lease_schedule 각 항목: {annual_payment, term_years, discount_rate} (정액) 또는
    {payments:[...], discount_rate} (불균등). 옵션 lease_elapsed_years(기본 1)로
    경과연차 시점의 누적 상태를 산출한다. 감가상각(정액)+이자 vs 기존 정액 임차료의
    P&L 패턴차가 누적 순이익영향(자본)으로 반영된다.
    """
    elapsed = int(extra.get("lease_elapsed_years", 1))
    pv = acc_dep = liab = cum_ni = cum_rent = 0.0
    for l in extra["lease_schedule"]:
        r = float(l["discount_rate"])
        if "payments" in l:
            payments = [float(x) for x in l["payments"]]
        else:
            payments = [float(l["annual_payment"])] * int(l["term_years"])
        p, ad, bal, ni, rent = _lease_state(payments, r, elapsed)
        pv += p; acc_dep += ad; liab += bal; cum_ni += ni; cum_rent += rent
    rou_end = pv - acc_dep
    cum_interest = cum_rent - acc_dep - cum_ni       # 항등식으로 유도
    entries = [
        {"account": "사용권자산", "section": "비유동자산", "delta": rou_end},
        {"account": "리스부채", "section": "부채", "delta": liab},
        {"account": "이익잉여금", "section": "자본", "delta": cum_ni},
        # P&L 패턴(정보용, 누적): 감가상각·이자 인식, 기존 임차료 환입
        {"account": "감가상각비", "section": "비용", "statement": "PL", "delta": acc_dep},
        {"account": "이자비용", "section": "비용", "statement": "PL", "delta": cum_interest},
        {"account": "지급임차료", "section": "비용", "statement": "PL", "delta": -cum_rent},
    ]
    note = (f"운용리스→IFRS16: PV {pv:,.0f}, {elapsed}년 경과 기준 사용권자산 {rou_end:,.0f}·"
            f"리스부채 {liab:,.0f}. 누적 감가상각 {acc_dep:,.0f}+이자 {cum_interest:,.0f} "
            f"vs 임차료 {cum_rent:,.0f} → 누적 순이익영향 {cum_ni:,.0f}")
    return entries, note


def compute_revaluation(tb, extra, mapped=None):
    """유형자산 재평가모형, K-IFRS 1016. 공정가치 상승분 → 재평가잉여금(자본).

    revaluation 입력: {uplift: n} (총액) 또는 {assets:[{name, carrying_amount,
    fair_value}, ...]} (자산별 공정가치 - 장부금액).
    """
    rev = extra["revaluation"]
    if "assets" in rev:
        details = []
        uplift = 0.0
        for a in rev["assets"]:
            up = float(a["fair_value"]) - float(a["carrying_amount"])
            uplift += up
            details.append(f"{a.get('name', '자산')} {up:+,.0f}")
        note = f"유형자산 자산별 재평가: {'; '.join(details)} → 재평가잉여금 {uplift:,.0f}"
    else:
        uplift = float(rev["uplift"])
        note = f"유형자산 공정가치 상승 {uplift:,.0f} → 재평가잉여금"
    entries = [
        {"account": "유형자산", "section": "비유동자산", "delta": uplift},
        {"account": "재평가잉여금", "section": "자본", "delta": uplift},
    ]
    return entries, note


def compute_devcost(tb, extra, mapped=None):
    """개발비 자본화 요건 차이, K-IFRS 1038. 요건 미충족분 → 비용화(자본감소)."""
    ineligible = float(extra["dev_capitalization"]["ineligible_amount"])
    entries = [
        {"account": "무형자산", "section": "비유동자산", "delta": -ineligible},
        {"account": "이익잉여금", "section": "자본", "delta": -ineligible},
    ]
    note = f"개발비 자본화 요건 미충족 {ineligible:,.0f} → 비용화"
    return entries, note


def compute_defined_benefit(tb, extra, mapped=None):
    """퇴직급여충당부채(일시퇴직기준) → 순확정급여부채(PBP−사외적립자산), K-IFRS 1019."""
    db = extra["defined_benefit"]
    pbo = float(db["pbo"])
    plan_assets = float(db.get("plan_assets", 0))
    ifrs_net = pbo - plan_assets
    if mapped:
        existing = abs(_mapped_amount(mapped, "순확정급여부채"))
    else:
        existing = abs(_acc(tb, "퇴직급여충당부채"))
    delta_liab = ifrs_net - existing                     # +면 부채 증가
    entries = [
        {"account": "순확정급여부채", "section": "부채", "delta": delta_liab},
        {"account": "이익잉여금", "section": "자본", "delta": -delta_liab},
    ]
    note = (f"IFRS 순확정급여부채 = PBO {pbo:,.0f} − 사외적립자산 {plan_assets:,.0f} = {ifrs_net:,.0f} "
            f"vs 종전 {existing:,.0f} → 부채 {delta_liab:+,.0f}")
    return entries, note


def compute_financial_instruments(tb, extra, mapped=None):
    """금융상품 공정가치 측정, K-IFRS 1109. FVPL→당기손익, FVOCI→기타포괄손익."""
    fvpl = fvoci = 0.0
    for it in extra["financial_instruments"]["instruments"]:
        up = float(it["fair_value"]) - float(it["carrying_amount"])
        if str(it.get("category", "FVPL")).upper() == "FVOCI":
            fvoci += up
        else:
            fvpl += up
    entries = []
    if fvpl:
        entries += [{"account": "당기손익-공정가치측정금융자산", "section": "유동자산", "delta": fvpl},
                    {"account": "이익잉여금", "section": "자본", "delta": fvpl}]
    if fvoci:
        entries += [{"account": "기타포괄손익-공정가치측정금융자산", "section": "비유동자산", "delta": fvoci},
                    {"account": "기타포괄손익누계액", "section": "자본", "delta": fvoci}]
    note = f"공정가치 평가: FVPL {fvpl:+,.0f}(당기손익), FVOCI {fvoci:+,.0f}(기타포괄손익)"
    return entries, note


COMPUTERS = {
    "compute_ecl": compute_ecl,
    "compute_lease": compute_lease,
    "compute_revaluation": compute_revaluation,
    "compute_devcost": compute_devcost,
    "compute_defined_benefit": compute_defined_benefit,
    "compute_financial_instruments": compute_financial_instruments,
}


def _has_trigger(tb, rule):
    names = {a.name_src for a in tb.accounts}
    return any(t in names for t in rule.get("trigger_accounts", []))


def _applies(tb, rule, extra):
    # 트리거 계정이 있거나, 이 조정에 필요한 보조자료가 제공되면 적용 대상.
    return _has_trigger(tb, rule) or any(i in extra for i in rule.get("required_inputs", []))


def apply_adjustments(tb, extra_inputs=None, mapped=None):
    extra = extra_inputs or {}
    out = []
    for rule in load_adjustment_rules():
        if not _applies(tb, rule, extra):
            continue
        basis = rule.get("basis", {})
        missing = [i for i in rule.get("required_inputs", []) if i not in extra]
        if missing:
            out.append(Adjustment(
                id=rule["id"], title=rule["title"], standard=rule["standard"],
                entries=[], confidence="flagged", flagged=True, basis=basis,
                note=f"필요자료 없음: {', '.join(missing)} — 판단/추가자료 필요"))
            continue
        entries, note = COMPUTERS[rule["computer"]](tb, extra, mapped)
        out.append(Adjustment(
            id=rule["id"], title=rule["title"], standard=rule["standard"],
            entries=entries, confidence="high", note=note, basis=basis))
    return out
