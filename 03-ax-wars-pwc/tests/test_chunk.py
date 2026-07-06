from tools.ingest.extract import Page
from tools.ingest.chunk import chunk_pages, ChunkingError, KGAAP_BODY_PARA_RE

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
