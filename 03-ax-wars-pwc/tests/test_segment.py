from tools.ingest.segment import (strip_frontmatter, split_sections, SECTION_KEYS,
                                   _strip_chapter_toc_previews, _TOC_SCAN_BOUND,
                                   strip_frontmatter_kgaap, split_sections_kgaap)

# Small synthetic fixture mirroring the REAL structure confirmed against the
# downloaded kifrs_1002/1019/1116 PDFs/HWPs: cover + bilingual copyright +
# table of contents (with bare paragraph-number lines that would otherwise
# collide with the real body) + 본문 + a lettered appendix + a board-
# resolution voting log + 적용사례(IE) + 결론도출근거(BC).
FULL_DOC = """- 1 -
기업회계기준서 제9999호
테스트기준

저작권
국제회계기준위원회 연락처는 다음과 같습니다.
7 Westferry Circus, Canary Wharf, London E14 4HD, United Kingdom.
Copyright (c) 2025 IFRS Foundation
국제회계기준재단은 정부의 동의를 얻어... resides in the Republic of Korea.

COPYRIGHT NOTICE
International Financial Reporting Standards are issued by the IASB.
7 Westferry Circus, Canary Wharf, London E14 4HD, United Kingdom.
Reproduction of the integral part of the standards is permitted... resides in the Republic of Korea.
The IFRS Foundation reserves all rights... resides in the Republic of Korea.

- 4 -
본 문

- 5 -
목  차
1
2
3
기업회계기준서 제9999호는 문단 1부터 3까지와 부록 B로 구성되어 있다. 모든 문단의 권위는 같다.

- 9 -
기업회계기준서 제9999호
테스트기준
목적
1
첫째 문단 내용이다.
2
둘째 문단 내용이다.
3
셋째 문단 내용이다.

부록 B. 적용지침
이 부록은 이 기준서의 일부를 구성한다.
B1
적용지침 첫 문단이다.
B2
적용지침 둘째 문단이다.

기업회계기준서 제9999호의 제정에 대한 회계기준위원회의 의결(2020년)
기업회계기준서 제9999호의 제정(2020. 1. 1.)은 위원 7명 전원의 찬성으로 의결하였다.
회계기준위원회 위원:
홍길동(위원장), 김철수

적용사례
실무적용지침

기업회계기준서 제9999호의 적용사례
이 적용사례는 기업회계기준서 제9999호에 첨부되지만, 이 기준서의 일부를 구성하지는 않는다.
IE1
예시 문단 하나이다.
IE2
예시 문단 둘이다.

결론도출근거
IFRS 9999의 결론도출근거 (BC1-BC2)
BC1
결론도출근거 문단 하나이다.
BC2
결론도출근거 문단 둘이다.
"""


def test_strip_frontmatter_removes_copyright_boilerplate():
    kept, info = strip_frontmatter(FULL_DOC)
    assert info["copyright_removed"] is True
    assert "Westferry" not in kept
    assert "IFRS Foundation" not in kept
    # real content survives
    assert "첫째 문단 내용이다" in kept


def test_strip_frontmatter_removes_toc_bare_numbers():
    # Before stripping, the bare TOC lines "1"/"2"/"3" (cross-reference
    # numbers, not real paragraphs) sit ahead of the real "1"/"2"/"3" body
    # paragraphs. If they survived, a paragraph-boundary regex would find TWO
    # "1"s, TWO "2"s, TWO "3"s. After stripping there must be exactly one
    # occurrence of each real paragraph's own text.
    kept, info = strip_frontmatter(FULL_DOC)
    assert info["toc_removed"] is True
    assert kept.count("첫째 문단 내용이다") == 1
    assert kept.count("둘째 문단 내용이다") == 1
    assert "목  차" not in kept


def test_strip_frontmatter_noop_without_copyright_anchor():
    plain = "1 첫 문단.\n2 둘째 문단."
    kept, info = strip_frontmatter(plain)
    assert kept == plain
    assert info["copyright_removed"] is False
    assert info["chars_dropped"] == 0


