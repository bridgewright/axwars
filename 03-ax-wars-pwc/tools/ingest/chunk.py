import re
from gaap_standards_mcp.schema import Record
from gaap_standards_mcp.normalize import normalize_text
from .segment import (strip_frontmatter, split_sections, strip_frontmatter_kgaap, split_sections_kgaap,
                       strip_frontmatter_cas, split_sections_cas,
                       strip_frontmatter_vas, split_sections_vas,
                       VAS_PLAIN_PARA_RE, VAS_TABLE_PARA_RE, VAS_GUIDANCE_PARA_RE)
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

# K-GAAP 본문: "<장번호>.<문단번호>" (e.g. "13.1") for the 33 numbered 장, OR
# bare "N"/"N." (e.g. 재무회계개념체계's "2. 본개념체계는...", 시행일 및
# 경과규정's bare "1"/"2"/"3", 보험업회계처리준칙's legacy "1. 목적") for the
# non-chapter items -- see tools/ingest/segment.py's K-GAAP module comment.
# The trailing literal period is OPTIONAL (present for the bare-integer
# styles, absent for the chapter.paragraph style) and is discarded from the
# captured group either way, matching K-IFRS's own convention of paragraph_no
# never carrying trailing punctuation; trailing whitespace is MANDATORY for
# the same line-wrap-safety reason DIGIT_PARA_RE requires it (a wrapped
# continuation line can legitimately start with a bare number that is not a
# paragraph marker).
# A THIRD, letter-suffixed style is also 본문-tier despite sitting under a
# "부록A. 적용보충기준" / "부록 A. 적용보충기준"-labeled heading in some 장's
# PDFs (confirmed in real 제6장/제19장): "<장번호>.<LETTER><숫자>" optionally
# followed by a Korea-only insert-paragraph suffix "의<숫자>" (e.g. "6.A1",
# "6.A1의2", "6.A1의3", "19.A1", "19.A2"...). 문단 1.2 of 제1장 itself defines
# "적용보충기준" (Supplementary Application Standard) as part of 본문 --
# "본문(적용보충기준 포함)" -- NOT part of 부록's authoritative-guidance/
# rationale/example trio, so despite the "부록A." label these paragraphs are
# tagged tier="본문" here (they sit in the 본문 region's own text: neither
# split_sections_kgaap's 실무지침/결론도출근거/적용사례/소수의견 dividers nor
# a bare "부록" line are section boundaries -- see segment.py's module
# comment -- so this was purely a paragraph-REGEX gap, not a section-split
# one; confirmed empirically -- without this alternative, 제6장/제19장 each
# produced one wildly oversized 본문 chunk swallowing this whole sub-section
# into the preceding real paragraph). Tried FIRST in the alternation (more
# specific pattern before the more general bare-integer one) -- alternation
# is ordered specific-to-general, the standard-safe convention, though
# "6.102" would never reach this branch anyway since a digit (not a letter)
# follows its dot.
KGAAP_BODY_PARA_RE = re.compile(r"(?m)^\s*(\d+\.[A-Z]\d+(?:의\d+)?|\d+(?:\.\d+)*)\.?\s+")

# K-GAAP 실무지침 (Practical Guidance, the 적용지침-equivalent tier): always
# "실<장번호>.<문단번호>" in every sample seen (e.g. "실13.1" .. "실13.46") --
# decimal mandatory, mirroring how K-IFRS's own "한" (Korea-only insert
# paragraph) prefix requires at least one dotted component so a bare "실1)"
# footnote-style marker (not observed, but not ruled out either) is never
# mistaken for a real paragraph.
KGAAP_GUIDANCE_PARA_RE = re.compile(r"(?m)^\s*(실\d+(?:\.\d+)+)\s+")

