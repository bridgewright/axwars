"""청커 경계 정합성 (2026-07-08): 페이지푸터 제거 + 후행 절/장 제목을 문단
text에서 떼어 다음 문단 heading으로 재귀속 + 새 검증 게이트. 실제 결함(K-IFRS
1116 문단 22의 '측정/최초 측정/사용권자산의 최초 측정' 혼입)을 회귀 방지한다."""
import pytest
from tools.ingest.extract import Page
from tools.ingest.chunk import (chunk_pages, strip_page_footers, _is_heading_line,
                                 _is_content_line, _split_piece)
from tools.ingest.fidelity import (assert_no_page_footer, assert_no_trailing_heading,
                                    assert_no_orphan_heading, FidelityError)
from gaap_standards_mcp.schema import Record


def _rec(text, heading="", pno="1", lang="ko"):
    return Record(id=f"kifrs:1:본문:{pno}", gaap="K-IFRS", standard_no="1",
                  standard_title="t", paragraph_no=pno, heading=heading, text=text,
                  text_norm="", lang=lang, tier="본문", source_url="", as_of="")


# --- 프리미티브 ---------------------------------------------------------------

def test_strip_page_footers_removes_dashed_keeps_content():
    t = "리스이용자는 리스개시일에 인식한다.\n- 19 -\n측정"
    out, removed = strip_page_footers(t)
    assert "- 19 -" not in out
    assert "인식한다." in out and "측정" in out
    assert removed > 0


def test_is_heading_line_distinguishes_heading_from_sentence():
    assert _is_heading_line("측정", "ko")
    assert _is_heading_line("사용권자산의 최초 측정", "ko")
    assert not _is_heading_line("리스이용자는 리스개시일에 인식한다.", "ko")   # 문장
    assert not _is_heading_line("⑴광물, 석유, 천연가스", "ko")               # 리스트
    assert not _is_heading_line("| 项 目 | 行次 |", "zh")                     # 표


def test_is_content_line_excludes_marker_and_heading():
    assert _is_content_line("리스이용자는 인식한다.", "ko")
    assert not _is_content_line("22", "ko")            # 순수 마커
    assert not _is_content_line("측정", "ko")          # 헤딩
    assert not _is_content_line("- 15 -", "ko")        # 푸터


def test_split_piece_separates_trailing_headings():
    span = "22\n리스이용자는 리스개시일에 사용권자산과 리스부채를 인식한다.\n측정\n최초 측정\n사용권자산의 최초 측정"
    body, trailing = _split_piece(span, "ko")
    assert body == "22\n리스이용자는 리스개시일에 사용권자산과 리스부채를 인식한다."
    assert trailing == ["측정", "최초 측정", "사용권자산의 최초 측정"]


def test_split_piece_returns_none_for_heading_only():
    body, trailing = _split_piece("측정\n최초 측정", "ko")
    assert body is None
    assert trailing == ["측정", "최초 측정"]


# --- 통합: chunk_pages (실제 1116 문단 22 결함 재현·수정 확인) ----------------

def test_chunk_pages_reattributes_trailing_heading_to_next_paragraph():
    # K-IFRS 1116 문단 22의 실제 구조: 한 문장 문단 뒤에 다음 절 제목 3줄.
    doc = ("22\n리스이용자는 리스개시일에 사용권자산과 리스부채를 인식한다.\n"
           "측정\n최초 측정\n사용권자산의 최초 측정\n"
           "23\n리스이용자는 리스개시일에 사용권자산을 원가로 측정한다.\n")
    recs = chunk_pages([Page(doc, 1, "p1")], "K-IFRS", "1116", "리스", "ko", "u", "2025-01-01")
    by = {r.paragraph_no: r for r in recs}
    # 문단 22 text = 그 한 문장만 (절 제목 혼입 없음)
    assert by["22"].text == "22\n리스이용자는 리스개시일에 사용권자산과 리스부채를 인식한다."
    assert "측정" not in by["22"].text
    # 떼어낸 절 제목은 다음 문단(23)의 heading으로 재귀속 (무손실)
    assert by["23"].heading == "측정 최초 측정 사용권자산의 최초 측정"
    assert by["23"].text.startswith("23")


def test_chunk_pages_strips_page_footer_between_paragraphs():
    doc = "1\n첫 문단이다.\n- 15 -\n2\n둘째 문단이다.\n"
    recs = chunk_pages([Page(doc, 1, "p1")], "K-IFRS", "1", "t", "ko", "u", "2025-01-01")
    assert not any("- 15 -" in r.text for r in recs)
    assert [r.paragraph_no for r in recs] == ["1", "2"]


def test_chunk_pages_lead_heading_becomes_next_paragraph_heading():
    doc = "목적\n1\n첫 문단이다.\n2\n둘째 문단이다.\n"
    recs = chunk_pages([Page(doc, 1, "p1")], "K-IFRS", "1", "t", "ko", "u", "2025-01-01")
    assert "0" not in [r.paragraph_no for r in recs]        # 헤딩전용 '0' 레코드 없음
    by = {r.paragraph_no: r for r in recs}
    assert by["1"].heading == "목적"


# --- 게이트 -------------------------------------------------------------------

def test_assert_no_trailing_heading():
    assert assert_no_trailing_heading([_rec("1\n리스이용자는 인식한다.")]) == []
    with pytest.raises(FidelityError):
        assert_no_trailing_heading([_rec("1\n리스이용자는 인식한다.\n측정")])


def test_assert_no_page_footer():
    assert assert_no_page_footer([_rec("1\n리스이용자는 인식한다.")]) == []
    with pytest.raises(FidelityError):
        assert_no_page_footer([_rec("1\n리스이용자는 인식한다.\n- 15 -")])


def test_assert_no_orphan_heading():
    assert assert_no_orphan_heading([_rec("1\n리스이용자는 인식한다.")]) == []
    with pytest.raises(FidelityError):
        assert_no_orphan_heading([_rec("측정\n최초 측정", pno="0")])
