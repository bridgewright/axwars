import re
from gaap_standards_mcp.schema import Record
from gaap_standards_mcp.normalize import normalize_text
from .segment import strip_frontmatter, split_sections
from .fidelity import flag_oversized_chunks

# 본문: digit paragraph numbers -- "1", "22", "5.5.1", "40G" -- plus the
# Korea-only "한2.1" insert-paragraph convention KASB adds into the IFRS
# translation (e.g. "한2.1", "한40.1"). The decimal part is mandatory for the
# "한" form so a footnote marker like "한1)" (no ".N", never followed by a
# paragraph body) is never mistaken for a paragraph: real "한" paragraphs are
# always "한<N>.<M>" in every sample seen, while KASB's own footnote marker
# convention is "한<N>)" with a closing paren, not a period.
#
# Trailing `\s+` is MANDATORY (not `\s*`): a real paragraph marker in PDF text
# is always either alone on its own line (followed by a newline) or same-line
# with a real space before the body text. PDF is heavily line-wrapped (one
# text line per *visual* line, not per paragraph), so a wrapped continuation
# line can legitimately start with a bare number that is NOT a paragraph
# marker -- e.g. a transition-paragraph sentence wrapping onto a new line
# right before "2018년 12월에 공표한...", or a stray table/diagram fragment
# like "1037" in a jumbled appendix flowchart. Requiring real trailing
# whitespace is what keeps those from being mistaken for a new paragraph
# (confirmed empirically against all 3 real standards: relaxing this to `\s*`
# reproduced exactly this failure mode on 1019 PDF). HWP's dropped space after
# the number ("1이 기준서는..." instead of "1 이 기준서는...") is handled
# separately by normalize_missing_space(), applied to each region's text
# BEFORE this pattern ever sees it -- so by the time it runs, both formats
# look the same (number, then real whitespace, then body).
#
# Trailing letters allow up to two (`[A-Z]{0,2}`, not `[A-Z]?`): amendments
# inserted after a lettered paragraph stack further letters, e.g. 1116's
# COVID rent-concession amendments produced "C20BA", "C20BB", "C20BC" as
# three distinct paragraphs (confirmed in the real 1116 PDF/HWP) on top of
# the plain single-letter "100~102A"/"40G" style seen elsewhere.
DIGIT_PARA_RE = re.compile(r"(?m)^\s*(한\d+(?:\.\d+)+|\d+[A-Z]{0,2}(?:\.\d+)*)\s+")

# 적용지침 (appendices): letter-prefixed numbers -- "A1", "B1", "C1", "C1A",
# "C20BA", and (1032/1039/2112/2116's "적용지침" appendices, titled "AG..."
# for Application Guidance) the TWO-letter "AG1"..."AG99" form. Up to two
# leading letters are allowed, but "BC1"/"IE1" (the two-letter 결론도출근거/
# 적용사례 prefixes) are explicitly excluded by name via lookahead so a leaked
# BC/IE paragraph is never mistaken for appendix content even if a section
# boundary were ever misdetected -- defense in depth on top of split_sections
# already excluding them. Confirmed against all 63 real standards: "AG" is the
# only two-letter appendix prefix in use; no three-letter prefix was ever
# observed, so the cap stays at two, not an unbounded `[A-Z]+`.
LETTER_PARA_RE = re.compile(r"(?m)^\s*((?!BC\d)(?!IE\d)[A-Z]{1,2}\d+[A-Z]{0,2}(?:\.\d+)*)\s+")

DEFAULT_PARA_RE = DIGIT_PARA_RE  # backward-compatible alias (original 본문-only regex)

_SLUG = {"K-IFRS": "kifrs", "K-GAAP": "kgaap", "US-GAAP": "usgaap", "CAS": "cas", "VAS": "vas"}

# Matches a paragraph-number marker sitting at the start of a block (start of
# the region's text, or right after a blank line) that is NOT followed by any
# whitespace at all -- i.e. exactly HWP's missing-space bug. Only fires at a
# block start (never mid-paragraph, never at a plain PDF line-wrap), and only
# when whitespace is well and truly absent (a lookahead, so an already-correct
# "22 text" or "22\ntext" is left untouched) -- so it is safe to run
# unconditionally on both PDF- and HWP-sourced region text.
#
# The integer part is capped at 3 digits (\d{1,3}, not \d+) because HWP can
# fuse the paragraph number directly onto body text that ALSO starts with
# digits, with no separator anywhere to find -- confirmed in 1019 HWP, whose
# transition-paragraph "179" runs straight into the calendar year it
# discusses: "1792018년 12월에 공표한...". An unbounded \d+ would greedily
# swallow "1792018" as one number; real paragraph numbers in these standards
# never reach 4 digits (K-IFRS standards top out at a few hundred paragraphs
# even in 결론도출근거, let alone 본문/적용지침), so capping at 3 correctly
# splits "179" from "2018" while still matching every real paragraph number
# observed (max 3 digits, e.g. "179").
# The whole alternation is wrapped in an atomic group `(?>...)`: without it,
# Python's greedy backtracking defeats the point -- e.g. matching "22 리스..."
# would first try the full "22", find the trailing lookahead fails (a real
# space already follows, so no fix is needed), and then, wrongly, backtrack
# down to matching just "2" so the lookahead can succeed against the *second*
# "2" instead. An atomic group forbids that backtrack: once the alternation
# commits to the longest possible number, it either satisfies the lookahead
# as-is or the whole match attempt fails at this position (which is exactly
# what "no fix needed here" should mean).
_LEAD_NUM_RE = re.compile(
    r"(\A|\n\n+)([ \t]*)((?>한\d{1,3}(?:\.\d+)+|(?!BC\d)(?!IE\d)[A-Z]{1,2}\d{1,3}[A-Z]{0,2}(?:\.\d+)*|\d{1,3}[A-Z]{0,2}(?:\.\d+)*))(?=\S)"
)


