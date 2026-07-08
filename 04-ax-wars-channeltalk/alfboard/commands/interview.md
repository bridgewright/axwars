---
description: 고객 현업을 음성으로 인터뷰해 deployment-discovery.json을 만든다 (alfboard 도입 준비 ①단계)
allowed-tools: [Bash, Read, Write, AskUserQuestion]
---

alfboard의 `interview` 스킬(`skills/interview/SKILL.md`)을 사용해 고객 현업 음성 인터뷰를 진행하고, transcript에서 `deployment-discovery.json`을 도출한다.

스킬의 전체 절차를 따른다: ElevenLabs 인터뷰어 에이전트 셋업 → 음성 인터뷰(브라우저 또는 CLI) → transcript 확보 → `references/discovery-spec.md` 스키마대로 `deployment-discovery.json` 조립 → `scripts/validate_discovery.py` 게이트 통과. 미확보 슬롯은 상상하지 말고 `open_questions`로 남긴다.

사용자가 인자를 주면 반영: $ARGUMENTS
