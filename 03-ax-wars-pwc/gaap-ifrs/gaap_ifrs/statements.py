"""Build IFRS BS/PL from mapped lines and adjustment entries."""
from collections import defaultdict


def build_statements(mapped, adjustments):
    bs = defaultdict(lambda: defaultdict(float))
    pl = defaultdict(lambda: defaultdict(float))
    for ml in mapped:
        tgt = pl if ml.statement == "PL" else bs          # BS or "?" both land in BS
        tgt[ml.section][ml.ifrs_account] += ml.source.amount
    # Post each non-flagged adjustment's balanced entries.
    for adj in adjustments:
        if adj.flagged:
            continue
        for e in adj.entries:
            section = e.get("section", "")
            account = e["account"]
            delta = e.get("delta", 0.0)
            tgt = pl if e.get("statement") == "PL" else bs
            tgt[section][account] += delta
    return ({k: dict(v) for k, v in bs.items()}, {k: dict(v) for k, v in pl.items()})
