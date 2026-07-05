import anyio
from gaap_standards_mcp.schema import Record
from gaap_standards_mcp import corpus, server

def test_tool_listing(tmp_path):
    recs = [Record(id="K-IFRS:1116:22", gaap="K-IFRS", standard_no="1116", standard_title="리스",
                   paragraph_no="22", heading="", text="리스부채를 인식한다",
                   text_norm="리스부채를 인식한다", lang="ko", tier="본문",
                   source_url="u", as_of="2025-01-01", extract_flag=False)]
    corpus.write_jsonl_zst(recs, tmp_path / "kifrs.jsonl.zst")
    app, _ = server.make_app(str(tmp_path))

    async def go():
        tools = await app.list_tools()
        return {t.name for t in tools}
    names = anyio.run(go)
    assert {"search_standards","get_paragraph","get_context","list_standards"} <= names
