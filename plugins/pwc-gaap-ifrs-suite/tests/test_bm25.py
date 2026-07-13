from gaap_standards_mcp.schema import Record
from gaap_standards_mcp.bm25 import BM25Index

def _r(i, gaap, text):
    return Record(id=str(i), gaap=gaap, standard_no="x", standard_title="",
                  paragraph_no=str(i), heading="", text=text, text_norm=text,
                  lang="ko", tier="본문", source_url="", as_of="", extract_flag=False)

def test_bm25_ranks_and_filters():
    recs = [_r(0,"K-IFRS","사용권자산과 리스부채를 인식한다"),
            _r(1,"K-IFRS","재고자산은 저가법으로 측정한다"),
            _r(2,"US-GAAP","operating lease right-of-use asset")]
    idx = BM25Index(recs)
    top = idx.search("리스부채 인식", top_k=2)
    assert top[0][0] == 0
    only_us = idx.search("lease", top_k=5, gaap="US-GAAP")
    assert all(recs[i].gaap == "US-GAAP" for i, _ in only_us)
