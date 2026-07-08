"""deployment-discovery.json → product-input.prd.md 렌더 (결정적, stdlib only).

- product-input.prd.md : 고객 페인 + PRD 제언서 (본진 프로덕트팀용, to-prd 틀)

주의: deployment-brief.md는 더 이상 이 스크립트가 렌더하지 않는다.
배포 계획서는 `brief` 스킬이 references/deployment-brief-format.md를 따라 **에이전트가 직접 집필**한다.
(PRD 포맷 개편은 후속 예정 — 그때 이 스크립트도 정리한다.)

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


def _bullets(items, fmt, empty="_확인 불가 — 아래 '결정 필요' 참조_"):
    return "\n".join(fmt(x) for x in items) if items else empty


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
    ap = argparse.ArgumentParser(description="render product-input.prd from discovery")
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
    (out / "product-input.prd.md").write_text(render_prd(d), encoding="utf-8")
    print(f"wrote {out}/product-input.prd.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
