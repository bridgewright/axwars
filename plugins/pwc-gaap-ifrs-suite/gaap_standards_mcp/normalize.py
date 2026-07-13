import re, unicodedata

_WS = re.compile(r"\s+")
_CJK = re.compile(r"[　-鿿가-힯]")
_LATIN = re.compile(r"[A-Za-z0-9]+")

def normalize_text(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = _WS.sub(" ", s).strip()
    return s.rstrip(".。·").strip()

def char_ngrams(s: str, n_min=2, n_max=3) -> list[str]:
    cjk = "".join(ch for ch in s if _CJK.match(ch))
    out = []
    for n in range(n_min, n_max + 1):
        out += [cjk[i:i+n] for i in range(len(cjk) - n + 1)]
    return out

def tokenize(s: str) -> list[str]:
    s = normalize_text(s).lower()
    return _LATIN.findall(s) + char_ngrams(s)
