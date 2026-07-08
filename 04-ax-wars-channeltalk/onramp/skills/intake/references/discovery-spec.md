# discovery-spec — deployment-discovery.json 스키마 (단일 계약)

> 음성 인터뷰 transcript에서 도출한 **채널톡 배포 discovery의 구조화 진실 = `deployment-discovery.json`**.
> `scripts/validate_discovery.py`가 이 스펙을 강제한다. 다운스트림 `brief` 스킬은 이 discovery로
> `deployment-brief.md`(배포 계획서 — 에이전트가 `deployment-brief-format.md`대로 직접 집필)와
> `product-input.prd.md`(본진 페인+PRD 제언서 — `brief/scripts/build_reports.py`가 렌더)를 만든다.
> 필드명·규칙을 바꾸려면 **여기부터** 고친다(SKILL·validator·renderer·테스트가 이 파일을 단일 출처로 따른다).

---

## 1. 핵심 모델

- 인터뷰어는 고정 질문지가 아니라 **아래 슬롯(빈칸)을 grill-me로 채우는 목표 주도** 방식이다.
- 세 축으로 묶인다: **A 업무·병목**(`context`/`bottlenecks`/`automation_scope`/`org_change`) · **B 시스템·연동**(`integration`/`knowledge_readiness`) · **C 성과·임팩트**(`metrics`).
- 인터뷰에서 확보하지 못한 슬롯은 **상상해서 채우지 않는다** → `"unknown"` 표기 또는 `open_questions`로 이동.

## 2. 스키마

```jsonc
{
  "meta": {
    "customer": "가상몰",                    // 필수, 비어있으면 안 됨
    "interviewee_role": "cs_lead",           // 필수. enum: cs_lead|exec|agent|it|multi (여러 그룹을 하나로 통합하면 multi)
    "interviewees": [{ "role": "cs_lead", "who": "CS팀장" }],  // 선택. 여러 명/그룹 인터뷰 시 명단(보고서 헤더에 표기)
    "company_size": "enterprise",            // 필수. smb|enterprise
    "created_at": "2026-07-06",              // 필수 YYYY-MM-DD
    "created_by": "intake voice interview",  // 필수
    "source_transcript": "output/transcript.jsonl"  // 권장(출처 추적)
  },
  "context": {                               // 축 A — 배포 계획서 2장(현황 파악) baseline
    "team_size": "4",
    "daily_volume": "300",
    "monthly_volume": "약 12,000",           // 선택. 총 인입량(현황 표에 사용)
    "channels": ["chat","phone"],
    "org": {                                  // 선택. 상담 조직·R&R (현황 표)
      "headcount": 11,
      "structure": "CS팀장 1 · 파트리더 2 · 상담사 8",
      "peak_surge": "피크 시 단기 +5",
      "roles": [ { "role": "CS팀장", "count": 1, "rnr": "정책·에스컬레이션" } ]
    },
    "inquiry_types": [                         // avg_leadtime: 페인 매핑(리드타임 축)에 사용
      { "type": "배송조회", "share_pct": 40, "avg_leadtime": "2분", "repetitive": true }
    ]
  },
  "bottlenecks": [                           // 축 A — 일화 기반(직접 인용)
    { "scene": "프로모션 때 하루 2000건이 들어와서 팀이 못 버텨요", "frequency": "피크 시즌", "why_unsolved": "주문 상태를 시스템에서 봐야 함", "desired": "주문 조회를 알프가 대신" }
  ],
  "automation_scope": [                      // 보고서① 2항
    { "task": "배송조회", "current_handling": "상담사 수기 확인", "fit": "high", "priority": 1 }
  ],
  "integration": [                           // 축 B — 해결률 상한을 가르는 핵심
    { "task": "주문취소", "backend_system": "자체 어드민", "separate_or_integrated": "integrated",
      "has_api": "unknown", "built": "inhouse", "dev_effort": "미정", "tier": "system_task" }
  ],
  "it_capacity": {                           // 선택. 축 B — 배포 계획서 5·6장(기술 고려·원가)
    "internal_dev": "자체 개발팀 있음 | 외주 의존 | 없음",
    "availability": "대응 개발 여력(예: 1인 1주 확보 가능)",
    "vendor_dependency": "외주 규격 대응 필요 지점(예: 회수 WMS·환불 PG)",
    "security_notes": "결제·개인정보 토큰화·로그·권한 분리 등 전제"
  },
  "knowledge_readiness": {                   // 축 B — 알프 '지식' 에이전트 도입 난이도의 핵심 변수(보고서 4·5장)
    "docs_exist": "yes|partial|no",          // 지식베이스에 적재할 문서가 있는지
    "faq_count_est": 65,                     // 표준 안내 문구/FAQ 개수(추정)
    "faq_format": "단어형|문장형|혼재",        // 정리 포맷·수준(자연어 매칭 가능 여부를 가름)
    "standard_templates": "표준 안내 문구 정리 여부·수준(예: 일부만 공식화, 상담사별 제각각)",
    "doc_scope": "긴 안내 문서의 범위·위치(예: 정책 문서 10건이 노션 산재)",
    "quality_gap": "정비 필요 포인트(문장형 전환, 위치 표준화 등)",
    "authoring_effort": "알프가 읽게 정비하는 데 드는 공수(예: 하루~이틀)"
  },
  "org_change": {                            // 축 A / 보고서① 7항
    "agent_role_shift": "단순 응대 → 지식 세팅·VoC 분석", "change_mgmt_risk": "낮음"
  },
  "metrics": {                               // 축 C
    "goals": ["문의량 감소","응답시간 단축"],
    "success_definition": "재인입률 하락 + CS 만족 유지",
    "resolution_trap_aware": true,           // 해결률 절대치 함정 인지 여부
    "impact_link": "재구매율"
  },
  "product_gaps": [                          // 보고서② 8항 — 간접 surface
    { "signal": "실제 처리(취소)까지 원함", "quote": "취소까지 알아서 됐으면", "tag": "action_task" }
  ],
  "open_questions": ["주문 시스템 API 제공 여부 확인 필요"],  // 배포 전 미해결(사전 단서)
  "synthesis": {                             // 두괄식 보고서용 종합 — intake가 인터뷰를 요약해 채운다(보고서가 맨 앞에 세움)
    "deployment_headline": "무엇을 어떻게 배포할지 한 줄 권고(BLUF)",
    "deployment_rationale": "왜(2~3문장, 현장 근거)",
    "readiness": "green|yellow|red — 한 줄 진단",
    "top_risks": ["먼저 볼 리스크", "..."],
    "product_headline": "본진 프로덕트팀에 전할 한 줄 제언(BLUF)",
    "product_rationale": "왜(핵심 근거)"
  }
}
```

