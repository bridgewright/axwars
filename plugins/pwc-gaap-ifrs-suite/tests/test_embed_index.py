import numpy as np, json
from gaap_standards_mcp.schema import Record
from tools.ingest import embed_index

def _r(i):
    return Record(id=f"K-IFRS:1116:{i}", gaap="K-IFRS", standard_no="1116", standard_title="",
                  paragraph_no=str(i), heading="", text=f"문단{i}", text_norm=f"문단{i}",
                  lang="ko", tier="본문", source_url="", as_of="", extract_flag=False)

def test_build_vectors(tmp_path, monkeypatch):
    recs = [_r(i) for i in range(40)]
    monkeypatch.setattr(embed_index, "embed_passages",
                        lambda texts, model_name=None: np.random.RandomState(0).rand(len(texts), 96).astype("float32"))
    embed_index.build_vectors(recs, tmp_path)
    assert (tmp_path / "index.faiss").exists()
    ids = json.load(open(tmp_path / "id_map.json", encoding="utf-8"))
    assert ids[0] == "K-IFRS:1116:0" and len(ids) == 40
