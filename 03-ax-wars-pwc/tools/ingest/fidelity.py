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
                       _KGAAP_DISSENT_DIVIDER_RE, _CAS_FOOTER_RE, _CAS_MEMO_RE,
                       _CAS_XMU_SOURCE_URL_ROW_RE, _VAS_SITE_CHROME_RE,
                       _VAS_DECISION_PREAMBLE_RE, _VAS_FORM_TEMPLATE_RE)

class FidelityError(Exception):
    pass

_WS = re.compile(r"\s+")

def _canon(s):
    return _WS.sub("", s)

def roundtrip_coverage(raw_text, records):
    raw = _canon(raw_text)
    if not raw:
        return 1.0
    # text + heading 합산: 후행 헤딩은 text에서 heading 필드로 재배치될 뿐
    # 손실이 아니므로 coverage 회계에 함께 포함한다(2026-07-08 경계 정합성).
    joined = _canon("".join((r.text or "") + (r.heading or "") for r in records))
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
    tools/ingest/segment.py's K-GAAP module comment); `gaap="CAS"` likewise
    routes through strip_frontmatter_cas/split_sections_cas (see that
    module's CAS comment -- split_sections_cas always returns 본문=full text
    and the other three regions empty, so the "retained" baseline here is
    just the frontmatter-stripped text in full); `gaap="VAS"` routes through
    strip_frontmatter_vas/split_sections_vas (see that module's VAS comment --
    VAS 24's own excluded Phụ lục 1/2 form templates land in the "적용사례"
    drop-bucket here, same labeling-convenience-only reuse K-GAAP's own
    소수의견 already established for "결론도출근거"); every other gaap keeps
    the original K-IFRS-shaped path unchanged.

    Import is local to avoid a module-load cycle (chunk.py imports this
    module for flag_oversized_chunks)."""
    if gaap == "K-GAAP":
        from .segment import strip_frontmatter_kgaap, split_sections_kgaap
        kept, frontmatter_info = strip_frontmatter_kgaap(raw_text)
        sections = split_sections_kgaap(kept)
    elif gaap == "CAS":
        from .segment import strip_frontmatter_cas, split_sections_cas
        kept, frontmatter_info = strip_frontmatter_cas(raw_text)
        sections = split_sections_cas(kept)
    elif gaap == "VAS":
        from .segment import strip_frontmatter_vas, split_sections_vas
        kept, frontmatter_info = strip_frontmatter_vas(raw_text)
        sections = split_sections_vas(kept)
    else:
        from .segment import strip_frontmatter, split_sections
        kept, frontmatter_info = strip_frontmatter(raw_text)
        sections = split_sections(kept)
    retained = sections.get("본문", "") + sections.get("적용지침", "")
    # 페이지 푸터('- 15 -')는 청커가 제거하므로 coverage baseline에서도 제거해
    # 정당 제거분이 fidelity에 불리하게 계산되지 않도록 맞춘다(chunk.py와 동일).
    from .chunk import strip_page_footers
    retained, _footer_chars = strip_page_footers(retained)
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

# CAS-specific (see tools/ingest/segment.py's CAS module comment): reused,
# not redefined, same "assert_no_leak can never drift out of sync with what
# segmentation itself excludes" rationale as every other import from
# segment.py above. Unlike K-IFRS/K-GAAP, CAS has no dropped-content bucket
# at all (응용指南/해석 are both KEPT, not dropped -- see the task spec), so
# there is no CAS paragraph_no-prefix signature to add here; only the three
# boilerplate shapes strip_frontmatter_cas is meant to have already removed
# -- the casc.org.cn trailing footer, the casc.org.cn transmittal-memo
# preamble, and cas.xmu.edu.cn's own "原文网址" metadata-table row -- need a
# leak signature, as a hard backstop in case that stripping ever misses.
# Inert no-ops for every other GAAP: none of these Chinese-language phrases
# can appear in Korean/English K-IFRS/K-GAAP text.
_CAS_LEAK_SIGNATURES = (
    ("cas_footer", _CAS_FOOTER_RE, "text"),
    ("cas_transmittal_memo", _CAS_MEMO_RE, "text"),
    ("cas_xmu_source_url_row", _CAS_XMU_SOURCE_URL_ROW_RE, "text"),
)

# VAS-specific (see tools/ingest/segment.py's VAS module comment): reused,
# not redefined, same discipline as every other GAAP-specific tuple above.
# strip_frontmatter_vas's own value==1 anchor already structurally excludes
# the KrestonVN site-chrome header and (VAS 29 only) the Decision-document
# preamble from any kept region, and split_sections_vas already routes VAS
# 24's own blank form-template appendices to the dropped "적용사례" bucket --
# these three signatures are a hard backstop for each, in case that
# structural exclusion is ever missed, not something normally expected to
# fire. Unlike K-IFRS/K-GAAP, VAS has no paragraph_no-prefix signature to add
# here: excluded content is dropped wholesale, before paragraph-chunking ever
# assigns it a paragraph_no, so there is no dropped-bucket prefix convention
# (like K-IFRS's "BC"/"IE" or K-GAAP's "결"/"사례"/"소") to check against.
# Inert no-ops for every other GAAP: none of this Vietnamese-language
# boilerplate can appear in Korean/English/Chinese K-IFRS/K-GAAP/CAS text.
_VAS_LEAK_SIGNATURES = (
    ("vas_site_chrome", _VAS_SITE_CHROME_RE, "text"),
    ("vas_decision_preamble", _VAS_DECISION_PREAMBLE_RE, "text"),
    ("vas_form_template", _VAS_FORM_TEMPLATE_RE, "text"),
)

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
) + _CAS_LEAK_SIGNATURES + _VAS_LEAK_SIGNATURES


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


# --- 경계 정합성 게이트 (2026-07-08) -----------------------------------------
# chunk.py의 새 청커가 페이지 푸터를 제거하고 후행 절/장 제목을 heading 필드로
# 재귀속하도록 바뀌었다. 아래 세 HARD 게이트는 그 결과가 실제로 clean한지
# 강제한다(leak/shadow가 못 잡던 '경계가 의미적으로 틀림' 차원). 패턴 정의는
# chunk.py 한 곳에만 두고 여기서는 함수-지역 import로 재사용(모듈 사이클 회피 —
# chunk.py가 이 모듈의 flag_oversized_chunks를 top-level import 하므로).

def assert_no_page_footer(records):
    """HARD 게이트: 레코드 text에 페이지 푸터(대시형 '- N -' 또는 마커가 아닌
    단독 페이지번호 줄)가 남아 있으면 실패."""
    from .chunk import _PAGE_FOOTER_RE, _BARE_PAGENUM_RE
    bad = []
    for r in records:
        lines = r.text.split("\n")
        if any(_PAGE_FOOTER_RE.match(l) for l in lines) or \
           any(_BARE_PAGENUM_RE.match(l.strip()) for l in lines[1:]):
            bad.append(r.id)
    if bad:
        raise FidelityError(f"{len(bad)} record(s) with page footer in text: {bad[:8]}")
    return bad


def assert_no_trailing_heading(records):
    """HARD 게이트: 레코드 text에서 (종결부호 가드까지 적용한) _split_piece가
    여전히 후행 헤딩을 뗄 수 있으면 실패 — 즉 문단 본문에 흡수된 절/장 제목이
    남아 있는 상태. 스트리퍼와 동일 로직이라 정상 청커 출력엔 걸리지 않고,
    청커를 거치지 않은/드리프트된 레코드만 잡는다(회귀 방지)."""
    from .chunk import _split_piece
    bad = [r.id for r in records if _split_piece(r.text, r.lang)[1]]
    if bad:
        raise FidelityError(f"{len(bad)} record(s) ending with a heading line: {bad[:8]}")
    return bad


def assert_no_orphan_heading(records):
    """HARD 게이트: text에 실질 내용줄이 하나도 없이 마커/번호/헤딩만인 레코드."""
    from .chunk import _is_content_line
    bad = [r.id for r in records
           if not any(_is_content_line(l, r.lang) for l in r.text.split("\n"))]
    if bad:
        raise FidelityError(f"{len(bad)} orphan-heading record(s): {bad[:8]}")
    return bad
