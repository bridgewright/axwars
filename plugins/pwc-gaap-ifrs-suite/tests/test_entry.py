from gaap_standards_mcp.schema import Record
from gaap_standards_mcp import corpus, entry

def test_entry_degraded_without_vectors(tmp_path):
    recs = [Record(id="K-IFRS:1116:22", gaap="K-IFRS", standard_no="1116", standard_title="리스",
                   paragraph_no="22", heading="", text="리스부채를 인식한다",
                   text_norm="리스부채를 인식한다", lang="ko", tier="본문",
                   source_url="u", as_of="2025-01-01", extract_flag=False)]
    corpus.write_jsonl_zst(recs, tmp_path / "kifrs.jsonl.zst")  # vectors/ 없음
    res = entry.answer_query(str(tmp_path), "리스부채")
    assert res["mode"] in ("degraded", "no-mcp")
    assert res["hits"][0]["standard_no"] == "1116"
