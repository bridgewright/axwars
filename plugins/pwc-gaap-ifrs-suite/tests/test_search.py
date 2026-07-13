from gaap_standards_mcp.schema import Record
from gaap_standards_mcp.bm25 import BM25Index
from gaap_standards_mcp.search import HybridSearcher

class _StubVec:
    available = True
    def __init__(self, ranked): self.ranked = ranked
    def search(self, q, top_k=8): return self.ranked

def _r(i, text):
    return Record(id=str(i), gaap="K-IFRS", standard_no="1116", standard_title="",
                  paragraph_no=str(i), heading="", text=text, text_norm=text,
                  lang="ko", tier="본문", source_url="", as_of="", extract_flag=False)

def test_hybrid_merges_bm25_and_vectors():
    recs = [_r(0,"리스부채 인식"), _r(1,"재고 저가법"), _r(2,"사용권자산")]
    bm = BM25Index(recs)
    vec = _StubVec([("2", 0.9), ("0", 0.8)])
    hs = HybridSearcher(recs, bm, vec)
    hits = hs.search("리스부채", top_k=3)
    assert hits and "fused" in hits[0] and hits[0]["bm25"] >= 0

def test_bm25_only_when_vectors_unavailable():
    recs = [_r(0,"리스부채 인식")]
    class _Off: available = False; search = lambda self,q,top_k=8: []
    hs = HybridSearcher(recs, BM25Index(recs), _Off())
    assert hs.search("리스부채")[0]["id"] == "0"
