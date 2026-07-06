import re
import statistics
from collections import defaultdict
from dataclasses import replace

# Reused, not redefined: these are the EXACT structural patterns
# strip_frontmatter/split_sections already use to decide what counts as
# boilerplate/BC/IE/board-resolution (see tools/ingest/segment.py). Importing
# them instead of writing new lookalike regexes here means assert_no_leak can
# never quietly drift out of sync with what segmentation itself excludes.
# Verified no import cycle: segment.py has no dependency on fidelity.py or
# chunk.py, so this (like chunk.py's own top-level `from .segment import
# ...`) is safe as a module-level import.
from .segment import (_BC_DIVIDER_RE, _IE_DIVIDER_RE, _BOARD_RESOLUTION_RE, _COPYRIGHT_TAIL_RE,
                       _KGAAP_DISSENT_DIVIDER_RE)

class FidelityError(Exception):
    pass

_WS = re.compile(r"\s+")

def _canon(s):
    return _WS.sub("", s)

def roundtrip_coverage(raw_text, records):
    raw = _canon(raw_text)
    if not raw:
        return 1.0
    joined = _canon("".join(r.text for r in records))
    # 멀티셋 교집합 근사: 재결합 길이 / 원문 길이(정규화 공백 제거)
    return min(len(joined), len(raw)) / len(raw)

def detect_mojibake(text):
    return "�" in text or text.count("�") > 0

def detect_empty_pages(pages):
    return [p.page_no for p in pages if not p.text.strip()]

def assert_coverage(raw_text, records, min_cov=0.995):
    """Coverage against the FULL raw extraction. Only meaningful when nothing
    was intentionally dropped (e.g. plain text with no BC/IE/frontmatter) --
    for real K-IFRS documents where 결론도출근거/적용사례/frontmatter are
    deliberately excluded from the corpus, use assert_retained_coverage
    instead, or this will fail on correct output."""
    cov = roundtrip_coverage(raw_text, records)
    if cov < min_cov:
        raise FidelityError(f"coverage {cov:.4f} < {min_cov}")

def dual_extract_diff(a, b):
    ca, cb = _canon(a), _canon(b)
    if not ca and not cb:
        return 0.0
    import difflib
    return 1.0 - difflib.SequenceMatcher(None, ca, cb).ratio()

def retained_text_for_coverage(raw_text, gaap="K-IFRS"):
    """Reconstruct the RETAINED region (본문+적용지침, after intentionally
    dropping frontmatter/결론도출근거/적용사례) exactly as chunk_pages sees
    it, so it can be used as the coverage baseline instead of the full raw
    extraction. Returns (retained_text, drop_info) where drop_info logs the
    dropped byte counts by category instead of silently discarding them.

    `gaap="K-GAAP"` routes through strip_frontmatter_kgaap/split_sections_kgaap
    instead (K-GAAP's document structure is unrelated to K-IFRS's -- see
    tools/ingest/segment.py's K-GAAP module comment); every other gaap keeps
    the original K-IFRS-shaped path unchanged.

    Import is local to avoid a module-load cycle (chunk.py imports this
    module for flag_oversized_chunks)."""
    if gaap == "K-GAAP":
        from .segment import strip_frontmatter_kgaap, split_sections_kgaap
        kept, frontmatter_info = strip_frontmatter_kgaap(raw_text)
        sections = split_sections_kgaap(kept)
    else:
        from .segment import strip_frontmatter, split_sections
        kept, frontmatter_info = strip_frontmatter(raw_text)
        sections = split_sections(kept)
    retained = sections.get("본문", "") + sections.get("적용지침", "")
    drop_info = {
        "total_chars": len(raw_text),
        "frontmatter_chars": frontmatter_info["chars_dropped"],
        "결론도출근거_chars": len(sections.get("결론도출근거", "")),
        "적용사례_chars": len(sections.get("적용사례", "")),
        "retained_chars": len(retained),
    }
    drop_info["dropped_chars"] = drop_info["total_chars"] - drop_info["retained_chars"]
    return retained, drop_info

def assert_retained_coverage(raw_text, records, min_cov=0.995, gaap="K-IFRS"):
    """Coverage check scoped to the RETAINED region (본문+적용지침) instead of
    the full raw extraction, so intentionally dropping frontmatter/BC/IE never
    counts against fidelity. Returns (coverage, drop_info); raises
    FidelityError if the retained region itself is not faithfully covered by
    the records (a real extraction/chunking loss, not an intentional drop).

    `gaap` is forwarded to retained_text_for_coverage (see there); it is
    keyword-only in practice (placed after min_cov) so every existing
    2-positional-arg caller keeps working unchanged."""
    retained, drop_info = retained_text_for_coverage(raw_text, gaap)
    cov = roundtrip_coverage(retained, records)
    if cov < min_cov:
        raise FidelityError(f"retained coverage {cov:.4f} < {min_cov} "
                             f"(dropped {drop_info['dropped_chars']} of "
                             f"{drop_info['total_chars']} chars as frontmatter/BC/IE)")
    return cov, drop_info

