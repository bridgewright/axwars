import json
from gaap_ifrs.parse import load_trial_balance
from gaap_ifrs.adjustments import apply_adjustments


def test_ecl_computed():
    tb = load_trial_balance("tests/fixtures/sample_tb_kgaap.csv", "K-GAAP")
    extra = json.load(open("tests/fixtures/sample_aging.json", encoding="utf-8"))
    adjs = apply_adjustments(tb, extra)
    ecl = [a for a in adjs if a.id == "ecl_allowance"][0]
    # 목표충당금 = 2.5M*1% + 0.4M*10% + 0.1M*30% = 95,000
    # 기존 150,000 → 55,000 환입 → 자본 +55,000
    assert round(ecl.equity_effect()) == 55000
    assert ecl.standard == "K-IFRS 1109"
    assert not ecl.flagged


def test_flag_when_missing_input():
    tb = load_trial_balance("tests/fixtures/sample_tb_kgaap.csv", "K-GAAP")
    adjs = apply_adjustments(tb, extra_inputs=None)         # aging 없음
    ecl = [a for a in adjs if a.id == "ecl_allowance"][0]
    assert ecl.flagged and ecl.confidence == "flagged"
    assert ecl.equity_effect() == 0
