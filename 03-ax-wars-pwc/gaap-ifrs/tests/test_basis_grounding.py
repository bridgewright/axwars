from types import SimpleNamespace

from gaap_ifrs.basis_grounding import (
    parse_ifrs_ref, ground_ref, load_corpus_for_grounding,
)


# ---- Task 1: parser ----
def test_parse_single():
    assert parse_ifrs_ref("K-IFRS 제1109호 문단 4.1.2") == ("K-IFRS", "1109", ["4.1.2"])


def test_parse_comma():
    assert parse_ifrs_ref("K-IFRS 제1002호 문단 9, 25") == ("K-IFRS", "1002", ["9", "25"])


def test_parse_range():
    assert parse_ifrs_ref("K-IFRS 제1109호 문단 4.1.1-4.1.4") == \
        ("K-IFRS", "1109", ["4.1.1", "4.1.2", "4.1.3", "4.1.4"])


def test_parse_range_plus_single():
    g, s, p = parse_ifrs_ref("K-IFRS 제1109호 문단 4.1.1-4.1.4, 5.2.1")
    assert (g, s) == ("K-IFRS", "1109")
    assert p[-1] == "5.2.1" and "4.1.3" in p


def test_parse_unparseable():
    assert parse_ifrs_ref("") == (None, None, [])
    assert parse_ifrs_ref("그냥 텍스트") == (None, None, [])


# ---- Task 2: resolver ----
def _rec(std, pn, text):
    return SimpleNamespace(gaap="K-IFRS", standard_no=std, paragraph_no=pn, text=text)


def test_ground_ref_found():
    recs = [_rec("1109", "4.1.2", "4.1.2 상각후원가로 측정한다.")]
    found, missing = ground_ref("K-IFRS 제1109호 문단 4.1.2", recs)
    assert len(found) == 1 and "상각후원가" in found[0]["text"]
    assert found[0]["label"] == "K-IFRS 제1109호 문단 4.1.2" and missing == []


def test_ground_ref_partial_missing():
    recs = [_rec("1002", "9", "9 취득원가와 순실현가능가치 중 낮은 금액.")]
    found, missing = ground_ref("K-IFRS 제1002호 문단 9, 25", recs)
    assert len(found) == 1 and missing == ["25"]


def test_ground_ref_no_corpus():
    assert ground_ref("K-IFRS 제1109호 문단 4.1.2", None) == ([], [])


def test_load_corpus_missing_dir_returns_none():
    assert load_corpus_for_grounding("/nonexistent/path/xyz-does-not-exist") is None


# ---- Task 3: renderer ----
from gaap_ifrs.difference_report import _basis_block


def test_basis_block_grounded():
    recs = [SimpleNamespace(gaap="K-IFRS", standard_no="1109", paragraph_no="4.1.2",
                            text="4.1.2 상각후원가로 측정한다.")]
    basis = {"ifrs_ref": "K-IFRS 제1109호 문단 4.1.2", "ifrs_requires": "요약문"}
    out = "\n".join(_basis_block(basis, corpus=recs))
    assert "코퍼스 원문" in out and "상각후원가로 측정한다." in out
    assert "요약문" not in out


def test_basis_block_fallback_when_no_corpus():
    basis = {"ifrs_ref": "K-IFRS 제1109호 문단 4.1.2", "ifrs_requires": "요약문"}
    out = "\n".join(_basis_block(basis, corpus=None))
    assert "큐레이션 요약 — 코퍼스 원문 미확인" in out and "요약문" in out
