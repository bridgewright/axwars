from gaap_standards_mcp.schema import Record
from gaap_standards_mcp import corpus, fallback

def test_fallback_bm25_only(tmp_path):
    recs = [Record(id="K-IFRS:1116:22", gaap="K-IFRS", standard_no="1116",
                   standard_title="리스", paragraph_no="22", heading="",
                   text="사용권자산과 리스부채를 인식한다",
                   text_norm="사용권자산과 리스부채를 인식한다", lang="ko",
                   tier="본문", source_url="", as_of="", extract_flag=False)]
    corpus.write_jsonl_zst(recs, tmp_path / "kifrs.jsonl.zst")
    hits = fallback.fallback_search(tmp_path, "리스부채", top_k=3)
    assert hits[0]["id"] == "K-IFRS:1116:22" and "bm25" in hits[0]
