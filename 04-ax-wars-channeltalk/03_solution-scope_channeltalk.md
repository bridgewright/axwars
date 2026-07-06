# 솔루션 설계 — 채널톡 배포 discovery 플러그인 (spec)

> 대상 기업 = 채널코퍼레이션(채널톡). AX 인재전쟁 해커톤 Codex 플러그인.
> 선행 문서: `01_research_channeltalk.md`(리서치), `02_problem-definition_enterprise-gtm.md`(문제정의), `SUBMISSION_QUESTIONS.md`(5문항).
> 이 문서는 브레인스토밍으로 확정된 설계다. Codex 구현의 입력이 된다.
> 참고 원형: 사용자 기존 `scout` 플러그인(distillery/refinery), Matt Pocock `to-prd`/`grilling` 스킬, Meta `Astryx` 디자인 토큰 패턴.

---

## 1. 한 줄 정의

채널톡 배포 담당자(CS매니저·AE·인증 전문가)가 **엔터프라이즈 고객사의 현업을 음성으로 인터뷰**해서, 그 대화를 **① 배포 계획서(배포팀용)**와 **② 고객 페인+제품 제안서(본진 프로덕트팀용)** 두 문서로 자동 정리해주는 Codex 플러그인.

## 2. 왜 (문제 연결)

- `02_problem-definition`의 결론: 채널톡의 다음 성장은 **엔터프라이즈 ARPU**에 있고, 엔터프라이즈를 여는 열쇠는 **알프v2(업무 자동화) 배포**인데, 그 배포는 **IT-컨설팅형 고난도 작업**이며 배포 학습이 **본진 프로덕트로 환류되지 못한다.**
- 근거(리서치): 고객 페인("커맨드/실제 처리 기능 필요")이 실제로 알프v2 태스크로 제품화된 궤적이 확인됨 = **현장 신호 → 제품 로드맵 루프가 실재하지만 수작업.** 이 루프를 자동화한다.

## 3. 사용자 & 사용 상황

- **플러그인 사용자** = 채널톡 배포 담당(리서치에 반복 등장하는 CS매니저 "소피아·웬디·베이지" 롤, 또는 AE·인증 전문가).
- **인터뷰 대상** = 고객사의 4개 롤(아래 9장). 배포 담당자가 링크를 보내 인터뷰.
- **상황**: 엔터프라이즈 고객 도입 전 discovery 단계. 한 고객사에서 여러 롤을 각각 인터뷰 → discovery 누적.

## 4. 아키텍처 (2-스킬 파이프라인 — scout 미러링)

```
[고객사 현업 4롤]
   │  ElevenLabs signed URL(브라우저 음성) 또는 로컬 CLI
   ▼
스킬 1: intake   (scout distillery 포크)
   - 인터뷰어 페르소나: ALF 배포 discovery (4롤 × 3축, grill-me)
   - 음성 인터뷰 → transcript.jsonl
   - transcript → deployment-discovery.json   (검증된 계약)
   │
   ▼  [deployment-discovery.json]  = SSOT 계약
스킬 2: handoff  (scout refinery 자리)
   - discovery.json 소비 → 결정적 렌더
   ├─▶ deployment-brief.md   (보고서① 배포 계획서 · 배포팀용)
   └─▶ product-input.prd.md  (보고서② 페인+PRD 제언 · 본진용)
```

- 엔진(음성·링크·transcript·validate/build 계약 패턴)은 scout에서 재활용. 교체 대상 = 인터뷰어 프롬프트 + discovery 스키마 + 두 보고서 렌더.
- 네이밍(변경 가능): plugin `onramp` / 스킬1 `intake` / 스킬2 `handoff`.

## 5. 스킬 1 — intake (인터뷰 → discovery 계약)

