r"""Frontmatter stripping and section splitting for K-IFRS standard documents.

KASB-published K-IFRS PDFs/HWPs bundle FOUR kinds of material in one file:

1. Cover page + bilingual (Korean/English) IFRS Foundation copyright notice +
   table of contents ("목차") -- administrative front matter, never citable body
   text, and a source of false paragraph-boundary matches (bare TOC numbers like
   a lone "22" or address fragments like "7 Westferry Circus...").
2. 본문 -- the main numbered paragraphs (digit numbering: 1, 2, 5.5.1, 40G, plus
   the Korea-only "한2.1" insert-paragraph convention KASB adds into the IFRS
   translation).
3. 부록 A/B/C 적용지침 -- appendices (defined terms, application guidance,
   effective date & transition). Letter-prefixed numbering: A1, B1, C1, C1A.
   "이 부록은 이 기준서의 일부를 구성한다" -- same authority as the main body,
   so this is corpus-depth in scope and retained.
4. 결론도출근거 (Basis for Conclusions, "BC...") and 적용사례*실무적용지침
   (Illustrative Examples, "IE...") -- both explicitly say of themselves "이
   기준서를 구성하지는 않는다" (does not form part of the standard). Dropped.

Both functions below are anchor-based: they search for byte-stable KASB/IFRS
Foundation template phrases rather than doing exact byte-diffing or relying on
page numbers, so the same logic works across both the PDF extraction (one text
line per *visual* line, heavy wrapping) and the HWP extraction (one text line
per logical paragraph, no wrapping, occasionally missing the space after a
paragraph number) despite their very different line-shapes.

GENERALIZATION NOTES (63-standard full-set pass):

* PDF line-wrapping can split an anchor phrase mid-word at an unpredictable
  character offset. Many K-IFRS PDFs render Korean prose with NO inter-word
  spaces at all (a font/extraction characteristic of these particular PDFs,
  out of scope to "fix" here -- extract.py is not touched), so there is no
  natural break point and PyMuPDF's visual-line-wrap newline can land between
  ANY two characters of a multi-syllable anchor word. Confirmed empirically:
  the self-description sentence "...로 구성되어 있다" wraps as "...로구\n성되어있다"
  in 1103, "...로 구성\n되어 있다" in 1113, and "...구성되\n어 있다" in 1032 --
  three DIFFERENT split points for the same 4-syllable word. `_loose()` below
  builds a regex tolerating an optional line-wrap between every character of
  an anchor word so this is no longer a per-standard game of whack-a-mole.
* The old TOC-closing anchor (`구성되어\s*있다|부여되어\s*있다`) was searched
  UNBOUNDED from the end of the copyright block to the end of the document.
  Combined with the mid-word-wrap problem above, this was catastrophic: for
  1032/1103/1113 the near-front, legitimate occurrence of the sentence was
  wrap-split and so invisible to the old regex, and the search then matched
  some UNRELATED later use of "구성되어 있다"/"부여되어 있다" as ordinary
  Korean phrasing deep inside 결론도출근거/적용사례 (e.g. 1032's real hit was
  at char 117,941 of a 126,296-char document) -- which then became the cut
  point, discarding the entire real 본문/적용지침/부록 as "frontmatter". The
  fix has two parts: (a) require the anchor to be self-referential --
  "기업회계기준(해석)?서 제NNNN호"-style, immediately followed (within a
  short span) by "구성"/"부여" -- which a random BC/IE sentence never is, and
  (b) even so, bound the whole search to `_TOC_SCAN_BOUND` characters past the
  copyright block. Bounding means a miss now degrades to "some TOC residue
  survives into 본문" (a MINOR, gate-catchable defect) instead of "the entire
  body is gone" (CRITICAL). Every legitimate near-front gap measured across
  all 63 real standards is <=2,922 chars; every pathological deep/BC-side
  match measured is >=15,000 chars -- `_TOC_SCAN_BOUND` sits well inside that
  gap.
* 해석서 (interpretations) use a structurally different template from 기준서:
  no "구성되어 있다." sentence in isolation -- instead "...으로 구성되어
  있으며, 결론도출근거가 첨부되어 있다." (a connective "-며" clause, not a
  full stop) or even "...으로 구성되며" (no 있다/있으며 at all). The
  self-ref+"구성" anchor (deliberately not requiring any particular verb
  ending) covers both.
* 개념체계 and both 번역서 (non-mandatory translated guidance, no 제NNNN호
  number) have NO self-referential "구성되어 있다"-style sentence anywhere
  near the front at all -- so the primary anchor legitimately does not fire
  for them. All three DO carry a "[기타 참고사항]" (or "기타 참고사항:")
  bracket/label that is the last piece of TOC preview content before the real
  title repeats, so `_KICHA_RE` is used as the fallback anchor. Confirmed
  present, close to the copyright block, in all 63 standards (max legitimate
  gap 2,825 chars, for the largest document, 1109).
* Appendix ("부록") headings are punctuated inconsistently: "부록 A. 용어의
  정의" (letter + period + title, same line -- 1103/1113/1111 style), "부록
  A\n현재가치기법을 사용한 사용가치 측정" (letter, NO period, title on the
  NEXT line -- 1036/2120/2121/2122 style), "부록 적용지침" (no letter at all,
  title same line -- 1032 style), "부록. 적용지침" (no letter, period, title
  same line, no-space PDF -- 2116 style), "부록\n용어의 정의" (no letter, no
  punctuation, title on next line -- 개념체계/번역서-경영진설명서/
  번역서-중요성판단 style). Rather than enumerate punctuation variants,
  `_find_appendix_heads()` anchors on the semantic CONFIRMING sentence that
  immediately follows every one of these headings in real documents -- "이
  부록은 ... 일부를 구성한다/구성하며/이다" ("this appendix forms part of
  ..."), the same sentence the module docstring above already quotes as the
  reason appendices are in-scope. This generalizes across every punctuation
  style above in one pattern instead of five. The lone exception found is
  개념체계's own glossary appendix, which has no confirming sentence at all
  (it launches straight into the glossary content) -- handled by a narrow,
  additional "부록" + nearby "용어의 정의" fallback.
* The board-resolution voting-log line was anchored on a literal
  "기업회계기준서" prefix, which never matches 해석서's "기업회계기준해석서"
  (extra "해석" infix) or 개념체계's quoted-title self-reference ("'재무보고를
  위한 개념체계'의 ... 회계기준위원회의 의결") -- so this log leaked into
  본문 for every one of the 19 해석서 and for 개념체계. Re-anchored on the
  stable suffix "...회계기준위원회의 의결" (with a short, line-scoped prefix
  budget) instead of the standard-specific prefix.
"""
import re


