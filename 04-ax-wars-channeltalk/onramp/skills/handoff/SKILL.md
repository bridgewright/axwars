---
name: handoff
description: intake 인터뷰가 만든 deployment-discovery.json을 입력으로 받아, ① 배포 계획서(deployment-brief.md, 배포팀용)와 ② 고객 페인+PRD 제언서(product-input.prd.md, 본진 프로덕트팀용) 두 문서를 결정적으로 생성한다. Use when 사용자가 "discovery로 배포 계획서를 만들어 달라", "본진 PRD 제언서 뽑아 달라", "handoff 보고서 생성"을 요청하거나 intake 인터뷰가 끝난 뒤 두 보고서가 필요할 때.
---

# Handoff — discovery → 두 보고서 (②단계)

배포 discovery 파이프라인의 **②단계**. ①단계(**intake** 음성 인터뷰)가 만든 **`deployment-discovery.json`**을 입력으로 받아, 같은 인터뷰 하나에서 **두 문서**를 렌더한다.

- **`deployment-brief.md`** — 배포 계획서. 배포팀이 "이 고객에 어떻게 깔지" 정하는 실행 문서.
- **`product-input.prd.md`** — 고객 페인 + 제품 제안서. 본진 프로덕트팀이 바로 쓰는 to-prd 형식.

> **계약(SSOT)**: 입력 `deployment-discovery.json` 스키마는 intake가 소유 → [`../intake/references/discovery-spec.md`](../intake/references/discovery-spec.md). 핸드오프 계약은 [`../intake/references/handoff-contract.md`](../intake/references/handoff-contract.md).

## 워크플로우

### Step 0 — discovery 로드 + 검증
1. `deployment-discovery.json` 경로 확인. 우선순위: ⓐ 사용자 지정 → ⓑ intake 산출물 `../intake/output/deployment-discovery.json` → ⓒ (테스트) 샘플 `../intake/assets/sample-discovery.json`.
2. **검증**: `python3 scripts/build_reports.py`가 렌더 전 `validate_discovery.validate`를 호출한다. errors면 렌더 거부 → intake로 되돌아가 보강.

### Step 1 — 두 보고서 렌더
```bash
python3 scripts/build_reports.py <discovery.json> --out-dir <out>
```
→ `<out>/deployment-brief.md` + `<out>/product-input.prd.md` (결정적, stdlib only).

### Step 2 — 보고
사용자에게 ⓐ 어느 고객·롤의 discovery를 썼는지 ⓑ 배포 브리프 핵심(연동 tier가 해결률 상한을 어떻게 가르는지, 자동화 우선순위) ⓒ 본진 PRD 핵심(제품 갭 태그 분류) ⓓ 산출 파일 경로를 간단히 보고한다.

## 가드레일
- **증거 기반**: 보고서의 모든 항목은 discovery 슬롯에서 나온다. 비어 있으면 "확인 불가 — open_questions 참조"로 표기(상상 금지).
- **해결률 함정 명문화**: 배포 브리프의 성과 지표는 해결률 단독이 아니라 재인입률·응답시간·인력·CSAT 묶음으로 제시.
- **결정적 렌더**: 같은 discovery → 같은 두 보고서. `build_reports.py`는 stdlib only.

## 파일
- `scripts/build_reports.py` — `render_brief`·`render_prd` + `main(argv)`. intake의 `validate_discovery`를 게이트로 사용.
- `tests/test_reports.py` — 두 보고서 섹션·인용·태그 렌더 테스트.
