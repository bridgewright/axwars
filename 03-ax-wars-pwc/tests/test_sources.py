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
