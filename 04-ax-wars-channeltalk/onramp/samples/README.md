# 예시 샘플 — 1개 회사 × 4개 그룹 인터뷰 → 두 보고서

라이브 인터뷰 없이 결과를 확인할 수 있도록, **한 회사(무브온, 애슬레저 패션 이커머스)를 4개 그룹·총 9명 인터뷰**한 것으로 가정해 만든 테스트 샘플이다. 모두 가상 데이터.

```
무브온/
  transcripts/
    cs_lead.md   — CS팀장 김서연 · CS파트리더 박준호 (2명)
    exec.md      — 대표 이하늘 · COO 정민재 (2명)
    agent.md     — 상담사 윤지아 · 최다은 · 한소미 (3명)
    it.md        — 개발리드 오세훈 · 백엔드 강태영 (2명)
  deployment-discovery.json   — 4개 그룹 인터뷰를 통합한 계약(interviewee_role: "multi" + org/리드타임/it_capacity/synthesis)
  deployment-brief.md         — 배포 계획서 (C레벨 보고서, 에이전트가 deployment-brief-format.md대로 집필한 exemplar)
  product-input.prd.md        — 고객 페인 → 제품 제언서 (본진용, build_reports.py 렌더)
```

## 이 샘플이 보여주는 것

1. **그룹마다 다른 것을 캐낸다.** CS리더는 업무·병목·정량 현황(조직·비중·리드타임), 경영진은 성과·예산·확장, 현장 상담사는 엣지케이스·수작업·건당 시간, IT는 연동·보안·내부 개발 여력. 네 그룹을 합치면 discovery의 모든 슬롯이 촘촘히 채워진다.
2. **배포 계획서는 C레벨 보고서다.** `deployment-brief.md`는 두괄식·명사형·각주 원칙을 지켜 Executive Summary → 현황 → 페인포인트(현황 위 매핑) → 도입 우선순위(스코어링 테이블) → 기술 고려 → 원가·제시가 → 추가 세일즈 순으로 전개된다. 포맷 정본은 `skills/brief/references/deployment-brief-format.md`.
3. **원가는 가정 × 공수로 계산된다.** 6장 제시가는 `skills/brief/references/costing-assumptions.md`의 표준 가정에 인터뷰가 캐낸 연동 공수를 곱해 산식 그대로 노출한다.
4. **미확보는 상상하지 않는다.** 확인 안 된 항목은 '지금 결정·확인해야 할 것'과 `open_questions`로 남는다.

## 재생성

배포 계획서(`deployment-brief.md`)는 `brief` 스킬을 호출해 에이전트가 포맷 레퍼런스대로 집필한다(결정론 스크립트가 아님).

PRD는 스크립트로 재생성한다:
```bash
python3 skills/brief/scripts/build_reports.py samples/무브온/deployment-discovery.json --out-dir samples/무브온
```
