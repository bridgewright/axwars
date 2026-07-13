from gaap_ifrs.schema import Account, TrialBalance


def test_trial_balance_total():
    tb = TrialBalance("K-GAAP", "KRW", "2025-12-31",
                      [Account("현금", 5000), Account("매출채권", 3000)])
    assert sum(a.amount for a in tb.accounts) == 8000
    assert tb.source_gaap == "K-GAAP"
