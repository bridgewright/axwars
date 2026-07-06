# 예시 샘플 — 1개 회사 × 4개 그룹 인터뷰 → 두 보고서

라이브 인터뷰 없이 결과를 확인할 수 있도록, **한 회사(무브온, 애슬레저 패션 이커머스)를 4개 그룹·총 9명 인터뷰**한 것으로 가정해 만든 테스트 샘플이다. 모두 가상 데이터.

```
무브온/
  transcripts/
    cs_lead.md   — CS팀장 김서연 · CS파트리더 박준호 (2명)
    exec.md      — 대표 이하늘 · COO 정민재 (2명)
    agent.md     — 상담사 윤지아 · 최다은 · 한소미 (3명)
    it.md        — 개발리드 오세훈 · 백엔드 강태영 (2명)
  deployment-discovery.json   — 4개 그룹 인터뷰를 통합한 계약(interviewee_role: "multi" + synthesis)
  deployment-brief.md         — 배포 계획서 (두괄식, 배포팀용)
  product-input.prd.md        — 고객 페인 → 제품 제언서 (두괄식, 본진용)
```

## 이 샘플이 보여주는 것

1. **그룹마다 다른 것을 캐낸다.** CS리더는 업무·병목, 경영진은 성과·의사결정, 현장 상담사는 엣지케이스·수작업, IT는 연동·보안. 네 그룹을 합치면 discovery의 모든 슬롯이 촘촘히 채워진다.
2. **보고서는 두괄식이다.** 두 보고서 모두 **⚡ 결론 먼저(권고/제언)** 로 시작해 So-What을 명확히 하고, 이어서 **현장 인용**으로 설득한다. 이 요약은 discovery의 `synthesis` 블록(intake가 인터뷰를 종합해 채움)에서 온다.
3. **신호 강도가 집계된다.** 같은 제품 갭을 여러 인터뷰이가 말하면(`product_gaps[].tag`) PRD에서 건수로 집계돼 우선순위가 보인다(예: `[action_task]` 2건, `[reask_context]` 2건).
4. **미확보는 상상하지 않는다.** 확인 안 된 항목은 `open_questions`로 남아 '지금 결정·확인해야 할 것'이 된다.

## 재생성
```bash
python3 skills/handoff/scripts/build_reports.py samples/무브온/deployment-discovery.json --out-dir samples/무브온
```