def test_split_sections_keeps_bonmun_and_guidance_drops_bc_and_ie():
    kept, _ = strip_frontmatter(FULL_DOC)
    sections = split_sections(kept)
    assert set(sections) == set(SECTION_KEYS)

    body = sections["본문"]
    assert "첫째 문단 내용이다" in body
    assert "둘째 문단 내용이다" in body
    assert "셋째 문단 내용이다" in body
    assert "B1" not in body and "적용지침 첫 문단" not in body
    assert "BC1" not in body and "IE1" not in body

    guidance = sections["적용지침"]
    assert "적용지침 첫 문단이다" in guidance
    assert "적용지침 둘째 문단이다" in guidance
    assert "첫째 문단 내용이다" not in guidance
    assert "BC1" not in guidance and "IE1" not in guidance

    ie = sections["적용사례"]
    assert "예시 문단 하나이다" in ie
    assert "예시 문단 둘이다" in ie
    assert "BC1" not in ie and "B1" not in ie

    bc = sections["결론도출근거"]
    assert "결론도출근거 문단 하나이다" in bc
    assert "결론도출근거 문단 둘이다" in bc
    # the board-resolution voting log is not application guidance and not
    # part of the standard -- it must not be left attached to 적용지침.
    assert "회계기준위원회의 의결" in bc
    assert "홍길동" in bc
    assert "IE1" not in bc and "B1" not in bc


def test_split_sections_merges_multiple_appendix_headings():
    text = ("목적\n1\n첫 문단이다.\n\n"
            "부록 A. 용어의 정의\n이 부록은 이 기준서의 일부를 구성한다.\n용어1\n뜻풀이\n\n"
            "부록 B. 적용지침\n이 부록은 이 기준서의 일부를 구성한다.\nB1\nB1 문단이다.\n\n"
            "결론도출근거\nBC1\nBC1 문단이다.\n")
    sections = split_sections(text)
    # both appendices land in the SAME 적용지침 region, in document order
    assert "용어1" in sections["적용지침"]
    assert "B1 문단이다" in sections["적용지침"]
    assert sections["적용지침"].index("용어1") < sections["적용지침"].index("B1 문단이다")
    assert "BC1 문단이다" not in sections["적용지침"]


def test_appendix_heading_requires_period_after_letter():
    # "부록 B를 참조한다" (no period right after the letter) is a prose
    # cross-reference, not a heading -- it must not split the document.
    text = "목적\n1\n이 문단은 부록 B를 참조한다.\n2\n둘째 문단이다.\n"
    sections = split_sections(text)
    assert sections["적용지침"] == ""
    assert "부록 B를 참조한다" in sections["본문"]
    assert "둘째 문단이다" in sections["본문"]


def test_split_sections_plain_text_is_all_bonmun():
    sections = split_sections("1 첫 문단.\n2 둘째 문단.")
    assert sections["본문"] == "1 첫 문단.\n2 둘째 문단."
    assert sections["적용지침"] == sections["결론도출근거"] == sections["적용사례"] == ""


# ---------------------------------------------------------------------------
# Bounded-TOC-scan regression tests: the CRITICAL bug (1032/1103/1113 losing
# their entire real body) was an unbounded search for a generic "구성되어
# 있다"-shaped phrase landing on some unrelated, much later occurrence deep
# inside BC/IE. These fixtures don't need to reproduce the mid-word PDF
# line-wrap that made the real near-front sentence invisible -- omitting a
# near-front anchor entirely is observationally identical from
# strip_frontmatter's point of view (no match within the bound either way),
# and is a much smaller, more direct fixture for the same invariant.
# ---------------------------------------------------------------------------

