import json
from gaap_ifrs.parse import load_trial_balance
from gaap_ifrs.mapping import map_accounts
from gaap_ifrs.adjustments import apply_adjustments
from gaap_ifrs.impact import compute_impact


def test_impact_reports_deltas():
    tb = load_trial_balance("tests/fixtures/sample_tb_kgaap.csv", "K-GAAP")
    mapped = map_accounts(tb)
    adjs = apply_adjustments(tb, json.load(open("tests/fixtures/sample_aging.json", encoding="utf-8")))
    imp = compute_impact(mapped, adjs)
    # ECL 환입 55,000 → 자본총계·자산총계 각각 +55,000 (충당금 감소로 순채권 증가)
    assert imp["metrics"]["자본총계"]["delta"] == 55000
    assert imp["metrics"]["자산총계"]["delta"] == 55000
    assert imp["metrics"]["부채총계"]["delta"] == 0
    assert isinstance(imp["narrative"], str) and imp["narrative"]
