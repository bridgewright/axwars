import pytest
from tools.ingest.extract import Page
from tools.ingest.chunk import chunk_pages
from tools.ingest.fidelity import (roundtrip_coverage, detect_mojibake, assert_coverage, FidelityError,
                                    assert_no_leak, detect_leaks, detect_shadows)
from gaap_standards_mcp.schema import Record

def test_roundtrip_full_coverage():
    text = "22 사용권자산을 인식한다.\n23 리스부채를 측정한다."
    recs = chunk_pages([Page(text,1,"p")], "K-IFRS","1116","리스","ko","u","2025-01-01")
    assert roundtrip_coverage(text, recs) >= 0.995
    assert_coverage(text, recs)  # no raise

def test_mojibake_and_low_coverage():
    assert detect_mojibake("리스�부채") is True
    with pytest.raises(FidelityError):
        assert_coverage("가"*1000, [])


def _rec(id, standard_no, para, text, tier="본문"):
    return Record(id=id, gaap="K-IFRS", standard_no=standard_no, standard_title="테스트",
                  paragraph_no=para, heading="", text=text, text_norm=text, lang="ko",
                  tier=tier, source_url="u", as_of="2025-01-01")


# --- assert_no_leak / detect_leaks -----------------------------------------

def test_assert_no_leak_passes_clean_records():
    recs = [_rec("kifrs:9999:본문:1", "9999", "1", "1 진짜 본문 문단이다."),
            _rec("kifrs:9999:본문:2", "9999", "2", "2 또 다른 진짜 문단이다.")]
    assert assert_no_leak(recs) == []  # no raise


def test_assert_no_leak_raises_on_westferry_residue():
    recs = [_rec("kifrs:9999:본문:1", "9999", "1",
                  "1 Westferry Circus 주소가 섞여 들어간 문단이다.")]
    with pytest.raises(FidelityError):
        assert_no_leak(recs)


def test_assert_no_leak_raises_on_board_resolution_residue():
    recs = [_rec("kifrs:9999:본문:1", "9999", "1",
                  "기업회계기준서 제9999호의 제정에 대한 회계기준위원회의 의결(2020년)")]
    with pytest.raises(FidelityError):
        assert_no_leak(recs)


def test_assert_no_leak_catches_bc_divider_line_leaked_whole():
    text = "일부 본문 다음에\n\n결론도출근거\n\nBC 내용이 이어진다."
    recs = [_rec("kifrs:9999:본문:0", "9999", "0", text)]
    leaks = detect_leaks(recs)
    assert len(leaks) == 1
    assert leaks[0][1] == "bc_divider"


def test_assert_no_leak_catches_bc_ie_prefixed_paragraph_no():
    # Structural check: paragraph_no itself is BC/IE-prefixed. Chunk.py's own
    # paragraph regexes should make this impossible in practice (defense in
    # depth per the task spec), but the gate must still catch it if it ever
    # happens.
    recs = [_rec("kifrs:9999:적용지침:BC12", "9999", "BC12", "새어 들어온 결론도출근거 문단이다.",
                  tier="적용지침")]
    leaks = detect_leaks(recs)
    assert len(leaks) == 1
    assert leaks[0][1] == "paragraph_no_bc_ie"


def test_assert_no_leak_does_not_misfire_on_legitimate_inline_citations():
    # "결론도출근거"/"적용사례" as ordinary inline citations inside real,
    # correctly-retained body text -- confirmed against the real downloaded
    # 개념체계/1032/1036/번역서-중요성판단 PDFs (see fidelity.py's module
    # comment) -- must NOT be flagged. Only a standalone BC/IE divider LINE
    # (never how a real citation is phrased) counts as a leak.
    recs = [_rec("kifrs:9999:본문:28", "9999", "28", "28 IAS 1의 결론도출근거 문단 BC30F를 참조."),
            _rec("kifrs:1033:적용지침:A10", "1033", "A10",
                 "A10 문단 63의 적용사례를 보여주기 위해서 다음과 같이 가정한다.", tier="적용지침")]
    assert detect_leaks(recs) == []


def test_assert_no_leak_does_not_misfire_on_bare_copyright_word_in_real_body():
    # "저작권" (copyright) legitimately appears as a real intangible-asset
    # example inside 1038's real body -- confirmed empirically -- so it must
    # never be a bare-keyword leak signature on its own.
    recs = [_rec("kifrs:1038:본문:6", "1038", "6",
                  "6 특허권, 저작권과 같은 항목에 대한 라이선스 계약이다.")]
    assert detect_leaks(recs) == []


# --- detect_shadows ---------------------------------------------------------

def test_detect_shadows_removes_toc_preview_fragment_keeps_real_paragraph():
    # Mirrors the real 기업회계기준해석서 제2010호 TOC-preview fragment
    # "한1.1\n1~2" sharing its canonical key with the real, much longer
    # 한1.1 paragraph.
    shadow = _rec("kifrs:2010:본문:한1.1", "2010", "한1.1", "한1.1\n1~2")
    real = _rec("kifrs:2010:본문:한1.1#2", "2010", "한1.1",
                "한1.1\n" + "이 해석서는 실제로 이런저런 긴 내용을 담고 있는 진짜 문단이다. " * 3)
    clean, n = detect_shadows([shadow, real])
    assert n == 1
    assert clean == [real]


def test_detect_shadows_leaves_comparable_length_duplicates_alone():
    # Two substantial, comparably-sized fragments sharing a paragraph number
    # (e.g. a genuine jumbled-numeric-table byproduct, as in 1019's real
    # 본문) must NOT be pruned -- there is no reliable content-only way to
    # tell which of two substantial fragments is "the real one".
    a = _rec("kifrs:1019:본문:131", "1019", "131", "131\n" + "실제 표 값 내용 한 조각이다. " * 5)
    b = _rec("kifrs:1019:본문:131#2", "1019", "131", "131\n" + "또 다른 표 값 내용 조각이다. " * 5)
    clean, n = detect_shadows([a, b])
    assert n == 0
    assert clean == [a, b]


def test_detect_shadows_ignores_different_tiers():
    # Same paragraph_no, different tier -- never a shadow pair (a 본문
    # paragraph "1" and an 적용지침 paragraph "1" are unrelated).
    a = _rec("kifrs:9999:본문:1", "9999", "1", "1 " + "실제 본문 내용이다. " * 20, tier="본문")
    b = _rec("kifrs:9999:적용지침:1", "9999", "1", "1", tier="적용지침")
    clean, n = detect_shadows([a, b])
    assert n == 0
    assert clean == [a, b]
