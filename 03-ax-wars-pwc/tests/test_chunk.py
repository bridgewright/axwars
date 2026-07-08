from tools.ingest.extract import Page
from tools.ingest.chunk import (chunk_pages, ChunkingError, KGAAP_BODY_PARA_RE,
                                 CAS_ARTICLE_RE, CAS_GUIDANCE_PARA_RE)

def test_chunk_splits_on_paragraph_numbers():
    text = "22 리스이용자는 사용권자산을 인식한다.\n23 리스부채는 현재가치로 측정한다."
    recs = chunk_pages([Page(text, 1, "p1")], "K-IFRS", "1116", "리스", "ko",
                       "https://x", "2025-01-01")
    assert [r.paragraph_no for r in recs] == ["22", "23"]
    assert recs[0].text.startswith("22") and "사용권자산" in recs[0].text
    # id now carries the tier so a 본문 and an 적용지침 chunk sharing the same
    # paragraph number (e.g. both "0" for unclaimed lead text) can never
    # collide -- see the corpus-depth split in tools/ingest/segment.py.
    assert recs[0].id == "kifrs:1116:본문:22"


# Mirrors the real structure confirmed against kifrs_1002/1019/1116: cover +
# copyright + TOC (with colliding bare paragraph numbers) + 본문 + a lettered
# appendix + a board-resolution voting log + 적용사례(IE) + 결론도출근거(BC).
_FULL_DOC = """- 1 -
기업회계기준서 제9999호
테스트기준

저작권
7 Westferry Circus, Canary Wharf, London E14 4HD, United Kingdom.
Copyright (c) 2025 IFRS Foundation... resides in the Republic of Korea.

COPYRIGHT NOTICE
7 Westferry Circus, Canary Wharf, London E14 4HD, United Kingdom.
Reproduction is permitted... resides in the Republic of Korea.
All rights reserved... resides in the Republic of Korea.

- 4 -
본 문

- 5 -
목  차
1
2
기업회계기준서 제9999호는 문단 1부터 2까지와 부록 B로 구성되어 있다. 모든 문단의 권위는 같다.

- 9 -
기업회계기준서 제9999호
테스트기준
목적
1
첫째 문단 내용이다.
2
둘째 문단 내용이다.

부록 B. 적용지침
이 부록은 이 기준서의 일부를 구성한다.
B1
적용지침 첫 문단이다.
B2
적용지침 둘째 문단이다.

기업회계기준서 제9999호의 제정에 대한 회계기준위원회의 의결(2020년)
회계기준위원회 위원: 홍길동(위원장), 김철수

적용사례
실무적용지침

기업회계기준서 제9999호의 적용사례
이 적용사례는 기업회계기준서 제9999호에 첨부되지만, 이 기준서의 일부를 구성하지는 않는다.
IE1
예시 문단 하나이다.

결론도출근거
IFRS 9999의 결론도출근거 (BC1-BC1)
BC1
결론도출근거 문단이다.
"""


def _chunk_full_doc():
    return chunk_pages([Page(_FULL_DOC, 1, "p1")], "K-IFRS", "9999", "테스트기준", "ko",
                       "https://x", "2025-01-01")


def test_chunk_pages_drops_bc_and_ie_keeps_appendix_as_guidance_tier():
    recs = _chunk_full_doc()
    texts = [r.text for r in recs]
    assert not any("결론도출근거 문단이다" in t for t in texts)
    assert not any("예시 문단 하나이다" in t for t in texts)
    assert not any("Westferry" in t for t in texts)
    assert not any("회계기준위원회의 의결" in t for t in texts)

    by_id = {r.id: r for r in recs}
    body1 = by_id["kifrs:9999:본문:1"]
    assert body1.tier == "본문"
    assert "첫째 문단 내용이다" in body1.text

    guidance_b1 = by_id["kifrs:9999:적용지침:B1"]
    assert guidance_b1.tier == "적용지침"
    assert "적용지침 첫 문단이다" in guidance_b1.text

    ids = [r.id for r in recs]
    assert len(set(ids)) == len(ids)