def _loose(word):
    """Regex fragment matching `word` character-by-character, tolerating an
    optional line-wrap (newline + leading spaces/tabs on the continuation
    line) between any two characters. Any literal spaces already in `word`
    are dropped before building the fragment -- these K-IFRS PDFs are
    inconsistent about rendering inter-word spaces at all (see module
    docstring), so a real space and no space must both be accepted, which
    `[ \\t\\n]*` between every character already covers on its own.

    This is what lets a single anchor phrase survive PDF line-wrapping that
    splits it at an unpredictable character offset (confirmed: the same
    4-syllable word wraps at three different internal points across
    1032/1103/1113 -- see module docstring)."""
    chars = [c for c in word if not c.isspace()]
    return r"[ \t\n]*".join(re.escape(c) for c in chars)


# The bilingual copyright notice always closes with this exact English sentence,
# repeated 3x total (twice in the Korean section's inline English aside, once
# more at the end of the separate "COPYRIGHT NOTICE" English section) in every
# K-IFRS PDF/HWP sampled from KASB (all 63 standards/interpretations plus the
# framework and both translated practice statements). Cutting after the LAST
# occurrence removes the cover page + both copyright blocks in one shot,
# independent of standard number/title and of exactly how many times it
# repeats. Unlike the Korean anchors below, this one is plain English prose
# with normal spacing in every sample seen, so it needs no loose/wrap-tolerant
# matching.
_COPYRIGHT_TAIL_RE = re.compile(r"resides in the Republic of Korea\.?")

# How far past the end of the copyright block to search for a TOC-closing
# anchor. Every legitimate near-front anchor measured across all 63 real
# K-IFRS standards/interpretations (plus 개념체계 and both 번역서) sits at
# <=2,922 chars (the largest document, 1109, has the largest legitimate TOC).
# Every confirmed-pathological deep match (the old bug landing inside BC/IE)
# sits at >=15,000 chars. This bound is deliberately far above the former and
# far below the latter, so it can never again turn a stray BC/IE match into a
# whole-body-deleting cut -- a miss inside this window just means "no TOC
# anchor found here", not "search until we find *something*".
_TOC_SCAN_BOUND = 6000

# How far past a found anchor's end to search for the blank line closing its
# paragraph (frontmatter sentences run a few more clauses after the anchor
# word itself, e.g. "...구성되어 있다. 모든 문단의 권위는 같다. ..."). Bounded
# for the same reason as `_TOC_SCAN_BOUND`: an unbounded `str.find("\n\n", ...)`
# is itself a smaller-scale version of the same unbounded-search bug.
_BLANK_SWEEP_BOUND = 1500

# Self-reference to the standard/interpretation's own number, e.g.
# "기업회계기준서 제1116호" or "기업회계기준해석서 제2010호" (해석서 insert
# "해석" before "서"). Deliberately loose/wrap-tolerant on every piece.
_SELF_REF_FRAG = (
    _loose("기업회계기준") + r"[ \t\n]*(?:" + _loose("해석") + r"[ \t\n]*)?"
    + _loose("서") + r"[ \t\n]*" + _loose("제") + r"[ \t\n]*\d+[ \t\n]*" + _loose("호")
)

# The TOC-closing self-description sentence, e.g.:
#   "기업회계기준서 제1116호 '리스'는 문단 1부터 106까지와 부록 A~C로
#    구성되어 있다. 모든 문단의 권위는 같다. ..."
#   "기업회계기준해석서 제2010호 '...'는 문단 한1.1~한3.1로 구성되어
#    있으며, 결론도출근거가 첨부되어 있다."
# It is the last thing before the body restarts (title repeated, "목적"
# heading, paragraph "1"), so sweeping through the end of its enclosing
# paragraph removes the TOC's bare paragraph-number lines (e.g. a lone "22" or
# "88" sitting on its own line as a cross-reference) that would otherwise
# collide with the real paragraph of the same number later in the document.
# Requiring the standard's own self-reference immediately before "구성되"/
# "구성된"/"부여되"/"부여된" (rather than matching those verbs bare, as the
# old regex did) is what makes this safe to search for -- a random sentence
# describing something else as "구성된다"/"구성되어 있다" (e.g. a footnote on
# what a financial statement is composed of) never also opens with
# "기업회계기준서 제NNNN호". The verb stem must be the PASSIVE "구성되/구성된"
# (구성되어/구성되며/구성된다 -- "되"+"ㄴ다" writes as the single syllable
# "된", not "되"+"다") rather than bare "구성", which would also match the
# ACTIVE-negated "구성하지는 않는다" ("does NOT form part of ...") -- every
# 기준서/해석서/개념체계 opens its very first TOC-preview line with exactly
# that disclaimer, self-referenced by number, e.g. "...기타 참고사항은 기업
# 회계기준서 제1116호를 구성하지는 않으나..."; without requiring 되/된 this
# matched THAT sentence (far too early, right at the top of the TOC) instead
# of the real closing sentence, which reintroduced a smaller-scale version of
# the original bug (confirmed: 1034/1036/1038/1041/1102/1116/1117 all lost
# nearly all of 본문 to this during development). No further verb ending is
# required after 되/된 (해석서 uses "-며"/"-며,", not always the "-다." full
# stop 기준서 uses) -- the stem alone is specific enough given the
# self-reference requirement immediately before it.
_STRUCTURE_NOTE_RE = re.compile(
    _SELF_REF_FRAG + r"[\s\S]{0,150}?(?:" + _loose("구성") + "|" + _loose("부여") + r")[ \t\n]*[되된]"
)

# Fallback TOC-closing anchor for documents with no self-referential
# "구성되어 있다"-style sentence at all: 개념체계 and both 번역서 (translated,
# non-mandatory guidance -- not numbered 기준서/해석서, so they never
# self-reference "제NNNN호"). All three, like every 기준서/해석서, carry a
# "[기타 참고사항]" (or, for 번역서-중요성판단, colon-separated "기타
# 참고사항: ...") label as the LAST bracketed preview item in the TOC, right
# before the real content restarts -- confirmed present and close to the
# copyright block in all 63 standards, so it doubles as a universal fallback
# when the primary anchor is legitimately absent.
_KICHA_RE = re.compile(_loose("기타") + r"[ \t\n]*" + _loose("참고사항"))


def _advance_past_paragraph(text, start, bound):
    """From `start` (the end of a matched anchor), return the position just
    past the next blank line within `bound` characters, so the anchor's
    WHOLE enclosing paragraph (not just the matched word) is swept up.
    Degrades to `start` itself if no blank line is found in range -- never
    searches past `bound`."""
    blank = text.find("\n\n", start, start + bound)
    return blank if blank != -1 else start


