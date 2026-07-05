#!/usr/bin/env python3
"""검증 파이프라인 end-to-end 실증 (문항 5) — 다조정 전환.

엔진이 산출한 K-IFRS 자본·조정을 IFRS 1101 전환조정 '정답셋'과 대조해 일치 여부를
판정하는 전체 흐름을, ECL·재평가·개발비·리스 4개 조정이 섞인 전환 시나리오로 보여준다.
정답셋(ground truth)은 전환 상장사의 첫 K-IFRS 주석(IFRS 1101 '종전기업회계기준 →
K-IFRS 자본 조정표')에서 온다.

정직 고지: 아래 정답셋은 '독립 수기계산'으로 재구성한 다조정 전환이다. 특정 전환사의
실제 공시 조정표를 확보하면 transition_ground_truth.json 값만 교체하면 된다. 대형 상장사의
전환주석은 첫 K-IFRS 연도(조기채택 2010 / 정규 2011) 보고서에만 있고 문서구조 편차가 커
OpenDART 자동추출은 best-effort다(analysis/fetch_ifrs1_note.py).

사용: python3 analysis/validate_transition_demo.py
"""
import os
import sys
import json

PKG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gaap-ifrs")
sys.path.insert(0, PKG)

from gaap_ifrs.convert import run_conversion          # noqa: E402
from gaap_ifrs.validate import validate_against        # noqa: E402

FX = os.path.join(PKG, "tests/fixtures")


def main():
    extra = json.load(open(os.path.join(FX, "transition_extra.json"), encoding="utf-8"))
    gt = json.load(open(os.path.join(FX, "transition_ground_truth.json"), encoding="utf-8"))
    result = run_conversion(os.path.join(FX, "transition_tb_kgaap.csv"), "K-GAAP", extra)
    report = validate_against(result, gt)

    eq = report["ifrs_equity"]
    print("=== IFRS 1101 전환 검증 (엔진 ↔ 정답셋) · 4개 조정 종합 ===")
    print(f"자본총계  엔진 {eq['engine']:,.0f}  vs  정답 {eq['ground_truth']:,.0f}  "
          f"→ 차이 {eq['diff']:,.2f} ({eq['pct']}%)  [{'일치' if eq['match'] else '불일치'}]")
    print("\n조정 항목별 (정답 ↔ 엔진):")
    for l in report["lines"]:
        status = "일치" if l["match"] else "불일치"
        em = f"{l['engine_amount']:,.0f}" if l["engine_amount"] is not None else "-"
        print(f"  - '{l['ground_truth_label']}' {l['ground_truth_amount']:>12,.0f}  ↔  "
              f"'{l['engine_match']}' {em:>14}  [{status}]")
    print(f"\n종합 판정: {'PASS ✅' if report['overall_match'] else 'FAIL ❌'}")


if __name__ == "__main__":
    main()