def test_chunk_pages_no_oversized_chunk_and_no_extract_flag_for_normal_doc():
    recs = _chunk_full_doc()
    assert all(not r.extract_flag for r in recs)
    assert max(len(r.text) for r in recs) < 500


def test_chunk_pages_flags_oversized_chunk():
    # one paragraph's body is a wild outlier relative to its 본문 siblings
    huge = "내용 " * 3000
    text = f"1\n첫 문단이다.\n\n2\n{huge}\n\n3\n셋째 문단이다.\n"
    recs = chunk_pages([Page(text, 1, "p1")], "K-IFRS", "9998", "테스트", "ko", "u", "2025-01-01")
    by_para = {r.paragraph_no: r for r in recs}
    assert by_para["2"].extract_flag is True
    assert by_para["1"].extract_flag is False
    assert by_para["3"].extract_flag is False


def test_chunk_pages_tolerates_hwp_missing_space_after_number():
    # hwp5txt sometimes drops the space right after a leading paragraph
    # number ("1첫째 문단이다" instead of "1 첫째 문단이다."); paragraphs are
    # blank-line delimited in HWP's extraction, matching the block-start
    # normalization in tools/ingest/chunk.normalize_missing_space.
    text = "1첫째 문단이다.\n\n한2.1둘째 문단(한국 전용)이다.\n\n2셋째 문단이다.\n"
    recs = chunk_pages([Page(text, 1, "p1")], "K-IFRS", "9997", "테스트", "ko", "u", "2025-01-01")
    assert [r.paragraph_no for r in recs] == ["1", "한2.1", "2"]
    assert recs[0].text == "1 첫째 문단이다."
    assert recs[1].text == "한2.1 둘째 문단(한국 전용)이다."
    assert recs[2].text == "2 셋째 문단이다."


def test_chunk_pages_handles_double_trailing_letter_appendix_paragraphs():
    # Real 1116 amendment history stacks a second letter onto a lettered
    # appendix paragraph across successive amendments: C20BA, C20BB, C20BC.
    text = ("목적\n1\n첫 문단이다.\n\n"
            "부록 C. 시행일과 경과 규정\n이 부록은 이 기준서의 일부를 구성한다.\n"
            "C20BA\n첫 개정 문단이다.\n\nC20BB\n둘째 개정 문단이다.\n")
    recs = chunk_pages([Page(text, 1, "p1")], "K-IFRS", "9996", "테스트", "ko", "u", "2025-01-01")
    # "0" is the unclaimed appendix-intro lead text ("이 부록은...구성한다.")
    # ahead of the first lettered match -- same convention as any unnumbered
    # lead text (see the real Appendix A defined-terms glossary, which has no
    # numbering at all and is entirely a "0" chunk).
    guidance_paras = [r.paragraph_no for r in recs if r.tier == "적용지침"]
    assert guidance_paras == ["0", "C20BA", "C20BB"]


def test_chunk_pages_suffixes_repeated_paragraph_numbers_within_one_tier():
    # A jumbled table/diagram can make PDF extraction repeat a bare number
    # (confirmed in the real 1019 PDF's numeric worked example); ids must
    # still come out globally unique via an occurrence suffix rather than
    # colliding or raising.
    text = "1\n첫 문단이다.\n\n2\n표 값 조각\n\n2\n또 다른 표 값 조각\n\n3\n셋째 문단이다.\n"
    recs = chunk_pages([Page(text, 1, "p1")], "K-IFRS", "9995", "테스트", "ko", "u", "2025-01-01")
    ids = [r.id for r in recs]
    assert len(set(ids)) == len(ids)
    assert ids.count("kifrs:9995:본문:2") == 1
    assert "kifrs:9995:본문:2#2" in ids


def test_chunking_error_is_importable():
    # the hard-gate exception type is part of chunk.py's public surface
    assert issubclass(ChunkingError, Exception)