> **두괄식 보고서**: 두 보고서 모두 `synthesis`의 headline·rationale를 **맨 앞 '결론 먼저(권고/제언)'**로 세우고, 이어서 `bottlenecks`·`product_gaps`의 **인용**으로 뒷받침한다. `synthesis`가 없으면 렌더러가 데이터에서 보수적으로 유도하지만 설득력이 약해지므로 채우는 것을 권장(검증에서 WARNING).

## 3. 검증 규칙 (`validate_discovery.py`)

`validate(data) -> (errors, warnings)`. **errors 있으면 invalid (exit 1)**. warnings는 valid이되 경고(exit 0).

### ERROR
1. 최상위 키 누락: `meta, context, bottlenecks, automation_scope, integration, knowledge_readiness, org_change, metrics, product_gaps, open_questions`.
2. `meta.customer/interviewee_role/company_size/created_at/created_by` 빈 값.
3. `meta.interviewee_role` ∉ `{cs_lead, exec, agent, it}`.
4. 어느 `integration[i].tier` ∉ `{no_integration, workflow, system_task}`.
5. 어느 `product_gaps[i].tag` ∉ `{action_task, reask_context, knowledge_authoring, voc_distribution, metric_redefine, handoff_quality, multilingual, small_team}`.

### WARNING
- `context.inquiry_types` 빈 배열 (자동화 스코프 산정 불가).
- `bottlenecks` 빈 배열 (인터뷰 보강 권장).
- `context.org` 없음 (배포 계획서 2장 조직·R&R 표가 비어짐 — 권장).
- `context.inquiry_types`에 `avg_leadtime` 전무 (3장 페인 매핑의 리드타임 축 약화 — 권장).
- `it_capacity` 없음 (5·6장 고객 IT 여력·원가 산정에 필요 — 권장).

## 4. 불변 / 가변

- **불변(코드 의존)**: 위 최상위 키, `interviewee_role`·`tier`·`tag` enum.
- **가변(인터뷰가 채움)**: 각 배열·객체 내용, 자유 텍스트 슬롯. 미확보는 `"unknown"`/`open_questions`.