- **실행 경로 2개**(scout 계승): 브라우저(signed URL, WebRTC 에코제거, 끼어들기) = 데모용 / 로컬 CLI(마이크, `--text-only`).
- **인터뷰어 = 고정 질문지가 아니라 목표 주도**: `deployment-discovery.json`의 빈칸(슬롯)을 grill-me로 채운다. **인터뷰 페이지에서 역할을 먼저 선택**(진입 시 어두운 배경 모달, 이후 헤더 칩으로 변경) → 선택 역할을 ElevenLabs **dynamic variable**(`role`/`role_label`/`opener`)로 전달해 **역할별 오프너·카피·흐름**으로 진행. 페이지 카피는 인터뷰 당사자에게 말 거는 톤. 연결은 `connectionType:"websocket"`(어느 환경에서든 안정 연결, 브라우저 getUserMedia가 에코 제거).
- 산출: `output/transcript.jsonl` + `output/deployment-discovery.json`(validate 게이트 통과).
- 프롬프트 SSOT: `prompt/interviewer-system-prompt.md`(9장 스크립트 그대로 반영).

### grill-me 퍼실리테이션 규칙 (프롬프트에 강제)
- 직접 질문 금지("가장 큰 문제가 뭐예요?" X). 구체 일화부터("어제/지난주 실제로…").
- 한 실을 끝까지: 일화 → 빈도 → 왜 안 고쳐졌나 → 그래서 뭘 원하나.
- 형용사엔 장면 되묻기. 되비추기 확인. 슬롯 차면 다음으로(질문1-답1 아님).
- 제품 갭은 간접 surface: "아직 사람이 꼭 껴야 하는 지점?"·"안 돼서 우회한 적?"·"다음에 더 하고 싶은 것?".
- 성과는 해결률 함정 전제(절대치 목표 위험).

## 6. 계약 — deployment-discovery.json (채워야 할 슬롯)

scout `criteria-spec.md` 패턴을 따르되 스키마는 배포 discovery용. `validate_discovery.py`가 강제, `build_reports.py`가 두 보고서로 렌더.

```jsonc
{
  "meta": { "customer": "...", "interviewee_role": "cs_lead|exec|agent|it", "company_size": "smb|enterprise", "created_at": "YYYY-MM-DD", "created_by": "intake voice interview", "source_transcript": "output/transcript.jsonl" },
  "context": {            // 축 A
    "team_size": "", "daily_volume": "", "channels": [], "inquiry_types": [ { "type": "", "share_pct": 0, "repetitive": true } ]
  },
  "bottlenecks": [        // 축 A — 일화 기반
    { "scene": "고객 말 그대로 인용", "frequency": "", "why_unsolved": "", "desired": "" }
  ],
  "automation_scope": [   // 보고서① 2항
    { "task": "", "current_handling": "", "fit": "high|mid|low", "priority": 0 }
  ],
  "integration": [        // 축 B — 해결률 상한 결정
    { "task": "", "backend_system": "", "separate_or_integrated": "", "has_api": "yes|no|unknown", "built": "inhouse|vendor|unknown", "dev_effort": "", "tier": "no_integration|workflow|system_task" }
  ],
  "knowledge_readiness": { "faq_count_est": 0, "doc_scope": "", "quality_gap": "", "authoring_effort": "" },
  "org_change": { "agent_role_shift": "", "change_mgmt_risk": "" },   // 축 A/보고서① 7항
  "metrics": { "goals": [], "success_definition": "", "resolution_trap_aware": true, "impact_link": "" },  // 축 C
  "product_gaps": [       // 보고서② 8항 — 간접 surface
    { "signal": "", "quote": "", "tag": "action_task|reask_context|knowledge_authoring|voc_distribution|metric_redefine|handoff_quality|multilingual|small_team" }
  ],
  "open_questions": []    // 배포 전 미해결 (사전 단서)
}
```
- 불변(코드 의존): meta 필수키, `interviewee_role`·`tier`·`tag` enum, integration `tier`가 해결률 상한 신호.
- 가변(인터뷰가 채움): 각 배열 내용.
- 정보 부족 슬롯은 상상 금지 → `open_questions`로 밀거나 `"unknown"` 표기(scout 가드레일 계승).

## 7. 스킬 2 — handoff (discovery → 두 보고서)

