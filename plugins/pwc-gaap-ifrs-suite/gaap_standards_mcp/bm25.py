from rank_bm25 import BM25Okapi
from .normalize import tokenize

class BM25Index:
    def __init__(self, records):
        self.records = records
        self._tok = [tokenize(r.text_norm) for r in records]
        self._bm25 = BM25Okapi(self._tok) if records else None

    def search(self, query, top_k=8, gaap=None, tier=None):
        if not self._bm25:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        cand = []
        for i, s in enumerate(scores):
            r = self.records[i]
            if gaap and r.gaap != gaap:
                continue
            if tier and r.tier != tier:
                continue
            if s > 0:
                cand.append((i, float(s)))
        cand.sort(key=lambda x: x[1], reverse=True)
        return cand[:top_k]
