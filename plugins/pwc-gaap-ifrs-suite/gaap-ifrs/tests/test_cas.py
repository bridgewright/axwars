"""Task A: China CAS(ASBE) -> K-IFRS coverage (source-GAAP pluggable)."""
from gaap_ifrs.schema import TrialBalance, Account
from gaap_ifrs.mapping import map_accounts
from gaap_ifrs.knowledge import load_mappings, find_mapping


def test_cas_mapping_chinese_and_english():
    tb = TrialBalance("CAS", "CNY", "2025-12-31", [
        Account("货币资金", 5000000),
        Account("Accounts receivable", 3000000),      # English alias
        Account("营业收入", 20000000),
        Account("固定资产", 10000000),
    ])
    by = {l.source.name_src: l for l in map_accounts(tb)}
    assert by["货币资金"].ifrs_account == "현금및현금성자산"
    assert by["Accounts receivable"].ifrs_account == "매출채권및기타유동채권"
    assert by["营业收入"].statement == "PL"
    assert by["固定资产"].ifrs_account == "유형자산"


def test_cas_registered_separately():
    cas = load_mappings("CAS")
    assert find_mapping("实收资本", cas)["ifrs_account"] == "자본금"
    assert find_mapping("实收资本", load_mappings("K-GAAP")) is None
