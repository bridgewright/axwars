import re

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
    cov = roundtrip_coverage(raw_text, records)
    if cov < min_cov:
        raise FidelityError(f"coverage {cov:.4f} < {min_cov}")

def dual_extract_diff(a, b):
    ca, cb = _canon(a), _canon(b)
    if not ca and not cb:
        return 0.0
    import difflib
    return 1.0 - difflib.SequenceMatcher(None, ca, cb).ratio()
