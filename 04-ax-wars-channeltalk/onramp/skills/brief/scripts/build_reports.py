"""deployment-discovery.json → 두 보고서 렌더 (결정적, stdlib only).

- deployment-brief.md     : 배포 계획서 (배포팀용)
- product-input.prd.md    : 고객 페인 + PRD 제언서 (본진 프로덕트팀용, to-prd 틀)

작성 원칙: **두괄식**. 각 보고서는 '결론 먼저(권고/제언)'로 시작해 So-What을 명확히 하고,
그다음 현장 인터뷰 인용으로 설득력 있게 뒷받침한다. 두괄식 요약은 discovery의 `synthesis`
블록(intake가 인터뷰를 종합해 채움)에서 오며, 없으면 데이터에서 보수적으로 유도한다.

렌더 전 intake/scripts/validate_discovery.py 게이트를 통과해야 한다(errors면 거부).
사용: python3 build_reports.py <discovery.json> --out-dir <dir>
"""
import json
import sys
import argparse
import pathlib

_INTAKE_SCRIPTS = pathlib.Path(__file__).resolve().parents[2] / "intake" / "scripts"
sys.path.insert(0, str(_INTAKE_SCRIPTS))
from validate_discovery import validate  # noqa: E402

TAG_KO = {
    "action_task": "실제 처리(액션/태스크)",
    "reask_context": "되묻기·맥락 수집",
    "knowledge_authoring": "지식 저작 자동화",
    "voc_distribution": "상담 데이터 타부서 유통",
    "metric_redefine": "성과 지표 재정의",
    "handoff_quality": "사람 이관 품질·보안",
    "multilingual": "다국어",
    "small_team": "소규모 팀 최적화",
}


def _who(meta):
    ivs = meta.get("interviewees")
    if ivs:
        return " · ".join(x.get("who", x.get("role", "?")) for x in ivs)
    return meta.get("interviewee_role", "?")


def _syn(d, key, fallback=""):
    return (d.get("synthesis") or {}).get(key) or fallback


def _tier_ceiling(d):
    tiers = {i.get("tier") for i in d.get("integration", [])}
    if "system_task" in tiers:
        unknown = any(i.get("tier") == "system_task" and i.get("has_api") in (None, "unknown")
                      for i in d.get("integration", []))
        return "실제 처리(주문·예약 등)까지 자동화 가능 — 다만 백엔드 연동이 해결률 상한을 좌우" + \
               ("하고, 일부 시스템은 API 유무가 아직 미확인" if unknown else "")
    if "workflow" in tiers:
        return "조회·분기 수준까지 자동화 가능(중간 해결률)"
    return "FAQ/RAG 응답 수준(해결률 상한 낮음)"


def _bullets(items, fmt, empty="_확인 불가 — 아래 '결정해야 할 것' 참조_"):
    return "\n".join(fmt(x) for x in items) if items else empty


def render_brief(d):
    meta, c, m = d["meta"], d.get("context", {}), d.get("metrics", {})
    k, o = d.get("knowledge_readiness", {}), d.get("org_change", {})
    P = []
    P.append(f"# 배포 계획서 — {meta['customer']}")
    P.append(f"> 인터뷰 대상: {_who(meta)} · 작성 {meta.get('created_at','')}\n")

    # ── 결론 먼저 (BLUF) ──
    headline = _syn(d, "deployment_headline",
                    "빠른 효과 지점부터 단계적으로 도입하되, 실제 처리 업무는 연동 확인 후 확장한다")
    rationale = _syn(d, "deployment_rationale",
                     "반복·정형 문의는 즉시 자동화 효과가 크고, 실제 처리(주문·교환 등)는 시스템 연동이 해결률을 좌우하기 때문이다.")
    readiness = _syn(d, "readiness", _tier_ceiling(d))
    risks = (d.get("synthesis") or {}).get("top_risks") or d.get("open_questions", [])[:2]
    P.append("## ⚡ 결론 먼저 — 권고\n")
    P.append(f"**{headline}**\n")
    P.append(rationale + "\n")
    P.append(f"- **준비도 진단**: {readiness}")
    P.append("- **먼저 볼 리스크**: " + ("; ".join(risks) if risks else "특이 리스크 낮음") + "\n")
    P.append("---\n")

    # ── 1. 왜 지금인가 (현장 인용) ──
    P.append("## 1. 왜 지금인가 — 현장의 목소리\n")
    P.append(_bullets(d.get("bottlenecks", []), lambda b:
                      f"> \"{b['scene']}\"\n>\n> — {b.get('frequency','')} · 막힌 이유: {b.get('why_unsolved','?')} · 원하는 것: **{b.get('desired','?')}**\n") + "\n")

    # ── 2. 무엇부터 ──
    P.append("## 2. 무엇부터 자동화하나 (우선순위)\n")
    P.append("반복·정형이면서 상담원 개입이 불필요한 것부터. 개별 확인이 필요한 유형은 후순위.\n")
    P.append(_bullets(sorted(d.get("automation_scope", []), key=lambda a: a.get("priority", 99)),
                      lambda a: f"{a.get('priority','?')}. **{a['task']}** — 현재: {a.get('current_handling','?')} · 적합도 {a.get('fit','?')}") + "\n")

    # ── 3. 연동 진단 (핵심) ──
    P.append("## 3. 성패를 가르는 연동 진단\n")
    P.append(f"**{_tier_ceiling(d)}.** Task별 연동 난이도가 곧 해결률 상한이다.\n")
    P.append(_bullets(d.get("integration", []), lambda i:
                      f"- **{i['task']}** — `{i.get('tier','?')}` · 시스템 {i.get('backend_system','?')}"
                      f"({i.get('separate_or_integrated','?')}) · API {i.get('has_api','?')} · {i.get('built','?')}"
                      f" · 공수 {i.get('dev_effort','?')}") + "\n")

    # ── 4. 지식·공수 ──
    P.append("## 4. 알프에게 무엇을 준비시키나 (지식·공수)\n")
    P.append(f"- FAQ 추정 **{k.get('faq_count_est','?')}개**, 문서 {k.get('doc_scope','?')}\n"
             f"- 정비 포인트: {k.get('quality_gap','?')} · 예상 공수 {k.get('authoring_effort','?')}\n"
             "- 데모는 몇 분이지만 실운영 품질은 지식 정비 수준이 좌우한다.\n")

    # ── 5. 성과 기준 ──
    trap = "성과 지표는 **자동해결률 단독으로 잡지 않는다**(무리한 자동화는 CX를 해친다). 해결률 × 재인입률 × 응답시간 × 인력 절감 × CSAT를 묶어서 본다."
    P.append("## 5. 성공을 무엇으로 볼까 (지표)\n")
    P.append(f"- 목표: {', '.join(m.get('goals', [])) or '?'}\n"
             f"- 성공 정의: {m.get('success_definition','?')}\n"
             f"- {trap}\n")

    # ── 6. 조직 변화 ──
    P.append("## 6. 상담팀은 어떻게 바뀌나\n")
    P.append(f"- 역할 전환: {o.get('agent_role_shift','?')}\n- 변화관리 리스크: {o.get('change_mgmt_risk','?')}\n")

    # ── 7. 결정 필요 ──
    P.append("## 7. 지금 결정·확인해야 할 것\n")
    P.append(_bullets(d.get("open_questions", []), lambda q: f"- [ ] {q}") + "\n")
    return "\n".join(P)


