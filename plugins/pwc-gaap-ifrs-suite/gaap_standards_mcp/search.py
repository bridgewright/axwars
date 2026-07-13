from .fusion import rrf_merge
from .normalize import tokenize

class HybridSearcher:
    def __init__(self, records, bm25, vectors, threshold=0.0):
        self.records = records
        self.bm25 = bm25
        self.vectors = vectors
        self.threshold = threshold
        self._id_to_idx = {r.id: i for i, r in enumerate(records)}

    def _bm25_rescue(self, query, pool, gaap, tier):
        # rank_bm25는 코퍼스가 아주 작으면(예: 문서 1개) 매칭 문서에도 음수
        # 점수를 줄 수 있어 BM25Index.search의 s>0 필터가 전부 걸러낸다.
        # 이때 점수가 0이 아닌(=토큰 매칭이 있는) 문서로 순위를 복원한다.
        # 무매칭(0점) 문서는 계속 제외되므로 "근거없음 → []" 계약은 유지된다.
        raw = getattr(self.bm25, "_bm25", None)
        if raw is None:
            return []
        scores = raw.get_scores(tokenize(query))
        cand = []
        for i, s in enumerate(scores):
            r = self.records[i]
            if gaap and r.gaap != gaap:
                continue
            if tier and r.tier != tier:
                continue
            if s != 0:
                cand.append((i, float(s)))
        cand.sort(key=lambda x: x[1], reverse=True)
        return cand[:pool]

    def search(self, query, gaap=None, tier=None, top_k=8):
        pool = max(top_k * 4, 20)
        bm_hits = self.bm25.search(query, top_k=pool, gaap=gaap, tier=tier)
        if not bm_hits:
            bm_hits = self._bm25_rescue(query, pool, gaap, tier)
        bm_rank = [i for i, _ in bm_hits]
        bm_score = {i: s for i, s in bm_hits}
        rankings = [bm_rank]
        vec_score = {}
        if self.vectors.available:
            for rid, s in self.vectors.search(query, top_k=pool):
                idx = self._id_to_idx.get(rid)
                if idx is None:
                    continue
                r = self.records[idx]
                if gaap and r.gaap != gaap:
                    continue
                if tier and r.tier != tier:
                    continue
                vec_score[idx] = s
            rankings.append(list(vec_score.keys()))
        fused = rrf_merge(rankings)
        if not fused or fused[0][1] < self.threshold:
            return []
        out = []
        for idx, fs in fused[:top_k]:
            d = self.records[idx].to_dict()
            d.update(bm25=bm_score.get(idx, 0.0), vec=vec_score.get(idx, 0.0), fused=fs)
            out.append(d)
        return out
