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


# ---- Task 4: wiring + integration + determinism ----
import json
from gaap_ifrs.convert import run_conversion
from gaap_ifrs.difference_report import build_markdown
from gaap_ifrs.report import write_all
from gaap_ifrs.basis_grounding import DEFAULT_CORPUS_DIR

_TB = "../examples/kgaap/input_trial_balance.csv"
_EXTRA = "../examples/kgaap/input_adjustments.json"


def _result():
    extra = json.load(open(_EXTRA, encoding="utf-8"))
    return run_conversion(_TB, "K-GAAP", extra, "KRW", "")


def test_write_all_threads_corpus_into_md(tmp_path):
    paths = write_all(_result(), str(tmp_path), str(DEFAULT_CORPUS_DIR))
    md = open(paths["difference"], encoding="utf-8").read()
    if load_corpus_for_grounding(DEFAULT_CORPUS_DIR) is not None:
        assert "IFRS 근거 (코퍼스 원문)" in md
        assert "상각후원가로 측정한다" in md  # 1109:4.1.2 원문 일부
    else:
        assert "큐레이션 요약 — 코퍼스 원문 미확인" in md


def test_determinism_bytewise():
    corpus = load_corpus_for_grounding(DEFAULT_CORPUS_DIR)
    assert build_markdown(_result(), corpus) == build_markdown(_result(), corpus)
