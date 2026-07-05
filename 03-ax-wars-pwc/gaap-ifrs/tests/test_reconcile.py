import json
from gaap_ifrs.parse import load_trial_balance
from gaap_ifrs.mapping import map_accounts
from gaap_ifrs.adjustments import apply_adjustments
from gaap_ifrs.reconcile import build_reconciliation


def test_reconciliation_has_citation_and_bridge():
    tb = load_trial_balance("tests/fixtures/sample_tb_kgaap.csv", "K-GAAP")
    mapped = map_accounts(tb)
    adjs = apply_adjustments(tb, json.load(open("tests/fixtures/sample_aging.json", encoding="utf-8")))
    rows = build_reconciliation(tb, mapped, adjs)
    ecl_rows = [r for r in rows if r.get("kind") == "adjustment" and "ECL" in r["item"]]
    assert ecl_rows and ecl_rows[0]["standard"] == "K-IFRS 1109"
    bridge = [r for r in rows if r.get("kind") == "bridge"]
    assert bridge and bridge[0]["ifrs_equity"] == bridge[0]["source_equity"] + bridge[0]["adjustments"]
