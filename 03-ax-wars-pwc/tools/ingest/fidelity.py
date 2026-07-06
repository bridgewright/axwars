import re
import statistics
from collections import defaultdict
from dataclasses import replace

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

def retained_text_for_coverage(raw_text):
    """Reconstruct the RETAINED region (본문+적용지침, after intentionally
    dropping frontmatter/결론도출근거/적용사례) exactly as chunk_pages sees
    it, so it can be used as the coverage baseline instead of the full raw
    extraction. Returns (retained_text, drop_info) where drop_info logs the
    dropped byte counts by category instead of silently discarding them.

    Import is local to avoid a module-load cycle (chunk.py imports this
    module for flag_oversized_chunks)."""
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

def assert_retained_coverage(raw_text, records, min_cov=0.995):
    """Coverage check scoped to the RETAINED region (본문+적용지침) instead of
    the full raw extraction, so intentionally dropping frontmatter/BC/IE never
    counts against fidelity. Returns (coverage, drop_info); raises
    FidelityError if the retained region itself is not faithfully covered by
    the records (a real extraction/chunking loss, not an intentional drop)."""
    retained, drop_info = retained_text_for_coverage(raw_text)
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
