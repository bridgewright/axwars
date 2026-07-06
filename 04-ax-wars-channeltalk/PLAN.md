# onramp 플러그인 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 채널톡 배포 담당자가 고객사 현업을 음성 인터뷰해 `deployment-discovery.json`을 만들고(intake), 그걸로 배포 계획서 + 본진 PRD 제언서 두 문서를 렌더(handoff)하는 Codex 플러그인을 `scout`에서 포크해 만든다.

**Architecture:** 2-스킬 파이프라인. `intake`(scout `distillery` 포크: ElevenLabs 음성 인터뷰 → transcript → discovery.json) → 계약 `deployment-discovery.json` → `handoff`(scout `refinery` 자리: discovery.json → 두 마크다운 보고서). 결정적 파트(validate/build)는 stdlib Python, 인터뷰 엔진은 scout 그대로 재활용.

**Tech Stack:** Python 3.12(uv), stdlib only(scripts), ElevenLabs Agents Platform(음성), 순수 HTML/CSS(무CDN) + Pretendard(vendored), pytest.

## Global Constraints

- **설계 정본**: `03_solution-scope_channeltalk.md`. 모든 스키마·보고서 항목·인터뷰 스크립트·색값은 이 문서 기준.
- **포크 원본**: `scout` 플러그인. 추출본 위치는 구현자가 `scout-plugin-v1.0.0.zip`을 풀어 확보(`scout/skills/distillery`, `scout/skills/refinery`).
- **scripts는 stdlib only**(scout 규약). argparse, `main(argv)` 패턴.
- **무CDN**: 인터뷰 페이지는 외부 CDN 금지. Pretendard woff2·로고를 `assets/`에 vendoring.
- **PII**: `.env`(API키)·`_samples/`·실제 transcript는 gitignore. 커밋 예시는 전부 가상.
- **네이밍**: plugin `onramp` / 스킬 `intake`·`handoff`.
- **브랜드 색(verbatim)**: primary `#6157EA`, hover `#4E40C9`, bright `#5E56F0`, cobalt `#3292E3`, success `#20AB55`, bg `#FFFFFF`/`#F7F7F8`, text `rgba(0,0,0,.85/.6/.4)`, grad `linear-gradient(135deg,#6157EA,#8E57E7)`, radius 999px(pill)/12px(card).
- **discovery 계약 enum**: `interviewee_role ∈ {cs_lead,exec,agent,it}`, `integration[].tier ∈ {no_integration,workflow,system_task}`, `product_gaps[].tag ∈ {action_task,reask_context,knowledge_authoring,voc_distribution,metric_redefine,handoff_quality,multilingual,small_team}`.
- **가드레일**: 인터뷰 미확보 슬롯은 상상 금지 → `open_questions` 또는 `"unknown"`. validate 실패 시 렌더 거부.

---

## 파일 구조 (생성/수정)

```
onramp/
  .claude-plugin/plugin.json            # 수정(scout→onramp 메타)
  skills/
    intake/                             # distillery 포크
      SKILL.md                          # 수정(인터뷰→discovery)
      prompt/interviewer-system-prompt.md   # 신규(4롤 스크립트)
      references/discovery-spec.md      # 신규(스키마 계약)
      scripts/
        setup_agent.py                  # 재활용(프롬프트 경로만)
        serve_browser.py                # 재활용
        run_interview.py                # 재활용
        sd_audio.py                     # 재활용
        fetch_transcript.py             # 재활용
        validate_discovery.py           # 신규
      assets/
        talk_template.html              # 리스타일(채널톡 룩)
        channel-logo.webp               # 신규(로고 교체)
        pretendard/*.woff2              # 신규(폰트 vendoring)
        sample-discovery.json           # 신규(가상 샘플)
      output/README.md                  # 수정(핸드오프 계약)
      tests/test_discovery.py           # 신규
    handoff/                            # refinery 자리
      SKILL.md                          # 신규
      scripts/build_reports.py          # 신규(두 보고서 렌더)
      references/
        deployment-brief-template.md    # 신규(참고)
        product-input-template.md       # 신규(참고, to-prd)
      tests/test_reports.py             # 신규
```

---

## Task 0: 포크 & 스캐폴드

