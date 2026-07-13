"""Canonical data model shared across the conversion pipeline."""
from dataclasses import dataclass, field


@dataclass
class Account:
    name_src: str
    amount: float
    code: str | None = None


@dataclass
class TrialBalance:
    source_gaap: str
    currency: str
    period: str
    accounts: list[Account]


@dataclass
class MappedLine:
    source: Account
    ifrs_account: str
    statement: str          # "BS" | "PL" | "?"
    section: str            # e.g. "유동자산"
    standard: str           # citation, e.g. "K-IFRS 1109"
    note: str = ""          # 이전 GAAP 대비 IFRS 차이/유의점
    basis: dict = field(default_factory=dict)   # 조항 근거(ifrs_ref/requires, prev_gaap, difference)
    flagged: bool = False
    flag_reason: str = ""


@dataclass
class Adjustment:
    """A Layer-2 measurement adjustment.

    `entries` are balanced double-entry postings applied to the IFRS statements:
    each is {"account": str, "section": str, "delta": float}. The net effect on
    equity is derived from the entries landing in the 자본 section — the engine
    never carries a hand-set equity number, so books always balance.
    A flagged adjustment carries no entries (nothing is fabricated).
    """
    id: str
    title: str
    standard: str
    entries: list[dict] = field(default_factory=list)
    confidence: str = "high"                # "high" | "flagged"
    note: str = ""
    basis: dict = field(default_factory=dict)   # 조항 근거(ifrs_ref/requires, prev_gaap, difference, reasoning)
    flagged: bool = False

    def equity_effect(self) -> float:
        return sum(e.get("delta", 0.0) for e in self.entries if e.get("section") == "자본")


@dataclass
class ConversionResult:
    trial_balance: TrialBalance
    mapped: list[MappedLine]
    adjustments: list[Adjustment]
    ifrs_bs: dict
    ifrs_pl: dict
    impact: dict
