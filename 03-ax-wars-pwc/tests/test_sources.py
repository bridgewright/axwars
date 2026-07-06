import sys
import types
from tools.ingest.sources import SOURCES, get_source, download_kasb, KASB_DOWNLOAD_URL

def test_sources_cover_all_gaaps():
    assert set(SOURCES) == {"K-IFRS","K-GAAP","US-GAAP","CAS","VAS"}
    assert get_source("K-IFRS")["lang"] == "ko"
    assert all("standards" in v for v in SOURCES.values())

def test_kifrs_standards_carry_kasb_download_tokens():
    # KASB has no stable per-standard GET URL -- downloads are POST
    # https://www.kasb.or.kr/commonFile/fileDownload.do with fileNo/fileSeq
    # form fields, so each standard entry carries the tokens needed to build
    # that request instead of a url.
    by_no = {s["no"]: s for s in get_source("K-IFRS")["standards"]}
    # Spot-check the 3 standards the pipeline was originally validated against;
    # full-registry structural checks (below) cover the rest.
    for no, expected_file_no in [("1116", "10510"), ("1002", "9837"), ("1019", "-49992028")]:
        std = by_no[no]
        assert std["file_no"] == expected_file_no
        assert "file_seq_pdf" in std and "file_seq_hwp" in std
        assert std["tier"] == "본문"
        assert std["title"]

def test_kifrs_registry_is_the_complete_kasb_enumeration():
    # Full enumeration of https://www.kasb.or.kr/front/board/ingAccountingList.do
    # (the "시행중" tab): 63 rows total on the site (scraped 2026-07-06) -- 41
    # 기준서 (1xxx) + 19 해석서 (2xxx) + 3 non-numbered items (Conceptual
    # Framework + 2 translated IASB Practice Statements). 정공법: nothing
    # enumerated on the page is arbitrarily trimmed from this registry.
    standards = get_source("K-IFRS")["standards"]
    assert len(standards) == 63

    nos = [s["no"] for s in standards]
    assert len(set(nos)) == len(nos), "duplicate standard_no in K-IFRS registry"

    numbered = [n for n in nos if n.isdigit()]
    assert len(numbered) == 60
    assert sum(1 for n in numbered if n.startswith("1")) == 41
    assert sum(1 for n in numbered if n.startswith("2")) == 19

    non_numbered = set(nos) - set(numbered)
    assert non_numbered == {"개념체계", "번역서-중요성판단", "번역서-경영진설명서"}

    for std in standards:
        assert std["title"]
        assert std["file_no"]
        assert std["file_seq_pdf"] and std["file_seq_hwp"]
        assert std["file_seq_pdf"] != std["file_seq_hwp"]
        assert std["tier"] == "본문"

def test_kgaap_registry_is_the_complete_kasb_enumeration():
    # Full enumeration of https://www.kasb.or.kr/front/board/List3003.do
    # (37 rows total on the site, scraped 2026-07-06, no pagination) -- 33
    # numbered 장 (1-33, contiguous) + 4 non-chapter items: 재무회계개념체계
    # ("개념체계"), 일반기업회계기준 시행일 및 경과규정
    # ("시행일-경과규정"), 보험업회계처리준칙, and 일반기업회계기준
    # 재무제표 영문양식 ("영문양식", the only HWP-only row on the whole
    # board). 정공법: nothing enumerated on the page is arbitrarily trimmed
    # from this registry (the 영문양식 item is EXCLUDED at the ingestion
    # step instead, for a documented content reason -- see the ingestion
    # report -- not omitted from the catalog here).
    standards = get_source("K-GAAP")["standards"]
    assert len(standards) == 37

    nos = [s["no"] for s in standards]
    assert len(set(nos)) == len(nos), "duplicate standard_no in K-GAAP registry"

    numbered = [n for n in nos if n.isdigit()]
    assert len(numbered) == 33
    assert sorted(numbered, key=int) == [str(i) for i in range(1, 34)]

    non_numbered = set(nos) - set(numbered)
    assert non_numbered == {"개념체계", "시행일-경과규정", "보험업회계처리준칙", "영문양식"}

    for std in standards:
        assert std["title"]
        assert std["file_no"]
        assert std["file_seq_hwp"]
        assert std["tier"] == "본문"
        # every entry except the one confirmed HWP-only item carries a PDF
        # attachment token too
        if std["no"] == "영문양식":
            assert std["file_seq_pdf"] is None
            assert std.get("format") == "hwp"
        else:
            assert std["file_seq_pdf"]
            assert std["file_seq_pdf"] != std["file_seq_hwp"]


def test_download_kasb_posts_file_no_and_seq(monkeypatch, tmp_path):
    calls = {}

    class _Resp:
        content = b"%PDF-fake-bytes"
        def raise_for_status(self):
            pass

    def _fake_post(url, data=None, timeout=None):
        calls["url"] = url
        calls["data"] = data
        return _Resp()

    fake_requests = types.SimpleNamespace(post=_fake_post)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)

    dest = tmp_path / "kifrs_1116.pdf"
    out = download_kasb("10510", "1", dest)
    assert out == dest
    assert calls["url"] == KASB_DOWNLOAD_URL
    assert calls["data"] == {"fileNo": "10510", "fileSeq": "1"}
    assert dest.read_bytes() == b"%PDF-fake-bytes"