**Files:**
- Create: `onramp/` (scout 복사)
- Modify: `onramp/.claude-plugin/plugin.json`
- Delete: refinery 채용 채점 자산(`github_analyze.py`, `build_ranking.py`, `extract_pdf.py`, refinery references/scorecard 등)

- [ ] **Step 1: scout 추출 후 onramp로 복사**

```bash
cd 04-ax-wars-channeltalk
unzip -o scout-plugin-v1.0.0.zip -d _scout_src
cp -R _scout_src/scout onramp
git mv onramp/skills/distillery onramp/skills/intake
git mv onramp/skills/refinery onramp/skills/handoff
```

- [ ] **Step 2: refinery(현 handoff) 채용 로직 제거**

```bash
rm onramp/skills/handoff/scripts/github_analyze.py \
   onramp/skills/handoff/scripts/build_ranking.py \
   onramp/skills/handoff/scripts/extract_pdf.py
rm -rf onramp/skills/handoff/references
```

- [ ] **Step 3: plugin.json 갱신**

```json
{
  "name": "onramp",
  "version": "1.0.0",
  "displayName": "Onramp",
  "description": "Onramp — 채널톡 엔터프라이즈 배포 discovery. 고객 현업을 음성 인터뷰해(intake) 배포 계획서와 본진 PRD 제언서를 자동 생성한다(handoff).",
  "license": "MIT",
  "keywords": ["onramp","channeltalk","deployment","discovery","interview","alf","prd","intake","handoff"],
  "skills": "./skills/"
}
```

- [ ] **Step 4: 커밋**

```bash
git add onramp && git commit -m "chore: fork scout into onramp (intake/handoff)"
```

---

## Task 1: discovery 계약 스키마 + 검증기 (TDD)

**Files:**
- Create: `onramp/skills/intake/references/discovery-spec.md`
- Create: `onramp/skills/intake/scripts/validate_discovery.py`
- Test: `onramp/skills/intake/tests/test_discovery.py`

**Interfaces:**
- Produces: `validate(data: dict) -> tuple[list[str], list[str]]` (errors, warnings). `main(argv)` CLI(exit 1 if errors).

- [ ] **Step 1: discovery-spec.md 작성** — `03_solution-scope_channeltalk.md` §6의 JSON 스키마를 그대로 옮기고, 아래 검증 규칙을 명문화한다(필수 최상위 키, enum, tier/tag 허용값, 슬롯 미확보 시 `unknown`/`open_questions`).

- [ ] **Step 2: 실패 테스트 작성**

```python
# onramp/skills/intake/tests/test_discovery.py
import json, subprocess, sys, pathlib
from scripts.validate_discovery import validate   # sys.path: skill dir

def _base():
    return {
      "meta": {"customer":"가상몰","interviewee_role":"cs_lead","company_size":"enterprise",
               "created_at":"2026-07-06","created_by":"intake","source_transcript":"output/transcript.jsonl"},
      "context": {"team_size":"4","daily_volume":"300","channels":["chat"],
                  "inquiry_types":[{"type":"배송조회","share_pct":40,"repetitive":True}]},
      "bottlenecks":[{"scene":"프로모션 때 하루 2000건","frequency":"피크","why_unsolved":"시스템 확인 필요","desired":"자동 조회"}],
      "automation_scope":[{"task":"배송조회","current_handling":"수기","fit":"high","priority":1}],
      "integration":[{"task":"주문취소","backend_system":"자체 어드민","separate_or_integrated":"integrated",
                      "has_api":"unknown","built":"inhouse","dev_effort":"미정","tier":"system_task"}],
      "knowledge_readiness":{"faq_count_est":65,"doc_scope":"정책 10건","quality_gap":"문장형 필요","authoring_effort":"2.5h"},
      "org_change":{"agent_role_shift":"지식세팅으로","change_mgmt_risk":"낮음"},
      "metrics":{"goals":["문의량 감소"],"success_definition":"재인입률 하락","resolution_trap_aware":True,"impact_link":"재구매"},
      "product_gaps":[{"signal":"실제 처리 원함","quote":"취소까지 됐으면","tag":"action_task"}],
      "open_questions":["주문시스템 API 유무 확인"]
    }

def test_valid_base_passes():
    errors, _ = validate(_base()); assert errors == []

def test_missing_top_key_errors():
    d = _base(); del d["metrics"]
    errors, _ = validate(d); assert any("metrics" in e for e in errors)

def test_bad_role_enum_errors():
    d = _base(); d["meta"]["interviewee_role"] = "manager"
    errors, _ = validate(d); assert any("interviewee_role" in e for e in errors)

def test_bad_tier_enum_errors():
    d = _base(); d["integration"][0]["tier"] = "maybe"
    errors, _ = validate(d); assert any("tier" in e for e in errors)

def test_bad_gap_tag_errors():
    d = _base(); d["product_gaps"][0]["tag"] = "misc"
    errors, _ = validate(d); assert any("tag" in e for e in errors)

def test_empty_context_warns_not_errors():
    d = _base(); d["context"]["inquiry_types"] = []
    errors, warnings = validate(d); assert errors == [] and warnings
```