_COVER_AND_COPYRIGHT = """- 1 -
기업회계기준서 제9999호
테스트기준

저작권
국제회계기준위원회 연락처는 다음과 같습니다.
7 Westferry Circus, Canary Wharf, London E14 4HD, United Kingdom.
Copyright (c) 2025 IFRS Foundation
국제회계기준재단은 정부의 동의를 얻어... resides in the Republic of Korea.

COPYRIGHT NOTICE
International Financial Reporting Standards are issued by the IASB.
7 Westferry Circus, Canary Wharf, London E14 4HD, United Kingdom.
Reproduction of the integral part of the standards is permitted... resides in the Republic of Korea.
The IFRS Foundation reserves all rights... resides in the Republic of Korea.
"""


def test_strip_frontmatter_bounded_toc_scan_ignores_decoy_beyond_bound():
    # No near-front structure-note sentence at all here (standing in for the
    # real bug's "invisible because PDF-line-wrap-split" case -- the effect
    # on the search is identical: no match within the bound). A decoy
    # self-referential "...구성되어 있다."-shaped sentence sits deep inside
    # padding standing in for real BC/IE prose, well past _TOC_SCAN_BOUND
    # chars from the copyright block. If the search were still unbounded (the
    # original bug), it would find this decoy and cut there, deleting every
    # real paragraph between the copyright block and the decoy -- exactly
    # the 1032/1103/1113 failure mode. Bounded, it must find nothing and
    # leave all real content (and even the decoy itself) untouched.
    padding = "이것은 실제 결론도출근거 본문을 대신하는 채움 문장이다. " * 200
    assert len(padding) > _TOC_SCAN_BOUND
    decoy = "기업회계기준서 제9999호는 전혀 다른 문맥에서 다시 구성되어 있다고 서술한다."
    text = (_COVER_AND_COPYRIGHT
            + "\n목적\n1\n첫째 문단 내용이다.\n2\n둘째 문단 내용이다.\n3\n셋째 문단 내용이다.\n\n"
            + padding + "\n" + decoy + "\n")
    kept, info = strip_frontmatter(text)
    assert info["copyright_removed"] is True
    assert info["toc_removed"] is False  # no anchor found WITHIN the bound
    assert "첫째 문단 내용이다" in kept
    assert "둘째 문단 내용이다" in kept
    assert "셋째 문단 내용이다" in kept
    assert decoy in kept  # the "BC-side" decoy is real retained content here


def test_strip_frontmatter_uses_near_front_anchor_not_deep_decoy():
    # A REAL near-front anchor and a deep decoy both exist; the cut must
    # land at the near one (a small, TOC-sized drop), never reach the decoy.
    padding = "이것은 실제 결론도출근거 본문을 대신하는 채움 문장이다. " * 200
    assert len(padding) > _TOC_SCAN_BOUND
    near_anchor = "기업회계기준서 제9999호는 문단 1부터 3까지와 부록 B로 구성되어 있다. 모든 문단의 권위는 같다."
    deep_decoy = "기업회계기준서 제9999호는 전혀 다른 문맥에서 다시 구성되어 있다고 서술한다."
    text = (_COVER_AND_COPYRIGHT
            + "\n목  차\n1\n2\n3\n" + near_anchor + "\n\n"
            + "목적\n1\n첫째 문단 내용이다.\n2\n둘째 문단 내용이다.\n3\n셋째 문단 내용이다.\n\n"
            + padding + "\n" + deep_decoy + "\n")
    kept, info = strip_frontmatter(text)
    assert info["toc_removed"] is True
    assert info["toc_anchor"] == "structure_note"
    assert info["chars_dropped"] < len(padding)  # cut at the near anchor, not the decoy
    assert "첫째 문단 내용이다" in kept
    assert "둘째 문단 내용이다" in kept
    assert "셋째 문단 내용이다" in kept
    assert deep_decoy in kept
    assert "목  차" not in kept


# ---------------------------------------------------------------------------
# 해석서 (interpretation) template: different self-reference ("기업회계기준
# 해석서" with the extra "해석" infix) and a "-며" connective TOC-closing
# clause instead of 기준서's "-다." full stop.
# ---------------------------------------------------------------------------

