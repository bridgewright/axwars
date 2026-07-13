import json, os
import faiss
from gaap_standards_mcp.vectors import embed_passages, build_pq_index

def build_vectors(records, out_dir, model_name="intfloat/multilingual-e5-small"):
    os.makedirs(out_dir, exist_ok=True)
    vecs = embed_passages([r.text_norm for r in records], model_name=model_name)
    # 정확탐색 flat IP 인덱스가 압축본 예산(약 60MB) 안이면 flat(양자화손실 0, recall 최상)을
    # 쓰고, 그 이상 대규모에서만 PQ로 압축한다(파일 형식 동일, faiss.read_index 호환).
    # flat 크기 = N × dim × 4B. dim=384 기준 60MB ≈ 약 39,000 벡터. (PQ<9,984면 미학습이라
    # 어차피 flat 구간과 겹치지 않음.)
    flat_bytes = len(records) * vecs.shape[1] * 4
    if flat_bytes < 60_000_000:
        index = faiss.IndexFlatIP(vecs.shape[1])
        index.add(vecs)
    else:
        index = build_pq_index(vecs)
    faiss.write_index(index, os.path.join(str(out_dir), "index.faiss"))
    json.dump([r.id for r in records], open(os.path.join(str(out_dir), "id_map.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
