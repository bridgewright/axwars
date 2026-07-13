from gaap_ifrs.parse import load_trial_balance
from gaap_ifrs.mapping import map_accounts
from gaap_ifrs.schema import TrialBalance, Account


def test_mapping_and_citation():
    tb = load_trial_balance("tests/fixtures/sample_tb_kgaap.csv", "K-GAAP")
    lines = map_accounts(tb)
    by = {l.source.name_src: l for l in lines}
    assert by["매출채권"].ifrs_account == "매출채권및기타유동채권"
    assert by["매출채권"].standard.startswith("K-IFRS 1109")
    assert by["매출"].statement == "PL"


def test_unmapped_flagged():
    tb = TrialBalance("K-GAAP", "KRW", "", [Account("이상한계정", 100)])
    line = map_accounts(tb)[0]
    assert line.flagged and "매핑규칙 없음" in line.flag_reason
