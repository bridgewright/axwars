"""Orchestrate the full conversion pipeline."""
from .parse import load_trial_balance
from .mapping import map_accounts
from .adjustments import apply_adjustments
from .statements import build_statements
from .impact import compute_impact
from .schema import ConversionResult


def run_conversion(tb_path, source_gaap, extra_inputs=None, currency="KRW", period=""):
    tb = load_trial_balance(tb_path, source_gaap, currency, period)
    mapped = map_accounts(tb)
    adjustments = apply_adjustments(tb, extra_inputs, mapped)
    bs, pl = build_statements(mapped, adjustments)
    impact = compute_impact(mapped, adjustments)
    return ConversionResult(tb, mapped, adjustments, bs, pl, impact)
