import json, os
import numpy as np

_MODEL_CACHE = {}

def _load_model(name):
    if name not in _MODEL_CACHE:
        from sentence_transformers import SentenceTransformer  # lazy: 최초 실행 시 다운로드
        _MODEL_CACHE[name] = SentenceTransformer(name)
    return _MODEL_CACHE[name]

def embed_passages(texts, model_name="intfloat/multilingual-e5-small"):
    m = _load_model(model_name)
    return np.asarray(m.encode([f"passage: {t}" for t in texts], normalize_embeddings=True), dtype="float32")

def build_pq_index(vecs):
    import faiss
    d = vecs.shape[1]
    m = 48 if d % 48 == 0 else 32
    index = faiss.index_factory(d, f"PQ{m}", faiss.METRIC_INNER_PRODUCT)
    index.train(vecs)
    index.add(vecs)
    return index

class VectorIndex:
    def __init__(self, index_path, id_map_path, model_name="intfloat/multilingual-e5-small"):
        self.model_name = model_name
        self._index = None
        self._ids = None
        self.available = False
        try:
            if os.path.exists(index_path) and os.path.exists(id_map_path):
                import faiss
                self._index = faiss.read_index(str(index_path))
                self._ids = json.load(open(id_map_path, encoding="utf-8"))
                self.available = True
        except Exception:
            self.available = False

    def search(self, query, top_k=8):
        if not self.available:
            return []
        try:
            m = _load_model(self.model_name)
            q = np.asarray(m.encode([f"query: {query}"], normalize_embeddings=True), dtype="float32")
            D, I = self._index.search(q, top_k)
            return [(self._ids[i], float(d)) for d, i in zip(D[0], I[0]) if i >= 0]
        except Exception:
            return []
