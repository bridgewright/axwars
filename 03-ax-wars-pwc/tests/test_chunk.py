from tools.ingest.extract import Page
from tools.ingest.chunk import chunk_pages, ChunkingError

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
