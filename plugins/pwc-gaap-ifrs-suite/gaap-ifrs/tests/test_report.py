import os
import json
from gaap_ifrs.convert import run_conversion
from gaap_ifrs.report import write_all


def test_write_all(tmp_path):
    extra = json.load(open("tests/fixtures/sample_aging.json", encoding="utf-8"))
    res = run_conversion("tests/fixtures/sample_tb_kgaap.csv", "K-GAAP", extra)
    paths = write_all(res, str(tmp_path))
    for key in ("financials", "reconciliation", "impact", "difference", "json"):
        assert os.path.exists(paths[key]), key
    diff = open(paths["difference"], encoding="utf-8").read()
    assert "회계기준 전환 차이 분석" in diff and "K-IFRS 1109" in diff
    # 상세 보고서 필수 요소: 조항 근거·판단논리·분개 파급효과·단위
    assert "IFRS 근거" in diff and "판단·작업(엔진)" in diff
    assert "분개 및 파급효과" in diff and "단위: KRW" in diff
    assert "문단" in diff                                   # 조항 문단 인용
    data = json.load(open(paths["json"], encoding="utf-8"))
    assert data["impact"]["metrics"]["자본총계"]["delta"] == 55000