# ---------------------------------------------------------------------------
# K-GAAP (일반기업회계기준) chunking -- routed through its own frontmatter/
# section/paragraph-regex path (see segment.py's K-GAAP module comment and
# chunk_pages' own docstring), NOT K-IFRS's. Mirrors the real structure
# confirmed against the downloaded kgaap_1/13/19/26 PDFs: tiny "의결 YYYY"
# title block, "<장번호>.<문단번호>" 본문 paragraphs, a self-referential
# "부록" opening a container of up to four sub-headings (결론도출근거 kept
# out, 실무지침 kept as 적용지침 tier, 적용사례 kept out).
# ---------------------------------------------------------------------------

_KGAAP_FULL_DOC = """일반기업회계기준
제9994장 테스트장
한국회계기준원 회계기준위원회
의결 2020. 1. 1.

- 2 -
제9994장 테스트장
목적
9994.1
첫째 문단 내용이다.
9994.2
둘째 문단 내용이다.

일반기업회계기준 제9994장 '테스트장'의
부록
결론도출근거
결9994.1
결론도출근거 문단이다.

실무지침
실9994.1
실무지침 첫 문단이다.

적용사례
사례1
적용사례 문단이다.
"""


def _chunk_kgaap_full_doc():
    return chunk_pages([Page(_KGAAP_FULL_DOC, 1, "p1")], "K-GAAP", "9994", "테스트장", "ko",
                       "https://x", "2026-07-06")


def test_chunk_pages_kgaap_drops_bc_and_ie_keeps_silmujichim_as_guidance_tier():
    recs = _chunk_kgaap_full_doc()
    texts = [r.text for r in recs]
    assert not any("결론도출근거 문단이다" in t for t in texts)
    assert not any("적용사례 문단이다" in t for t in texts)
    assert not any("한국회계기준원" in t for t in texts)

    by_id = {r.id: r for r in recs}
    body1 = by_id["kgaap:9994:본문:9994.1"]
    assert body1.tier == "본문"
    assert "첫째 문단 내용이다" in body1.text

    guidance = by_id["kgaap:9994:적용지침:실9994.1"]
    assert guidance.tier == "적용지침"
    assert "실무지침 첫 문단이다" in guidance.text

    ids = [r.id for r in recs]
    assert len(set(ids)) == len(ids)


def test_chunk_pages_kgaap_splits_chapter_dot_paragraph_numbering():
    recs = _chunk_kgaap_full_doc()
    body_paras = [r.paragraph_no for r in recs if r.tier == "본문"]
    # "0" is the unclaimed lead text ahead of the first real match -- the
    # page-break marker + repeated chapter-title header left after the tiny
    # title block is stripped (harmless residue, same convention as any
    # other unnumbered lead text -- see split_sections_kgaap's docstring).
    assert body_paras == ["0", "9994.1", "9994.2"]


# Confirmed real structure: 적용보충기준 (Supplementary Application
# Standard) paragraphs sit under a "부록A. 적용보충기준"-labeled heading in
# some 장's PDFs (e.g. 제6장/제19장) but are 본문-tier per 제1장 문단 1.2's
# own definition ("본문(적용보충기준 포함)"), numbered
# "<장번호>.<LETTER><숫자>" with an optional Korea-only insert-paragraph
# suffix "의<숫자>" (e.g. "6.A1", "6.A1의2"). Without this alternative,
# chunk_pages swallowed this whole sub-section into the preceding real
# paragraph as one wildly oversized chunk (confirmed against the real
# 제6장/제19장 downloads before this pattern was added).
def test_kgaap_body_para_re_matches_supplementary_standard_paragraphs():
    text = "6.A1 첫 문단이다.\n6.A1의2 둘째 문단이다.\n6.A2 셋째 문단이다.\n"
    matches = [m.group(1) for m in KGAAP_BODY_PARA_RE.finditer(text)]
    assert matches == ["6.A1", "6.A1의2", "6.A2"]


