"""Task B: US GAAP -> K-IFRS coverage (source-GAAP pluggable)."""
from gaap_ifrs.schema import TrialBalance, Account
from gaap_ifrs.mapping import map_accounts
from gaap_ifrs.knowledge import load_mappings, find_mapping


def test_usgaap_mapping():
    tb = TrialBalance("US-GAAP", "USD", "2025-12-31", [
        Account("Cash and cash equivalents", 5000000),
        Account("Inventory", 2000000),
        Account("Property, plant and equipment", 10000000),
        Account("Net sales", 20000000),                 # alias of Revenue
    ])
    by = {l.source.name_src: l for l in map_accounts(tb)}
    assert by["Cash and cash equivalents"].ifrs_account == "현금및현금성자산"
    assert by["Net sales"].ifrs_account == "수익(매출)"
    assert by["Inventory"].ifrs_account == "재고자산"


def test_usgaap_difference_notes_and_registry():
    for key in ("US-GAAP", "USGAAP", "US GAAP"):
        m = load_mappings(key)
        assert find_mapping("Retained earnings", m)["ifrs_account"] == "이익잉여금"
    m = load_mappings("US-GAAP")
    assert "LIFO" in find_mapping("Inventory", m)["note"]        # US GAAP↔IFRS 차이 인용