def strip_frontmatter(text):
    """Remove the IFRS Foundation cover/copyright boilerplate and (on PDF,
    where it is rendered as real text) the table of contents.

    Returns (kept_text, dropped_info). dropped_info logs what was removed
    instead of silently discarding it: {"copyright_removed": bool,
    "toc_removed": bool, "toc_anchor": str|None, "chars_dropped": int,
    "dropped_text": str}.

    Degrades gracefully at every step: if the copyright anchor is not found at
    all (e.g. a plain text fixture, or a future non-IFRS-sourced GAAP with no
    IASB copyright block), this is a no-op and the input is returned
    unchanged. If a copyright block IS found but no TOC-closing anchor is
    found within `_TOC_SCAN_BOUND` characters of it, only the copyright block
    itself is removed -- some TOC residue may remain in the kept text (a
    MINOR, gate-catchable defect), but the search NEVER ranges far enough to
    mistake real body/BC/IE content for frontmatter (a CRITICAL defect)."""
    info = {"copyright_removed": False, "toc_removed": False, "toc_anchor": None,
            "chars_dropped": 0, "dropped_text": ""}
    tail_matches = list(_COPYRIGHT_TAIL_RE.finditer(text))
    if not tail_matches:
        return text, info
    cut = tail_matches[-1].end()
    info["copyright_removed"] = True

    window_end = cut + _TOC_SCAN_BOUND
    note = _STRUCTURE_NOTE_RE.search(text, cut, window_end)
    if note:
        cut = _advance_past_paragraph(text, note.end(), _BLANK_SWEEP_BOUND)
        info["toc_removed"] = True
        info["toc_anchor"] = "structure_note"
    else:
        kicha_matches = list(_KICHA_RE.finditer(text, cut, window_end))
        if kicha_matches:
            cut = _advance_past_paragraph(text, kicha_matches[-1].end(), _BLANK_SWEEP_BOUND)
            info["toc_removed"] = True
            info["toc_anchor"] = "기타참고사항"

    info["chars_dropped"] = cut
    info["dropped_text"] = text[:cut]
    return text[cut:], info


# Real heading forms confirmed across the full 63-standard set: "부록 A. 용어의
# 정의" (period + title, same line), "부록 A\n현재가치기법을 ..." (letter, no
# period, title on the NEXT line), "부록 적용지침" (no letter at all, title
# same line), "부록. 적용지침" (no letter, period, no-space PDF), "부록\n용어의
# 정의" (no letter, no punctuation, title on next line). Rather than enumerate
# punctuation styles, a "부록" line-start is confirmed as a REAL heading (not
# an inline prose cross-reference like "이 부록 A에서 정의하는 '리스료'..." or
# a TOC preview mention) by the CONFIRMING sentence that follows every one of
# them in real documents: "이 부록은 이 기준서의/해석서의 일부를
# 구성한다/구성하며/구성하다", or "이 부록은 이 실무서의 일부이다.". A TOC
# preview mention of "부록" is never followed by this sentence (the TOC just
# lists more heading previews, or moves straight to the "문단번호" column), so
# this also protects against matching residual, imperfectly-stripped TOC text.
_APPENDIX_LINE_RE = re.compile(r"(?m)^부록\b")
_APPENDIX_CONFIRM_RE = re.compile(_loose("부록") + r"[ \t\n]*[은는][\s\S]{0,80}?" + _loose("일부"))
# The lone exception: 개념체계's own glossary appendix ("부록\n용어의 정의\n다음
# 용어에 대한 정의는 ...") has no confirming sentence at all -- it launches
# straight into the glossary. "부록" immediately followed by "용어의 정의" is
# specific enough to stand on its own (a TOC preview mention of the SAME title
# is, again, already removed by strip_frontmatter before split_sections ever
# runs).
_APPENDIX_GLOSSARY_RE = re.compile(_loose("부록") + r"[\s\S]{0,20}?" + _loose("용어의") + r"[ \t\n]*" + _loose("정의"))
_APPENDIX_CONFIRM_WINDOW = 220


# One confirmed exception among all 63 real standards: 1007's "부록 B.
# 금융회사의 현금흐름표" confirms itself with "이 부록은 기업회계기준서
# 제1007호에 첨부되지만, 이 기준서의 일부를 구성하는 것은 아니다." -- an
# explicitly NEGATED variant of the same confirming sentence, i.e. this
# appendix says of ITSELF that it does *not* form part of the standard
# (word-for-word the same disclaimer 적용사례/결론도출근거 make about
# themselves). Authority, not just presence under a "부록" heading, is what
# puts content in scope for the 적용지침 tier (see module docstring) -- so a
# negated confirmation must route to the dropped bucket instead, the same as
# 적용사례/결론도출근거, not to 적용지침 and not left to fall into 본문 either.
_APPENDIX_NEGATION_RE = re.compile(r"아니다|않는다|않다")


def _find_appendix_heads(text):
    """Return (authoritative_heads, disclaimed_heads): the start positions of
    every REAL "부록" (appendix) heading in `text`, confirmed via the sentence
    that follows it (see comment above) -- not just any line starting with
    "부록", which would also catch inline prose cross-references and TOC
    residue -- split by whether that confirming sentence affirms or negates
    ("...일부를 구성하는 것은 아니다") the appendix's own standard-authority."""
    authoritative, disclaimed = [], []
    for m in _APPENDIX_LINE_RE.finditer(text):
        window = text[m.start(): m.start() + _APPENDIX_CONFIRM_WINDOW]
        confirm = _APPENDIX_CONFIRM_RE.search(window) or _APPENDIX_GLOSSARY_RE.search(window)
        if not confirm:
            continue
        tail = window[confirm.end(): confirm.end() + 40]
        if _APPENDIX_NEGATION_RE.search(tail):
            disclaimed.append(m.start())
        else:
            authoritative.append(m.start())
    return authoritative, disclaimed


# Both 결론도출근거 and 적용사례*실무적용지침 open with a short standalone
# divider line/page (mirroring how the main body opens with a "본 문"
# divider), confirmed in every 기준서 and every 해석서 that has each section:
# e.g. line "결론도출근거" alone, then Korean-specific preamble, then the real
# "IFRS 16의 결론도출근거 (BC1-BC310)" heading and BC1 itself. Matching the
# divider (not the varying real heading text, which differs per standard) is
# what generalizes.
_IE_DIVIDER_RE = re.compile(r"(?m)^적용사례\s*$")
_BC_DIVIDER_RE = re.compile(r"(?m)^결론도출근거\s*$")