- [ ] **Step 3: 실패 확인**

Run: `cd onramp/skills/intake && python -m pytest tests/test_discovery.py -v`
Expected: FAIL (`validate` 미정의 / ImportError).

- [ ] **Step 4: validate_discovery.py 구현**

```python
# onramp/skills/intake/scripts/validate_discovery.py
import json, sys, argparse

TOP_KEYS = ["meta","context","bottlenecks","automation_scope","integration",
            "knowledge_readiness","org_change","metrics","product_gaps","open_questions"]
ROLES = {"cs_lead","exec","agent","it"}
TIERS = {"no_integration","workflow","system_task"}
TAGS = {"action_task","reask_context","knowledge_authoring","voc_distribution",
        "metric_redefine","handoff_quality","multilingual","small_team"}

def validate(data):
    errors, warnings = [], []
    if not isinstance(data, dict):
        return (["root is not an object"], [])
    for k in TOP_KEYS:
        if k not in data:
            errors.append(f"missing top-level key: {k}")
    meta = data.get("meta", {})
    for k in ("customer","interviewee_role","company_size","created_at","created_by"):
        if not meta.get(k):
            errors.append(f"meta.{k} empty")
    if meta.get("interviewee_role") and meta["interviewee_role"] not in ROLES:
        errors.append(f"meta.interviewee_role invalid: {meta.get('interviewee_role')}")
    for i, it in enumerate(data.get("integration", []) or []):
        if it.get("tier") not in TIERS:
            errors.append(f"integration[{i}].tier invalid: {it.get('tier')}")
    for i, g in enumerate(data.get("product_gaps", []) or []):
        if g.get("tag") not in TAGS:
            errors.append(f"product_gaps[{i}].tag invalid: {g.get('tag')}")
    if not (data.get("context", {}) or {}).get("inquiry_types"):
        warnings.append("context.inquiry_types empty — 자동화 스코프 산정 불가")
    if not data.get("bottlenecks"):
        warnings.append("bottlenecks empty — 인터뷰 보강 권장")
    return (errors, warnings)

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    args = ap.parse_args(argv)
    data = json.load(open(args.path, encoding="utf-8"))
    errors, warnings = validate(data)
    for w in warnings: print(f"WARN: {w}")
    for e in errors: print(f"ERROR: {e}")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: 통과 확인**

Run: `cd onramp/skills/intake && python -m pytest tests/test_discovery.py -v`
Expected: PASS (6 passed).

- [ ] **Step 6: 커밋** — `git commit -m "feat(intake): deployment-discovery schema + validator"`

---

## Task 2: 인터뷰어 프롬프트 (4롤 스크립트)

**Files:**
- Create: `onramp/skills/intake/prompt/interviewer-system-prompt.md`
- Modify: `onramp/skills/intake/scripts/setup_agent.py` (프롬프트 경로가 새 파일을 가리키는지 확인만)

- [ ] **Step 1: interviewer-system-prompt.md 작성** — `03_solution-scope_channeltalk.md` §5(grill-me 규칙)·§8(4롤 스크립트)를 그대로 프롬프트화. 구조:
  - `# 역할` — 채널톡 배포 담당을 돕는 인터뷰어. 고객 현업에게서 배포 결정에 필요한 사실을 일화로 끌어낸다. 점수·문서 만들지 말 것(그건 다음 단계).
  - `# grill-me 규칙` — §5 전체(직접질문 금지, 일화→빈도→왜→원하는것, 형용사 되묻기, 되비추기, 슬롯 차면 다음).
  - `# 채울 빈칸(커버리지 맵)` — §6 슬롯을 축 A/B/C로.
  - `# 롤별 진행` — §8 4롤 흐름(A CS리더/B 경영진/C 상담사/D IT) 각 흐름 그대로.
  - `=== FIRST MESSAGE ===` — 시작 시 "인터뷰 대상 롤과 회사 규모"를 먼저 확인하고 해당 롤 오프너로 진입.
  - **말하기 규칙**(scout 계승): 한국어 구어체, 한 번에 한 질문, 목록·마크다운·이모지 금지(음성).

