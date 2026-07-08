import sys
import json
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scripts.build_reports import render_prd  # noqa: E402

SAMPLE_PATH = pathlib.Path(__file__).resolve().parents[2] / "intake" / "assets" / "sample-discovery.json"
SAMPLE = json.load(open(SAMPLE_PATH, encoding="utf-8"))

# 주의: deployment-brief.md는 더 이상 스크립트가 렌더하지 않는다(에이전트가 직접 집필).
# 이 테스트는 PRD 렌더만 검증한다.


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
