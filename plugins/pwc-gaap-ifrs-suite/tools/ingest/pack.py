import os, json
from gaap_standards_mcp.corpus import write_jsonl_zst
from gaap_standards_mcp.schema import Record  # noqa: F401
from .embed_index import build_vectors

_SLUG = {"K-IFRS": "kifrs", "K-GAAP": "kgaap", "US-GAAP": "usgaap", "CAS": "cas", "VAS": "vas"}

def pack(records_by_gaap, corpus_dir):
    os.makedirs(corpus_dir, exist_ok=True)
    all_records = []
    manifest = {"gaaps": {}}
    for gaap, recs in records_by_gaap.items():
        write_jsonl_zst(recs, os.path.join(str(corpus_dir), f"{_SLUG[gaap]}.jsonl.zst"))
        all_records += recs
        stds = {r.standard_no for r in recs}
        manifest["gaaps"][gaap] = {"standards": sorted(stds), "paragraphs": len(recs),
                                   "as_of": recs[0].as_of if recs else ""}
    build_vectors(all_records, os.path.join(str(corpus_dir), "vectors"))
    json.dump(manifest, open(os.path.join(str(corpus_dir), "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
