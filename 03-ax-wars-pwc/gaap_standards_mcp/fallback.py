import sys, json
from .corpus import load_corpus
from .bm25 import BM25Index
from .normalize import tokenize

def _rescue_hits(bm, records, query, gaap=None, tier=None, top_k=8):
    # 소형 코퍼스에서는 rank_bm25 IDF가 0 이하가 되어 BM25Index.search의
    # 양수 점수 필터에 모두 걸러질 수 있다. 질의 토큰과 겹치는(어휘 근거가
    # 있는) 문서만 원점수 내림차순 + 겹침 수 tie-break로 재순위한다.
    if bm._bm25 is None:
        return []
    q_toks = tokenize(query)
    q_set = set(q_toks)
    scores = bm._bm25.get_scores(q_toks)
    cand = []
    for i, s in enumerate(scores):
        r = records[i]
        if gaap and r.gaap != gaap:
            continue
        if tier and r.tier != tier:
            continue
        overlap = len(q_set & set(bm._tok[i]))
        if overlap:
            cand.append((i, float(s), overlap))
    cand.sort(key=lambda x: (x[1], x[2]), reverse=True)
    return [(i, s) for i, s, _ in cand[:top_k]]

def fallback_search(corpus_dir, query, gaap=None, tier=None, top_k=8):
    records = load_corpus(str(corpus_dir))
    bm = BM25Index(records)
    hits = bm.search(query, top_k=top_k, gaap=gaap, tier=tier)
    if not hits:
        hits = _rescue_hits(bm, records, query, gaap=gaap, tier=tier, top_k=top_k)
    out = []
    for i, s in hits:
        d = records[i].to_dict()
        d["bm25"] = s
        out.append(d)
    return out

if __name__ == "__main__":
    corpus_dir, query = sys.argv[1], sys.argv[2]
    print(json.dumps(fallback_search(corpus_dir, query), ensure_ascii=False, indent=2))
