import argparse, os
from .sources import get_source
from .extract import extract
from .chunk import chunk_pages, _SLUG
from .fidelity import assert_retained_coverage, assert_no_leak, detect_shadows
from .pack import pack

def download_path(download_dir, gaap, standard_no, fmt):
    """Resolve the on-disk path for one registry standard's download.

    BUG (fixed here): this used to build `f"{gaap}_{std['no']}.{fmt}"`, e.g.
    "K-IFRS_1001.pdf" -- but downloaded files are saved under the same
    lowercase GAAP slug chunk.py/pack.py already use for record ids (e.g.
    "K-IFRS" -> "kifrs"), never under the registry's own display key. The
    real file is "kifrs_1001.pdf", so the old path never existed on disk and
    a real run silently found 0 files. Reusing chunk.py's `_SLUG` (rather
    than a third copy of the same mapping) keeps this in sync with however
    that convention is defined elsewhere. Confirmed this resolves all 63
    K-IFRS registry entries against downloads/ with 0 missing, including the
    3 non-numbered items (e.g. "kifrs_개념체계.pdf") whose `no` is a
    descriptive slug instead of a 제NNNN호 number.
    """
    return os.path.join(download_dir, f"{_SLUG[gaap]}_{standard_no}.{fmt}")

def ingest_gaap(gaap, download_dir):
    src = get_source(gaap)
    records = []
    for std in src["standards"]:
        path = download_path(download_dir, gaap, std["no"], src["format"])
        if not os.path.exists(path):
            continue
        pages = extract(path, src["format"])
        recs = chunk_pages(pages, gaap, std["no"], std["title"], src["lang"],
                           std.get("url", ""), std.get("as_of", ""), tier=std.get("tier_hint", "본문"))
        # Coverage is measured over the RETAINED region (본문+적용지침) only:
        # 결론도출근거/적용사례/frontmatter are intentionally dropped (corpus
        # depth = body + application guidance), so checking against the FULL
        # raw extraction would fail correct output. Dropped byte counts are
        # returned in info for logging rather than silently discarded.
        _cov, info = assert_retained_coverage("\n".join(p.text for p in pages), recs)
        # Shadow cleanup BEFORE the leak gate: a TOC-derived short fragment
        # shadowing a real longer paragraph (see fidelity.detect_shadows) is
        # noise to prune, not itself a leak signature -- pruning first means
        # the leak gate only ever has to judge genuine records.
        recs, shadow_removed = detect_shadows(recs)
        # HARD gate: raises FidelityError (halting ingestion for this GAAP)
        # if any retained record still carries a BC/IE/board-resolution/TOC/
        # copyright-boilerplate signature. Deliberately fail-fast rather than
        # silently packing bad data -- see tools/ingest/fidelity.py.
        assert_no_leak(recs)
        print(f"  {gaap} {std['no']}: retained={info['retained_chars']} "
              f"dropped={info['dropped_chars']} of {info['total_chars']} chars "
              f"(frontmatter={info['frontmatter_chars']}, "
              f"결론도출근거={info['결론도출근거_chars']}, 적용사례={info['적용사례_chars']}, "
              f"shadows_removed={shadow_removed})")
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
