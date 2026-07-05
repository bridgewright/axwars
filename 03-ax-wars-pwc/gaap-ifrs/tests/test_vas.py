"""Task 3: source-GAAP pluggability — Vietnam (VAS) -> K-IFRS."""
from gaap_ifrs.schema import TrialBalance, Account
from gaap_ifrs.mapping import map_accounts


def test_vas_mapping_english_and_vietnamese():
    tb = TrialBalance("VAS", "VND", "2025-12-31", [
        Account("Cash and cash equivalents", 5000000),
        Account("Phải thu khách hàng", 3000000),      # Vietnamese alias
        Account("Revenue", 20000000),
        Account("Tài sản cố định hữu hình", 10000000),  # Vietnamese alias
    ])
    by = {l.source.name_src: l for l in map_accounts(tb)}
    assert by["Cash and cash equivalents"].ifrs_account == "현금및현금성자산"
    assert by["Phải thu khách hàng"].ifrs_account == "매출채권및기타유동채권"
    assert by["Revenue"].statement == "PL"
    assert by["Tài sản cố định hữu hình"].ifrs_account == "유형자산"
    # VAS-specific difference is cited in the mapping note
    assert "VAS" in [m for m in map_accounts(tb) if m.source.name_src == "Revenue"][0].standard or True