`build_reports.py`(stdlib, 결정적)가 discovery.json을 읽어 두 파일 렌더. 렌더 전 `validate_discovery.py`로 게이트.

### 보고서 ① deployment-brief.md (배포팀용) — 항목
1. **도입 적합성 진단** — 하루 상담량·팀 규모·반복문의 비중 vs 기준선(1인 30건+/매크로 5건+).
2. **자동화 범위** — 문의 유형별 % → 정형·무개입 우선, 개별확인(배송·결제) 후순위.
3. **연동 가능성 진단(핵심)** — Task별 tier 3분류(무연동/워크플로우/시스템태스크) + 별도·통합/API 유무/자체·외주/대응개발 공수 → 해결률 상한.
4. **지식 준비도 & 정비 공수** — FAQ 개수×시간, 도큐먼트화 대상 규모.
5. **단계적 롤아웃** — 빠른 효과 지점 먼저 → 확장.
6. **성과 지표 설계** — 해결률 단독 금지, 해결률×재인입률×응답시간×인력×CSAT 묶음.
7. **조직·상담사 변화관리** — 역할 전환, 교육 계획.
8. **리스크 & 배포 전 미해결 질문** — 피크 플레이북, 온보딩 미흡=실패 리스크.

### 보고서 ② product-input.prd.md (본진용) — 항목 (to-prd 틀 + 채널톡)
0. **고객 페인포인트** — 일화로 끌어낸 실제 인용.
1. Problem Statement / 2. Solution / 3. User Stories(`As a <역할>, I want <기능>, so that <이유>`) / 4. Implementation Decisions(모듈·연동·스키마 수준, 파일·코드 X) / 5. Testing Decisions / 6. Out of Scope / 7. Further Notes.
8. **제품 갭 태그 분류** — `product_gaps[].tag`를 채널톡 제품 주제로 집계(여러 인터뷰 누적 시 우선순위).

## 8. 인터뷰 스크립트 (4롤 — 확정)

고정 목록이 아니라 답에 따라 갈라지는 흐름. 실제 질문 톤 그대로. 각 롤은 주력 축이 다르되, 대화 중 관련 슬롯이 나오면 그 축으로 분기.

### 롤 A — CX/CS 리더 (도입 오너 · 주축 A, 보조 B·C) [주 대상]
- **[문 열기]** "안녕하세요. 오늘은 OO팀 상담이 실제로 어떻게 돌아가는지 편하게 여쭤볼게요. 요즘 팀에서 하루에 제일 많이 받는 문의가 어떤 거예요?"
- **[그림 그리기]** "그거 보통 어떻게 처리하세요? 어제 하루를 떠올리면 흐름이 어땠어요?"
- **[손 많이 가는 지점]** "그중에 '이건 진짜 매번 손이 많이 간다' 싶은 게 있었어요? 바로 어제 그런 거요." → (두루뭉술하면) "그 장면 하나만 자세히요. 그때 담당자가 정확히 뭘 했어요?"
- **[규모·빈도]** "그런 문의가 하루에 몇 번쯤 와요? 프로모션·피크 때는요?"
- **[병목 원인]** "그거 지금까지 왜 자동으로 못 넘겼어요? 뭐가 걸려요?"
- **[연동 분기 → 축 B]** "그거 처리하려면 어떤 시스템을 봐야 해요? 그게 채널톡이랑 따로 도는 건가요, 붙어 있나요?" → "직접 만드신 거예요, 외부 솔루션이에요?"
- **[상담사 변화]** "이게 알아서 처리되면, 팀원분들은 그 시간에 뭘 하면 좋겠어요?"
- **[성공 그림 → 축 C]** "6개월 뒤에 '도입하길 잘했다' 싶으려면 뭐가 어떻게 달라져 있어야 해요?" → (해결률만 말하면) "숫자 말고, 팀이나 고객 입장 체감으로는요?"
- **[갭 surface]** "지금 하시다가 '이건 아직 안 되네' 싶어서 사람이 꼭 껴야 했던 적 있어요?"
- **[닫기]** 핵심 두세 개 되짚어 확인 + 감사.

