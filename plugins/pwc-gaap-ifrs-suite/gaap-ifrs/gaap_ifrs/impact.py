"""Compute source-GAAP vs IFRS impact on key totals + a narrative.

Totals are summed from the actual statements (pre-adjustment vs post-adjustment),
so gross-ups (e.g. lease) and equity moves (e.g. revaluation) are all reflected.
"""
from .statements import build_statements

ASSET_SECTIONS = ("유동자산", "비유동자산")
LIAB_SECTIONS = ("유동부채", "부채")
EQUITY_SECTIONS = ("자본",)


def _total(bs, sections):
    return sum(v for s in sections for v in bs.get(s, {}).values())


def compute_impact(mapped, adjustments):
    src_bs, _ = build_statements(mapped, [])
    ifrs_bs, _ = build_statements(mapped, adjustments)
    metrics = {}
    for label, sections in (("자산총계", ASSET_SECTIONS),
                            ("부채총계", LIAB_SECTIONS),
                            ("자본총계", EQUITY_SECTIONS)):
        s = _total(src_bs, sections)
        i = _total(ifrs_bs, sections)
        metrics[label] = {"source": s, "ifrs": i, "delta": i - s,
                          "pct": round((i - s) / s * 100, 2) if s else 0.0}
    flags = [a.title for a in adjustments if a.flagged]
    eq = metrics["자본총계"]
    narrative = (f"전환조정으로 자본총계 {eq['delta']:,.0f} ({eq['pct']}%), "
                 f"자산총계 {metrics['자산총계']['delta']:,.0f} 변동. ")
    if flags:
        narrative += f"추가 판단/자료 필요: {', '.join(flags)}."
    else:
        narrative += "미해결(flagged) 항목 없음."
    return {"metrics": metrics, "narrative": narrative}
