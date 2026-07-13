import json, glob, os
import zstandard as zstd
from .schema import Record

def write_jsonl_zst(records, path):
    data = "\n".join(json.dumps(r.to_dict(), ensure_ascii=False) for r in records)
    with open(path, "wb") as f:
        f.write(zstd.ZstdCompressor(level=19).compress(data.encode("utf-8")))

def load_corpus(corpus_dir):
    out = []
    for p in sorted(glob.glob(os.path.join(corpus_dir, "*.jsonl.zst"))):
        with open(p, "rb") as f:
            raw = zstd.ZstdDecompressor().decompress(f.read()).decode("utf-8")
        out += [Record.from_dict(json.loads(line)) for line in raw.splitlines() if line]
    return out

def get_paragraph(records, gaap, standard_no, paragraph_no):
    for r in records:
        if r.gaap == gaap and r.standard_no == standard_no and r.paragraph_no == paragraph_no:
            return r
    return None

def get_context(records, id, window=2):
    idx = next((i for i, r in enumerate(records) if r.id == id), None)
    if idx is None:
        return []
    base = records[idx]
    same = [r for r in records if r.gaap == base.gaap and r.standard_no == base.standard_no]
    pos = same.index(base)
    return same[max(0, pos - window): pos + window + 1]

def list_standards(records, gaap=None):
    agg = {}
    for r in records:
        if gaap and r.gaap != gaap:
            continue
        key = (r.gaap, r.standard_no)
        a = agg.setdefault(key, {"gaap": r.gaap, "standard_no": r.standard_no,
                                 "standard_title": r.standard_title, "as_of": r.as_of,
                                 "paragraphs": 0})
        a["paragraphs"] += 1
    return sorted(agg.values(), key=lambda x: (x["gaap"], x["standard_no"]))
