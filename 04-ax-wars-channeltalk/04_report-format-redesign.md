# 산출물 포맷 개편 — deployment-brief (C레벨 보고서화)

> 확정일 2026-07-08. 이 문서는 `onramp` 플러그인의 산출물 포맷 개편 계약이다. 사용자 승인 완료(결정 1-A, 2-원가가정파일).

## 목표

`deployment-brief.md`를 **BCG 컨설턴트가 프로젝트 챔피언(C레벨)에게 보고하는 문서** 수준으로 끌어올린다. 단어 나열식 말투를 걷어내고, 두괄식·명사형·근거 상세·각주 원칙을 지키는 서사형 보고서로 만든다.

## 확정된 결정

- **결정 1 — 렌더링 방식: (A) LLM 저작.** `brief` 스킬은 결정론적 Python 렌더러가 아니라, 에이전트가 discovery.json + 원가 가정을 읽어 포맷 레퍼런스대로 **직접 집필**한다. 산문 품질이 본질이라 템플릿으로는 못 낸다.
- **결정 2 — 숫자·원가 출처.** 현황 정량(상담 수/비중/리드타임/조직)은 **인터뷰에서 캐낸다**(미확보 시 "확인 필요" 명시). 원가·마진·제시가격은 고객 인터뷰가 아니라 **채널톡 배포팀 내부 경제성**이므로 플러그인의 **원가 가정 파일**(인력 단가·라이선스·tier별 소요·최소 마진율)에 두고, 인터뷰가 캐낸 연동 공수를 곱해 산출한다.
- **스킬 이름: `handoff` → `brief`** (기존 스킬명과 충돌 회피).

## 작성 원칙 (플러그인 내 모든 산출물 공통)

1. 두괄식 — 결론·권고를 문서 맨 앞, 섹션 맨 앞에 먼저.
2. 핵심 메시지 = 각 문단의 첫 문장. 각 섹션의 헤드 메시지는 섹션 최상단에 별도로.
3. 명사형 종결어미("~해야 함 / ~로 판단됨 / ~가 필요 / ~구간임").
4. 각 문단 마지막 문장에는 마침표를 찍지 않음.
5. 핵심 메시지의 근거는 상세·친절하게. 인터뷰 인용으로 뒷받침.
6. Jargon 통제 — 채널톡 내부 용어(AICC, 알프 v2 Task 등)는 허용하되 그 외 전문어는 쉬운 말로 풀거나 각주로 개념 설명 필수. 전문어를 조사로 줄줄이 잇는 말투 금지.

## 새 deployment-brief 목차

```
# 채널톡 배포 계획서: {고객사}({업종})
0. (메타) 보고 대상 · 작성일 · 근거(인터뷰 대상)
1. Executive Summary   — 각 섹션 헤드메시지를 하나의 서사로 연결 + sub-bullet 부연
2. 현황 파악           — 상담 정량 진단: 총 인입량 / 상담원 수 / 조직·R&R / 유형별 비중 / 유형별 리드타임
3. 페인포인트(원인 진단) — 페인 그룹핑 + 현황(비중·리드타임) 위에 매핑 + 총 N개·최빈 항목
4. 도입 고려 에이전트 & 우선순위 — 평가기준 스코어링 테이블
5. 우선순위 에이전트의 기술 고려사항 — 자체개발/솔루션·내부 IT 여력·보안
6. 도입 원가 & 제시 가격 — 필요 인력·기간 → 원가(인력+라이선스) → 최소 마진 기준 제시가
7. 추가 세일즈 기회
```

## 파일 변경 (이번 턴)

- `skills/handoff/` → `skills/brief/` (git mv).
- `skills/brief/SKILL.md` — LLM 저작 오케스트레이션으로 재작성.
- `skills/brief/references/deployment-brief-format.md` — 새 포맷·6원칙·7섹션·우선순위 테이블·각주 용어집·원가 계산법(신규).
- `skills/brief/references/costing-assumptions.md` — 채널톡 배포 원가 가정(신규).
- `skills/brief/scripts/build_reports.py` — PRD 전용으로 축소(render_brief 제거). PRD는 이번엔 기존 방식 유지.
- `skills/intake/references/discovery-spec.md` + `scripts/validate_discovery.py` — 스키마 확장(context.org, inquiry_types[].avg_leadtime, it_capacity 등, 하위호환 optional).
- `skills/intake/prompt/interviewer-system-prompt.md` — 커버리지 맵 + 4개 롤 흐름 + grill-me 2-꼬리질문 규칙 강화(정량 현황·IT 여력·원가·세일즈 신호까지).
- `samples/무브온/transcripts/*` + `deployment-discovery.json` — 정량 데이터 보강.
- `samples/무브온/deployment-brief.md` — 새 포맷 exemplar 손집필.
- plugin.json / README / handoff-contract 내 `handoff`→`brief` 참조 갱신.

## 이번 턴 out of scope

- `product-input.prd.md` 포맷 전면 개편(다음 턴에 동일 원칙 적용). 이번엔 기존 렌더러로 계속 생성.
