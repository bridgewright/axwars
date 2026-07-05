import argparse, os
from .sources import get_source
from .extract import extract
from .chunk import chunk_pages
from .fidelity import assert_coverage
from .pack import pack

def ingest_gaap(gaap, download_dir):
    src = get_source(gaap)
    records = []
    for std in src["standards"]:
        path = os.path.join(download_dir, f"{gaap}_{std['no']}.{src['format']}")
        if not os.path.exists(path):
            continue
        pages = extract(path, src["format"])
        recs = chunk_pages(pages, gaap, std["no"], std["title"], src["lang"],
                           std["url"], std.get("as_of", ""), tier=std.get("tier_hint", "본문"))
        assert_coverage("\n".join(p.text for p in pages), recs)
        records += recs
    return records

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gaap", required=True)
    ap.add_argument("--download-dir", default="downloads")
    ap.add_argument("--corpus-dir", default="corpus")
    a = ap.parse_args()
    recs = ingest_gaap(a.gaap, a.download_dir)
    pack({a.gaap: recs}, a.corpus_dir)
    print(f"{a.gaap}: {len(recs)} paragraphs")

if __name__ == "__main__":
    main()
