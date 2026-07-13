"""Build the conversion reconciliation (전환조정 명세서) — the audit-trail output."""

_EQUITY = ("자본금", "이익잉여금", "이월이익잉여금", "자본잉여금")


def _equity(tb):
    return sum(a.amount for a in tb.accounts if a.name_src in _EQUITY)


def build_reconciliation(tb, mapped, adjustments):
    rows = []
    for ml in mapped:
        rows.append({
            "kind": "reclass", "source": ml.source.name_src,
            "ifrs_account": ml.ifrs_account, "amount": ml.source.amount,
            "standard": ml.standard,
            "flag": ml.flag_reason if ml.flagged else "",
        })
    adj_total = 0.0
    for a in adjustments:
        eff = a.equity_effect()
        entries_str = "; ".join(f"{e['account']} {e.get('delta', 0):+,.0f}" for e in a.entries)
        rows.append({
            "kind": "adjustment", "item": a.title, "entries": entries_str,
            "equity_effect": eff, "standard": a.standard,
            "confidence": a.confidence, "flagged": a.flagged, "note": a.note,
        })
        if not a.flagged:
            adj_total += eff
    src_eq = _equity(tb)
    rows.append({
        "kind": "bridge", "item": "자본 전환 브릿지",
        "source_equity": src_eq, "adjustments": adj_total,
        "ifrs_equity": src_eq + adj_total,
    })
    return rows
