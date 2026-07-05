import os
from .corpus import load_corpus, get_paragraph, get_context, list_standards
from .bm25 import BM25Index
from .vectors import VectorIndex
from .search import HybridSearcher

class Context:
    def __init__(self, corpus_dir):
        self.records = load_corpus(corpus_dir)
        bm = BM25Index(self.records)
        vec = VectorIndex(os.path.join(corpus_dir, "vectors", "index.faiss"),
                          os.path.join(corpus_dir, "vectors", "id_map.json"))
        self.searcher = HybridSearcher(self.records, bm, vec)
        self.vectors_available = vec.available

    def search(self, query, gaap=None, tier=None, top_k=8):
        return self.searcher.search(query, gaap=gaap, tier=tier, top_k=top_k)

    def get_paragraph(self, gaap, standard_no, paragraph_no):
        r = get_paragraph(self.records, gaap, standard_no, paragraph_no)
        return r.to_dict() if r else None

    def get_context(self, id, window=2):
        return [r.to_dict() for r in get_context(self.records, id, window)]

    def list_standards(self, gaap=None):
        return list_standards(self.records, gaap)

def make_app(corpus_dir):
    from mcp.server.fastmcp import FastMCP
    ctx = Context(corpus_dir)
    app = FastMCP("gaap-standards")

    @app.tool()
    def search_standards(query: str, gaap: str = None, tier: str = None, top_k: int = 8) -> list:
        """회계기준 원문을 하이브리드 검색해 문단(원문 verbatim)+출처를 반환."""
        return ctx.search(query, gaap, tier, top_k)

    @app.tool()
    def get_paragraph(gaap: str, standard_no: str, paragraph_no: str) -> dict:
        """특정 기준서 문단의 원문을 정확히 반환."""
        return ctx.get_paragraph(gaap, standard_no, paragraph_no)

    @app.tool()
    def get_context(id: str, window: int = 2) -> list:
        """해당 문단의 앞뒤 인접 문단을 반환."""
        return ctx.get_context(id, window)

    @app.tool()
    def list_standards(gaap: str = None) -> list:
        """적재된 기준서·문단수·as_of(커버리지 투명성)를 반환."""
        return ctx.list_standards(gaap)

    return app, ctx
