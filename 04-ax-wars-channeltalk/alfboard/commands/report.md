---
description: discovery로 배포 계획서와 제품 인풋(제품팀 피드백) 문서를 집필한다 (alfboard 도입 준비 ②단계)
allowed-tools: [Bash, Read, Write]
---

alfboard의 `report` 스킬(`skills/report/SKILL.md`)을 사용해 `deployment-discovery.json`으로 두 문서를 집필한다.

- **배포 계획서** `deployment-brief.md` — 고객 C레벨용. 포맷: `skills/report/references/deployment-brief-format.md`, 원가: `costing-assumptions.md`.
- **제품 인풋** `product-input.md` — 본진 프로덕트팀 피드백(고객 페인/니즈 + 제품 고려사항). 포맷: `skills/report/references/product-input-format.md`.

집필 전 `../interview/scripts/validate_discovery.py`로 discovery를 검증한다. 공통 작성 원칙(두괄식, 명사형, 각주·가운데점 금지, `[라벨]` 불렛)을 지킨다. 미확보 항목은 "확인 필요"로 표기.

사용자가 인자(예: discovery 경로)를 주면 반영: $ARGUMENTS
