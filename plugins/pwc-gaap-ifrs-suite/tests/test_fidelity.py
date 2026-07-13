import pytest
from tools.ingest.extract import Page
from tools.ingest.chunk import chunk_pages
from tools.ingest.fidelity import (roundtrip_coverage, detect_mojibake, assert_coverage, FidelityError,
                                    assert_no_leak, detect_leaks, detect_shadows,
                                    assert_retained_coverage)
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


# --- K-GAAP-specific leak signatures -----------------------------------

def _kgaap_rec(id, standard_no, para, text, tier="본문"):
    return Record(id=id, gaap="K-GAAP", standard_no=standard_no, standard_title="테스트장",
                  paragraph_no=para, heading="", text=text, text_norm=text, lang="ko",
                  tier=tier, source_url="u", as_of="2026-07-06")


def test_assert_no_leak_catches_kgaap_dissenting_opinion_divider_leaked_whole():
    text = "일부 본문 다음에\n\n소수의견\n\n반대의견 내용이 이어진다."
    recs = [_kgaap_rec("kgaap:9999:본문:0", "9999", "0", text)]
    leaks = detect_leaks(recs)
    assert len(leaks) == 1
    assert leaks[0][1] == "kgaap_dissent_divider"


def test_assert_no_leak_catches_kgaap_dropped_section_paragraph_no():
    # Structural check mirroring K-IFRS's own BC/IE paragraph_no gate:
    # 결<N>.<M>/사례<N>/소<N> paragraph_no values should be structurally
    # impossible (split_sections_kgaap already routes that text to the
    # dropped buckets before chunk_pages ever assigns paragraph numbers to
    # it), checked anyway as defense in depth per the task spec.
    for para in ("결9.1", "사례1", "소1"):
        recs = [_kgaap_rec("kgaap:9999:적용지침:x", "9999", para, "새어 들어온 문단이다.",
                           tier="적용지침")]
        leaks = detect_leaks(recs)
        assert len(leaks) == 1, f"expected a leak for paragraph_no={para!r}"
        assert leaks[0][1] == "paragraph_no_kgaap_dropped"


def test_assert_no_leak_does_not_misfire_on_kgaap_clean_records():
    recs = [_kgaap_rec("kgaap:13:본문:13.1", "13", "13.1", "13.1 진짜 본문 문단이다."),
            _kgaap_rec("kgaap:13:적용지침:실13.1", "13", "실13.1", "실13.1 진짜 실무지침 문단이다.",
                      tier="적용지침")]
    assert detect_leaks(recs) == []


# --- CAS-specific leak signatures ------------------------------------------

def _cas_rec(id, standard_no, para, text, tier="본문"):
    return Record(id=id, gaap="CAS", standard_no=standard_no, standard_title="测试准则",
                  paragraph_no=para, heading="", text=text, text_norm=text, lang="zh",
                  tier=tier, source_url="u", as_of="2006-01-01")


def test_assert_no_leak_catches_cas_footer_residue():
    recs = [_cas_rec("cas:99:본문:二", "99", "二", "二 结尾条文。\n地址：北京市西城区月坛南街14号月新大厦2层")]
    leaks = detect_leaks(recs)
    assert len(leaks) == 1
    assert leaks[0][1] == "cas_footer"


def test_assert_no_leak_catches_cas_transmittal_memo_residue():
    text = "财会〔2020〕1号\n为深入贯彻实施企业会计准则，现予印发，请遵照执行。\n财 政 部\n2020年1月1日"
    recs = [_cas_rec("cas:해석99:본문:0", "해석99", "0", text)]
    leaks = detect_leaks(recs)
    assert len(leaks) == 1
    assert leaks[0][1] == "cas_transmittal_memo"


def test_assert_no_leak_catches_cas_xmu_source_url_row_residue():
    recs = [_cas_rec("cas:해석99:본문:0", "해석99", "0",
                     "| 原文网址 | https://www.casc.org.cn/2020/0101/999999.shtml |")]
    leaks = detect_leaks(recs)
    assert len(leaks) == 1
    assert leaks[0][1] == "cas_xmu_source_url_row"


def test_assert_no_leak_does_not_misfire_on_clean_cas_records():
    recs = [_cas_rec("cas:99:본문:一", "99", "一", "第一条 为了规范测试准则的确认、计量，制定本准则。"),
            _cas_rec("cas:99:적용지침:一", "99", "一",
                     "一、测试要点一 本准则第一条规定了测试要点一的处理方法。", tier="적용지침")]
    assert detect_leaks(recs) == []