# CAS (中国企业会计准则) 준칙 본문: Chinese-numeral articles "第<한자숫자>条"
# (e.g. "第一条".."第六十八条" for CAS21 租赁) -- see segment.py's CAS module
# comment for the full structural writeup. Trailing whitespace is MANDATORY
# (mirroring every other GAAP's own paragraph regex here), since real
# article markers always carry a real space/nbsp before the body text in
# every sample seen; requiring "条" specifically (not bare "第<숫자>") is
# what excludes chapter ("第<숫자>章") and section ("第<숫자>节") headings
# from being mistaken for paragraph boundaries -- neither ever ends in "条".
_CAS_NUM = "一二三四五六七八九十百千零两"
CAS_ARTICLE_RE = re.compile(r"(?m)^第([%s]+)条\s+" % _CAS_NUM)

# CAS 응용指南 (application guidance) and 해석 (interpretations): BOTH use a
# completely different, article-FREE top-level numbering -- bare
# "<한자숫자>、" (Chinese numeral + IDEOGRAPHIC COMMA, e.g. "一、", "二、"),
# with no space after the comma (confirmed distinct from 준칙 본문's own
# "条 " shape, which DOES carry real whitespace) -- nested "（一）"
# (parenthesized) and "1." (arabic-dot) sub-items are deliberately NOT
# separate paragraph boundaries here (no line-start bare numeral to match),
# so they stay attached to their enclosing "<한자숫자>、" chunk, same
# coarser-grained-but-faithful tolerance K-IFRS's own chunker already has
# for prose subheadings between two real paragraph markers. Selected via
# chunk_pages' `para_pattern` override, never chunk_pages' own gaap-level
# default (see tools/ingest/run_ingest.py's `ingest_cas`, which picks this
# per FILE, not per gaap, since 준칙 본문 and 응용指南/해석 are always
# separate CAS downloads).
CAS_GUIDANCE_PARA_RE = re.compile(r"(?m)^([%s]+)、" % _CAS_NUM)

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
# Blank-line detection tolerates a "blank" line that is not perfectly empty
# but contains only spaces/tabs (`\n[ \t]*\n` instead of a strict `\n\n+`) --
# confirmed necessary against the real K-GAAP 제9장 HWP (its own attachment
# is the one K-GAAP chapter needing an HWP fallback -- see sources.py): a
# "blank" line between two real paragraphs there is literally "\n \n" (a
# single stray space character on its own line), which the original
# `\n\n+` (strictly CONSECUTIVE newlines, nothing between them) never
# matched, so the block-start check silently never fired for the paragraph
# right after it. Still matches a truly empty "\n\n" identically (`[ \t]*`
# allows zero chars), so every existing K-IFRS case is unaffected.
#
# The alternation also gains two K-GAAP-specific shapes (harmless no-ops for
# every other GAAP, whose paragraph numbers never start with "실" or take
# the "<N>.<LETTER><M>" form): "실<N>.<M>" (실무지침, K-GAAP's
# 적용지침-equivalent tier -- confirmed missing its space in the same real
# 제9장 HWP, e.g. "실9.1조인트벤처가...") and "<N>.<LETTER><M>[의<M>]"
# (적용보충기준, e.g. "6.A1"/"6.A1의2" -- see KGAAP_BODY_PARA_RE). The
# letter-suffixed shape is placed BEFORE the generic bare-digit alternative:
# since Python tries alternatives left-to-right and commits to the FIRST one
# that succeeds (not the longest), the generic `\d{1,3}[A-Z]{0,2}(?:\.\d+)*`
# would otherwise match just the leading "6" of "6.A1" (a shorter, WRONG,
# but still "successful" match: `[A-Z]{0,2}` finds no letter immediately
# after the digit run since a "." comes next, and `(?:\.\d+)*` cannot
# consume ".A1" either since a letter follows the dot, not a digit) instead
# of ever trying the more specific alternative at all -- same ordering
# discipline `KGAAP_BODY_PARA_RE` already documents.
_LEAD_NUM_RE = re.compile(
    r"(\A|\n[ \t]*\n)([ \t]*)((?>한\d{1,3}(?:\.\d+)+|실\d{1,3}(?:\.\d+)+|"
    r"(?!BC\d)(?!IE\d)[A-Z]{1,2}\d{1,3}[A-Z]{0,2}(?:\.\d+)*|"
    r"\d{1,3}\.[A-Z]\d{1,3}(?:의\d+)?|\d{1,3}[A-Z]{0,2}(?:\.\d+)*))(?=\S)"
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
    always uses the letter-prefixed/실-prefixed pattern -- there is no legacy
    caller that ever needed to override that; CAS's own `ingest_cas` uses
    this same override to select 준칙 본문's article numbering vs 응용指南/
    해석's section numbering per FILE -- see below).

    K-GAAP (일반기업회계기준) has a document structure unrelated to K-IFRS's
    (organized by 장/chapter with "<장번호>.<문단번호>" paragraph numbering,
    no IFRS Foundation copyright block at all -- see
    tools/ingest/segment.py's K-GAAP module comment), so it is routed through
    its OWN frontmatter-stripper/section-splitter/paragraph-regex pair below
    rather than reusing the K-IFRS ones. CAS (中国企业会计准则) is likewise
    unrelated to either (HTML-sourced, Chinese-numeral "第X条" articles, no
    within-document tier split at all -- see tools/ingest/segment.py's CAS
    module comment) and gets its own third branch. Every other gaap's
    behavior (this function's pre-existing K-IFRS/US-GAAP path) is completely
    unchanged. VAS (Vietnamese Accounting Standards) gets its own fourth
    branch below -- HTML-sourced, plain digit "01."/table "| 01. |" đoạn
    numbering, at most one letter-numbered Phụ lục appendix per standard (see
    tools/ingest/segment.py's VAS module comment) -- chunked by
    `_chunk_region_vas` (not the shared `_chunk_region` every other gaap
    above uses), since VAS additionally needs the table-vs-list distinction
    and the cross-reference-line-wrap monotonic filter documented there.
    """
    full = "\n".join(p.text for p in pages)
    slug = _SLUG[gaap]

    if gaap == "K-GAAP":
        kept, _dropped_info = strip_frontmatter_kgaap(full)
        sections = split_sections_kgaap(kept)
        default_body_pattern = KGAAP_BODY_PARA_RE
        guidance_pattern = KGAAP_GUIDANCE_PARA_RE
    elif gaap == "CAS":
        kept, _dropped_info = strip_frontmatter_cas(full)
        sections = split_sections_cas(kept)
        default_body_pattern = CAS_ARTICLE_RE
        # split_sections_cas always leaves 적용지침 empty (see its own
        # docstring) so this pattern never actually runs against real text
        # -- kept as CAS_ARTICLE_RE (rather than None) only so the variable
        # is never unbound; the real 응용指南/해석 section-numbering pattern
        # is selected per-file via `para_pattern`, not via this slot.
        guidance_pattern = CAS_ARTICLE_RE
    elif gaap == "VAS":
        kept, _dropped_info = strip_frontmatter_vas(full)
        sections = split_sections_vas(kept)
        # default_body_pattern is unused for VAS: _chunk_region_vas always
        # merges VAS_PLAIN_PARA_RE + VAS_TABLE_PARA_RE for 본문 regardless of
        # what is passed here (see _vas_marks) -- kept as VAS_PLAIN_PARA_RE
        # only so the variable is never unbound, mirroring CAS's own
        # guidance_pattern placeholder above.
        default_body_pattern = VAS_PLAIN_PARA_RE
        guidance_pattern = VAS_GUIDANCE_PARA_RE
    else:
        kept, _dropped_info = strip_frontmatter(full)
        sections = split_sections(kept)
        default_body_pattern = DIGIT_PARA_RE
        guidance_pattern = LETTER_PARA_RE

    has_structure = any(sections[k].strip() for k in ("적용지침", "결론도출근거", "적용사례"))
    body_tier = "본문" if has_structure else tier
    body_pattern = para_pattern if para_pattern is not None else default_body_pattern

    region_chunker = _chunk_region_vas if gaap == "VAS" else _chunk_region
    recs = []
    recs += region_chunker(sections["본문"], body_pattern, slug, gaap, standard_no,
                           standard_title, lang, body_tier, source_url, as_of)
    recs += region_chunker(sections["적용지침"], guidance_pattern, slug, gaap, standard_no,
                           standard_title, lang, "적용지침", source_url, as_of)

    recs = flag_oversized_chunks(recs)

    ids = [r.id for r in recs]
    if len(set(ids)) != len(ids):
        raise ChunkingError(f"duplicate record ids produced for {gaap} {standard_no}: "
                             f"{[i for i in ids if ids.count(i) > 1]}")
    return recs


# --- 페이지푸터 제거 & 헤딩 경계 분리 (2026-07-08 정합성 개선) ---------------
# PDF 소스(K-IFRS·K-GAAP)는 문단 사이에 (1) 페이지 푸터("- 15 -")와 (2) 번호 없는
# 절/장 제목("측정"·"리스이용자"·"第二章 …")을 끼워 넣는다. 마커 기반 분할은 이들을
# 앞 문단 text 꼬리에 흡수해 verbatim을 오염시켰다(전수 스캔: 후행헤딩 24~30%,
# 페이지푸터 31%). 아래 프리미티브가 푸터를 제거하고, 후행 헤딩을 문단 text에서
# 떼어 '다음 문단의 heading'으로 재귀속한다 — 원문 문장은 불변, 헤딩은 heading
# 필드로 보존(무손실).
_PAGE_FOOTER_RE = re.compile(r"^[ \t]*[-–—][ \t]*\d{1,4}[ \t]*[-–—][ \t]*$")
_BARE_PAGENUM_RE = re.compile(r"^[ \t]*\d{1,4}[ \t]*$")
# 순수 마커/번호만 있는 줄(문단번호 그 자체). 헤딩도 내용도 아님.
_MARKER_ONLY_RE = re.compile(r"^\s*(한?\d+[A-Z]{0,2}(?:\.\d+)*|[A-Z]\d+[A-Z]{0,2}(?:\.\d+)*|"
                             r"第[〇零一二三四五六七八九十百千]+条|[A-Z])\s*$")
# 언어별 문장/절 종결 신호: 이 글자로 끝나면 완결된 내용줄(헤딩 아님)로 본다.
_SENT_END = {
    "ko": tuple(".?!:;)]}”\"’」』…다"),
    "zh": tuple("。？！：；）】》”’…"),
    "vi": tuple(".?!:;)]}”\"’…"),
    "en": tuple(".?!:;)]}\"’…"),
}
# 리스트/불릿/괄호 항목 시작(내용줄 취급 → 헤딩으로 오인 금지). CAS 第N章/节은
# 여기서 보호하지 않는다(그건 절 제목이라 헤딩으로 떼어야 함); 第N条는 조문
# 마커라 항상 조각의 첫 줄(마커 줄)로 보존되므로 별도 보호 불필요.
_LIST_HEAD_RE = re.compile(r"^\s*([(（\[]|[⑴-⒇]|[①-⑳]|\d{1,3}[.)]\s|[가-힣][.)]\s|"
                           r"[A-Za-z][.)]\s|[•·・◦▪‣∙*\-–—])")


def strip_page_footers(text):
    """대시형 페이지 푸터('- 15 -')를 줄 단위로 제거. 단독 숫자줄은 문단 마커일
    수 있어 여기서 건드리지 않고(_split_piece가 마커 판정 후 처리), 대시형만
    안전하게 제거한다. (text, 제거문자수) 반환."""
    kept, removed = [], 0
    for ln in text.split("\n"):
        if _PAGE_FOOTER_RE.match(ln):
            removed += len(ln)
            continue
        kept.append(ln)
    return "\n".join(kept), removed


def _is_heading_line(s, lang="ko"):
    """절/장 제목류: 짧고, 문장 종결부호로 안 끝나고, 리스트/번호/표가 아님."""
    s = s.strip()
    if not s or len(s) > 24:
        return False
    if s[-1] in _SENT_END.get(lang, _SENT_END["en"]):
        return False
    if _LIST_HEAD_RE.match(s):
        return False
    if "|" in s or "\t" in s:            # 표 행은 내용
        return False
    if re.search(r"\d{2,}", s):          # 숫자 다수면 데이터/표 조각
        return False
    return True


def _is_content_line(s, lang="ko"):
    """실제 본문 줄: 헤딩도, 순수 마커/번호도, 페이지번호도, 빈줄도 아님."""
    t = s.strip()
    if not t:
        return False
    if _MARKER_ONLY_RE.match(t) or _BARE_PAGENUM_RE.match(t) or _PAGE_FOOTER_RE.match(t):
        return False
    if _is_heading_line(t, lang):
        return False
    return True


def _split_piece(chunk_text, lang):
    """한 문단 span을 (body_text 또는 None, 후행/단독 헤딩줄 list)로 분해.
    - 첫 줄(마커) 이후의 단독 페이지번호 줄 제거.
    - 마지막 '내용줄' 뒤의 헤딩류는 떼어 trailing으로(다음 문단 heading 후보).
      내용줄은 항상 body에 포함되므로 마커 줄이 헤딩처럼 보여도 보존된다.
    - 내용줄이 하나도 없으면(전부 헤딩/번호) body_text=None(레코드 미생성)."""
    lines = chunk_text.split("\n")
    if lines:
        lines = [lines[0]] + [l for l in lines[1:] if not _BARE_PAGENUM_RE.match(l.strip())]
    last_content = -1
    for i, l in enumerate(lines):
        if _is_content_line(l, lang):
            last_content = i
    if last_content < 0:
        heads = [l.strip() for l in lines if l.strip() and _is_heading_line(l, lang)]
        return None, heads
    body = lines[:last_content + 1]
    trailing = [l.strip() for l in lines[last_content + 1:]
                if l.strip() and _is_heading_line(l, lang)]
    return "\n".join(body).strip(), trailing


def _finalize_pieces(raw_pieces, slug, gaap, standard_no, standard_title, lang, tier,
                     source_url, as_of):
    """raw_pieces[(para_no, span_text)] → Record 리스트. 각 조각을 _split_piece로
    정리하고, 떼어낸 후행 헤딩은 '다음 레코드의 heading'으로 이월한다."""
    recs = []
    seen = {}
    pending_heading = ""
    for para_no, chunk_text in raw_pieces:
        body_text, trailing = _split_piece(chunk_text, lang)
        if body_text is None:
            if trailing:
                pending_heading = (pending_heading + " " + " ".join(trailing)).strip()
            continue
        base_id = f"{slug}:{standard_no}:{tier}:{para_no}"
        n = seen.get(base_id, 0)
        seen[base_id] = n + 1
        rec_id = base_id if n == 0 else f"{base_id}#{n + 1}"
        recs.append(_mk(rec_id, gaap, standard_no, standard_title, para_no, body_text,
                        lang, tier, source_url, as_of, heading=pending_heading))
        pending_heading = " ".join(trailing)
    return recs


def _chunk_region(text, pattern, slug, gaap, standard_no, standard_title, lang, tier,
                   source_url, as_of):
    if not text.strip():
        return []
    text = normalize_missing_space(text)
    text, _ = strip_page_footers(text)
    marks = list(pattern.finditer(text))
    raw_pieces = []
    if not marks:
        stripped = text.strip()
        if stripped:
            raw_pieces.append(("0", stripped))
    else:
        if marks[0].start() > 0:
            lead = text[:marks[0].start()].strip()
            if lead:
                raw_pieces.append(("0", lead))
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            raw_pieces.append((m.group(1), text[m.start():end].strip()))
    return _finalize_pieces(raw_pieces, slug, gaap, standard_no, standard_title,
                            lang, tier, source_url, as_of)


def _vas_marks(text, pattern):
    """VAS counterpart to plain `pattern.finditer(text)`: for the 본문 region
    (`pattern is VAS_PLAIN_PARA_RE`, chunk_pages' VAS default_body_pattern),
    merges VAS_PLAIN_PARA_RE + VAS_TABLE_PARA_RE (see segment.py's VAS module
    comment for why 본문 always needs both shapes at once, never just one);
    for 적용지침 (`pattern is VAS_GUIDANCE_PARA_RE`) uses that pattern alone,
    since Phụ lục A never uses table-style markers.

    Then drops any candidate whose captured integer does not STRICTLY exceed
    the previous KEPT candidate's -- a stateful filter `_chunk_region`'s own
    plain `pattern.finditer()` has no equivalent of, needed here because a
    genuine đoạn/phụ-lục-paragraph sequence is confirmed strictly monotonic
    in every one of the 26 real VAS files, so any non-increasing candidate is
    necessarily a false positive: a cross-reference number that happens to
    line-wrap onto its own line with real trailing same-line space before the
    next real sentence (confirmed real case: VAS 11 본문's own "...theo các
    đoạn 50 đến\n54. Phần lớn..." and "...theo đoạn\n55.\nLợi ích..." -- both
    structurally indistinguishable from a genuine marker by shape alone, both
    correctly rejected here since a real đoạn 54/55 already preceded them).
    The letter prefix (적용지침 candidates only) is stripped before comparing
    so "A17" compares as 17, not against 본문's own separate 1..74 sequence
    (적용지침 is always chunked as a fully separate call from 본문, so the two
    sequences' running-max state never mixes)."""
    if pattern is VAS_GUIDANCE_PARA_RE:
        raw = list(pattern.finditer(text))
    else:
        raw = list(VAS_PLAIN_PARA_RE.finditer(text)) + list(VAS_TABLE_PARA_RE.finditer(text))
    raw.sort(key=lambda m: m.start())

    kept = []
    running_max = 0
    for m in raw:
        v = int(re.match(r"[A-Z]?(\d+)", m.group(1)).group(1))
        if v > running_max:
            kept.append(m)
            running_max = v
    return kept


def _chunk_region_vas(text, pattern, slug, gaap, standard_no, standard_title, lang, tier,
                       source_url, as_of):
    """VAS counterpart to `_chunk_region`: identical piece-slicing/Record-
    building shape (marker match's OWN start is where its paragraph's stored
    `text` begins -- i.e. the marker itself, pipes included where the source
    is table-style, is part of the verbatim record, same convention every
    other GAAP's own chunker uses -- see segment.py's VAS module comment on
    why pipes are never stripped), but sourced from `_vas_marks` (merged
    plain+table shapes, cross-reference-line-wrap-filtered) instead of a bare
    `pattern.finditer(text)`. VAS never needs `_chunk_region`'s own
    `normalize_missing_space` call here -- VAS's missing-space fix
    (`normalize_missing_space_vas`) already ran once, on the full raw page
    text, inside `strip_frontmatter_vas`, before section-splitting."""
    if not text.strip():
        return []
    marks = _vas_marks(text, pattern)
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


def _mk(rec_id, gaap, std, title, para, text, lang, tier, url, as_of, heading=""):
    return Record(id=rec_id, gaap=gaap, standard_no=std, standard_title=title,
                  paragraph_no=para, heading=heading, text=text, text_norm=normalize_text(text),
                  lang=lang, tier=tier, source_url=url, as_of=as_of, extract_flag=False)
