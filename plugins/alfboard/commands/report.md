---
description: discovery로 배포 계획서와 제품 인풋 문서를 집필한다. discovery가 없으면 무브온 예시를 보여준다 (alfboard 도입 준비 ②단계)
allowed-tools: [Bash, Read, Write, AskUserQuestion]
---

alfboard의 `report` 스킬(`skills/report/SKILL.md`)을 사용한다. **먼저 discovery 유무를 본다.**

- 실제 `deployment-discovery.json`이 없거나 슬롯이 비었으면 → 집필하지 말고 **AskUserQuestion**으로 "무브온 예시 산출물을 보여드릴까요?"를 먼저 묻는다. [예]면 `samples/무브온/`의 배포 계획서(`deployment-brief.md`), 제품 인풋(`product-input.md`), 원본 `deployment-discovery.json`을 안내한다(데모).
- 실제 discovery가 있으면 → `skills/interview/scripts/validate_discovery.py`로 검증 후 두 문서를 집필한다.
  - **배포 계획서** `deployment-brief.md` — 고객 C레벨용. 포맷 `skills/report/references/deployment-brief-format.md`, 원가 `costing-assumptions.md`.
  - **제품 인풋** `product-input.md` — 본진 프로덕트팀 피드백(고객 페인/니즈 + 제품 고려사항). 포맷 `skills/report/references/product-input-format.md`.

공통 작성 원칙(두괄식, 명사형, 각주·가운데점 금지, `[라벨]` 불렛)을 지킨다. 미확보 항목은 "확인 필요"로 표기.

사용자가 인자(예: discovery 경로)를 주면 반영: $ARGUMENTS
