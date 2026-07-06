import argparse, json, os
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

def ingest_gaap(gaap, download_dir, skip_nos=()):
    """`skip_nos`: standard `no` values to skip entirely (no extract/chunk
    attempted) -- for registry entries that are catalogued (per 정공법: no
    arbitrary trimming from the registry itself) but are not citable
    regulatory paragraph text at all, e.g. K-GAAP's "영문양식" item, which is
    a blank English-language financial-statement FORM exhibit (confirmed via
    hwp5txt: placeholder tables, no 문단-numbered content whatsoever) rather
    than standard body/guidance text. This is an explicit, documented
    editorial exclusion decided by the caller, not something the leak/shadow
    gates below are relied on to catch (a paragraph-less form would sail
    through both gates and still be wrong to ship)."""
    src = get_source(gaap)
    records = []
    for std in src["standards"]:
        if std["no"] in skip_nos:
            print(f"  {gaap} {std['no']}: SKIPPED ({std['title']}) -- not citable paragraph text")
            continue
        # Per-standard format override (defaults to the GAAP-level format):
        # K-GAAP's "영문양식" item is the only registry entry so far with no
        # PDF attachment at all (HWP-only) -- see tools/ingest/sources.py.
        # Every existing K-IFRS entry has no "format" key, so this is a
        # no-op there (falls through to src["format"] == "pdf" unchanged).
        fmt = std.get("format", src["format"])
        path = download_path(download_dir, gaap, std["no"], fmt)
        if not os.path.exists(path):
            continue
        pages = extract(path, fmt)
        # Per-standard as_of overrides a GAAP-level default (falls back to ""
        # if neither is set) -- K-IFRS has neither today (unaffected, "" as
        # before); K-GAAP sets a GAAP-level default (see sources.py) since
        # its listing page carries no single canonical vintage statement the
        # way K-IFRS's own page does.
        as_of = std.get("as_of", src.get("as_of", ""))
        recs = chunk_pages(pages, gaap, std["no"], std["title"], src["lang"],
                           std.get("url", ""), as_of, tier=std.get("tier_hint", "본문"))
        # Coverage is measured over the RETAINED region (본문+적용지침) only:
        # 결론도출근거/적용사례/frontmatter are intentionally dropped (corpus
        # depth = body + application guidance), so checking against the FULL
        # raw extraction would fail correct output. Dropped byte counts are
        # returned in info for logging rather than silently discarded.
        # `gaap=gaap` routes K-GAAP through its own frontmatter/section logic
        # (see fidelity.retained_text_for_coverage); every other gaap is
        # unaffected (default arg reproduces the original K-IFRS-only path).
        _cov, info = assert_retained_coverage("\n".join(p.text for p in pages), recs, gaap=gaap)
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

def write_without_vectors(gaap, recs, corpus_dir):
    """Write ONE gaap's corpus/<slug>.jsonl.zst and MERGE its manifest entry
    into any existing corpus/manifest.json (creating one if absent), leaving
    every other GAAP's .jsonl.zst and corpus/vectors/ completely untouched.

    Unlike pack() (a whole-corpus rebuild: replaces manifest.json wholesale
    with only the gaaps passed to it, and always rebuilds vectors from
    scratch over every record passed in), this is for incrementally adding
    ONE more GAAP's corpus to an existing multi-GAAP build without forcing a
    combined-embedding rebuild each time a new source GAAP is ingested --
    e.g. K-IFRS is already packed+embedded and K-GAAP is being ingested as a
    separate, later step; embedding is a combined step done once at the end
    across every GAAP's corpus."""
    from gaap_standards_mcp.corpus import write_jsonl_zst
    os.makedirs(corpus_dir, exist_ok=True)
    write_jsonl_zst(recs, os.path.join(str(corpus_dir), f"{_SLUG[gaap]}.jsonl.zst"))
    manifest_path = os.path.join(str(corpus_dir), "manifest.json")
    manifest = {"gaaps": {}}
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
        manifest.setdefault("gaaps", {})
    stds = sorted({r.standard_no for r in recs})
    manifest["gaaps"][gaap] = {"standards": stds, "paragraphs": len(recs),
                               "as_of": recs[0].as_of if recs else ""}
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return manifest

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gaap", required=True)
    ap.add_argument("--download-dir", default="downloads")
    ap.add_argument("--corpus-dir", default="corpus")
    ap.add_argument("--no-vectors", action="store_true",
                     help="write only this GAAP's jsonl.zst + merge manifest.json "
                          "instead of calling pack() (which replaces manifest.json "
                          "wholesale and always rebuilds corpus/vectors/) -- for "
                          "staged multi-GAAP builds where embedding happens once, "
                          "combined, at the end")
    a = ap.parse_args()
    recs = ingest_gaap(a.gaap, a.download_dir)
    if a.no_vectors:
        write_without_vectors(a.gaap, recs, a.corpus_dir)
    else:
        pack({a.gaap: recs}, a.corpus_dir)
    print(f"{a.gaap}: {len(recs)} paragraphs")

if __name__ == "__main__":
    main()
