from gaap_standards_mcp.schema import Record
from gaap_standards_mcp import corpus, server

def _seed(tmp_path):
    recs = [Record(id="K-IFRS:1116:22", gaap="K-IFRS", standard_no="1116", standard_title="리스",
                   paragraph_no="22", heading="", text="사용권자산과 리스부채를 인식한다",
                   text_norm="사용권자산과 리스부채를 인식한다", lang="ko", tier="본문",
                   source_url="u", as_of="2025-01-01", extract_flag=False)]
    corpus.write_jsonl_zst(recs, tmp_path / "kifrs.jsonl.zst")

def test_handlers(tmp_path):
    _seed(tmp_path)
    ctx = server.Context(str(tmp_path))
    hits = ctx.search("리스부채", top_k=3)
    assert hits[0]["standard_no"] == "1116"
    assert ctx.get_paragraph("K-IFRS","1116","22")["text"].startswith("사용권자산")
    assert ctx.list_standards("K-IFRS")[0]["paragraphs"] == 1
