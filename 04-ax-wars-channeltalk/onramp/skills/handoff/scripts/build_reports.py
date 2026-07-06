"""deployment-discovery.json → 두 보고서 렌더 (결정적, stdlib only).

- deployment-brief.md     : 배포 계획서 (배포팀용)
- product-input.prd.md    : 고객 페인 + PRD 제언서 (본진 프로덕트팀용, to-prd 틀)

렌더 전 intake/scripts/validate_discovery.py 게이트를 통과해야 한다(errors면 거부).
사용: python3 build_reports.py <discovery.json> --out-dir <dir>
"""
import json
import sys
import argparse
import pathlib

# intake/scripts 를 import 경로에 추가 (계약 정본 소유)
_INTAKE_SCRIPTS = pathlib.Path(__file__).resolve().parents[2] / "intake" / "scripts"
sys.path.insert(0, str(_INTAKE_SCRIPTS))
from validate_discovery import validate  # noqa: E402


def _lines(items, fmt, empty="_확인 불가 — open_questions 참조_"):
    return "\n".join(fmt(x) for x in items) if items else empty


def render_brief(d):
    c = d.get("context", {})
    m = d.get("metrics", {})
    k = d.get("knowledge_readiness", {})
    o = d.get("org_change", {})
    parts = []
    parts.append(f"# 배포 계획서 — {d['meta']['customer']}\n")
    parts.append(f"> 인터뷰 대상: `{d['meta']['interviewee_role']}` · 회사 규모: {d['meta']['company_size']} · 작성: {d['meta']['created_at']}\n")

    parts.append("## 1. 도입 적합성\n"
                 f"- 팀 규모: {c.get('team_size','?')} · 하루 상담량: {c.get('daily_volume','?')} · 채널: {', '.join(c.get('channels', []))}\n"
                 "- 기준선(1인 하루 30건+ · 매크로 답변 5건+) 대비 도입 적합성 판단 필요\n")

    parts.append("## 2. 자동화 범위 (우선순위 순)\n" + _lines(
        sorted(d.get("automation_scope", []), key=lambda a: a.get("priority", 99)),
        lambda a: f"- **{a['task']}** (적합도 {a['fit']}, 우선순위 {a['priority']}) — 현재: {a['current_handling']}") + "\n")

    parts.append("## 3. 연동 가능성 진단 (해결률 상한을 가르는 핵심)\n" + _lines(
        d.get("integration", []),
        lambda i: (f"- **{i['task']}** — tier `{i['tier']}` · 시스템 {i.get('backend_system','?')}"
                   f"({i.get('separate_or_integrated','?')}) · API {i.get('has_api','?')}"
                   f" · {i.get('built','?')} · 공수 {i.get('dev_effort','?')}")) + "\n"
                 "\n> tier `system_task`가 있으면 백엔드 연동이 해결률 상한을 결정한다. "
                 "`no_integration`만이면 FAQ/RAG 수준(해결률 상한 낮음).\n")

    parts.append("## 4. 지식 준비도 & 정비 공수\n"
                 f"- FAQ 추정 {k.get('faq_count_est','?')}개 · 문서 {k.get('doc_scope','?')} · 갭 {k.get('quality_gap','?')} · 공수 {k.get('authoring_effort','?')}\n")

    parts.append("## 5. 단계적 롤아웃\n"
                 "- 빠른 효과 지점 먼저 → 확장. 권장 순서: " +
                 " → ".join(a["task"] for a in sorted(d.get("automation_scope", []), key=lambda a: a.get("priority", 99))) + "\n")

    parts.append("## 6. 성과 지표 설계 (해결률 단독 금지)\n"
                 f"- 목표: {', '.join(m.get('goals', [])) or '?'}\n"
                 f"- 성공 정의: {m.get('success_definition','?')} · 해결률 함정 인지: {m.get('resolution_trap_aware')}\n"
                 "- 지표 묶음: 해결률 × 재인입률 × 응답시간 × 인력 절감 × CSAT\n")

    parts.append("## 7. 조직·상담사 변화관리\n"
                 f"- 역할 전환: {o.get('agent_role_shift','?')} · 변화관리 리스크: {o.get('change_mgmt_risk','?')}\n")

    parts.append("## 8. 리스크 & 배포 전 미해결 질문 (사전 단서)\n" +
                 _lines(d.get("open_questions", []), lambda q: f"- {q}") + "\n")
    return "\n".join(parts)