# Right after the appendices (and, for a standard with none, right after 본문
# itself) KASB inserts a "제·개정 등에 대한 회계기준위원회의 의결" log: one
# paragraph per historical enactment/amendment recording how the standard-
# setting board voted, e.g. "기업회계기준서 제1019호의 제정에 대한
# 회계기준위원회의 의결(2007년)" then a series of "...의 개정에 대한
# 회계기준위원회의 의결(20XX년)" entries with board member name lists. It is
# pure governance record-keeping, not part of the standard and not
# application guidance, so it must not be left to fall into whatever kept
# region happens to precede it.
#
# Anchored on the stable SUFFIX "...회계기준위원회의 의결" (with a short,
# same-neighbourhood prefix budget) rather than a literal "기업회계기준서"
# prefix: 해석서 write "기업회계기준해석서" (extra "해석" infix -- the old
# regex, anchored on the literal 기준서 prefix, never matched this at all, so
# this log leaked into every one of the 19 해석서's 본문 uncaught), and
# 개념체계 self-references by quoted title instead of a standard number
# ("'재무보고를 위한 개념체계'의 전면개정에 대한 회계기준위원회의 의결" -- no
# "기업회계기준서 제NNNN호" at all). There is no reliable one-line-only
# divider for it (unlike 적용사례/결론도출근거); routing it into the
# 결론도출근거 bucket is a labeling convenience only -- both buckets are
# dropped identically by chunk_pages.
#
# The prefix gap deliberately uses `.` (excludes newline), NOT `[\s\S]`: every
# real board-resolution line (both the bare TOC-preview mention and every
# per-amendment entry, in every 기준서/해석서/개념체계 sample seen) sits on
# ONE physical line, and confining the gap to that one line matters -- a
# DOTALL-style gap here previously matched starting from an unrelated EARLIER
# line (e.g. an appendix's opening "이 부록은 ... 일부를 구성한다." sentence)
# whenever some real board-resolution text happened to follow within the
# character budget a few lines down, truncating that appendix's own content.
# `_loose()` inside the anchor words themselves still tolerates a mid-word
# wrap, same as every other anchor in this module.
_BOARD_RESOLUTION_RE = re.compile(r"(?m)^.{0,80}?" + _loose("회계기준위원회의") + r"[ \t\n]*" + _loose("의결"))

# 개념체계 (and, generalized, any future document sharing its structure)
# repeats a per-CHAPTER mini table-of-contents at the start of every "제N장"
# (Chapter N) heading throughout its real body -- confirmed at all 8 real
# chapter transitions in 개념체계's own 본문 (and, a second time, in its own
# 결론도출근거, which mirrors the same 8-chapter structure -- but that whole
# section is already dropped wholesale via _BC_DIVIDER_RE, so those
# occurrences never reach a kept region regardless). Each block opens with
# the exact same "목\n차"/"목차" heading the document-level frontmatter TOC
# uses (see _KICHA_RE's neighbourhood and the module docstring), followed by
# the chapter title and a heading-preview list, and reliably closes with a
# "문단번호" ("paragraph number[s]") column label right before the bare
# paragraph-number preview list (itself already cleaned up separately by
# fidelity.detect_shadows, since each previewed number collides with -- and
# is dwarfed by -- the real, later paragraph of the same number). Left
# unstripped, this glues onto the TAIL of whatever real paragraph happens to
# immediately precede the next chapter (confirmed: 개념체계 본문 paragraph
# 1.23's captured text correctly starts with 1.23's own real prose, then
# also swallows the whole of 제2장's mini-TOC preview up to "문단번호") -- no
# real paragraph is ever entirely lost to this (unlike the original
# unbounded-search bug), only contaminated at the tail with preview junk.
# Bounded the same way as every other anchor in this module: a miss just
# leaves the preview text in place (gate-catchable via
# fidelity.assert_no_leak's toc_heading signature), never an unbounded reach
# into unrelated real content. 1200 chars comfortably covers every real span
# measured across all 63 standards (documents with no such block --
# every 기준서/해석서, both 번역서 -- have no "목차" at all in their kept
# body text, so this is a no-op for them; max legitimate span measured in
# 개념체계 itself, across both its 본문 and its own dropped 결론도출근거, is
# 477 chars).
_CHAPTER_TOC_RE = re.compile(
    _loose("목") + r"[ \t\n]*" + _loose("차") + r"[\s\S]{0,1200}?" + _loose("문단번호")
)


def _strip_chapter_toc_previews(text):
    """Remove every per-chapter mini-TOC block (see _CHAPTER_TOC_RE) from
    already-frontmatter-stripped text. Safe to run unconditionally on every
    document: one with no such block simply has no match, so this is a
    no-op."""
    return _CHAPTER_TOC_RE.sub("", text)


SECTION_KEYS = ("본문", "적용지침", "결론도출근거", "적용사례")


def split_sections(text):
    """Split already-frontmatter-stripped body text into the four corpus-depth
    regions: 본문, 적용지침, 결론도출근거, 적용사례 (dict of region -> text).

    Everything before the first recognized heading is 본문. A 부록 A/B/C
    heading (defined terms + application guidance + effective date/transition
    -- all letter-numbered, all "part of the standard") switches into
    적용지침 and stays there until 적용사례 or 결론도출근거 is hit. Multiple
    headings of the same kind (부록 A, then B, then C) just extend the same
    region rather than fragmenting it -- and since 적용사례/결론도출근거 are
    BOTH dropped in the end, a heading misdetected as one instead of the other
    (e.g. deep inside a wrapped BC discussion) cannot leak either into a kept
    region, so only the 본문/적용지침 boundary actually has to be precise.
    The board-resolution voting log (see _BOARD_RESOLUTION_RE) is routed into
    결론도출근거 for the same reason: it must never be left attached to a kept
    본문/적용지침 region. A "부록" heading that explicitly disclaims standard
    authority for itself (confirmed so far only in 1007's 부록 B -- see
    _find_appendix_heads) is routed into 적용사례 for the same reason: it must
    never be left attached to (or mistaken for) the real, authoritative
    적용지침 region either. Per-chapter mini-TOC previews (see
    _strip_chapter_toc_previews -- so far confirmed only in 개념체계) are
    stripped first, before any of the above boundary detection runs, since
    they are front-matter-shaped noise wherever in the document they recur
    and must never survive into a kept region either.
    """
    text = _strip_chapter_toc_previews(text)
    authoritative_appendix, disclaimed_appendix = _find_appendix_heads(text)
    marks = [(pos, "적용지침") for pos in authoritative_appendix]
    marks += [(pos, "적용사례") for pos in disclaimed_appendix]
    marks += [(m.start(), "적용사례") for m in _IE_DIVIDER_RE.finditer(text)]
    marks += [(m.start(), "결론도출근거") for m in _BC_DIVIDER_RE.finditer(text)]
    marks += [(m.start(), "결론도출근거") for m in _BOARD_RESOLUTION_RE.finditer(text)]
    marks.sort(key=lambda x: x[0])

    boundaries = [(0, "본문")]
    for pos, name in marks:
        if boundaries[-1][1] != name:
            boundaries.append((pos, name))

    regions = {k: [] for k in SECTION_KEYS}
    for i, (start, name) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        regions[name].append(text[start:end])
    return {k: "".join(v) for k, v in regions.items()}


