#!/usr/bin/env python3
"""각 소스 GAAP 예제(입력 시산표+조정)를 변환 엔진으로 돌려 산출물을 같은 폴더에 쓴다.

각 examples/<gaap>/ 폴더에 입력(input_trial_balance.csv, input_adjustments.json)과
출력(ifrs_financials.xlsx, reconciliation.xlsx, impact_analysis.xlsx,
difference_analysis.md, result.json)이 함께 정리된다.

사용: python3 examples/build_examples.py
"""
import os
import sys
import json

EX = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(os.path.dirname(EX), "gaap-ifrs")
sys.path.insert(0, PKG)

from gaap_ifrs.convert import run_conversion          # noqa: E402
from gaap_ifrs.report import write_all                 # noqa: E402

CASES = [("kgaap", "K-GAAP", "KRW"), ("usgaap", "US-GAAP", "USD"),
         ("vas", "VAS", "VND"), ("cas", "CAS", "CNY")]


def main():
    for folder, gaap, currency in CASES:
        d = os.path.join(EX, folder)
        tb = os.path.join(d, "input_trial_balance.csv")
        ap = os.path.join(d, "input_adjustments.json")
        extra = json.load(open(ap, encoding="utf-8")) if os.path.exists(ap) else None
        result = run_conversion(tb, gaap, extra, currency=currency)
        write_all(result, d)
        eq = result.impact["metrics"]["자본총계"]
        computed = [a.title for a in result.adjustments if not a.flagged]
        flagged = [a.title for a in result.adjustments if a.flagged]
        print(f"[{gaap:8s}] 자본총계 {eq['source']:,.0f} → {eq['ifrs']:,.0f} "
              f"(Δ {eq['delta']:,.0f}) · 조정 계산 {len(computed)}개, 판단필요 {len(flagged)}개")


if __name__ == "__main__":
    main()
