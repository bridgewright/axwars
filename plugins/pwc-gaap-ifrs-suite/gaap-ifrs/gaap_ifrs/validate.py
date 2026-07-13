"""Validate engine output against a published IFRS 1101 transition reconciliation.

Ground truth (from a real K-GAAP -> K-IFRS transition company's first K-IFRS
notes) is expected as:
  {"ifrs_equity": <int>, "adjustment_lines": {<label>: <equity_effect>, ...}}

The engine's IFRS equity and per-adjustment equity effects are compared within
a tolerance. This is how the tool proves it reproduces real transitions (문항 5).
"""


def validate_against(result, ground_truth, tol=1.0):
    engine_eq = result.impact["metrics"]["자본총계"]["ifrs"]
    gt_eq = ground_truth["ifrs_equity"]
    diff = engine_eq - gt_eq
    equity = {
        "engine": engine_eq, "ground_truth": gt_eq, "diff": diff,
        "match": abs(diff) <= tol,
        "pct": round(diff / gt_eq * 100, 4) if gt_eq else 0.0,
    }

    engine_lines = {a.title: a.equity_effect() for a in result.adjustments if not a.flagged}
    gt_lines = ground_truth.get("adjustment_lines", {})
    line_results = []
    for label, gt_amt in gt_lines.items():
        # match by nearest engine adjustment amount within tolerance
        best = None
        for etitle, eamt in engine_lines.items():
            if abs(eamt - gt_amt) <= max(tol, abs(gt_amt) * 0.01):
                best = (etitle, eamt)
                break
        line_results.append({
            "ground_truth_label": label, "ground_truth_amount": gt_amt,
            "engine_match": best[0] if best else None,
            "engine_amount": best[1] if best else None,
            "match": best is not None,
        })

    return {
        "ifrs_equity": equity,
        "lines": line_results,
        "overall_match": equity["match"] and all(l["match"] for l in line_results),
    }