def render_prd(d):
    meta = d["meta"]
    gaps = d.get("product_gaps", [])
    # 태그 집계
    by_tag = {}
    for g in gaps:
        by_tag.setdefault(g["tag"], []).append(g)
    top = sorted(by_tag.items(), key=lambda kv: -len(kv[1]))

    P = []
    P.append(f"# 고객 페인 → 제품 제언 — {meta['customer']}")
    P.append(f"> 본진 프로덕트팀 전달용 · 근거: {_who(meta)} 인터뷰\n")

    # ── 결론 먼저 (BLUF) ──
    headline = _syn(d, "product_headline",
                    (f"'{TAG_KO.get(top[0][0], top[0][0])}'가 이 고객의 최우선 제품 요구다" if top else "현장 페인을 제품 로드맵으로 연결한다"))
    rationale = _syn(d, "product_rationale",
                     "현장에서 반복적으로 드러난 페인이 그대로 제품 요구로 이어진다. 아래 신호와 인용이 근거다.")
    P.append("## ⚡ 결론 먼저 — 제언\n")
    P.append(f"**{headline}**\n")
    P.append(rationale + "\n")
    if top:
        P.append("- **신호 강도(태그별 건수)**: " +
                 ", ".join(f"{TAG_KO.get(t, t)} {len(gs)}건" for t, gs in top) + "\n")
    P.append("---\n")

    # ── 고객 페인 (인용) ──
    P.append("## 고객이 실제로 겪는 문제 (현장 인용)\n")
    P.append(_bullets(d.get("bottlenecks", []), lambda b:
                      f"> \"{b['scene']}\"\n>\n> — {b.get('frequency','')}, 막힌 이유: {b.get('why_unsolved','?')}\n") + "\n")

    first = (d.get("bottlenecks") or [{"scene": "(미확보)", "desired": ""}])[0]
    P.append(f"## Problem Statement\n{first['scene']} — 반복·정형 문의가 특정 시점에 폭증하는데 실제 처리가 사람에 묶여 있다.\n")
    P.append("## Solution\n" + _bullets(d.get("bottlenecks", []), lambda b: f"- {b.get('desired','?')}") + "\n")
    P.append("## User Stories\n" + _bullets(d.get("automation_scope", []), lambda a:
             f"- As a 고객사 CS 담당, I want 알프가 **{a['task']}**를 자동 처리, so that 반복 응대를 줄이고 피크에 대응한다") + "\n")
    P.append("## Implementation Decisions\n" + _bullets(d.get("integration", []), lambda i:
             f"- {i['task']}: `{i.get('tier','?')}` — 백엔드 {i.get('backend_system','?')}, API {i.get('has_api','?')}"
             f", 개발 주체 {i.get('built','?')} (파일·코드는 명시하지 않음)") + "\n")
    P.append("## Testing Decisions\n- 외부 동작(고객 요청 → 처리 결과)만 검증한다. 구현 세부는 테스트하지 않는다.\n"
             "- 유사 선례: 기존 태스크 자동화(주문·교환·구독취소 등)의 종단 시나리오.\n")
    P.append("## Out of Scope\n- 이번 인터뷰에서 확인되지 않은 시스템·업무(아래 '결정 필요' 참조).\n")
    P.append("## Further Notes\n" + _bullets(d.get("open_questions", []), lambda q: f"- {q}") + "\n")

    # ── 제품 갭 태그: 무엇을, 왜 ──
    P.append("## 제품 갭 — 무엇을, 왜 (태그별 우선순위)\n")
    def gap_block(t, gs):
        head = f"### `[{t}]` {TAG_KO.get(t, t)} — {len(gs)}건"
        body = "\n".join(f"- 신호: {g.get('signal','')}\n  > \"{g.get('quote','')}\"" for g in gs)
        return head + "\n" + body
    P.append(("\n\n".join(gap_block(t, gs) for t, gs in top) if top else "_확인된 제품 갭 없음_") + "\n")
    return "\n".join(P)


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
