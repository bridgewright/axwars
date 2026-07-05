"""Layer 2 adjustments: lease (1116), revaluation (1016), dev cost (1038)."""
from gaap_ifrs.schema import TrialBalance, Account
from gaap_ifrs.adjustments import apply_adjustments


def _tb(*pairs):
    return TrialBalance("K-GAAP", "KRW", "", [Account(n, a) for n, a in pairs])


def _adj(tb, extra, aid):
    return [a for a in apply_adjustments(tb, extra) if a.id == aid][0]


def test_lease_pl_pattern_and_recognition():
    tb = _tb(("임차료", 1000000))
    extra = {"lease_schedule": [{"annual_payment": 1000000, "term_years": 3, "discount_rate": 0.05}]}
    lease = _adj(tb, extra, "lease_1116")
    assert not lease.flagged and lease.standard == "K-IFRS 1116"
    rou = [e for e in lease.entries if e["account"] == "사용권자산"][0]
    assert round(rou["delta"]) == 1815499                       # PV - 1년치 감가상각
    assert round(lease.equity_effect()) == -43912               # 감가상각+이자 > 임차료 (전진배분)
    pl = {e["account"] for e in lease.entries if e.get("statement") == "PL"}
    assert {"감가상각비", "이자비용", "지급임차료"} <= pl


def test_lease_multi_year_accumulates():
    tb = _tb(("임차료", 1000000))
    base = {"lease_schedule": [{"annual_payment": 1000000, "term_years": 3, "discount_rate": 0.05}]}
    y1 = _adj(tb, {**base, "lease_elapsed_years": 1}, "lease_1116")
    y2 = _adj(tb, {**base, "lease_elapsed_years": 2}, "lease_1116")
    rou1 = [e for e in y1.entries if e["account"] == "사용권자산"][0]["delta"]
    rou2 = [e for e in y2.entries if e["account"] == "사용권자산"][0]["delta"]
    assert rou2 < rou1                                          # 경과할수록 사용권자산 감소
    assert y2.equity_effect() < y1.equity_effect()             # 누적 순이익영향 더 음수


def test_lease_uneven_payments():
    tb = _tb(("임차료", 1000000))
    extra = {"lease_schedule": [{"payments": [1000000, 2000000, 3000000], "discount_rate": 0.05}]}
    lease = _adj(tb, extra, "lease_1116")
    assert not lease.flagged
    rou = [e for e in lease.entries if e["account"] == "사용권자산"][0]
    assert rou["delta"] > 0


def test_revaluation_uplift_total():
    tb = _tb(("유형자산", 10000000))
    rev = _adj(tb, {"revaluation": {"uplift": 3000000}}, "ppe_revaluation_1016")
    assert round(rev.equity_effect()) == 3000000
    assert rev.standard == "K-IFRS 1016"


def test_revaluation_per_asset():
    tb = _tb(("유형자산", 10000000))
    extra = {"revaluation": {"assets": [
        {"name": "토지", "carrying_amount": 5000000, "fair_value": 8000000},
        {"name": "건물", "carrying_amount": 3000000, "fair_value": 3500000}]}}
    rev = _adj(tb, extra, "ppe_revaluation_1016")
    assert round(rev.equity_effect()) == 3500000               # (8-5)+(3.5-3) = 3.5M


def test_devcost_flagged_without_input():
    tb = _tb(("개발비", 1200000))
    dev = _adj(tb, None, "development_cost_1038")
    assert dev.flagged and dev.equity_effect() == 0


def test_defined_benefit():
    tb = _tb(("퇴직급여충당부채", 8000000))
    extra = {"defined_benefit": {"pbo": 12000000, "plan_assets": 3000000}}
    db = _adj(tb, extra, "defined_benefit_1019")
    # IFRS 순액 = 12M-3M = 9M vs 종전 8M → 부채 +1M, 자본 -1M
    assert round(db.equity_effect()) == -1000000
    assert db.standard == "K-IFRS 1019"
    liab = [e for e in db.entries if e["account"] == "순확정급여부채"][0]
    assert round(liab["delta"]) == 1000000


def test_financial_instruments_fvpl_and_fvoci():
    tb = _tb(("단기매매증권", 2000000), ("매도가능증권", 3000000))
    extra = {"financial_instruments": {"instruments": [
        {"name": "주식A", "carrying_amount": 2000000, "fair_value": 2300000, "category": "FVPL"},
        {"name": "채권B", "carrying_amount": 3000000, "fair_value": 3200000, "category": "FVOCI"}]}}
    fi = _adj(tb, extra, "financial_instruments_1109")
    # FVPL +300k(이익잉여금) + FVOCI +200k(기타포괄손익누계액) = 자본 +500k
    assert round(fi.equity_effect()) == 500000
    accts = {e["account"] for e in fi.entries}
    assert "당기손익-공정가치측정금융자산" in accts and "기타포괄손익누계액" in accts