def flag_oversized_chunks(records, factor=6, min_abs_chars=6000):
    """Mark (extract_flag=True) any chunk whose length is a wild outlier
    relative to its section's (gaap, standard_no, tier) median -- catches a
    missed paragraph boundary (e.g. a letter-prefixed appendix paragraph
    invisible to a digit-only regex swallowing everything after it into one
    giant chunk; the diagnosed "52,102-char paragraph" bug). A record is only
    flagged if it exceeds BOTH `factor` times its group's median length AND
    the absolute floor `min_abs_chars`, so a handful of naturally short
    paragraphs (small median) don't make one ordinary-length paragraph look
    like an outlier. Order of `records` is preserved."""
    groups = defaultdict(list)
    for r in records:
        groups[(r.gaap, r.standard_no, r.tier)].append(len(r.text))
    thresholds = {}
    for key, lengths in groups.items():
        med = statistics.median(lengths)
        thresholds[key] = max(factor * med, min_abs_chars)
    out = []
    for r in records:
        threshold = thresholds[(r.gaap, r.standard_no, r.tier)]
        out.append(replace(r, extract_flag=True) if len(r.text) > threshold else r)
    return out


# --- Leak gate ---------------------------------------------------------
#
# Deliberately NOT a bare-keyword search for "저작권"/"결론도출근거"/
# "적용사례" as free substrings anywhere in a record's text. Confirmed
# empirically -- by running the CURRENT (fixed) chunk_pages() across all 63
# real downloaded K-IFRS PDFs -- that every one of those three bare words
# legitimately appears inside real, correctly-retained 본문/적용지침 prose:
#   * "저작권" -- 1038/1115/1116/2032 all legitimately discuss "저작권"
#     (copyright) as a real-world example of an intangible asset/license;
#     it is never used as a stand-alone signature here.
#   * "결론도출근거" -- routinely appears as an inline footnote citation
#     ("IAS 1의 결론도출근거 문단 BC30F를 참조") inside real 본문
#     (개념체계, 번역서-중요성판단, ...), not just as the name of the section
#     it labels.
#   * "적용사례" -- routinely appears as an inline cross-reference
#     ("적용사례의 사례 5에서는 ... 예시한다", literally "Illustrative
#     Example 5 illustrates ...") inside real 본문/적용지침 (1032, 1036,
#     ...), meaning "an application/illustrative example", not a leak of the
#     Illustrative-Examples section itself.
# A bare-word gate on any of the three would misfire on multiple CLEAN,
# already-correct standards. Instead, every check below anchors on a shape
# that is unambiguous: the copyright block's own fixed English boilerplate,
# an entire standalone BC/IE divider LINE (never how a real inline citation
# is phrased -- confirmed none of the real citations above sit alone on their
# own line), the board-resolution log's specific suffix pattern (reused
# verbatim from segment.py), and the TOC heading itself (confirmed 0
# occurrences, false or true, anywhere in the current 63-standard output).
_WESTFERRY_RE = re.compile(r"Westferry")
_COPYRIGHT_NOTICE_HEADING_RE = re.compile(r"COPYRIGHT NOTICE")
_TOC_HEADING_RE = re.compile(r"목\s{0,2}차")

# paragraph_no is a STRUCTURAL field, not free text, so this is safe as a
# plain prefix check: chunk.py's own paragraph regexes already refuse to
# ever assign a BC/IE-prefixed paragraph_no to a 본문/적용지침 record
# (LETTER_PARA_RE excludes them by name; DIGIT_PARA_RE cannot match letters
# first at all) -- checked anyway as defense in depth, per the task spec,
# in case that invariant is ever weakened.
_LEAK_PARAGRAPH_NO_RE = re.compile(r"^(BC|IE)\d")

# K-GAAP-specific dropped-section paragraph-number prefixes: "결<N>.<M>"
# (결론도출근거), "사례<N>" (적용사례), "소<N>" (소수의견 -- see
# tools/ingest/segment.py's K-GAAP module comment). Defense in depth, per the
# task spec, mirroring _LEAK_PARAGRAPH_NO_RE's role for K-IFRS's own BC/IE
# prefixes: chunk.py's own K-GAAP paragraph regexes (KGAAP_BODY_PARA_RE/
# KGAAP_GUIDANCE_PARA_RE) only ever run against the 본문/적용지침 region
# text, which split_sections_kgaap has already excluded 결론도출근거/
# 적용사례/소수의견 text from -- this should be structurally impossible,
# checked anyway in case that invariant is ever weakened. Safe against
# K-IFRS/US-GAAP/CAS/VAS records too: none of those GAAPs' paragraph_no
# values are ever prefixed with 결/사례/소 (Korean characters K-IFRS's own
# numbering never uses).
_KGAAP_LEAK_PARAGRAPH_NO_RE = re.compile(r"^(결\d|사례\d|소\d)")