def test_chunk_pages_kgaap_tags_supplementary_standard_paragraphs_as_bonmun():
    text = ("목적\n6.1\n첫 문단이다.\n\n"
            "일반기업회계기준 제6장 '금융자산·금융부채'의\n부록A. 적용보충기준\n"
            "6.A1\n적용보충기준 첫 문단이다.\n6.A1의2\n삽입된 문단이다.\n")
    recs = chunk_pages([Page(text, 1, "p1")], "K-GAAP", "6", "금융자산·금융부채", "ko",
                       "u", "2026-07-06")
    by_para = {r.paragraph_no: r for r in recs}
    assert by_para["6.A1"].tier == "본문"
    assert "적용보충기준 첫 문단이다" in by_para["6.A1"].text
    assert by_para["6.A1의2"].tier == "본문"
    assert "삽입된 문단이다" in by_para["6.A1의2"].text


def test_chunk_pages_kgaap_bare_integer_numbering_for_non_chapter_items():
    # 재무회계개념체계/시행일 및 경과규정 style: bare "N"/"N." numbering, no
    # chapter prefix (see segment.py's K-GAAP module comment).
    text = "1\n첫째 문단이다.\n2\n둘째 문단이다.\n"
    recs = chunk_pages([Page(text, 1, "p1")], "K-GAAP", "시행일-경과규정",
                       "일반기업회계기준 시행일 및 경과규정", "ko", "u", "2026-07-06")
    assert [r.paragraph_no for r in recs] == ["1", "2"]
    assert all(r.tier == "본문" for r in recs)


# ---------------------------------------------------------------------------
# CAS (中国企业会计准则) chunking -- routed through its own frontmatter/
# section/paragraph-regex path (see segment.py's CAS module comment and
# chunk_pages' own docstring), NOT K-IFRS's or K-GAAP's. Mirrors the real
# structure confirmed against the downloaded casc.org.cn/cas.xmu.edu.cn
# pages: Chinese-numeral "第X条" articles for 준칙 본문, bare "<한자>、"
# top-level sections for 응용指南/해석, and (unlike K-IFRS/K-GAAP) tier is
# ALWAYS caller-supplied since a CAS download is always single-tier already.
# ---------------------------------------------------------------------------

def test_cas_article_re_matches_articles_and_excludes_chapter_section_headings():
    text = "第一章 总则\n第一条 第一条内容。\n第一节 识别\n第二条 第二条内容。\n第十条 第十条内容。\n"
    matches = [m.group(1) for m in CAS_ARTICLE_RE.finditer(text)]
    assert matches == ["一", "二", "十"]


def test_cas_guidance_para_re_matches_bare_top_level_sections_only():
    text = "一、第一节要点\n（一）子项一，不是新段落。\n1.子项二，也不是新段落。\n二、第二节要点\n"
    matches = [m.group(1) for m in CAS_GUIDANCE_PARA_RE.finditer(text)]
    assert matches == ["一", "二"]


_CAS_BODY_DOC = """财会[2006]3号
第一章 总则
第一条 为了规范测试准则的确认、计量和相关信息的披露，制定本准则。
第二条 测试文，是指企业因测试而发生的相关事项。
地址：北京市西城区月坛南街14号月新大厦2层 邮编：100045 联系邮箱：kjzz@casc.org.cn
版权所有财政部会计准则委员会，如需转载，请注明来源 技术支持：上海国家会计学院
"""


def test_chunk_pages_cas_splits_chinese_numeral_articles():
    recs = chunk_pages([Page(_CAS_BODY_DOC, 1, "p1")], "CAS", "99", "测试准则", "zh",
                       "https://www.casc.org.cn/x", "2006-01-01")
    texts = [r.text for r in recs]
    assert not any("地址：" in t for t in texts)
    assert not any("财会[2006]3号" in t for t in texts)

    by_para = {r.paragraph_no: r for r in recs}
    assert by_para["一"].tier == "본문"
    assert by_para["一"].id == "cas:99:본문:一"
    assert "为了规范测试准则" in by_para["一"].text
    assert "测试文，是指" in by_para["二"].text


_CAS_GUIDANCE_DOC = """《企业会计准则第 99 号——测试》应用指南
时间：2022-08-05 浏览：次
《企业会计准则第 99 号——测试》应用指南
一、测试要点一
本准则第一条规定了测试要点一的处理方法。
二、测试要点二
本准则第二条规定了测试要点二的处理方法。
"""


