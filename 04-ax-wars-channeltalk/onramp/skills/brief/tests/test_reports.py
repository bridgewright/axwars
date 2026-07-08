import sys
import json
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scripts.build_reports import render_brief, render_prd  # noqa: E402

SAMPLE_PATH = pathlib.Path(__file__).resolve().parents[2] / "intake" / "assets" / "sample-discovery.json"
SAMPLE = json.load(open(SAMPLE_PATH, encoding="utf-8"))


def test_brief_is_lead_with_conclusion():
    md = render_brief(SAMPLE)
    # 두괄식: 결론(권고)이 상세 섹션보다 먼저 온다
    assert "결론 먼저" in md
    assert md.index("결론 먼저") < md.index("왜 지금인가")


def test_brief_has_core_sections():
    md = render_brief(SAMPLE)
    for h in ["결론 먼저", "왜 지금인가", "무엇부터 자동화", "연동 진단",
              "지식", "성공을 무엇으로", "상담팀은 어떻게", "결정"]:
        assert h in md, f"missing section: {h}"


def test_brief_integration_tier_shown():
    md = render_brief(SAMPLE)
    assert "system_task" in md


def test_prd_is_lead_with_recommendation():
    md = render_prd(SAMPLE)
    assert "결론 먼저 — 제언" in md
    assert md.index("결론 먼저") < md.index("Problem Statement")


def test_prd_has_toprd_sections():
    md = render_prd(SAMPLE)
    for h in ["Problem Statement", "Solution", "User Stories", "Implementation Decisions",
              "Testing Decisions", "Out of Scope", "Further Notes", "제품 갭"]:
        assert h in md, f"missing section: {h}"


def test_prd_quotes_customer_pain():
    md = render_prd(SAMPLE)
    assert SAMPLE["bottlenecks"][0]["scene"] in md


def test_prd_tags_aggregated():
    md = render_prd(SAMPLE)
    assert "[action_task]" in md and "[knowledge_authoring]" in md