# name -> (matcher, where) -- "text" matchers run against record.text,
# "paragraph_no" matchers run against record.paragraph_no.
_LEAK_SIGNATURES = (
    ("westferry_address", _WESTFERRY_RE, "text"),
    ("copyright_notice_heading", _COPYRIGHT_NOTICE_HEADING_RE, "text"),
    ("copyright_tail_sentence", _COPYRIGHT_TAIL_RE, "text"),
    ("toc_heading", _TOC_HEADING_RE, "text"),
    ("board_resolution", _BOARD_RESOLUTION_RE, "text"),
    ("bc_divider", _BC_DIVIDER_RE, "text"),
    ("ie_divider", _IE_DIVIDER_RE, "text"),
    ("paragraph_no_bc_ie", _LEAK_PARAGRAPH_NO_RE, "paragraph_no"),
    # K-GAAP-specific (see above) -- inert no-ops for every other GAAP.
    ("kgaap_dissent_divider", _KGAAP_DISSENT_DIVIDER_RE, "text"),
    ("paragraph_no_kgaap_dropped", _KGAAP_LEAK_PARAGRAPH_NO_RE, "paragraph_no"),
)


def detect_leaks(records):
    """Non-raising counterpart to assert_no_leak: return a list of
    (record, signature_name) for every RETAINED record that still carries a
    BC/IE/board-resolution/TOC/copyright-boilerplate signature. Empty list
    means clean. A record is reported at most once (first signature hit),
    so the count below equals the number of BAD records, not the number of
    signature hits."""
    leaks = []
    for r in records:
        for name, pattern, where in _LEAK_SIGNATURES:
            haystack = r.paragraph_no if where == "paragraph_no" else r.text
            if pattern.search(haystack or ""):
                leaks.append((r, name))
                break
    return leaks


def assert_no_leak(records):
    """HARD gate: raise FidelityError if any RETAINED record (chunk_pages()
    output -- 본문/적용지침 only, BC/IE/frontmatter already meant to be
    excluded) still carries a leak signature. Must be 0 for a clean
    standard. Returns the (empty) leak list on success so a caller can log
    "0 leaks" without a second call."""
    leaks = detect_leaks(records)
    if leaks:
        detail = "; ".join(f"{r.id} [{sig}]" for r, sig in leaks[:10])
        more = f" ... and {len(leaks) - 10} more" if len(leaks) > 10 else ""
        raise FidelityError(f"{len(leaks)} leaked record(s) found: {detail}{more}")
    return leaks


# --- Shadow gate ---------------------------------------------------------

# A "shadow" is only pruned when the gap between it and the real paragraph is
# large and unambiguous: the shadow itself is tiny (<= _SHADOW_MAX_CHARS --
# too small to carry any independently citable content: a bare TOC-preview
# paragraph-number/range line like 해석서 2010's real "한1.1\n1~2", or a
# content-free repeated-number byproduct of a jumbled PDF table like 1019's
# real bare "89"/"108"/"119"), the real paragraph is substantial
# (>= _SHADOW_MIN_REAL_CHARS), and it dwarfs the shadow by at least
# _SHADOW_MIN_RATIO. Confirmed against the real (pre-fix) corpus: every one
# of 2010/2025/2029's genuine TOC-shadow pairs clears this gap by 14x-290x;
# 2029's own 한7.1 pair (425 vs 522 chars -- two substantial, comparably-
# sized fragments, NOT a shadow) sits at a 1.2x ratio and is correctly left
# untouched. Groups of merely similar-sized fragments (e.g. several genuine
# rows of a jumbled numeric table) are never pruned -- there is no reliable
# content-only way to tell which of two substantial fragments is "the real
# one", so this gate does not guess.
#
# This is a separate, additive, opt-in cleanup step over chunk_pages()
# OUTPUT -- it does not change chunk_pages()/segment.py themselves, so it
# cannot regress their existing, separately-tested behavior (e.g. chunk.py's
# own test_chunk_pages_suffixes_repeated_paragraph_numbers_within_one_tier,
# which asserts chunk_pages() alone keeps every repeated-number occurrence
# with a unique id -- unaffected, since that test never calls detect_shadows).
_SHADOW_MAX_CHARS = 20
_SHADOW_MIN_REAL_CHARS = 30
_SHADOW_MIN_RATIO = 5


def detect_shadows(records, max_shadow_chars=_SHADOW_MAX_CHARS,
                    min_real_chars=_SHADOW_MIN_REAL_CHARS, min_ratio=_SHADOW_MIN_RATIO):
    """Find TOC- (or jumbled-table-) derived short fragments shadowing a
    real, substantially longer paragraph at the same canonical (gaap,
    standard_no, tier, paragraph_no), and drop the bogus fragment(s),
    keeping the real one. Returns (clean_records, removed_count)."""
    groups = defaultdict(list)
    for i, r in enumerate(records):
        groups[(r.gaap, r.standard_no, r.tier, r.paragraph_no)].append(i)

    drop = set()
    for idxs in groups.values():
        if len(idxs) < 2:
            continue
        longest = max(len(records[i].text) for i in idxs)
        if longest < min_real_chars:
            continue
        for i in idxs:
            n = len(records[i].text)
            if n <= max_shadow_chars and longest >= min_ratio * n:
                drop.add(i)

    clean = [r for i, r in enumerate(records) if i not in drop]
    return clean, len(drop)
