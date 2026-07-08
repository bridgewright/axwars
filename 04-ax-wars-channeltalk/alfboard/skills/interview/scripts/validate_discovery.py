"""deployment-discovery.json 검증기 (단일 계약 게이트).

스키마 정본: ../references/discovery-spec.md
사용: python3 validate_discovery.py <discovery.json>   (errors 있으면 exit 1)
stdlib only.
"""
import json
import sys
import argparse

TOP_KEYS = [
    "meta", "context", "bottlenecks", "automation_scope", "integration",
    "knowledge_readiness", "org_change", "metrics", "product_gaps", "open_questions",
]
ROLES = {"cs_lead", "exec", "agent", "it", "multi"}
TIERS = {"no_integration", "workflow", "system_task"}
TAGS = {
    "action_task", "reask_context", "knowledge_authoring", "voc_distribution",
    "metric_redefine", "handoff_quality", "multilingual", "small_team",
}


def validate(data):
    """Return (errors, warnings). errors non-empty => invalid."""
    errors, warnings = [], []
    if not isinstance(data, dict):
        return (["root is not an object"], [])

    for k in TOP_KEYS:
        if k not in data:
            errors.append(f"missing top-level key: {k}")

    meta = data.get("meta", {}) or {}
    for k in ("customer", "interviewee_role", "company_size", "created_at", "created_by"):
        if not meta.get(k):
            errors.append(f"meta.{k} empty")
    role = meta.get("interviewee_role")
    if role and role not in ROLES:
        errors.append(f"meta.interviewee_role invalid: {role}")

    for i, it in enumerate(data.get("integration", []) or []):
        if it.get("tier") not in TIERS:
            errors.append(f"integration[{i}].tier invalid: {it.get('tier')}")

    for i, g in enumerate(data.get("product_gaps", []) or []):
        if g.get("tag") not in TAGS:
            errors.append(f"product_gaps[{i}].tag invalid: {g.get('tag')}")

    ctx = data.get("context", {}) or {}
    inquiry_types = ctx.get("inquiry_types") or []
    if not inquiry_types:
        warnings.append("context.inquiry_types empty — 자동화 스코프 산정 불가")
    if not data.get("bottlenecks"):
        warnings.append("bottlenecks empty — 인터뷰 보강 권장")
    # 배포 계획서(brief) 정량 baseline 권고
    if not ctx.get("org"):
        warnings.append("context.org 없음 — 배포 계획서 2장 조직·R&R 표 비어짐(권고)")
    if inquiry_types and not any(t.get("avg_leadtime") for t in inquiry_types):
        warnings.append("inquiry_types에 avg_leadtime 없음 — 3장 페인 매핑 리드타임 축 약화(권고)")
    if not data.get("it_capacity"):
        warnings.append("it_capacity 없음 — 5·6장 고객 IT 여력·원가 산정에 필요(권고)")
    kr = data.get("knowledge_readiness") or {}
    if kr and not kr.get("faq_format"):
        warnings.append("knowledge_readiness.faq_format 없음 — 알프 지식 도입 난이도 평가에 정리 포맷 정보 필요(권고)")
    syn = data.get("synthesis") or {}
    if not syn.get("deployment_headline") or not syn.get("product_headline"):
        warnings.append("synthesis.deployment_headline/product_headline 없음 — 보고서 두괄식 요약이 약해짐(권고: 채울 것)")

    return (errors, warnings)


def main(argv=None):
    ap = argparse.ArgumentParser(description="validate deployment-discovery.json")
    ap.add_argument("path")
    args = ap.parse_args(argv)
    with open(args.path, encoding="utf-8") as fh:
        data = json.load(fh)
    errors, warnings = validate(data)
    for w in warnings:
        print(f"WARN: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    if errors:
        print(f"INVALID ({len(errors)} errors)")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