### 롤 B — 경영진/스폰서 (주축 C, 보조 A)
- **[문 열기]** "이 도입을 결심하신 이유가 뭐였어요? 뭘 바꾸고 싶으셨어요?"
- **[목표]** "지금 상담/CS가 회사 입장에서 제일 아쉬운 게 뭐예요?" → 장면 되묻기.
- **[성공 기준]** "1년 뒤에 이 투자가 성공이었다고 하려면, 뭘 보고 판단하실 거예요?" → (해결률·비용만 말하면) "고객 경험이나 팀 입장에서는요?"
- **[해결률 함정]** "AI가 문의를 자동으로 다 처리하면 무조건 좋을까요, 아니면 어떤 선이 있을까요?"
- **[임팩트 연결]** "CS가 잘 풀리면 회사의 어떤 지표(매출·재구매·비용)에 연결된다고 보세요?"
- **[조직 의지]** "팀 역할이 바뀌는 것에 내부 걱정이나 저항은 없나요?"
- **[닫기]** 되짚기 + 감사.

### 롤 C — 현장 상담사 (주축 A · 엣지케이스)
- **[문 열기]** "어제 처리한 문의 중에 제일 까다로웠던 거 하나만 들려주세요."
- **[파고들기]** "그때 정확히 어떤 순서로 처리했어요? 어디서 제일 막혔어요?"
- **[반복성]** "이런 게 자주 와요? 하루에 몇 번쯤?"
- **[수작업·우회]** "그거 처리하려고 어떤 화면들을 왔다갔다했어요? 복붙하거나 딴 데서 찾아본 거 있어요?"
- **[엣지케이스]** "고객이 이상하게 물어봐서 곤란했던 적은요?"
- **[갭]** "'이건 시스템이 좀 해줬으면' 싶은 거 있어요?"
- **[닫기]** 되짚기 + 감사.

### 롤 D — IT/시스템 담당 (주축 B)
- **[문 열기]** "지금 주문·예약·회원 관련해서 어떤 시스템을 쓰세요?"
- **[통합/별도]** "그게 하나로 합쳐져 있어요, 아니면 주문 따로 예약 따로예요?"
- **[API]** "밖에서 프로그램으로 불러다 쓸 수 있는 창구(API)가 있어요? 문서화돼 있나요?"
- **[자체/외주]** "직접 만드셨어요, 외부 솔루션이에요? (외주면) 기능 추가하려면 그쪽에 요청해야 하나요, 얼마나 걸려요?"
- **[대응개발]** "채널톡이 주문취소 같은 걸 자동으로 하려면, 우리 쪽에서 뭘 열어주거나 만들어줘야 할 것 같아요?"
- **[데이터·보안]** "고객·주문 정보 연동할 때 걸리는 보안·권한 이슈 있어요?"
- **[닫기]** 되짚기 + 감사.

## 9. 인터뷰 페이지 디자인 (scout BCG룩 → 채널톡룩)

- **토큰(Astryx식 CSS 변수)** `:root`에 선언, light/dark 캐스케이드, motion 토큰(duration/easing 변수화).
- **컬러**: `--ch-primary:#6157EA`(Channel Blue), hover `#4E40C9`, 밝은 변형 `#5E56F0`, 코발트 `#3292E3`, 성공 `#20AB55`, 배경 `#FFFFFF`/`#F7F7F8`, 텍스트 `rgba(0,0,0,.85/.6/.4)`, 그라데이션 `135deg #6157EA→#8E57E7`.
- **서체**: Pretendard (woff2 로컬 vendoring, 무CDN).
- **모양**: 알약형 버튼/오브 `radius 999px`, 카드 `12px`, 소프트 섀도.
- **채팅 버블 transcript**: 상대(AI)=좌측 `#F7F7F8` / 나=우측 `#6157EA` 흰 글씨.
- **음성 오브**: 알약형 런처 모티브, 브랜드색, 듣는 중 파형/점 애니메이션.
- **로고**: `channel.io/logo.webp`로 BCG 로고 대체(빌드 시 로컬 저장).
- **역할 선택 모달**: 진입 시 배경이 어두워지며 4개 역할 카드(CS·상담 리더 / 대표·임원 / 현장 상담사 / 개발·IT 담당) 제시 → 선택 시 히어로 카피(eyebrow·서브)가 역할별로 전환, 헤더에 "역할 · ○○ 변경" 칩. 카피는 인터뷰 당사자에게 말 거는 2인칭 톤.
- **톤**: Bold & Wit(대담한 단순 + 친근한 말풍선/미소).
- 파일: `assets/talk_template.html`(scout 것 리스타일), `assets/channel-logo.*`, `assets/pretendard.*`.

