---
name: report
description: interview 인터뷰가 만든 deployment-discovery.json을 입력으로 받아, ① 배포 계획서(deployment-brief.md, 고객 C레벨용)와 ② 본진 프로덕트팀용 제품 인풋(product-input.md, 고객 페인·니즈 + 제품 개발 시 고려사항)을 에이전트가 직접 집필한다. Use when 사용자가 "discovery로 배포 계획서를 만들어 달라", "제품 인풋 문서 뽑아 달라", "report 산출물 생성"을 요청하거나 interview 인터뷰가 끝난 뒤 산출물이 필요할 때.
---

# Report — discovery → 두 문서 (②단계)

도입 준비 파이프라인의 **②단계**. ①단계(**interview** 음성 인터뷰)가 만든 **`deployment-discovery.json`**을 입력으로 받아, 같은 인터뷰 하나에서 두 문서를 **에이전트가 직접 집필**한다(결정론 렌더 아님).

- **`deployment-brief.md`** — 배포 계획서. 고객 C레벨(프로젝트 챔피언) 보고서. 포맷: [`references/deployment-brief-format.md`](references/deployment-brief-format.md), 원가: [`references/costing-assumptions.md`](references/costing-assumptions.md).
- **`product-input.md`** — 본진 프로덕트팀용. 고객 페인·니즈 + 제품 개발 시 고려사항(PRD 아님). 포맷: [`references/product-input-format.md`](references/product-input-format.md).

> **계약(SSOT)**: 입력 스키마는 interview가 소유 → [`../interview/references/discovery-spec.md`](../interview/references/discovery-spec.md).

## 워크플로우

### Step 0 — discovery 로드 + 검증
1. `deployment-discovery.json` 경로 확인. 우선순위: ⓐ 사용자 지정 → ⓑ interview 산출물 `../interview/output/deployment-discovery.json` → ⓒ (테스트) 샘플 `../interview/assets/sample-discovery.json`.
2. **검증**: `python3 ../interview/scripts/validate_discovery.py <discovery.json>`. errors면 집필 거부 → interview로 되돌아가 보강.

### Step 1 — 배포 계획서 집필 (에이전트가 직접)
1. **반드시 먼저 읽는다**: [`references/deployment-brief-format.md`](references/deployment-brief-format.md) + [`references/costing-assumptions.md`](references/costing-assumptions.md).
2. discovery 슬롯을 근거로 포맷의 목차·원칙을 **예외 없이** 지켜 `deployment-brief.md`를 집필한다(두괄식, 명사형, 각주·가운데점 금지, `[라벨]` 불렛, 짧은 문장).
3. `<out>/deployment-brief.md`로 저장.

### Step 2 — 제품 인풋 집필 (에이전트가 직접)
1. **반드시 먼저 읽는다**: [`references/product-input-format.md`](references/product-input-format.md).
2. discovery의 `product_gaps`, `bottlenecks`, `integration`, `metrics`를 근거로, **고객 페인·니즈**와 **제품 개발 시 고려사항**을 집필한다. 기능을 처방(스펙)하지 말고 만들 때의 고려사항으로 쓴다.
3. `<out>/product-input.md`로 저장.

### Step 3 — 보고
사용자에게 ⓐ 어느 고객·롤의 discovery를 썼는지 ⓑ 배포 계획서 핵심(도입 우선순위, 단계, 원가) ⓒ 제품 인풋 핵심(가장 강한 페인·니즈 태그와 제품 표면) ⓓ 산출 파일 경로를 보고한다.

## 가드레일
- **증거 기반**: 두 문서의 모든 항목은 discovery 슬롯에서 나온다. 비어 있으면 "확인 필요"로 표기(상상 금지).
- **해결률 함정 명문화**: 성과 지표는 해결률 단독이 아니라 재인입률, 응답시간, 인력, 상담 만족도 묶음으로 제시.
- **원가는 가정 기반**: 배포 계획서 6장 금액은 `costing-assumptions.md` 가정 기반 개략치임을 명시.
- **처방 금지(제품 인풋)**: 제품 인풋은 "이렇게 만들어라"가 아니라 "만들 때 이런 것을 고려해야 한다"로 쓴다.
- **포맷 준수**: 두 문서 모두 각 포맷 레퍼런스의 원칙을 100% 지킨다. 어기면 다시 쓴다.

## 파일
- `references/deployment-brief-format.md` — 배포 계획서 포맷·원칙 정본.
- `references/product-input-format.md` — 제품 인풋 포맷·원칙 정본.
- `references/costing-assumptions.md` — 배포 원가 가정(배포 계획서 6장용).
