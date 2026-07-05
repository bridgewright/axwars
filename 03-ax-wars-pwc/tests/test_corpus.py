from gaap_standards_mcp.schema import Record
from gaap_standards_mcp import corpus

def _r(gaap, std, para, text):
    return Record(id=f"{gaap}:{std}:{para}", gaap=gaap, standard_no=std,
                  standard_title="t", paragraph_no=para, heading="", text=text,
                  text_norm=text, lang="ko", tier="본문", source_url="",
                  as_of="2025-01-01", extract_flag=False)

def test_write_load_and_queries(tmp_path):
    recs = [_r("K-IFRS","1116",str(p),f"문단 {p}") for p in (21,22,23)]
    corpus.write_jsonl_zst(recs, tmp_path / "kifrs.jsonl.zst")
    loaded = corpus.load_corpus(tmp_path)
    assert len(loaded) == 3
    assert corpus.get_paragraph(loaded, "K-IFRS", "1116", "22").text == "문단 22"
    ctx = corpus.get_context(loaded, "K-IFRS:1116:22", window=1)
    assert [r.paragraph_no for r in ctx] == ["21", "22", "23"]
    ls = corpus.list_standards(loaded, "K-IFRS")
    assert ls[0]["standard_no"] == "1116" and ls[0]["paragraphs"] == 3