# ---------------------------------------------------------------------------
# K-GAAP (일반기업회계기준) segmentation
#
# Structurally unrelated to the K-IFRS/KASB-translation template above: K-GAAP
# is KASB's OWN native-Korean standard (no IFRS Foundation copyright block at
# all -- confirmed absent from every sampled 장/chapter and from the
# conceptual-framework document), organized by 장 (chapter) rather than by
# 기준서 number, with 본문 paragraphs numbered "<장번호>.<문단번호>" (e.g.
# "13.1", "13.45" for 제13장 '리스') instead of K-IFRS's un-prefixed
# "22"/"5.5.1"/"40G".
#
# Confirmed (2026-07-06) against 9 downloaded real 장 (1/2/3/4/6/7/8/9/10/13/
# 15/31/33 sampled directly, remainder spot-checked) plus the 3 non-chapter
# items (재무회계개념체계, 일반기업회계기준 시행일 및 경과규정,
# 보험업회계처리준칙):
#
# * TITLE BLOCK: every 장 opens with a 4-line block -- "일반기업회계기준",
#   "제N장 <제목>", "한국회계기준원 회계기준위원회", "의결 YYYY. M. D." --
#   then repeats the "제N장 <제목>" heading once more on the next (page-break-
#   separated) page before real content starts. No bare-number TOC precedes
#   this (unlike K-IFRS), so there is no paragraph-number collision risk left
#   unstripped even if the anchor below is missed; cutting past the
#   "의결 YYYY.M.D." line just removes the block for cleanliness. PDF space-
#   rendering is inconsistent even WITHIN one document (e.g. 제31장's own
#   title-block renders with no inter-word spaces at all -- "의결2020. 10.
#   16." -- while its page-2 repeat heading has normal spacing) -- confirmed
#   the same characteristic K-IFRS's PDFs have (see module docstring above)
#   -- so `_loose()` is reused here too.
# * BODY: 본문 paragraphs are numbered "<장번호>.<문단번호>" (e.g. "13.1"
#   .."13.53") for the 33 numbered 장. The non-chapter items number
#   differently: 재무회계개념체계 uses bare "N." (digit + literal period +
#   space, e.g. "2. 본개념체계는..." -- confirmed NOT to match K-IFRS's own
#   DIGIT_PARA_RE, which requires whitespace immediately after the digits
#   with no intervening period), while 시행일 및 경과규정 uses bare "N"
#   (no chapter prefix, since it is not itself a 장) and 보험업회계처리준칙
#   (a pre-2011 "종전 기업회계기준" grandfathered into the 일반기업회계기준
#   category until superseded, per its own in-document editorial note) uses
#   legacy "N. <heading>" numbering with "(N-M)" parenthesized sub-items that
#   are not separately numbered here. chunk.py's KGAAP_BODY_PARA_RE covers
#   the first three shapes with one pattern; "(N-M)" sub-items are swept up
#   as part of whichever top-level "N." paragraph precedes them (same
#   coarser-grained-but-faithful tolerance K-IFRS's own chunker already has
#   for prose subheadings sitting between two real paragraph markers).
# * APPENDIX ("부록"): a 장 that has one opens with a self-referential
#   "일반기업회계기준 제N장 '<제목>'의" line followed immediately by a bare
#   "부록" heading line, which in turn is immediately followed by ONE of up
#   to four sub-headings (order not fixed, not all always present -- e.g.
#   제31장 has only 결론도출근거, no 실무지침/적용사례; 시행일 및 경과규정's
#   own 부록 has only 소수의견):
#     - 결론도출근거 (Basis for Conclusions) -- paragraphs "결<N>.<M>".
#       SAME term K-IFRS uses for its own BC section, so the existing
#       _BC_DIVIDER_RE is reused as-is (not redefined).
#     - 실무지침 (Practical/Implementation Guidance) -- paragraphs
#       "실<N>.<M>". This is K-GAAP's 적용지침-equivalent (문단 1.2 of 제1장
#       itself describes 부록 as composed of "결론도출근거, 실무지침 및
#       적용사례"; 실무지침 is the one of the three never accompanied by
#       "이 기준의 일부를 구성하지 아니한다"-style self-disclaiming language
#       anywhere near it in any sample checked, unlike 결론도출근거/
#       적용사례/소수의견) -- kept, tagged tier="적용지침" for cross-GAAP
#       consistency with schema.TIERS (same output tier name as K-IFRS's own
#       부록 A/B/C application guidance).
#     - 적용사례 (Illustrative Examples) -- case-based, numbered "사례1",
#       "사례2" (no chapter prefix, no decimal). SAME term/divider shape
#       K-IFRS uses for its own IE section, so the existing _IE_DIVIDER_RE is
#       reused as-is. Dropped (non-authoritative, case illustrations only).
#     - 소수의견 (board member dissenting opinion, confirmed present in the
#       시행일 및 경과규정 부록) -- paragraphs "소<N>". Dropped alongside
#       결론도출근거/적용사례 (rationale/opinion commentary, not the standard
#       itself) via its own divider, routed into the same "결론도출근거"
#       bucket as a labeling convenience only (both dropped identically by
#       chunk_pages, mirroring how K-IFRS routes its own board-resolution
#       voting log into the same bucket -- see split_sections's docstring
#       above).
# * 재무회계개념체계 (conceptual framework) has NO 부록/결론도출근거/
#   실무지침/적용사례 of its own (confirmed: 0 occurrences of all four terms
#   in the full downloaded text) -- entirely "본문"-tier once its frontmatter
#   is stripped. Its own frontmatter is much larger than a 장's: a short
#   "정본"(official-text) disclaimer + a "서문"(preface) + a multi-page,
#   per-chapter-repeating mini-TOC (headed "내\n용", PDF-wrapped from "내용")
#   that closes each block with a "문단번호" column of paragraph-range
#   previews (e.g. "1-3", "4-5", ...) -- the same per-chapter-mini-TOC-repeat
#   shape K-IFRS's OWN 개념체계 has (see _CHAPTER_TOC_RE above), just headed
#   "내용" instead of "목차". Anchoring on the LAST "문단번호" occurrence
#   (bounded -- see _KGAAP_FRAMEWORK_TOC_BOUND) and sweeping to the next
#   blank line removes the disclaimer+preface+TOC in one shot, degrading to a
#   no-op (nothing dropped) for every 장, none of which contain "문단번호" at
#   all. 보험업회계처리준칙 has no "의결" title block at all (it predates
#   that convention -- "제 정 1998. 12. 10" / "개정 YYYY.M.D." instead) and
#   no "문단번호" TOC either, so BOTH anchors below legitimately no-op for
#   it: its own short KASB editorial note + enactment/amendment history block
#   is left as harmless residue attached ahead of its first real paragraph
#   (same "cosmetic, not a fidelity violation" tolerance as everywhere else
#   in this module), rather than risk a bespoke third anchor for one legacy
#   document.
# ---------------------------------------------------------------------------

# Bounded the same way as K-IFRS's own _TOC_SCAN_BOUND (see above): every
# legitimate "문단번호" occurrence confirmed in the real 재무회계개념체계
# sits at <=6,200 chars from the start of the document (3 per-chapter-preview
# blocks, the last starting around char 6,100); every 장 (which never
# contains this marker at all) trivially has none within any bound. Kept far
# above the legitimate range and far below "search the whole document" to
# preserve the same never-mistake-real-content-for-frontmatter guarantee.
_KGAAP_FRAMEWORK_TOC_BOUND = 15000