- [ ] **Step 2: setup_agent.py 경로 확인** — `prompt/interviewer-system-prompt.md`를 읽는지 확인(scout가 이미 이 경로 → 변경 없으면 그대로). LLM 기본값·한국어 보이스 유지.

- [ ] **Step 3: 드라이런 확인**

Run: `cd onramp && uv run python skills/intake/scripts/setup_agent.py --dry-run`
Expected: 프롬프트가 로드되고 payload가 출력됨(에러 없음).

- [ ] **Step 4: 커밋** — `git commit -m "feat(intake): ALF-deployment interviewer prompt (4 roles, grill-me)"`

---

## Task 3: 배포 계획서 렌더 (보고서 ①, TDD)

**Files:**
- Create: `onramp/skills/handoff/scripts/build_reports.py`
- Test: `onramp/skills/handoff/tests/test_reports.py`

**Interfaces:**
- Produces: `render_brief(d: dict) -> str`, `render_prd(d: dict) -> str`, `main(argv)` → `deployment-brief.md` + `product-input.prd.md` 저장.

- [ ] **Step 1: 실패 테스트 작성**

```python
# onramp/skills/handoff/tests/test_reports.py
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scripts.build_reports import render_brief, render_prd
# 재사용: intake 샘플
import json
SAMPLE = json.load(open(pathlib.Path(__file__).resolve().parents[2] / "intake/assets/sample-discovery.json", encoding="utf-8"))

def test_brief_has_all_sections():
    md = render_brief(SAMPLE)
    for h in ["도입 적합성","자동화 범위","연동 가능성","지식","단계적 롤아웃","성과 지표","변화관리","미해결"]:
        assert h in md

def test_brief_integration_tier_drives_ceiling():
    md = render_brief(SAMPLE)
    assert "system_task" in md or "시스템" in md  # 연동 tier가 보고서에 반영

def test_prd_has_toprd_sections():
    md = render_prd(SAMPLE)
    for h in ["Problem Statement","Solution","User Stories","Implementation Decisions",
              "Testing Decisions","Out of Scope","Further Notes","제품 갭"]:
        assert h in md

def test_prd_quotes_customer_pain():
    md = render_prd(SAMPLE)
    assert SAMPLE["bottlenecks"][0]["scene"] in md  # 실제 인용 포함
```

- [ ] **Step 2: 실패 확인**

Run: `cd onramp/skills/handoff && python -m pytest tests/test_reports.py -v`
Expected: FAIL (ImportError / sample 없음 → Task 5.1에서 sample 생성. 우선 이 태스크 내 Step 3에서 최소 sample을 만들어 진행).

- [ ] **Step 3: 최소 sample-discovery.json 생성** — Task 1 테스트의 `_base()`와 동일 구조를 `onramp/skills/intake/assets/sample-discovery.json`으로 저장(가상 값). (Task 5.1에서 데모용으로 확장.)

- [ ] **Step 4: build_reports.py 구현** — 두 렌더 함수. `03_solution-scope_channeltalk.md` §7의 보고서①(8항)·②(to-prd+태그) 항목을 섹션으로. 렌더 전 `validate_discovery.validate` 호출, errors면 예외.

