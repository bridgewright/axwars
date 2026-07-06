# 예시 샘플 — 역할별 인터뷰 → 두 보고서 (4쌍)

라이브 인터뷰 없이 결과를 확인할 수 있도록, **4개 역할 각각의 가상 인터뷰 트랜스크립트**로부터 스킬을 돌려 만든 테스트 샘플이다. 모두 가상 고객·가상 데이터.

각 폴더 = 한 인터뷰:
- `transcript.md` — intake 음성 인터뷰를 글로 옮긴 예시(격식체)
- `deployment-discovery.json` — 트랜스크립트에서 도출한 계약(intake Step 4). `validate_discovery.py` 통과
- `deployment-brief.md` — 배포 계획서(handoff 산출, 배포팀용)
- `product-input.prd.md` — 고객 페인 + PRD 제언서(handoff 산출, 본진용)

| # | 역할 | 가상 고객 | 축 강조 | 관전 포인트 |
|---|---|---|---|---|
| 01 | `cs_lead` CS·상담 리더 | 무브온(패션 이커머스) | A 업무·병목 (풀커버) | 자동화 범위·연동 tier 혼재·성과 지표 묶음 |
| 02 | `exec` 대표·임원 | 트립메이커(여행 예약) | C 성과·임팩트 | 연동은 얇고 **미해결 질문**이 두터움, `metric_redefine`·`multilingual` 갭 |
| 03 | `agent` 현장 상담사 | 글로우랩(뷰티 D2C) | A 엣지케이스 | 성분·되묻기·조건부 교환접수, `reask_context`·`action_task` 갭 |
| 04 | `it` IT/시스템 담당 | 핀리(구독 핀테크) | B 시스템·연동 | 연동 진단이 구체적(자체 API vs PG 2~3주), 보안 `handoff_quality` 갭 |

**핵심 시연 포인트**: 같은 스킬이라도 **인터뷰한 역할에 따라 채워지는 슬롯과 보고서가 달라진다.** 경영진 인터뷰는 성과·의사결정이 두텁고 기술 세부는 "확인 필요"로 남으며, IT 인터뷰는 연동 진단이 촘촘하고 지표는 얕다. 미확보 슬롯은 상상 없이 `unknown`/`open_questions`로 처리된다.

## 재생성
```bash
python3 skills/handoff/scripts/build_reports.py samples/01-cs_lead-무브온/deployment-discovery.json --out-dir samples/01-cs_lead-무브온
```