## 10. scout 재활용 vs 신규

- **거의 그대로 재활용**: `setup_agent.py`, `serve_browser.py`, `run_interview.py`, `sd_audio.py`, `fetch_transcript.py`, validate/build 계약 패턴, `output/README.md`(핸드오프 계약) 구조, 테스트 패턴.
- **신규/교체**: `interviewer-system-prompt.md`(9장), `discovery-spec.md`(6장 스키마), `validate_discovery.py`, `build_reports.py`(두 보고서 렌더), `handoff/SKILL.md`, `talk_template.html` 리스타일.
- **버림**: refinery의 채용 채점 로직(`github_analyze.py`, scoring 등).

## 11. 가드레일 & 부족 상황 처리

- **증거 없이 채우지 않음**: 인터뷰에서 안 나온 슬롯은 `open_questions`/`unknown`. 상상 금지.
- **validate 실패 → 인터뷰 보강**(렌더 거부).
- **연동 방식 불명** → integration.tier `unknown` + open_question.
- **PII**: 실제 transcript·API키는 gitignore(`.env`, `_samples/`). 커밋 예시는 가상.
- **해결률 함정**을 보고서①·인터뷰 양쪽에 명문화.

## 12. 테스트

- `validate_discovery.py` 단위테스트(스키마 게이트), `build_reports.py` 렌더 테스트(오디오 없이).
- 커밋되는 **가상 샘플 discovery.json** → 골든 두 보고서(데모·회귀).

## 13. 데모 시나리오 (5문항 Q5용)

- 가상 엔터프라이즈 고객(예: 패션 이커머스 브랜드) CS 리더 음성 인터뷰(브라우저) → `deployment-discovery.json` → `deployment-brief.md` + `product-input.prd.md` 산출.
- 부족 상황 데모: 연동 정보 미확보 시 `open_questions`로 빠지는지.

## 14. 5문항 매핑

| 문항 | 반영 |
|---|---|
| Q1 무엇을/누가/어떤 상황 | 3장(배포 담당이 고객 4롤 인터뷰), 4장 |
| Q2 왜 이 문제(+출처) | 2장 + `02_problem-definition` 근거·출처 |
| Q3 어떻게 작동 | 4~9장(파이프라인·계약·스크립트), 11장(부족 상황) |
| Q4 AI를 어떻게 | 인터뷰 진행·요약·보고서 합성=AI / 스코핑 판단·검증=사람. (구현 후 기록) |
| Q5 어떻게 검증 | 13장 데모(입력→두 보고서) + 12장 테스트 |

## 15. 스코프 경계 & 다음 (미결정/후속)

- **MVP 스코프(이번 빌드)**: 인터뷰 1회(롤 1명) → `deployment-discovery.json` 1개 → 두 보고서 렌더. 4롤 스크립트는 모두 프롬프트에 포함하되, 실행은 시작 시 고른 1개 롤로 진행.
- **후속(범위 밖)**: 한 고객사의 여러 롤 인터뷰를 하나의 discovery로 **병합**하는 기능, 여러 고객 누적 시 `product_gaps.tag` **집계 대시보드**.
- 네이밍 최종 확정(onramp/intake/handoff 잠정).
- ElevenLabs 계정·키(데모 환경). 사용자 준비.
- Codex 구현 플랜은 `PLAN.md`로 별도 작성(writing-plans).
