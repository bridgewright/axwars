"""Validation harness.

Synthetic regression locks the deterministic equity bridge, and the validator
is exercised against an IFRS 1101-style ground truth (match + mismatch cases).
Real-data procedure (README): last K-GAAP audit report as input, first K-IFRS
notes' IFRS 1101 전환조정 as ground truth (fetch via analysis/fetch_ifrs1_note.py).
"""
import json
from gaap_ifrs.convert import run_conversion
from gaap_ifrs.validate import validate_against


def _result():
    extra = json.load(open("tests/fixtures/sample_aging.json", encoding="utf-8"))
    return run_conversion("tests/fixtures/sample_tb_kgaap.csv", "K-GAAP", extra)


def test_regression_equity_bridge():
    res = _result()
    src = sum(a.amount for a in res.trial_balance.accounts if a.name_src in ("자본금", "이익잉여금"))
    ifrs = res.impact["metrics"]["자본총계"]["ifrs"]
    assert ifrs - src == 55000


def test_validate_matches_ground_truth():
    res = _result()
    gt = json.load(open("tests/fixtures/ground_truth_ifrs1.json", encoding="utf-8"))
    report = validate_against(res, gt)
    assert report["overall_match"] is True
    assert report["ifrs_equity"]["match"] is True
    assert report["lines"][0]["match"] is True


def test_validate_detects_mismatch():
    res = _result()
    gt = {"ifrs_equity": 99999999, "adjustment_lines": {"엉뚱한 조정": 12345}}
    report = validate_against(res, gt)
    assert report["overall_match"] is False
    assert report["ifrs_equity"]["match"] is False


def test_validate_multi_adjustment_transition():
    """4개 조정(ECL·재평가·개발비·리스)이 섞인 전환을 정답셋과 대조 → 전건 일치."""
    extra = json.load(open("tests/fixtures/transition_extra.json", encoding="utf-8"))
    res = run_conversion("tests/fixtures/transition_tb_kgaap.csv", "K-GAAP", extra)
    gt = json.load(open("tests/fixtures/transition_ground_truth.json", encoding="utf-8"))
    report = validate_against(res, gt)
    assert report["overall_match"] is True
    assert len(report["lines"]) == 4
    assert all(l["match"] for l in report["lines"])