# The tiny title-block date line ("의결 YYYY. M. D.") sits within the first
# couple hundred characters in every sampled 장/non-chapter item that has one
# (confirmed <=120 chars in every one of 제1/2/3/4/6/7/8/9/10/13/15/31/33장,
# 시행일 및 경과규정). Bounded for the same reason as every other anchor in
# this module: a miss here degrades to "title block left unstripped"
# (harmless -- see module comment above), never an unbounded reach into real
# body content.
_KGAAP_ENACTMENT_SCAN_BOUND = 600

# Some (not all -- confirmed absent from 제1-25장's own downloads, present in
# 제26장) 장 PDFs additionally carry a WHOLE-STANDARD-SET "목차"/"목   차"
# (Table of Contents listing all 33 장 by title, no paragraph-range column at
# all -- unlike 재무회계개념체계's own "문단번호"-columned TOC, so a separate
# anchor is needed) right after the tiny title block, occasionally spanning a
# page break (confirmed: 제26장 repeats the "목   차" heading a second time
# after a "- 2 -" page-break marker, continuing the same chapter list, and
# ending with a trailing mention of "...회계기준위원회의 의결" as the TITLE of
# the enactment-log section being previewed -- exactly the shape
# _BOARD_RESOLUTION_RE exists to catch, confirmed empirically: this TOC leaked
# into a 본문 record and tripped that leak signature before this anchor was
# added). Confirmed real span in 제26장: first occurrence at char 55 (right
# after its 53-char title block), last occurrence at char 383, sweeping to
# the next blank line at char 606 -- the WHOLE 33-chapter+3-item list is
# <=560 chars end to end. Bounded well above that (a 2nd, 3rd, ... page
# repeat of the same list would still comfortably fit) and far below "search
# the whole document", same guarantee as every other anchor here.
_KGAAP_MASTER_TOC_BOUND = 3000

_KGAAP_TOC_MARKER_RE = re.compile(_loose("문단번호"))
_KGAAP_ENACTMENT_RE = re.compile(
    _loose("의결") + r"[ \t\n]*\d{4}[.\s]+\d{1,2}[.\s]+\d{1,2}\.?"
)
_KGAAP_MASTER_TOC_RE = re.compile(_loose("목") + r"[ \t\n]*" + _loose("차"))

# 실무지침/소수의견 headings: standalone lines, same shape as K-IFRS's own
# _IE_DIVIDER_RE/_BC_DIVIDER_RE (confirmed: every real heading occurrence
# sampled sits alone on its own line; the only OTHER occurrences found in
# real text are inline cross-references glued mid-line to surrounding prose
# with no preceding line break at all -- e.g. real 제13장 문단결13.11's
# "...구체적인적용을위한기준으로서실무지침에서75%(리스기간/내용연수)를제시
# 하였다", confirmed NOT matched by requiring the line to contain nothing
# else -- exactly the same false-positive shape K-IFRS's own module comment
# warns bare-keyword gates about).
_KGAAP_GUIDANCE_DIVIDER_RE = re.compile(r"(?m)^실무지침\s*$")
_KGAAP_DISSENT_DIVIDER_RE = re.compile(r"(?m)^소수의견\s*$")

# NOTE on a fallback that was tried and deliberately reverted: 제9장's HWP
# attachment (the one K-GAAP chapter needing an HWP fallback -- see
# sources.py) is missing the literal "실무지침" heading text from its
# extraction entirely (hwp5txt renders "<표>" in place of whatever the
# heading sat inside -- a table/textbox it cannot extract text from), even
# though its "실9.1", "실9.2", ... paragraphs extract as real text right
# after it -- so _KGAAP_GUIDANCE_DIVIDER_RE never fires for that one
# chapter, and its 실무지침 content is retained but stays classified as
# 본문 tier rather than 적용지침 (a documented, minor known limitation, NOT
# a fidelity violation -- nothing is dropped or leaked, see the ingestion
# report). A same-shape, unconfirmed content-based fallback (switching
# region the moment a bare "실<N>.<M>"-shaped line was seen ANYWHERE) was
# tried to recover this, but confirmed EMPIRICALLY to be unsafe: it fired
# on an incidental "실..."-shaped line inside 제18장's own (correctly
# dropped) 결론도출근거 text, misclassifying part of that BC discussion as
# kept 적용지침 -- caught by assert_no_leak's toc_heading signature, exactly
# the "unbounded reach into unrelated real content" failure mode this
# module's anchors are designed to avoid elsewhere (see e.g. _TOC_SCAN_BOUND
# above). A single missing heading in one HWP file is a smaller, safer
# thing to accept than a heuristic that can silently misclassify OTHER,
# otherwise-correct chapters, so no such fallback is used.


def strip_frontmatter_kgaap(text):
    """K-GAAP counterpart to strip_frontmatter(): removes, in document order,
    (1) the tiny "의결 YYYY.M.D."-anchored title block every 장/non-chapter
    item opens with, (2) a whole-standard-set "목차" chapter listing some 장
    PDFs additionally carry right after that title block (confirmed present
    in 제26장, absent from 제1-25장), and (3) (only for documents that have
    one -- confirmed so far only the 재무회계개념체계, which has neither of
    the first two) the multi-block "문단번호"-anchored preface+TOC. Each step
    is independently no-op-safe and only ever searches forward from where the
    previous step left off (see module comment above), so this never
    mistakes real body content for frontmatter even when any subset of the
    three anchors is absent -- exactly like strip_frontmatter()'s own
    degrade path for K-IFRS.

    Returns (kept_text, dropped_info) -- same shape as strip_frontmatter()'s
    return value, so callers do not need to special-case the GAAP."""
    info = {"copyright_removed": False, "toc_removed": False, "toc_anchor": None,
            "chars_dropped": 0, "dropped_text": ""}
    cut = 0

    enactment = _KGAAP_ENACTMENT_RE.search(text, cut, cut + _KGAAP_ENACTMENT_SCAN_BOUND)
    if enactment:
        cut = _advance_past_paragraph(text, enactment.end(), _BLANK_SWEEP_BOUND)
        info["copyright_removed"] = True

    master_toc_matches = list(_KGAAP_MASTER_TOC_RE.finditer(text, cut, cut + _KGAAP_MASTER_TOC_BOUND))
    if master_toc_matches:
        cut = _advance_past_paragraph(text, master_toc_matches[-1].end(), _BLANK_SWEEP_BOUND)
        info["toc_removed"] = True
        info["toc_anchor"] = "목차"

    toc_matches = list(_KGAAP_TOC_MARKER_RE.finditer(text, cut, cut + _KGAAP_FRAMEWORK_TOC_BOUND))
    if toc_matches:
        cut = _advance_past_paragraph(text, toc_matches[-1].end(), _BLANK_SWEEP_BOUND)
        info["toc_removed"] = True
        info["toc_anchor"] = "문단번호"

    info["chars_dropped"] = cut
    info["dropped_text"] = text[:cut]
    return text[cut:], info


