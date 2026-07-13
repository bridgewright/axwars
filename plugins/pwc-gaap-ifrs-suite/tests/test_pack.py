import json
from gaap_standards_mcp.schema import Record
from gaap_standards_mcp import corpus
from tools.ingest import pack as packmod

def _r(g, p):
    return Record(id=f"{g}:1:{p}", gaap=g, standard_no="1", standard_title="t", paragraph_no=str(p),
                  heading="", text=f"t{p}", text_norm=f"t{p}", lang="ko", tier="본문",
                  source_url="", as_of="2025-01-01", extract_flag=False)

def test_pack_writes_corpus_and_manifest(tmp_path, monkeypatch):
    import numpy as np
    from tools.ingest import embed_index
    monkeypatch.setattr(embed_index, "embed_passages",
                        lambda texts, model_name=None: np.random.RandomState(0).rand(len(texts),96).astype("float32"))
    data = {"K-IFRS": [_r("K-IFRS", p) for p in range(40)]}
    packmod.pack(data, tmp_path)
    assert corpus.load_corpus(tmp_path)  # jsonl.zst 로드됨
    man = json.load(open(tmp_path / "manifest.json", encoding="utf-8"))
    assert man["gaaps"]["K-IFRS"]["paragraphs"] == 40
    assert (tmp_path / "vectors" / "index.faiss").exists()