def test_chunk_pages_cas_guidance_uses_section_pattern_and_groups_under_parent_standard_no():
    # 응용指南 is always a SEPARATE download from its parent 준칙's own body
    # (see sources.py's CAS registry) -- standard_no is passed as the
    # PARENT's own number by the caller (tools/ingest/run_ingest.py's
    # `ingest_cas`), not the registry's own "<N>-지침" key, so guidance
    # groups with its body under one standard_no with tier as the only
    # distinguishing field, same convention K-GAAP's own 실무지침 uses.
    recs = chunk_pages([Page(_CAS_GUIDANCE_DOC, 1, "p1")], "CAS", "99", "测试", "zh",
                       "https://cas.xmu.edu.cn/x", "2022-08-05", tier="적용지침",
                       para_pattern=CAS_GUIDANCE_PARA_RE)
    by_para = {r.paragraph_no: r for r in recs}
    assert by_para["一"].tier == "적용지침"
    assert by_para["一"].id == "cas:99:적용지침:一"
    assert "测试要点一的处理方法" in by_para["一"].text
    assert "测试要点二的处理方法" in by_para["二"].text
    assert not any("浏览：次" in r.text for r in recs)


_CAS_INTERP_DOC = """企业会计准则解释第99号
一、关于测试问题的会计处理
该问题主要涉及测试准则。
二、生效日期
本解释自公布之日起施行。
"""


def test_chunk_pages_cas_interpretation_keeps_bonmun_tier_with_standalone_standard_no():
    # 해석 (interpretations) are kept as 본문 tier (same authority as the
    # standard they interpret) but use the SECTION pattern, not the article
    # pattern, and are their OWN standalone standard_no -- same convention
    # K-IFRS's own 해석서 (e.g. "2010") already uses, never nested under a
    # parent 준칙 number.
    recs = chunk_pages([Page(_CAS_INTERP_DOC, 1, "p1")], "CAS", "해석99",
                       "企业会计准则解释第99号", "zh", "https://www.casc.org.cn/x",
                       "2026-01-01", tier="본문", para_pattern=CAS_GUIDANCE_PARA_RE)
    by_para = {r.paragraph_no: r for r in recs}
    assert by_para["一"].tier == "본문"
    assert by_para["一"].id == "cas:해석99:본문:一"
    assert "关于测试问题的会计处理" in by_para["一"].text
    assert "本解释自公布之日起施行" in by_para["二"].text


def test_chunk_pages_cas_guidance_falls_back_to_single_chunk_without_section_headings():
    # Confirmed real case: CAS17 借款费用's own 应用指南 is plain
    # unstructured prose with no "<한자>、" heading at all -- degrades to a
    # single unnumbered ("0") chunk, same universal fallback every other
    # GAAP's chunker already has.
    text = "根据本准则规定，测试费用应当予以资本化，不存在任何编号小节。"
    recs = chunk_pages([Page(text, 1, "p1")], "CAS", "99", "测试", "zh", "u",
                       "2022-08-05", tier="적용지침", para_pattern=CAS_GUIDANCE_PARA_RE)
    assert len(recs) == 1
    assert recs[0].paragraph_no == "0"
    assert recs[0].tier == "적용지침"
    assert recs[0].text == text


# ---------------------------------------------------------------------------
# VAS (Vietnamese Accounting Standards) chunking -- HTML-sourced (see
# chunk_pages' own docstring), NOT K-IFRS's/K-GAAP's/CAS's. Mirrors the real
# structure confirmed against all 26 downloaded docs.kreston.vn pages: plain
# "01. " and table "| 01. |" đoạn numbering, at most one letter-numbered Phụ
# lục appendix per standard. See tools/ingest/segment.py's VAS module
# comment for the full structural writeup.
# ---------------------------------------------------------------------------

_VAS_PLAIN_DOC = """01. Mục đích của chuẩn mực này là quy định việc thử nghiệm.
02. Phạm vi áp dụng cho mọi doanh nghiệp.
03. Đoạn thứ ba của chuẩn mực.
"""