_INTERPRETATION_DOC = """- 1 -
기업회계기준해석서 제2010호
정부지원: 영업활동과 특정한 관련이 없는 경우

저작권
국제회계기준위원회 연락처는 다음과 같습니다.
7 Westferry Circus, Canary Wharf, London E14 4HD, United Kingdom.
Copyright (c) 2025 IFRS Foundation... resides in the Republic of Korea.

COPYRIGHT NOTICE
7 Westferry Circus, Canary Wharf, London E14 4HD, United Kingdom.
Reproduction is permitted... resides in the Republic of Korea.
All rights reserved... resides in the Republic of Korea.

목  차
한1.1
2
3
기업회계기준해석서 제2010호는 문단 한1.1부터 3까지로 구성되어 있으며, 결론도출근거가 첨부되어 있다.

기업회계기준해석서 제2010호
정부지원: 영업활동과 특정한 관련이 없는 경우
한1.1
이 해석서는 실제 적용범위에 관한 진짜 내용을 담고 있다.
2
둘째 문단 내용이다.
3
셋째 문단 내용이다.

기업회계기준해석서 제2010호의 제정에 대한 회계기준위원회의 의결(2007년)
회계기준위원회 위원: 이효익(위원장), 서정우

결론도출근거
SIC 10의 결론도출근거
BC1
결론도출근거 문단이다.
"""


def test_strip_frontmatter_handles_interpretation_dash_myeo_ending_no_period():
    # The old regex required a literal "있다" ending and so never matched
    # 해석서's "-며" connective clause at all, for any of the 19 해석서 (see
    # module docstring) -- the self-ref + bare 구성/부여 stem anchor (no
    # verb-ending requirement) must fire regardless.
    kept, info = strip_frontmatter(_INTERPRETATION_DOC)
    assert info["toc_removed"] is True
    assert info["toc_anchor"] == "structure_note"
    assert "목  차" not in kept
    assert "이 해석서는 실제 적용범위에 관한 진짜 내용을 담고 있다" in kept


def test_split_sections_routes_interpretation_board_resolution_despite_extra_infix():
    # 해석서 write "기업회계기준해석서" (extra "해석" infix) where 기준서
    # write "기업회계기준서" -- a board-resolution regex anchored on the
    # literal 기준서 prefix never matches this, leaking the voting log into
    # 본문 for every one of the 19 해석서 (see module docstring). The
    # suffix-anchored _BOARD_RESOLUTION_RE must catch it regardless.
    kept, _ = strip_frontmatter(_INTERPRETATION_DOC)
    sections = split_sections(kept)
    assert "이 해석서는 실제 적용범위에 관한 진짜 내용을 담고 있다" in sections["본문"]
    assert "둘째 문단 내용이다" in sections["본문"]
    assert "회계기준위원회의 의결" not in sections["본문"]
    assert "회계기준위원회의 의결" in sections["결론도출근거"]
    assert "결론도출근거 문단이다" in sections["결론도출근거"]
    assert "결론도출근거 문단이다" not in sections["본문"]


# ---------------------------------------------------------------------------
# 개념체계's per-chapter mini-TOC preview (see _strip_chapter_toc_previews).
# ---------------------------------------------------------------------------

def test_strip_chapter_toc_previews_removes_per_chapter_toc_block():
    text = ("1.23\n마지막 문단의 실제 내용이다.\n\n"
            "목\n차\n제2장 유용한 재무정보의 질적특성\n서론\n근본적질적특성\n문단번호\n"
            "2.1\n실제 2장 첫 문단 내용이다.\n")
    cleaned = _strip_chapter_toc_previews(text)
    assert "마지막 문단의 실제 내용이다" in cleaned
    assert "실제 2장 첫 문단 내용이다" in cleaned
    assert "유용한 재무정보의 질적특성" not in cleaned
    assert "근본적질적특성" not in cleaned
    assert "문단번호" not in cleaned


def test_strip_chapter_toc_previews_is_noop_without_chapter_structure():
    text = "1 첫 문단이다.\n2 둘째 문단이다."
    assert _strip_chapter_toc_previews(text) == text