```python
# onramp/skills/handoff/scripts/build_reports.py
import json, sys, argparse, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "intake/scripts"))
from validate_discovery import validate

def _lines(items, fmt):
    return "\n".join(fmt(x) for x in items) if items else "_확인 불가 — open_questions 참조_"

def render_brief(d):
    c, m = d["context"], d["metrics"]
    parts = []
    parts.append(f"# 배포 계획서 — {d['meta']['customer']}\n")
    parts.append(f"## 1. 도입 적합성\n- 팀 규모: {c.get('team_size','?')} · 하루 상담량: {c.get('daily_volume','?')} · 채널: {', '.join(c.get('channels',[]))}\n- 기준선(1인 30건+/매크로 5건+) 대비 판단 필요\n")
    parts.append("## 2. 자동화 범위\n" + _lines(d["automation_scope"],
        lambda a: f"- **{a['task']}** (적합도 {a['fit']}, 우선순위 {a['priority']}) — 현재: {a['current_handling']}") + "\n")
    parts.append("## 3. 연동 가능성 (해결률 상한 결정)\n" + _lines(d["integration"],
        lambda i: f"- **{i['task']}** — tier `{i['tier']}` · 시스템 {i['backend_system']}({i['separate_or_integrated']}) · API {i['has_api']} · {i['built']} · 공수 {i['dev_effort']}") + "\n")
    k = d["knowledge_readiness"]
    parts.append(f"## 4. 지식 준비도 & 공수\n- FAQ 추정 {k.get('faq_count_est','?')}개 · 문서 {k.get('doc_scope','?')} · 갭 {k.get('quality_gap','?')} · 공수 {k.get('authoring_effort','?')}\n")
    parts.append("## 5. 단계적 롤아웃\n- 빠른 효과 지점 먼저 → 확장. 우선순위 순: " +
        ", ".join(a["task"] for a in sorted(d["automation_scope"], key=lambda a:a.get("priority",99))) + "\n")
    parts.append(f"## 6. 성과 지표 (해결률 단독 금지)\n- 목표: {', '.join(m.get('goals',[]))}\n- 성공 정의: {m.get('success_definition','?')} · 해결률 함정 인지: {m.get('resolution_trap_aware')}\n- 지표 묶음: 해결률 × 재인입률 × 응답시간 × 인력 × CSAT\n")
    o = d["org_change"]
    parts.append(f"## 7. 조직·상담사 변화관리\n- 역할 전환: {o.get('agent_role_shift','?')} · 리스크: {o.get('change_mgmt_risk','?')}\n")
    parts.append("## 8. 리스크 & 배포 전 미해결 질문\n" + _lines(d["open_questions"], lambda q: f"- {q}") + "\n")
    return "\n".join(parts)

def render_prd(d):
    b = d["bottlenecks"][0] if d["bottlenecks"] else {"scene":"(미확보)"}
    parts = []
    parts.append(f"# 고객 페인 + 제품 제안 — {d['meta']['customer']}\n")
    parts.append("## 0. 고객 페인포인트 (실제 인용)\n" + _lines(d["bottlenecks"],
        lambda x: f"- \"{x['scene']}\" (빈도 {x.get('frequency','?')}, 미해결 원인 {x.get('why_unsolved','?')})") + "\n")
    parts.append(f"## Problem Statement\n{b['scene']} — 고객 관점에서 반복·과부하가 지속.\n")
    parts.append("## Solution\n" + _lines(d["bottlenecks"], lambda x: f"- {x.get('desired','?')}") + "\n")
    parts.append("## User Stories\n" + _lines(d["automation_scope"],
        lambda a: f"1. As a 고객사 CS 담당, I want {a['task']} 자동 처리, so that 반복 응대를 줄인다") + "\n")
    parts.append("## Implementation Decisions\n" + _lines(d["integration"],
        lambda i: f"- {i['task']}: tier `{i['tier']}`, 백엔드 {i['backend_system']}, API {i['has_api']} (파일·코드 명시 X)") + "\n")
    parts.append("## Testing Decisions\n- 외부 동작(요청→처리 결과)만 검증. 유사 선례: 기존 태스크 자동화 케이스.\n")
    parts.append("## Out of Scope\n- 이 인터뷰에서 확인되지 않은 시스템·업무.\n")
    parts.append("## Further Notes\n" + _lines(d["open_questions"], lambda q: f"- {q}") + "\n")
    tags = {}
    for g in d["product_gaps"]:
        tags.setdefault(g["tag"], []).append(g.get("quote", g.get("signal","")))
    parts.append("## 제품 갭 태그 분류\n" + _lines(list(tags.items()),
        lambda kv: f"- `[{kv[0]}]` × {len(kv[1])}: " + " / ".join(kv[1])) + "\n")
    return "\n".join(parts)

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("discovery")
    ap.add_argument("--out-dir", default=".")
    args = ap.parse_args(argv)
    d = json.load(open(args.discovery, encoding="utf-8"))
    errors, warnings = validate(d)
    for w in warnings: print(f"WARN: {w}")
    if errors:
        for e in errors: print(f"ERROR: {e}")
        raise SystemExit("discovery invalid — 인터뷰 보강 후 재시도")
    out = pathlib.Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "deployment-brief.md").write_text(render_brief(d), encoding="utf-8")
    (out / "product-input.prd.md").write_text(render_prd(d), encoding="utf-8")
    print(f"wrote {out}/deployment-brief.md, {out}/product-input.prd.md")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: 통과 확인**

Run: `cd onramp/skills/handoff && python -m pytest tests/test_reports.py -v`
Expected: PASS (4 passed).

- [ ] **Step 6: 커밋** — `git commit -m "feat(handoff): render deployment-brief + product-input.prd from discovery"`

---

## Task 4: handoff SKILL.md + intake 계약 갱신

**Files:**
- Create: `onramp/skills/handoff/SKILL.md`
- Modify: `onramp/skills/intake/SKILL.md`, `onramp/skills/intake/output/README.md`

- [ ] **Step 1: intake/SKILL.md 갱신** — distillery 내용을 배포 discovery로. 워크플로우: 셋업 → 롤·규모 확인 → 음성 인터뷰(브라우저/CLI) → transcript → `discovery-spec.md` 따라 `output/deployment-discovery.json` 조립 → `validate_discovery.py` 게이트 → handoff로 핸드오프. §5/§8 반영. frontmatter `name: intake`.

- [ ] **Step 2: intake/output/README.md 갱신** — 다운스트림(handoff)이 읽을 계약: `deployment-discovery.json`(스키마=`references/discovery-spec.md`), `build_reports.py`가 두 보고서 렌더.

- [ ] **Step 3: handoff/SKILL.md 작성** — frontmatter `name: handoff`. 입력=`deployment-discovery.json`, 출력=두 보고서. 절차: validate 게이트 → `build_reports.py <discovery> --out-dir <dir>` → 사용자에게 두 파일 경로·핵심(연동 tier·갭 태그) 요약 보고. 가드레일(§11) 명시.

- [ ] **Step 4: 스모크 확인**

Run: `cd onramp/skills/handoff && python scripts/build_reports.py ../intake/assets/sample-discovery.json --out-dir /tmp/onramp-out && ls /tmp/onramp-out`
Expected: `deployment-brief.md  product-input.prd.md` 생성.

- [ ] **Step 5: 커밋** — `git commit -m "docs: intake/handoff SKILL + handoff contract"`

---

## Task 5: 인터뷰 페이지 채널톡 리스타일

**Files:**
- Modify: `onramp/skills/intake/assets/talk_template.html`
- Create: `onramp/skills/intake/assets/channel-logo.webp`, `assets/pretendard/*.woff2`

- [ ] **Step 1: 폰트·로고 vendoring**

```bash
cd onramp/skills/intake/assets
curl -L -o channel-logo.webp https://channel.io/logo.webp
mkdir -p pretendard   # PretendardVariable woff2를 로컬로 배치(무CDN)
```

- [ ] **Step 2: CSS 토큰 교체(BCG→채널톡)** — `talk_template.html`의 `:root`에 §9 토큰 삽입(verbatim 색), Astryx식 motion 토큰(`--dur-*`,`--ease-*`) 추가, light/dark 캐스케이드.

```css
:root{
  --ch-primary:#6157EA; --ch-primary-strong:#4E40C9; --ch-primary-bright:#5E56F0;
  --ch-highlight:#3292E3; --ch-success:#20AB55;
  --ch-bg:#FFFFFF; --ch-bg-grey:#F7F7F8;
  --ch-text:rgba(0,0,0,.85); --ch-text-2:rgba(0,0,0,.6); --ch-text-3:rgba(0,0,0,.4);
  --ch-grad:linear-gradient(135deg,#6157EA,#8E57E7);
  --radius-pill:999px; --radius-card:12px;
  --dur-fast:120ms; --dur-base:240ms; --ease-out:cubic-bezier(.2,.8,.2,1);
  --font: 'Pretendard','Pretendard Variable',-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR',system-ui,sans-serif;
}
@media (prefers-color-scheme: dark){ :root{ --ch-bg:#0A0B0B; --ch-bg-grey:#17171A; --ch-text:rgba(255,255,255,.9);} }
```

- [ ] **Step 3: 컴포넌트 리스타일** — (a) 로고 `channel-logo.webp`, (b) transcript 채팅 버블(상대=좌측 `--ch-bg-grey`, 나=우측 `--ch-primary` 흰글씨, `--radius-card`), (c) 음성 오브·Start 버튼=알약형(`--radius-pill`, `--ch-primary`, hover `--ch-primary-strong`, 듣는 중 파형 애니메이션 `--dur-base --ease-out`), (d) @font-face로 Pretendard 로컬 로드.

- [ ] **Step 4: 브라우저 육안 확인**

Run: `cd onramp && uv run python skills/intake/scripts/serve_browser.py`
Expected: 채널톡 룩(파랑 `#6157EA`·알약·Pretendard·채팅버블) 페이지가 열림. 외부 요청 0(무CDN).

- [ ] **Step 5: 커밋** — `git commit -m "style(intake): channeltalk-look interview page (Channel Blue, Pretendard, bubbles)"`

---

## Task 6: 데모 샘플 + README

**Files:**
- Modify: `onramp/skills/intake/assets/sample-discovery.json` (데모용 확장)
- Create: `onramp/skills/intake/output/deployment-brief.md`, `product-input.prd.md` (골든 샘플)
- Modify: `onramp/skills/intake/README.md`

- [ ] **Step 1: sample-discovery.json을 데모 시나리오로 확장** — 가상 패션 이커머스 CS리더 인터뷰(§13). 연동 tier 혼재(배송조회=workflow, 주문취소=system_task), product_gaps 2~3개(action_task, knowledge_authoring).

- [ ] **Step 2: 골든 보고서 생성 & 커밋 대상화**

```bash
cd onramp/skills/handoff
python scripts/build_reports.py ../intake/assets/sample-discovery.json --out-dir ../intake/output
```

- [ ] **Step 3: 골든 회귀 테스트 추가** — `test_reports.py`에 "샘플→두 보고서가 비어있지 않고 필수 섹션 포함" assert(이미 Task 3에서 커버, sample 확장 반영 재확인).

Run: `cd onramp/skills/handoff && python -m pytest tests/test_reports.py -v`
Expected: PASS.

- [ ] **Step 4: intake/README.md 작성** — 무엇을/누구/어떻게(§1~4), 빠른 시작(uv·ElevenLabs 키·serve_browser), 산출물(discovery→두 보고서), PII 주의. 5문항 제출용 근거는 `03_solution-scope_channeltalk.md`·`02_problem-definition` 링크.

- [ ] **Step 5: 커밋** — `git commit -m "feat: demo sample + golden reports + README"`

---

## Self-Review (플랜↔스펙 커버리지)

- §4 아키텍처 → Task 0(포크). §5 intake → Task 2. §6 계약 → Task 1. §7 handoff/보고서 → Task 3·4. §8 4롤 스크립트 → Task 2. §9 페이지 → Task 5. §10 재활용/버림 → Task 0. §11 가드레일 → Task 1(validate)·3(렌더 거부). §12 테스트 → Task 1·3·6. §13 데모 → Task 6. §14 5문항 → README(Task 6). ✅ 전 항목 태스크 존재.
- Placeholder 스캔: 신규 결정 파트(validator·renderer)는 완전 코드. 재활용 scout 파일은 "복사/경로확인"으로 명시(재작성 아님) — 의도된 것.
- 타입 일관성: `validate(data)->(errors,warnings)`, `render_brief/render_prd(d)->str`, enum(ROLES/TIERS/TAGS)이 Global Constraints·Task1·Task3에서 동일.

## 미결정(구현 전 사용자 확인)

- 네이밍(onramp/intake/handoff) 확정 여부.
- ElevenLabs 계정·키 준비(브라우저 데모).
- Pretendard woff2 소스(로컬 배치 방법).
