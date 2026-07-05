SOURCES = {
    "K-IFRS": {"lang": "ko", "format": "pdf", "base_url": "https://www.kasb.or.kr",
               "standards": [{"no": "1116", "title": "리스", "url": "", "tier_hint": "본문"}]},
    "K-GAAP": {"lang": "ko", "format": "pdf", "base_url": "https://www.kasb.or.kr", "standards": []},
    "US-GAAP": {"lang": "en", "format": "html", "base_url": "https://asc.fasb.org", "standards": []},
    "CAS": {"lang": "zh", "format": "pdf", "base_url": "http://kjs.mof.gov.cn", "standards": []},
    "VAS": {"lang": "vi", "format": "pdf", "base_url": "", "standards": []},
}

def get_source(gaap):
    return SOURCES[gaap]
