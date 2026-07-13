# 예시 샘플 — 1개 회사 × 4개 그룹 인터뷰 → 두 문서

라이브 인터뷰 없이 결과를 확인할 수 있도록, **한 회사(무브온, 애슬레저 패션 이커머스)를 4개 그룹·총 9명 인터뷰**한 것으로 가정해 만든 테스트 샘플이다. 모두 가상 데이터.

```
무브온/
  transcripts/
    cs_lead.md   — CS팀장 김서연 · CS파트리더 박준호 (2명)
    exec.md      — 대표 이하늘 · COO 정민재 (2명)
    agent.md     — 상담사 윤지아 · 최다은 · 한소미 (3명)
    it.md        — 개발리드 오세훈 · 백엔드 강태영 (2명)
  deployment-discovery.json   — 4개 그룹 인터뷰를 통합한 계약(interviewee_role: "multi" + org/리드타임/it_capacity/synthesis)
  deployment-brief.md         — 배포 계획서 (고객 C레벨용, deployment-brief-format.md대로 집필한 exemplar)
  product-input.md            — 제품 인풋 (본진 프로덕트팀용, 고객 페인/니즈 + 제품 고려사항, product-input-format.md대로 집필)
```

## 이 샘플이 보여주는 것

1. **그룹마다 다른 것을 캐낸다.** CS리더는 업무·병목·정량 현황(조직·비중·리드타임), 경영진은 성과·예산·확장, 현장 상담사는 엣지케이스·수작업·건당 시간, IT는 연동·보안·내부 개발 여력. 네 그룹을 합치면 discovery의 모든 슬롯이 촘촘히 채워진다.
2. **두 문서는 독자가 다르다.** `deployment-brief.md`는 고객 C레벨을 설득하는 배포 계획서(두괄식, 7섹션, 원가·제시가)이고, `product-input.md`는 본진 프로덕트팀에 올리는 고객 페인/니즈와 제품 개발 시 고려사항이다. 작성 원칙(두괄식, 명사형, 각주·가운데점 금지, [라벨] 불렛)은 공유한다.
3. **원가는 가정 × 공수로 계산된다.** 배포 계획서 6장 제시가는 `skills/report/references/costing-assumptions.md`의 표준 가정에 인터뷰가 캐낸 연동 공수를 곱해 산식 그대로 노출한다.
4. **미확보는 상상하지 않는다.** 확인 안 된 항목은 각 문서의 '확인 필요'와 `open_questions`로 남는다.

## 재생성

두 문서 모두 `report` 스킬을 호출해 **에이전트가 각 포맷 레퍼런스대로 집필**한다(결정론 스크립트가 아님). discovery는 아래로 검증한다:
```bash
python3 skills/interview/scripts/validate_discovery.py samples/무브온/deployment-discovery.json
```
