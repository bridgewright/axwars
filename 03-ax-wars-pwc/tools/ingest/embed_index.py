import json, os
import faiss
from gaap_standards_mcp.vectors import embed_passages, build_pq_index

def build_vectors(records, out_dir, model_name="intfloat/multilingual-e5-small"):
    os.makedirs(out_dir, exist_ok=True)
    vecs = embed_passages([r.text_norm for r in records], model_name=model_name)
    try:
        index = build_pq_index(vecs)
    except RuntimeError:
        # 소규모 코퍼스: PQ 학습(서브양자화기당 256 센트로이드)에 필요한 최소
        # 학습점이 부족하면 정확 탐색 flat IP 인덱스로 대체(파일 형식 동일).
        index = faiss.IndexFlatIP(vecs.shape[1])
        index.add(vecs)
    faiss.write_index(index, os.path.join(str(out_dir), "index.faiss"))
    json.dump([r.id for r in records], open(os.path.join(str(out_dir), "id_map.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