def normalize_missing_space(text):
    """Insert the space HWP sometimes drops after a leading paragraph number
    at a block start (e.g. "1이 기준서는..." -> "1 이 기준서는..."). Must run
    AFTER frontmatter/section splitting so it only ever sees already-isolated
    body text, never boilerplate."""
    return _LEAD_NUM_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)} ", text)


class ChunkingError(Exception):
    """Raised when chunking cannot guarantee the invariants callers rely on
    (currently: globally-unique record ids within one chunk_pages() call)."""


def chunk_pages(pages, gaap, standard_no, standard_title, lang, source_url, as_of,
                tier="본문", para_pattern=None):
    """strip_frontmatter -> split_sections -> chunk each KEPT section with a
    section-appropriate paragraph regex -> Record list.

    결론도출근거 (Basis for Conclusions, "BC...") and 적용사례*실무적용지침
    (Illustrative Examples, "IE...") are intentionally dropped: both say of
    themselves that they do not form part of the standard. 본문 and 적용지침
    (부록 A/B/C: defined terms, application guidance, effective date &
    transition) are retained -- corpus depth per the approved spec.

    `tier` is kept for backward compatibility: when the document shows no
    recognizable section structure at all (no 부록/결론도출근거/적용사례
    heading found -- e.g. a small plain-text fixture with only digit
    paragraphs), the caller's `tier` is used for that lone region instead of
    hardcoding "본문", exactly matching the pre-existing behavior of simple
    callers. Whenever real structure IS found, tier is derived per-region
    (본문 vs 적용지침), since a single caller-supplied tier can no longer
    describe a whole multi-section document correctly.

    `para_pattern` overrides the 본문 region's paragraph regex only (적용지침
    always uses the letter-prefixed pattern -- there is no legacy caller that
    ever needed to override that).
    """
    full = "\n".join(p.text for p in pages)
    kept, _dropped_info = strip_frontmatter(full)
    sections = split_sections(kept)
    slug = _SLUG[gaap]

    has_structure = any(sections[k].strip() for k in ("적용지침", "결론도출근거", "적용사례"))
    body_tier = "본문" if has_structure else tier
    body_pattern = para_pattern if para_pattern is not None else DIGIT_PARA_RE

    recs = []
    recs += _chunk_region(sections["본문"], body_pattern, slug, gaap, standard_no,
                          standard_title, lang, body_tier, source_url, as_of)
    recs += _chunk_region(sections["적용지침"], LETTER_PARA_RE, slug, gaap, standard_no,
                          standard_title, lang, "적용지침", source_url, as_of)

    recs = flag_oversized_chunks(recs)

    ids = [r.id for r in recs]
    if len(set(ids)) != len(ids):
        raise ChunkingError(f"duplicate record ids produced for {gaap} {standard_no}: "
                             f"{[i for i in ids if ids.count(i) > 1]}")
    return recs


def _chunk_region(text, pattern, slug, gaap, standard_no, standard_title, lang, tier,
                   source_url, as_of):
    if not text.strip():
        return []
    text = normalize_missing_space(text)
    marks = list(pattern.finditer(text))
    pieces = []
    if not marks:
        stripped = text.strip()
        if stripped:
            pieces.append(("0", stripped))
    else:
        if marks[0].start() > 0:
            lead = text[:marks[0].start()].strip()
            if lead:
                pieces.append(("0", lead))
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            pieces.append((m.group(1), text[m.start():end].strip()))

    recs = []
    seen = {}
    for para_no, chunk_text in pieces:
        base_id = f"{slug}:{standard_no}:{tier}:{para_no}"
        n = seen.get(base_id, 0)
        seen[base_id] = n + 1
        rec_id = base_id if n == 0 else f"{base_id}#{n + 1}"
        recs.append(_mk(rec_id, gaap, standard_no, standard_title, para_no, chunk_text,
                        lang, tier, source_url, as_of))
    return recs


def _mk(rec_id, gaap, std, title, para, text, lang, tier, url, as_of):
    return Record(id=rec_id, gaap=gaap, standard_no=std, standard_title=title,
                  paragraph_no=para, heading="", text=text, text_norm=normalize_text(text),
                  lang=lang, tier=tier, source_url=url, as_of=as_of, extract_flag=False)
