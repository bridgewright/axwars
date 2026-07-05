from gaap_ifrs.knowledge import load_mappings, find_mapping, load_adjustment_rules


def test_load_and_find():
    m = load_mappings()
    assert len(m) >= 10
    hit = find_mapping("외상매출금", m)                 # alias 매칭
    assert hit["ifrs_account"] == "매출채권및기타유동채권"
    assert find_mapping("존재하지않는계정", m) is None


def test_adjustment_rules_loaded():
    rules = load_adjustment_rules()
    ids = {r["id"] for r in rules}
    assert "ecl_allowance" in ids
