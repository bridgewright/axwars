import sys
import json
import pathlib

# handoff dir (parents[1]) on sys.path so `scripts` importable
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scripts.build_reports import render_brief, render_prd  # noqa: E402

SAMPLE_PATH = pathlib.Path(__file__).resolve().parents[2] / "intake" / "assets" / "sample-discovery.json"
SAMPLE = json.load(open(SAMPLE_PATH, encoding="utf-8"))


def test_brief_has_all_sections():
    md = render_brief(SAMPLE)
    for h in ["도입 적합성", "자동화 범위", "연동 가능성", "지식", "단계적 롤아웃",
              "성과 지표", "변화관리", "미해결"]:
        assert h in md, f"missing section: {h}"


def test_brief_integration_tier_shown():
    md = render_brief(SAMPLE)
    assert "system_task" in md  # 연동 tier가 보고서에 반영


def test_prd_has_toprd_sections():
    md = render_prd(SAMPLE)
    for h in ["Problem Statement", "Solution", "User Stories", "Implementation Decisions",
              "Testing Decisions", "Out of Scope", "Further Notes", "제품 갭"]:
        assert h in md, f"missing section: {h}"


def test_prd_quotes_customer_pain():
    md = render_prd(SAMPLE)
    assert SAMPLE["bottlenecks"][0]["scene"] in md  # 실제 인용 포함


def test_prd_tags_aggregated():
    md = render_prd(SAMPLE)
    assert "[action_task]" in md and "[knowledge_authoring]" in md