def test_split_sections_strips_chapter_toc_preview_from_concept_framework_style_doc():
    text = ("목적\n1.23\n마지막 문단의 실제 내용이다.\n\n"
            "목\n차\n제2장 제목\n소제목\n문단번호\n"
            "2.1\n실제 2장 첫 문단 내용이다.\n")
    sections = split_sections(text)
    assert "마지막 문단의 실제 내용이다" in sections["본문"]
    assert "실제 2장 첫 문단 내용이다" in sections["본문"]
    assert "제2장 제목" not in sections["본문"]
    assert "소제목" not in sections["본문"]


# ---------------------------------------------------------------------------
# K-GAAP (일반기업회계기준) segmentation -- a structurally unrelated document
# template from K-IFRS's (see segment.py's K-GAAP module comment): organized
# by 장/chapter with "<장번호>.<문단번호>" paragraph numbering, no IFRS
# Foundation copyright block at all. Fixtures below mirror the REAL structure
# confirmed against the downloaded kgaap_1/13/19/26 PDFs and the
# 재무회계개념체계/시행일 및 경과규정 attachments.
# ---------------------------------------------------------------------------

_KGAAP_CHAPTER_DOC = """일반기업회계기준
제9998장 테스트장
한국회계기준원 회계기준위원회
의결 2020. 1. 1.

- 2 -
제9998장 테스트장
목적
9998.1
이 장의 목적은 테스트를 위한 것이다.
9998.2
둘째 문단 내용이다.

일반기업회계기준 제9998장 '테스트장'의
부록
결론도출근거
결9998.1
결론도출근거 문단이다.

실무지침
실9998.1
실무지침 첫 문단이다.
실9998.2
실무지침 둘째 문단이다.

적용사례
사례1
적용사례 문단이다.
"""


def test_strip_frontmatter_kgaap_removes_tiny_title_block():
    kept, info = strip_frontmatter_kgaap(_KGAAP_CHAPTER_DOC)
    assert info["copyright_removed"] is True
    assert "한국회계기준원 회계기준위원회" not in kept
    assert "의결 2020" not in kept
    assert "이 장의 목적은 테스트를 위한 것이다" in kept


def test_split_sections_kgaap_keeps_bonmun_and_silmu_jichim_drops_bc_and_ie():
    kept, _ = strip_frontmatter_kgaap(_KGAAP_CHAPTER_DOC)
    sections = split_sections_kgaap(kept)
    assert set(sections) == set(SECTION_KEYS)

    body = sections["본문"]
    assert "이 장의 목적은 테스트를 위한 것이다" in body
    assert "둘째 문단 내용이다" in body
    assert "실무지침 첫 문단이다" not in body
    assert "결론도출근거 문단이다" not in body

    guidance = sections["적용지침"]
    assert "실무지침 첫 문단이다" in guidance
    assert "실무지침 둘째 문단이다" in guidance
    assert "이 장의 목적은" not in guidance

    bc = sections["결론도출근거"]
    assert "결론도출근거 문단이다" in bc

    ie = sections["적용사례"]
    assert "적용사례 문단이다" in ie


# Confirmed real structure: 제26장 기본주당이익's PDF carries a
# WHOLE-STANDARD-SET "목   차" (33-chapter listing, no paragraph-range
# column) right after its own tiny title block, spanning a page break, and
# ending with a preview mention of the enactment-log section title itself
# ("...회계기준위원회의 의결") -- which, unstripped, tripped
# fidelity._BOARD_RESOLUTION_RE when first discovered (see chunk.py's own
# module history). Confirmed absent from most other 장 (e.g. 제1/13장) --
# strip_frontmatter_kgaap must handle BOTH cases correctly.
_KGAAP_MASTER_TOC_DOC = """일반기업회계기준
제9996장 테스트장
한국회계기준원 회계기준위원회
의결 2020. 1. 1.

목   차
제1장 목적, 구성 및 적용
제2장 재무제표의 작성과 표시Ⅰ

- 2 -
목   차
제9996장 테스트장
일반기업회계기준의 제정에 대한 회계기준위원회의 의결

- 3 -
제9996장 테스트장
목적
9996.1
이 장의 목적은 진짜 내용을 담고 있다.
"""


