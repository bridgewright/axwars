import sys
import types
from tools.ingest.sources import SOURCES, get_source, download_kasb, KASB_DOWNLOAD_URL, download_cas_url

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


def test_cas_registry_is_the_complete_enumeration():
    # Full enumeration: 기본준칙 + 42 구체준칙 (casc.org.cn, latest
    # promulgated version each) + 32 응용指南 (cas.xmu.edu.cn -- not all 42
    # standards have one, e.g. 15/25/26/29/32/36/39/40/41/42 never got a
    # separate 应用指南 of their own) + 20 해석 (mixed casc.org.cn/mirror
    # provenance) = 95 total. 정공법: nothing enumerated on either site is
    # arbitrarily trimmed from this registry.
    standards = get_source("CAS")["standards"]
    assert len(standards) == 95

    nos = [s["no"] for s in standards]
    assert len(set(nos)) == len(nos), "duplicate standard_no (registry key) in CAS registry"

    body = [s for s in standards if not s["no"].endswith("-지침") and not s["no"].startswith("해석")]
    guidance = [s for s in standards if s["no"].endswith("-지침")]
    interp = [s for s in standards if s["no"].startswith("해석")]
    assert len(body) == 43   # 기본준칙 + 42
    assert len(guidance) == 32
    assert len(interp) == 20

    numbered_body = sorted((n for n in (s["no"] for s in body) if n.isdigit()), key=int)
    assert numbered_body == [str(i) for i in range(1, 43)]
    assert {s["no"] for s in body} - set(numbered_body) == {"기본준칙"}

    for std in standards:
        assert std["title"]
        assert std["url"].startswith("https://")
        assert std.get("format") in ("html", "pdf")
        assert std.get("tier_hint") in ("본문", "적용지침")
        assert std.get("provenance") in ("official", "mirror")


def test_cas_guidance_entries_override_standard_no_to_parent():
    # 응용指南 is always a SEPARATE download from its own standard's body
    # (unlike K-GAAP's 실무지침, embedded in the same PDF) -- `standard_no`
    # must point back at the parent so guidance groups with its body under
    # one standard number, tier being the only distinguishing field.
    standards = get_source("CAS")["standards"]
    guidance = {s["no"]: s for s in standards if s["no"].endswith("-지침")}
    assert guidance["21-지침"]["standard_no"] == "21"
    assert guidance["21-지침"]["tier_hint"] == "적용지침"
    assert guidance["21-지침"]["para_style"] == "section"
    for no, std in guidance.items():
        assert std["standard_no"] == no.split("-")[0]


def test_cas_interpretations_are_standalone_not_nested_under_a_parent():
    # 해석 (interpretations) are their OWN standalone standard_no, same
    # convention K-IFRS's own 해석서 (e.g. "2010") already uses -- never a
    # `standard_no` override pointing at some other 준칙 number.
    standards = get_source("CAS")["standards"]
    interp = [s for s in standards if s["no"].startswith("해석")]
    assert len(interp) == 20
    for std in interp:
        assert "standard_no" not in std
        assert std["tier_hint"] == "본문"
        assert std["para_style"] == "section"


def test_cas_pdf_attachments_carry_a_referer_for_the_anti_hotlink_cdn():
    # 해석16-18's official PDF attachments live on upload-news.esnai.cn
    # (casc.org.cn's own credited tech-support CDN), which 404s on a bare
    # GET with no Referer (anti-hotlink protection) -- confirmed empirically
    # (2026-07-06). Every registry entry whose url is on that CDN must carry
    # the casc.org.cn notice page it was linked from as "referer".
    standards = get_source("CAS")["standards"]
    for std in standards:
        if "esnai.cn" in std["url"]:
            assert std.get("format") == "pdf"
            assert std.get("referer", "").startswith("https://www.casc.org.cn/")


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


def test_download_cas_url_gets_plain_url_and_forwards_referer(monkeypatch, tmp_path):
    calls = {}

    class _Resp:
        content = b"cas-fake-bytes"
        def raise_for_status(self):
            pass

    def _fake_get(url, headers=None, timeout=None):
        calls["url"] = url
        calls["headers"] = headers
        return _Resp()

    fake_requests = types.SimpleNamespace(get=_fake_get)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)

    dest = tmp_path / "cas_해석16.pdf"
    out = download_cas_url("https://upload-news.esnai.cn/x.pdf", dest,
                           referer="https://www.casc.org.cn/notice.shtml")
    assert out == dest
    assert calls["url"] == "https://upload-news.esnai.cn/x.pdf"
    assert calls["headers"]["Referer"] == "https://www.casc.org.cn/notice.shtml"
    assert dest.read_bytes() == b"cas-fake-bytes"


def test_vas_registry_is_the_complete_enumeration():
    # Full enumeration of the 26 issued VAS (numbers 01-30; 09/12/13/20 were
    # never issued -- not a gap in this registry, this is the complete real
    # set), each scraped from its own docs.kreston.vn page -- see sources.py's
    # VAS registry docstring for the full 5-Decision/5-batch provenance
    # writeup. 정공법: nothing is arbitrarily trimmed from this registry.
    standards = get_source("VAS")["standards"]
    assert len(standards) == 26

    nos = [s["no"] for s in standards]
    assert len(set(nos)) == len(nos), "duplicate standard_no in VAS registry"
    assert sorted(nos, key=int) == ["01", "02", "03", "04", "05", "06", "07", "08", "10", "11",
                                     "14", "15", "16", "17", "18", "19", "21", "22", "23", "24",
                                     "25", "26", "27", "28", "29", "30"]

    for std in standards:
        assert std["title"]
        assert std["url"].startswith("https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-")
        assert std["format"] == "html"
        assert std["tier"] == "본문"
        assert std["decision_no"].endswith("/QĐ-BTC")
        assert std["decision_date"]
        assert std["as_of"]

    # every standard traces to exactly one of 5 promulgating Decisions, in 5
    # issuance batches (đợt) -- see registry docstring for the per-batch
    # membership this cross-checks.
    by_decision = {}
    for s in standards:
        by_decision.setdefault(s["decision_no"], []).append(s["no"])
    assert len(by_decision) == 5
    assert sorted(len(v) for v in by_decision.values()) == [4, 4, 6, 6, 6]
    assert by_decision["149/2001/QĐ-BTC"] == ["02", "03", "04", "14"]
    assert by_decision["165/2002/QĐ-BTC"] == ["01", "06", "10", "15", "16", "24"]
    assert by_decision["234/2003/QĐ-BTC"] == ["05", "07", "08", "21", "25", "26"]
    assert by_decision["12/2005/QĐ-BTC"] == ["17", "22", "23", "27", "28", "29"]
    assert by_decision["100/2005/QĐ-BTC"] == ["11", "18", "19", "30"]