def test_chunk_pages_vas_splits_plain_doan_markers():
    recs = chunk_pages([Page(_VAS_PLAIN_DOC, 1, "p1")], "VAS", "99", "Chuẩn mực thử nghiệm", "vi",
                       "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-99/", "2005-01-01")
    assert [r.paragraph_no for r in recs] == ["01", "02", "03"]
    assert recs[0].id == "vas:99:본문:01"
    assert recs[0].tier == "본문"
    assert recs[0].lang == "vi"
    assert "Mục đích của chuẩn mực này" in recs[0].text
    assert "Phạm vi áp dụng" in recs[1].text


_VAS_TABLE_DOC = """| 01. | Mục đích của chuẩn mực này là quy định việc thử nghiệm. | 
| 02. | Phạm vi áp dụng cho mọi doanh nghiệp. | 
"""


def test_chunk_pages_vas_table_style_document():
    # VAS 23's real shape: EVERY đoạn rendered as a 2-column table row
    # (marker alone in col 1, prose in col 2).
    recs = chunk_pages([Page(_VAS_TABLE_DOC, 1, "p1")], "VAS", "23",
                       "Các sự kiện phát sinh sau ngày kết thúc kỳ kế toán năm", "vi", "u", "2005-03-23")
    assert [r.paragraph_no for r in recs] == ["01", "02"]
    assert "Mục đích của chuẩn mực này" in recs[0].text
    assert "Phạm vi áp dụng" in recs[1].text


# THE KNOWN BUG this test guards against (see tools/ingest/segment.py's VAS
# module comment): VAS 21 đoạn 51's real balance-sheet line-item list is
# rendered by trafilatura as pipe-delimited table rows, e.g.
# "| 1. Tiền và các khoản tương đương tiền; |  | ". A prior segmenter
# attempt stripped these pipes as a "table-row normalizer" cleanup pass
# BEFORE paragraph-marker detection ran; once stripped, "1. Tiền..." sat at
# a bare line start indistinguishable from a real marker, fragmenting đoạn
# 51 into 19 bogus one-line chunks instead of keeping it as ONE paragraph.
_VAS_EMBEDDED_LIST_DOC = """50. Đoạn trước đó.
51. Bảng cân đối kế toán phải bao
gồm các khoản mục chủ yếu sau đây :
| 1. Tiền và các khoản tương đương tiền; |  | 
| 2. Các khoản đầu tư tài chính ngắn hạn; |  | 
| 3. Các khoản phải thu thương mại và phải
  thu khác; |  | 
52. Các khoản mục bổ sung, các tiêu đề và số cộng chi tiết.
"""


def test_chunk_pages_vas_does_not_fragment_embedded_list_disguised_as_table():
    recs = chunk_pages([Page(_VAS_EMBEDDED_LIST_DOC, 1, "p1")], "VAS", "21",
                       "Trình bày Báo cáo tài chính", "vi", "u", "2004-02-15")
    # exactly 3 real đoạn -- 50, 51, 52 -- NOT 50 + 19 bogus list-item
    # fragments + 52.
    assert [r.paragraph_no for r in recs] == ["50", "51", "52"]
    by_para = {r.paragraph_no: r for r in recs}
    # every list item's own text survives verbatim, pipes and all, glued
    # onto đoạn 51 as ONE chunk (never stripped/reformatted -- see module
    # comment on why there is no separate table-row normalizer at all)
    doan51 = by_para["51"].text
    assert "Tiền và các khoản tương đương tiền" in doan51
    assert "Các khoản đầu tư tài chính ngắn hạn" in doan51
    assert "Các khoản phải thu thương mại" in doan51
    assert "| 1. Tiền và các khoản tương đương tiền; |  | " in doan51
    # đoạn 52 starts clean, right after the list, not swallowed into it and
    # not itself carrying any list-item residue
    assert by_para["52"].text.startswith("52.")
    assert "Tiền và các khoản tương đương tiền" not in by_para["52"].text