def test_assert_retained_coverage_routes_cas_through_cas_stripper():
    # Regression guard for the coverage baseline itself: without routing
    # gaap="CAS" through strip_frontmatter_cas/split_sections_cas (rather
    # than silently falling through to the K-IFRS-shaped default path),
    # the casc.org.cn footer/문호 stripped by chunk_pages would still count
    # against the coverage baseline here, since the K-IFRS stripper's own
    # anchors never fire on Chinese text at all.
    from tools.ingest.chunk import chunk_pages
    from tools.ingest.extract import Page
    text = ("财会[2006]3号\n第一条 为了规范测试准则的确认、计量，制定本准则。\n"
            "地址：北京市西城区月坛南街14号月新大厦2层 邮编：100045 联系邮箱：kjzz@casc.org.cn\n")
    recs = chunk_pages([Page(text, 1, "p1")], "CAS", "99", "测试准则", "zh", "u", "2006-01-01")
    cov, info = assert_retained_coverage(text, recs, gaap="CAS")
    assert cov >= 0.995
    assert info["frontmatter_chars"] > 0


# --- VAS-specific leak signatures ------------------------------------------

def _vas_rec(id, standard_no, para, text, tier="본문"):
    return Record(id=id, gaap="VAS", standard_no=standard_no, standard_title="Chuẩn mực thử nghiệm",
                  paragraph_no=para, heading="", text=text, text_norm=text, lang="vi",
                  tier=tier, source_url="u", as_of="2005-01-01")


def test_assert_no_leak_catches_vas_site_chrome_residue():
    recs = [_vas_rec("vas:99:본문:0", "99", "0",
                     "Chuyên trang văn bản pháp luật kế toán kiểm toán\nVAS 99 - Chuẩn mực thử nghiệm")]
    leaks = detect_leaks(recs)
    assert len(leaks) == 1
    assert leaks[0][1] == "vas_site_chrome"


def test_assert_no_leak_catches_vas_decision_preamble_residue():
    text = "BỘ TÀI CHÍNH  CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nQUYẾT ĐỊNH CỦA BỘ TRƯỞNG BỘ TÀI CHÍNH"
    recs = [_vas_rec("vas:99:본문:0", "99", "0", text)]
    leaks = detect_leaks(recs)
    assert len(leaks) == 1
    assert leaks[0][1] == "vas_decision_preamble"


def test_assert_no_leak_catches_vas_form_template_residue():
    text = "PHỤ\nLỤC 1\nBÁO\nCÁO LƯU CHUYỂN TIỀN TỆ (MẪU 1)\n| Chỉ tiêu | Mã số |"
    recs = [_vas_rec("vas:24:적용사례:0", "24", "0", text)]
    leaks = detect_leaks(recs)
    assert len(leaks) == 1
    assert leaks[0][1] == "vas_form_template"


def test_assert_no_leak_does_not_misfire_on_clean_vas_records():
    recs = [_vas_rec("vas:01:본문:01", "01", "01",
                     "01. Mục đích của chuẩn mực này là quy định và hướng dẫn."),
            _vas_rec("vas:11:적용지침:A1", "11", "A1",
                     "A1. Như đã quy định trong đoạn 21, đây là hướng dẫn bổ sung.", tier="적용지침")]
    assert detect_leaks(recs) == []


def test_assert_retained_coverage_routes_vas_through_vas_stripper():
    # Regression guard for the coverage baseline itself: without routing
    # gaap="VAS" through strip_frontmatter_vas/split_sections_vas (rather
    # than silently falling through to the K-IFRS-shaped default path -- an
    # IFRS-Foundation-copyright-block anchor that never fires on a
    # KrestonVN-sourced Vietnamese page at all), the site-chrome header and
    # Decision citation stripped by chunk_pages would still count against
    # the coverage baseline here.
    text = ("Chuyên trang văn bản pháp luật kế toán kiểm toán\nVAS 99 - Chuẩn mực thử nghiệm\n"
            "CHUẨN MỰC KẾ TOÁN VIỆT NAM SỐ 99\n(Ban hành và công bố theo Quyết định số "
            "999/2005/QĐ-BTC ngày 01 tháng 01 năm 2005 của Bộ trưởng Bộ Tài chính)\n"
            "QUY ĐỊNH CHUNG\n01. Mục đích của chuẩn mực này.\n")
    recs = chunk_pages([Page(text, 1, "p1")], "VAS", "99", "Chuẩn mực thử nghiệm", "vi", "u", "2005-01-01")
    cov, info = assert_retained_coverage(text, recs, gaap="VAS")
    assert cov >= 0.995
    assert info["frontmatter_chars"] > 0