def render_prd(d):
    bl = d.get("bottlenecks", [])
    first = bl[0] if bl else {"scene": "(미확보)"}
    parts = []
    parts.append(f"# 고객 페인 + 제품 제안서 — {d['meta']['customer']}\n")
    parts.append(f"> 본진 프로덕트팀 전달용. 근거: intake 음성 인터뷰(`{d['meta'].get('source_transcript','?')}`).\n")

    parts.append("## 0. 고객 페인포인트 (실제 인용)\n" + _lines(
        bl, lambda x: f"- \"{x['scene']}\" — 빈도 {x.get('frequency','?')}, 미해결 원인: {x.get('why_unsolved','?')}") + "\n")

    parts.append(f"## Problem Statement\n{first['scene']} — 반복·정형 문의가 피크에 폭증하는데 실제 처리가 사람에 묶여 있다.\n")

    parts.append("## Solution\n" + _lines(bl, lambda x: f"- {x.get('desired','?')}") + "\n")

    parts.append("## User Stories\n" + _lines(
        d.get("automation_scope", []),
        lambda a: f"1. As a 고객사 CS 담당, I want 알프가 {a['task']}를 자동 처리, so that 반복 응대를 줄이고 피크에 대응한다") + "\n")

    parts.append("## Implementation Decisions\n" + _lines(
        d.get("integration", []),
        lambda i: f"- {i['task']}: tier `{i['tier']}`, 백엔드 {i.get('backend_system','?')}, API {i.get('has_api','?')} — 파일·코드는 명시하지 않음") + "\n")

    parts.append("## Testing Decisions\n"
                 "- 외부 동작(고객 요청 → 처리 결과)만 검증한다. 구현 세부는 테스트하지 않는다.\n"
                 "- 유사 선례: 기존 태스크 자동화(주문취소·교환) 케이스의 종단 시나리오.\n")

    parts.append("## Out of Scope\n"
                 "- 이번 인터뷰에서 확인되지 않은 시스템·업무(아래 미해결 질문 참조).\n")

    parts.append("## Further Notes\n" + _lines(d.get("open_questions", []), lambda q: f"- {q}") + "\n")

    tags = {}
    for g in d.get("product_gaps", []):
        tags.setdefault(g["tag"], []).append(g.get("quote", g.get("signal", "")))
    parts.append("## 제품 갭 태그 분류 (누적 시 우선순위 신호)\n" + _lines(
        list(tags.items()),
        lambda kv: f"- `[{kv[0]}]` × {len(kv[1])}건: " + " / ".join(kv[1])) + "\n")
    return "\n".join(parts)


def main(argv=None):
    ap = argparse.ArgumentParser(description="render deployment-brief + product-input.prd from discovery")
    ap.add_argument("discovery")
    ap.add_argument("--out-dir", default=".")
    args = ap.parse_args(argv)

    with open(args.discovery, encoding="utf-8") as fh:
        d = json.load(fh)
    errors, warnings = validate(d)
    for w in warnings:
        print(f"WARN: {w}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        raise SystemExit("discovery invalid — 인터뷰 보강 후 재시도")

    out = pathlib.Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "deployment-brief.md").write_text(render_brief(d), encoding="utf-8")
    (out / "product-input.prd.md").write_text(render_prd(d), encoding="utf-8")
    print(f"wrote {out}/deployment-brief.md")
    print(f"wrote {out}/product-input.prd.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
