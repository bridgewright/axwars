import re
from gaap_standards_mcp.schema import Record
from gaap_standards_mcp.normalize import normalize_text

DEFAULT_PARA_RE = re.compile(r"(?m)^\s*((?:\d+[A-Z]?)(?:\.\d+)*)\s+")
_SLUG = {"K-IFRS": "kifrs", "K-GAAP": "kgaap", "US-GAAP": "usgaap", "CAS": "cas", "VAS": "vas"}

def chunk_pages(pages, gaap, standard_no, standard_title, lang, source_url, as_of,
                tier="본문", para_pattern=DEFAULT_PARA_RE):
    full = "\n".join(p.text for p in pages)
    marks = list(para_pattern.finditer(full))
    recs = []
    slug = _SLUG[gaap]
    if not marks:
        text = full.strip()
        if text:
            recs.append(_mk(slug, gaap, standard_no, standard_title, "0", text, lang, tier, source_url, as_of))
        return recs
    if marks[0].start() > 0:
        lead = full[:marks[0].start()].strip()
        if lead:
            recs.append(_mk(slug, gaap, standard_no, standard_title, "0", lead, lang, tier, source_url, as_of))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(full)
        para_no = m.group(1)
        text = full[m.start():end].strip()
        recs.append(_mk(slug, gaap, standard_no, standard_title, para_no, text, lang, tier, source_url, as_of))
    return recs

def _mk(slug, gaap, std, title, para, text, lang, tier, url, as_of):
    return Record(id=f"{slug}:{std}:{para}", gaap=gaap, standard_no=std, standard_title=title,
                  paragraph_no=para, heading="", text=text, text_norm=normalize_text(text),
                  lang=lang, tier=tier, source_url=url, as_of=as_of, extract_flag=False)
