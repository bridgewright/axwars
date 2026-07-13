import sys
import pathlib

# skill dir (parents[1] from tests/) on sys.path so `scripts` is importable
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scripts.validate_discovery import validate  # noqa: E402


def _base():
    return {
        "meta": {"customer": "가상몰", "interviewee_role": "cs_lead", "company_size": "enterprise",
                 "created_at": "2026-07-06", "created_by": "interview", "source_transcript": "output/transcript.jsonl"},
        "context": {"team_size": "4", "daily_volume": "300", "channels": ["chat"],
                    "inquiry_types": [{"type": "배송조회", "share_pct": 40, "repetitive": True}]},
        "bottlenecks": [{"scene": "프로모션 때 하루 2000건", "frequency": "피크",
                         "why_unsolved": "시스템 확인 필요", "desired": "자동 조회"}],
        "automation_scope": [{"task": "배송조회", "current_handling": "수기", "fit": "high", "priority": 1}],
        "integration": [{"task": "주문취소", "backend_system": "자체 어드민", "separate_or_integrated": "integrated",
                         "has_api": "unknown", "built": "inhouse", "dev_effort": "미정", "tier": "system_task"}],
        "knowledge_readiness": {"faq_count_est": 65, "doc_scope": "정책 10건",
                                "quality_gap": "문장형 필요", "authoring_effort": "2.5h"},
        "org_change": {"agent_role_shift": "지식세팅으로", "change_mgmt_risk": "낮음"},
        "metrics": {"goals": ["문의량 감소"], "success_definition": "재인입률 하락",
                    "resolution_trap_aware": True, "impact_link": "재구매"},
        "product_gaps": [{"signal": "실제 처리 원함", "quote": "취소까지 됐으면", "tag": "action_task"}],
        "open_questions": ["주문시스템 API 유무 확인"],
    }


def test_valid_base_passes():
    errors, _ = validate(_base())
    assert errors == []


def test_missing_top_key_errors():
    d = _base()
    del d["metrics"]
    errors, _ = validate(d)
    assert any("metrics" in e for e in errors)


def test_bad_role_enum_errors():
    d = _base()
    d["meta"]["interviewee_role"] = "manager"
    errors, _ = validate(d)
    assert any("interviewee_role" in e for e in errors)


def test_bad_tier_enum_errors():
    d = _base()
    d["integration"][0]["tier"] = "maybe"
    errors, _ = validate(d)
    assert any("tier" in e for e in errors)


def test_bad_gap_tag_errors():
    d = _base()
    d["product_gaps"][0]["tag"] = "misc"
    errors, _ = validate(d)
    assert any("tag" in e for e in errors)


def test_empty_context_warns_not_errors():
    d = _base()
    d["context"]["inquiry_types"] = []
    errors, warnings = validate(d)
    assert errors == [] and warnings
