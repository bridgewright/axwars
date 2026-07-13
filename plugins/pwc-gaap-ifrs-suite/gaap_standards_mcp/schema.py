from dataclasses import dataclass, asdict

GAAPS = ["K-IFRS", "K-GAAP", "US-GAAP", "CAS", "VAS"]
TIERS = ["본문", "적용지침"]

@dataclass(frozen=True)
class Record:
    id: str
    gaap: str
    standard_no: str
    standard_title: str
    paragraph_no: str
    heading: str
    text: str          # 원문 verbatim — 인용·표시 전용
    text_norm: str     # 정규화 — 검색·임베딩 전용
    lang: str
    tier: str
    source_url: str
    as_of: str
    extract_flag: bool = False

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)