def split_sections_kgaap(text):
    """K-GAAP counterpart to split_sections(): everything up to the first
    부록 sub-heading is 본문; 실무지침 is the KEPT 적용지침-equivalent
    (application guidance) region; 결론도출근거 and 적용사례 (SAME terms/
    divider shapes K-IFRS itself uses -- _BC_DIVIDER_RE/_IE_DIVIDER_RE are
    reused as-is, not redefined) and 소수의견 (dissenting board-member
    opinion, K-GAAP-specific) are all dropped, the latter routed into the
    "결론도출근거" bucket as a labeling convenience only -- see module
    comment above. The bare "부록" line itself is deliberately NOT a
    boundary: it is always immediately followed by one of the four
    sub-headings above in every sample seen, so the few words between it and
    that sub-heading (e.g. "일반기업회계기준 제13장 '리스'의") are harmless
    residue left attached to the tail of 본문's last real paragraph, same
    tolerance as K-IFRS's own split_sections has for comparable residue.

    If no "실무지침" heading is found at all (confirmed real case: 제9장's
    HWP attachment -- see module comment above), 본문 simply extends through
    that content instead of misclassifying it -- a documented, minor
    limitation, never a fidelity violation."""
    marks = [(m.start(), "적용지침") for m in _KGAAP_GUIDANCE_DIVIDER_RE.finditer(text)]
    marks += [(m.start(), "결론도출근거") for m in _BC_DIVIDER_RE.finditer(text)]
    marks += [(m.start(), "적용사례") for m in _IE_DIVIDER_RE.finditer(text)]
    marks += [(m.start(), "결론도출근거") for m in _KGAAP_DISSENT_DIVIDER_RE.finditer(text)]
    marks.sort(key=lambda x: x[0])

    boundaries = [(0, "본문")]
    for pos, name in marks:
        if boundaries[-1][1] != name:
            boundaries.append((pos, name))

    regions = {k: [] for k in SECTION_KEYS}
    for i, (start, name) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        regions[name].append(text[start:end])
    return {k: "".join(v) for k, v in regions.items()}


# ---------------------------------------------------------------------------
# CAS (中国企业会计准则 / China ASBE) segmentation
#
# Structurally unrelated to both K-IFRS's and K-GAAP's templates above: CAS
# source documents are HTML pages (trafilatura-extracted -- see
# tools/ingest/extract.py's "html" branch), one paragraph per source `<p>`/
# table-row, from two different sites (see tools/ingest/sources.py's CAS
# registry docstring for why): casc.org.cn (中国会计准则委员会, official)
# for 준칙 본문 + most 해석, and cas.xmu.edu.cn (Xiamen University mirror)
# for all 응用指南 and the remaining 해석. THREE fundamentally different
# per-file shapes, confirmed against all 95 real downloaded files
# (43 준칙 본문 incl. 기본준칙 + 32 응용지침 + 20 해석):
#
# 1. 준칙 본문 (기본준칙 + 42 구체준칙): chaptered, numbered "第<한자숫자>条"
#    (Chinese-numeral articles, e.g. "第一条".."第六十八条" for CAS21 租赁),
#    optionally grouped under "第<한자숫자>章" (chapter) and "第<한자숫자>节"
#    (section) headings -- both excluded from paragraph-boundary detection
#    below by requiring the "条" suffix specifically (a chapter/section
#    heading never ends in "条"). No appendix/BC/IE-equivalent structure
#    exists in these documents at all -- 응용指南 and 해석 are always
#    SEPARATE files/URLs from their parent 준칙's own body (unlike K-IFRS's
#    부록 A/B/C or K-GAAP's 실무지침, both embedded in the SAME PDF as 본문),
#    so there is no within-document tier split to perform here; tier is a
#    property of which FILE a given download is, decided by the caller (see
#    chunk_pages' `tier`/`para_pattern` parameters, and
#    tools/ingest/run_ingest.py's `ingest_cas`).
# 2. 응용指南 (application guidance, only 32 of the 42 구체준칙 have one --
#    e.g. 15/25/26/29/32/36/39/40/41/42 never got a separate 应用指南 of
#    their own): unchaptered prose, top-level sections numbered bare
#    "<한자숫자>、" (Chinese numeral + IDEOGRAPHIC COMMA, e.g. "一、"，"二、"，
#    no space after -- confirmed distinct from 준칙 본문's "第X条 " shape,
#    which DOES carry a real space/nbsp after "条"), with nested "（一）"
#    (parenthesized) and "1." (arabic-dot) sub-items that carry no
#    line-start numeral alone and so are swept up into their enclosing
#    "<한자숫자>、" chunk (coarser-grained-but-faithful, same tolerance
#    K-IFRS's own chunker already has for prose subheadings between two real
#    paragraph markers). One confirmed exception (CAS17 借款费用's
#    guidance): plain unstructured prose with no "<한자숫자>、" heading at
#    all -- degrades to a single unnumbered ("0") chunk, same universal
#    fallback every other GAAP's chunker already has.
# 3. 해석 (interpretations 1-20): SAME "<한자숫자>、" top-level numbering as
#    응용指南 (not article-numbered like 본문), typically closing with a
#    "<N>、生效日期" (effective-date) section. Kept as 본문 tier per the task
#    spec (해석 has the same authority as the standard it interprets) but
#    chunked with the SECTION pattern, not the article pattern -- selected
#    per-file by the caller via `para_pattern`, exactly like 응용指南.
#
# Both `strip_frontmatter_cas` and `split_sections_cas` are anchor-based,
# same discipline as every other stripper in this module: every anchor below
# is independently optional (a miss just leaves that particular piece of
# boilerplate in place as harmless residue attached to the nearest
# unnumbered "0" chunk -- never an unbounded reach into real content).
# Confirmed boilerplate shapes, by source:
#   * casc.org.cn 준칙 본문 pages: an optional bare leading "财会[YYYY]N号"-
#     style circular-number line (bracket style is NOT consistent --
#     confirmed ASCII "[ ]" in some samples, full-width "〔 〕" and small
#     tortoise-shell "﹝ ﹞" in others), then straight into 章/条 -- no
#     other frontmatter, no copyright block (this is a PRC government
#     ministry's own portal, not an IFRS-Foundation-style copyrighted
#     translation), and a STABLE trailing footer on every single page
#     (address/email/copyright/tech-support/WeChat mentions).
#   * casc.org.cn 해석 pages that publish the interpretation's text inline
#     (confirmed for 해석4-8, 19, 20): a standard PRC official-notice
#     (公文) preamble -- "财会〔...〕N号" + a distribution-list line ending
#     "...有关单位：" + a short transmittal paragraph ending "现予印发，请
#     遵照执行。" + "执行中如有问题，请及时反馈我部。" + a right-aligned
#     "财 政 部" + date signature block -- before the interpretation's own
#     title repeats and its real "一、..." content begins. (The other 13
#     해석's casc.org.cn notice pages are memo-ONLY, pointing to a detached
#     attachment -- handled by sourcing those from elsewhere entirely, see
#     sources.py; this anchor legitimately does not fire for them.)
#   * cas.xmu.edu.cn pages (응용指南 + 해석 1-3/9-15): the site's own title
#     line, then a "时间：YYYY-MM-DD 浏览：次" (upload-date/view-count) line,
#     then EITHER the title repeated a second time (응용指南 template) OR a
#     "发文文号/颁布单位/颁布日期/实施日期/废除日期/原文网址" metadata table
#     (해석 template, rendered by trafilatura as a sequence of "| key |
#     value |" lines) -- before real content begins. No trailing footer on
#     this site (confirmed absent from every sample).
# ---------------------------------------------------------------------------

