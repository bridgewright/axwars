---
name: brief
description: intake 인터뷰가 만든 deployment-discovery.json을 입력으로 받아, ① 배포 계획서(deployment-brief.md, C레벨 보고서 수준으로 에이전트가 직접 집필)와 ② 고객 페인+PRD 제언서(product-input.prd.md, 본진 프로덕트팀용)를 생성한다. Use when 사용자가 "discovery로 배포 계획서를 만들어 달라", "본진 PRD 제언서 뽑아 달라", "brief 보고서 생성"을 요청하거나 intake 인터뷰가 끝난 뒤 보고서가 필요할 때.
---

# Brief — discovery → 보고서 (②단계)

배포 discovery 파이프라인의 **②단계**. ①단계(**intake** 음성 인터뷰)가 만든 **`deployment-discovery.json`**을 입력으로 받아, 같은 인터뷰 하나에서 두 문서를 만든다.

- **`deployment-brief.md`** — 배포 계획서. **C레벨(프로젝트 챔피언) 보고서 수준으로 에이전트가 직접 집필**한다(결정론 렌더 아님). 포맷·원칙은 [`references/deployment-brief-format.md`](references/deployment-brief-format.md).
- **`product-input.prd.md`** — 고객 페인 + 제품 제안서. 본진 프로덕트팀용. 이 문서는 현재 `scripts/build_reports.py`가 렌더한다(포맷 개편은 후속 예정).

> **계약(SSOT)**: 입력 스키마는 intake가 소유 → [`../intake/references/discovery-spec.md`](../intake/references/discovery-spec.md).

## 워크플로우

### Step 0 — discovery 로드 + 검증
1. `deployment-discovery.json` 경로 확인. 우선순위: ⓐ 사용자 지정 → ⓑ intake 산출물 `../intake/output/deployment-discovery.json` → ⓒ (테스트) 샘플 `../intake/assets/sample-discovery.json`.
2. **검증**: `python3 ../intake/scripts/validate_discovery.py <discovery.json>`. errors면 렌더 거부 → intake로 되돌아가 보강.

### Step 1 — 배포 계획서 집필 (에이전트가 직접)
1. **반드시 먼저 읽는다**: [`references/deployment-brief-format.md`](references/deployment-brief-format.md)(포맷·6원칙·7섹션·스코어링·각주) + [`references/costing-assumptions.md`](references/costing-assumptions.md)(원가 가정).
2. discovery의 슬롯을 근거로, 포맷 문서의 목차·원칙을 **예외 없이** 지켜 `deployment-brief.md`를 집필한다.
   - 두괄식, 헤드 메시지 = 첫 문장, 명사형 종결, 문단 끝 마침표 없음, 근거 상세·인용, jargon 각주.
   - 2장 현황은 정량 표, 4장은 스코어링 테이블, 6장은 원가 산식 노출.
   - discovery에 없는 값은 상상하지 말고 "확인 필요"로 표기.
3. `<out>/deployment-brief.md`로 저장.

### Step 2 — PRD 렌더 (스크립트)
```bash
python3 scripts/build_reports.py <discovery.json> --out-dir <out>
```
→ `<out>/product-input.prd.md` (결정적, stdlib only).

### Step 3 — 보고
사용자에게 ⓐ 어느 고객·롤의 discovery를 썼는지 ⓑ 배포 계획서 핵심(도입 우선순위와 그 근거, 1차/2차 단계, 원가·제시가) ⓒ 본진 PRD 핵심(제품 갭 태그) ⓓ 산출 파일 경로를 간단히 보고한다.

## 가드레일
- **증거 기반**: 보고서의 모든 항목은 discovery 슬롯에서 나온다. 비어 있으면 "확인 필요 — open_questions 참조"로 표기(상상 금지).
- **해결률 함정 명문화**: 성과 지표는 해결률 단독이 아니라 재인입률·응답시간·인력·CSAT 묶음으로 제시.
- **원가는 가정 기반**: 6장 금액은 `costing-assumptions.md` 가정 기반 개략치임을 명시.
- **포맷 준수**: 배포 계획서는 `deployment-brief-format.md`의 원칙을 100% 지킨다. 어기면 다시 쓴다.

## 파일
- `references/deployment-brief-format.md` — 배포 계획서 포맷·원칙 정본(집필 시 필독).
- `references/costing-assumptions.md` — 배포 원가 가정(6장 산출용).
- `scripts/build_reports.py` — `render_prd` + `main(argv)`. PRD 렌더 전용. intake의 `validate_discovery`를 게이트로 사용.
- `tests/test_reports.py` — PRD 섹션·인용·태그 렌더 테스트.
