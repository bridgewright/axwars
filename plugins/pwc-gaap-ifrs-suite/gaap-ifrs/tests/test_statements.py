import json
from gaap_ifrs.parse import load_trial_balance
from gaap_ifrs.mapping import map_accounts
from gaap_ifrs.adjustments import apply_adjustments
from gaap_ifrs.statements import build_statements


def test_build_and_apply_adjustment():
    tb = load_trial_balance("tests/fixtures/sample_tb_kgaap.csv", "K-GAAP")
    mapped = map_accounts(tb)
    adjs = apply_adjustments(tb, json.load(open("tests/fixtures/sample_aging.json", encoding="utf-8")))
    bs, pl = build_statements(mapped, adjs)
    # 매출 → 수익(매출) 20,000,000
    assert pl["수익"]["수익(매출)"] == 20000000
    # ECL 환입 55,000 → 이익잉여금 = 13,250,000 + 55,000
    assert bs["자본"]["이익잉여금"] == 13305000