# Confirmed real case (VAS 11's own 본문): a cross-reference like "...theo
# các đoạn 50 đến\n54." or "...theo đoạn\n55." can line-wrap so the
# referenced number lands at a line start with real trailing whitespace
# before the next real sentence -- structurally indistinguishable from a
# genuine marker by shape alone. Rejected via chunk.py's `_vas_marks`
# monotonic filter: a real đoạn sequence is confirmed strictly increasing in
# every one of the 26 real files, so a candidate that does not exceed the
# previous KEPT candidate is always a false positive.
_VAS_CROSS_REF_WRAP_DOC = """53. Đoạn năm mươi ba nội dung thật.
54. Đoạn năm mươi tư nội dung thật.
55. Đoạn năm mươi lăm nội dung thật, được hạch toán theo các đoạn 50 đến
54. Phần lớn hơn giữa phần sở hữu của bên mua sẽ được hạch toán theo đoạn
55.
Lợi ích của cổ đông thiểu số
56. Đoạn năm mươi sáu nội dung thật.
"""


def test_chunk_pages_vas_rejects_cross_reference_line_wrap_false_positive():
    recs = chunk_pages([Page(_VAS_CROSS_REF_WRAP_DOC, 1, "p1")], "VAS", "11",
                       "Hợp nhất kinh doanh", "vi", "u", "2006-02-05")
    # exactly 53, 54, 55, 56 -- the two cross-reference-wrapped "54."/"55."
    # candidates inside đoạn 55's own prose must NOT create extra chunks or
    # truncate đoạn 55 early.
    assert [r.paragraph_no for r in recs] == ["53", "54", "55", "56"]
    by_para = {r.paragraph_no: r for r in recs}
    assert "được hạch toán theo các đoạn 50 đến" in by_para["55"].text
    assert "Lợi ích của cổ đông thiểu số" in by_para["55"].text
    assert by_para["56"].text.startswith("56.")


_VAS_GUIDANCE_DOC = """01. Mục đích của chuẩn mực này.
PHỤ
LỤC A
Hướng dẫn bổ sung
A1. Như đã quy định trong đoạn 01, đây là hướng dẫn bổ sung.
A2. Tiếp tục hướng dẫn bổ sung.
"""


def test_chunk_pages_vas_guidance_tier_letter_markers():
    recs = chunk_pages([Page(_VAS_GUIDANCE_DOC, 1, "p1")], "VAS", "11", "Hợp nhất kinh doanh", "vi",
                       "u", "2006-02-05")
    by_tier = {}
    for r in recs:
        by_tier.setdefault(r.tier, []).append(r)
    assert [r.paragraph_no for r in by_tier["본문"]] == ["01"]
    guidance_paras = [r.paragraph_no for r in by_tier["적용지침"]]
    assert "A1" in guidance_paras and "A2" in guidance_paras
    by_para = {r.paragraph_no: r for r in by_tier["적용지침"]}
    assert by_para["A1"].id == "vas:11:적용지침:A1"
    assert "hướng dẫn bổ sung" in by_para["A1"].text


_VAS_FORM_TEMPLATE_DOC = """01. Mục đích của chuẩn mực này.
PHỤ
LỤC 1
(Mẫu Báo cáo lưu chuyển tiền tệ)
BÁO
CÁO LƯU CHUYỂN TIỀN TỆ (MẪU 1)
| Chỉ tiêu | Mã số | Kỳ trước | Kỳ này | 
| 1. Tiền thu từ bán hàng | 01 |  |  | 
"""


def test_chunk_pages_vas_excludes_form_template_appendix_entirely():
    # VAS 24's real Phụ lục 1/2 shape: a blank statutory form template with
    # no lettered guidance marker at all -- excluded from BOTH tiers, same
    # "not citable paragraph text" treatment K-GAAP's own excluded
    # "영문양식" registry entry gets.
    recs = chunk_pages([Page(_VAS_FORM_TEMPLATE_DOC, 1, "p1")], "VAS", "24",
                       "Báo cáo lưu chuyển tiền tệ", "vi", "u", "2003-01-01")
    assert [r.paragraph_no for r in recs] == ["01"]
    assert not any("BÁO" in r.text and "LƯU CHUYỂN TIỀN TỆ" in r.text for r in recs)
    assert not any(r.tier == "적용지침" for r in recs)
