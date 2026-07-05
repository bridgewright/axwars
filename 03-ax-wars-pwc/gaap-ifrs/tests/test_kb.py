"""Task 4: expanded K-GAAP mapping coverage."""
from gaap_ifrs.knowledge import load_mappings, find_mapping


def test_expanded_kgaap_coverage():
    m = load_mappings("K-GAAP")
    assert len(m) >= 40
    # 실제 K-GAAP -> K-IFRS 재분류 사례들
    assert find_mapping("단기매매증권", m)["ifrs_account"] == "당기손익-공정가치측정금융자산"
    assert find_mapping("선수금", m)["ifrs_account"] == "계약부채"
    assert find_mapping("퇴직급여충당부채", m)["ifrs_account"] == "순확정급여부채"
    assert find_mapping("주식발행초과금", m)["ifrs_account"] == "자본잉여금"   # alias


def test_source_gaap_registry():
    kg = load_mappings("K-GAAP")
    vas = load_mappings("VAS")
    assert kg != vas
    assert find_mapping("Cash and cash equivalents", vas)["ifrs_account"] == "현금및현금성자산"
    assert find_mapping("Cash and cash equivalents", kg) is None    # VAS 계정은 K-GAAP에 없음
