import json, os
import faiss
from gaap_standards_mcp.vectors import embed_passages, build_pq_index

def build_vectors(records, out_dir, model_name="intfloat/multilingual-e5-small"):
    os.makedirs(out_dir, exist_ok=True)
    vecs = embed_passages([r.text_norm for r in records], model_name=model_name)
    # PQ 학습(서브양자화기당 256 센트로이드)엔 최소 ~9,984 학습점이 필요하다. 그 미만
    # 소규모 코퍼스에선 PQ가 미학습되어 recall만 나빠지고 크기 이득도 미미하므로, 정확
    # 탐색 flat IP 인덱스를 쓴다. 대규모(전 GAAP 합산)에서만 PQ로 압축한다(파일 형식 동일).
    if len(records) < 10000:
        index = faiss.IndexFlatIP(vecs.shape[1])
        index.add(vecs)
    else:
        index = build_pq_index(vecs)
    faiss.write_index(index, os.path.join(str(out_dir), "index.faiss"))
    json.dump([r.id for r in records], open(os.path.join(str(out_dir), "id_map.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