def test_strip_frontmatter_kgaap_removes_whole_document_toc_when_present():
    kept, info = strip_frontmatter_kgaap(_KGAAP_MASTER_TOC_DOC)
    assert info["toc_removed"] is True
    assert info["toc_anchor"] == "목차"
    assert "목   차" not in kept
    assert "제2장 재무제표의 작성과 표시" not in kept
    assert "회계기준위원회의 의결" not in kept
    assert "이 장의 목적은 진짜 내용을 담고 있다" in kept


def test_strip_frontmatter_kgaap_master_toc_is_noop_when_absent():
    # 제1/13장-style documents have no whole-document TOC at all -- the
    # anchor must be a clean no-op, not reach into unrelated real content.
    kept, info = strip_frontmatter_kgaap(_KGAAP_CHAPTER_DOC)
    assert info["toc_anchor"] != "목차"


# Confirmed real structure: 재무회계개념체계 has no "의결" title block and no
# whole-document "목차" listing -- instead a short "정본" disclaimer + a
# "서문" (preface) + a per-chapter-repeating "내용"-headed mini-TOC that
# closes with a "문단번호" column of paragraph-range previews, and its own
# 본문 paragraphs are bare "N." (digit + literal period + space), NOT the
# "<장번호>.<문단번호>" style every numbered 장 uses.
_KGAAP_FRAMEWORK_DOC = """재무회계개념체계
2019. 9. 27.
한국회계연구원
회계기준위원회
회계기준위원회에서 제정한 기업회계기준서의 정본은 웹사이트에 게재한 자료이다.

서
문
이것은 서문 내용이며 인용 대상이 아니다.

내
용
제1장 서론
개념체계의 목적
문단번호
1-2

- 1 -
재무회계개념체계
제1장서론
개념체계의목적
1. 첫째 문단 내용이다.
2. 둘째 문단 내용이다.
"""


def test_strip_frontmatter_kgaap_removes_disclaimer_preface_and_toc_for_framework_doc():
    kept, info = strip_frontmatter_kgaap(_KGAAP_FRAMEWORK_DOC)
    assert info["toc_removed"] is True
    assert info["toc_anchor"] == "문단번호"
    assert "정본" not in kept
    assert "서문 내용" not in kept
    assert "문단번호" not in kept
    assert "첫째 문단 내용이다" in kept
    assert "둘째 문단 내용이다" in kept


# Confirmed real structure: 일반기업회계기준 시행일 및 경과규정's own 부록
# contains ONLY a 소수의견 (dissenting board-member opinion) subsection, no
# 결론도출근거/실무지침/적용사례 at all -- paragraphs "소<N>". Dropped
# alongside 결론도출근거/적용사례 (rationale/opinion commentary, not the
# standard itself), routed into the same "결론도출근거" bucket as a labeling
# convenience (both dropped identically by chunk_pages).
_KGAAP_DISSENT_DOC = """일반기업회계기준
시행일 및 경과규정
한국회계기준원 회계기준위원회
의결 2020. 1. 1.

1
첫째 문단 내용이다.

일반기업회계기준 '시행일 및 경과규정'의
부록
소수의견
소1
반대의견 문단이다.
"""


def test_split_sections_kgaap_drops_dissenting_opinion_into_bc_bucket():
    kept, _ = strip_frontmatter_kgaap(_KGAAP_DISSENT_DOC)
    sections = split_sections_kgaap(kept)
    assert "첫째 문단 내용이다" in sections["본문"]
    assert "반대의견 문단이다" not in sections["본문"]
    assert "반대의견 문단이다" in sections["결론도출근거"]
    assert sections["적용지침"] == ""
    assert sections["적용사례"] == ""
