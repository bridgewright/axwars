"""Layer 1: map each source-GAAP account to its IFRS presentation account."""
from .schema import MappedLine
from .knowledge import load_mappings, find_mapping


def map_accounts(tb):
    mappings = load_mappings(tb.source_gaap)
    out = []
    for acc in tb.accounts:
        m = find_mapping(acc.name_src, mappings)
        if m:
            out.append(MappedLine(
                source=acc, ifrs_account=m["ifrs_account"],
                statement=m["statement"], section=m["section"],
                standard=m["standard"], note=m.get("note", ""), basis=m.get("basis", {})))
        else:
            out.append(MappedLine(
                source=acc, ifrs_account=acc.name_src,
                statement="?", section="미분류", standard="",
                flagged=True, flag_reason="매핑규칙 없음 — 수동 매핑 필요"))
    return out
