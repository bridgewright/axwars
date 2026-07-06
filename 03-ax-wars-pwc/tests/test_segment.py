from tools.ingest.segment import strip_frontmatter, split_sections, SECTION_KEYS

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