_CJK_NUM = "一二三四五六七八九十百千零两"

# Optional bare leading circular-number line on casc.org.cn 준칙 본문 pages,
# e.g. "财会[2006]3号" / "财会〔2021〕35号" / "财会﹝2017﹞16号" -- bracket
# style confirmed inconsistent across samples (ASCII, full-width tortoise-
# shell, small-form tortoise-shell), so all three are accepted. Anchored to
# the very start of the text (re.match, not re.search) since this is only
# ever seen as literally the first line -- never searched for elsewhere, so
# it can never mistake a mid-document mention of some OTHER circular for
# frontmatter.
_CAS_WENHAO_LINE_RE = re.compile(r"\s*财会[\[〔﹝][0-9]{4}[\]〕﹞]\s*[0-9]+\s*号\s*\n")

# cas.xmu.edu.cn's own upload-date/view-count line, present near the front of
# every mirror page (응용指南 and 해석 alike): "时间：2022-08-05 浏览：次".
_CAS_XMU_VIEWCOUNT_RE = re.compile(r"时间[：:]\s*\d{4}-\d{2}-\d{2}\s*浏览[：:]\s*次")

# The LAST row of cas.xmu.edu.cn's own 해석 metadata table (see module
# docstring) -- "原文网址" ("original source URL"), always followed by the
# casc.org.cn URL this very document was itself transcribed from. Cutting
# through the end of this line removes the whole table in one shot (the
# table's own first row, and every row above "원문网址", is between the
# viewcount line and this row with nothing else -- confirmed in every 해석
# 1-3/9-15 sample) without needing to separately anchor each of its
# individual "发文文号"/"颁布单位"/... rows. A no-op (nothing to remove) for
# every 응용指南 page, which has no such table.
_CAS_XMU_SOURCE_URL_ROW_RE = re.compile(r"原文网址[^\n]*\n?")

# casc.org.cn's own official-notice (公文) transmittal preamble for the 7
# 해석 it publishes inline (4-8, 19, 20) -- see module docstring. Anchored on
# the stable sign-off phrase "请遵照执行" through the dated "财政部" signature
# block that always immediately follows it; bounded gaps throughout, same
# discipline as every other anchor in this module (a miss here just leaves
# the memo attached to the nearest unnumbered "0" chunk, never an unbounded
# reach into real content). Legitimately does not fire on 준칙 본문 pages
# (which have no transmittal memo at all) or on any 해석 sourced from
# cas.xmu.edu.cn (whose own template has no such memo either -- its "原文网址"
# row is a plain citation, not a live transmittal paragraph).
_CAS_MEMO_RE = re.compile(
    r"请遵照执行[。.]?[\s\S]{0,120}?财\s*政\s*部[\s\S]{0,20}?[0-9]{4}\s*年\s*[0-9]{1,2}\s*月\s*[0-9]{1,2}\s*日"
)

# The stable trailing footer on every casc.org.cn page (본문 and inline-
# published 해석 alike): a physical address/postcode/email line followed by
# a copyright/tech-support attribution and two WeChat mentions. Confirmed
# identical, verbatim, across every one of the 63 casc.org.cn-sourced files
# downloaded. Absent from cas.xmu.edu.cn pages (confirmed no trailing
# boilerplate there at all) -- a no-op for those.
_CAS_FOOTER_RE = re.compile(r"地址：\s*北京市西城区月坛南街")


def strip_frontmatter_cas(text):
    """CAS counterpart to strip_frontmatter()/strip_frontmatter_kgaap(): strips
    whichever of the site-specific boilerplate shapes documented in this
    module's CAS section are present (bare circular-number line, casc.org.cn
    transmittal memo, cas.xmu.edu.cn view-count line, cas.xmu.edu.cn 해석
    metadata table, casc.org.cn trailing footer) -- every step is
    independently no-op-safe, so this never mistakes real 준칙/응용指南/해석
    content for frontmatter even when any subset of these anchors is absent
    (e.g. every 응용指南 page legitimately has no memo and no metadata
    table; every 준칙 본문 page legitimately has no view-count line at all).

    Returns (kept_text, dropped_info) -- same shape as strip_frontmatter()'s
    own return value."""
    info = {"copyright_removed": False, "toc_removed": False, "toc_anchor": None,
            "chars_dropped": 0, "dropped_text": ""}
    cut = 0

    wenhao = _CAS_WENHAO_LINE_RE.match(text)
    if wenhao:
        cut = wenhao.end()
        info["copyright_removed"] = True

    memo = _CAS_MEMO_RE.search(text, cut, cut + 700)
    if memo:
        cut = memo.end()
        info["toc_removed"] = True
        info["toc_anchor"] = "casc_transmittal_memo"

    viewcount = _CAS_XMU_VIEWCOUNT_RE.search(text, cut, cut + 300)
    if viewcount:
        cut = viewcount.end()
        info["toc_removed"] = True
        info["toc_anchor"] = info["toc_anchor"] or "xmu_viewcount"

    source_row = _CAS_XMU_SOURCE_URL_ROW_RE.search(text, cut, cut + 800)
    if source_row:
        cut = source_row.end()
        info["toc_removed"] = True
        info["toc_anchor"] = "xmu_metadata_table"

    kept = text[cut:]
    footer = _CAS_FOOTER_RE.search(kept)
    if footer:
        kept = kept[:footer.start()]
        info["copyright_removed"] = True

    info["chars_dropped"] = len(text) - len(kept)
    info["dropped_text"] = text[:cut]
    return kept, info


def split_sections_cas(text):
    """CAS counterpart to split_sections()/split_sections_kgaap(). Unlike
    K-IFRS/K-GAAP, a CAS download is ALWAYS single-tier already -- 준칙 본문,
    응용指南, and 해석 are always separate files/URLs (see sources.py's CAS
    registry and this module's CAS docstring above), never bundled into one
    PDF the way K-IFRS packs 본문+부록+BC+IE together. So there is no real
    within-document region to split out here: the whole (already
    frontmatter-stripped) text is returned as 본문, with the other three
    keys always empty. This deliberately makes chunk_pages' own
    `has_structure` check False for every CAS document, so tier is decided
    by the CALLER (chunk_pages' `tier` parameter) per file, exactly as
    tools/ingest/run_ingest.py's `ingest_cas` needs -- not guessed from
    content that was never split-worthy to begin with."""
    return {"본문": text, "적용지침": "", "결론도출근거": "", "적용사례": ""}
