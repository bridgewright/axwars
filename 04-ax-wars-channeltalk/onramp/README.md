# Onramp — 채널톡 엔터프라이즈 배포 discovery

> 고객 현업을 음성으로 인터뷰해, **배포 계획서**와 **본진 프로덕트팀용 페인+PRD 제언서**를 자동으로 뽑는 Codex 플러그인.

`intake`(인터뷰 → `deployment-discovery.json`) → `handoff`(→ 두 보고서) 2-스킬 파이프라인.

---

## 1. 무엇을, 누가, 어떤 상황에서 쓰나

**채널톡 배포 담당자(CS매니저·AE·인증 전문가)**가 엔터프라이즈 고객에게 알프(AI 상담 에이전트)를 도입하기 **전 discovery 단계**에서 쓴다. 고객사의 CS 리더·경영진·상담사·IT 담당에게 링크를 보내 **음성 인터뷰**하면, 그 대화 한 번에서 ① 배포팀용 **배포 계획서**와 ② 본진 프로덕트팀용 **고객 페인+PRD 제언서**가 나온다.

## 2. 왜 이 문제인가

채널톡의 다음 성장은 **엔터프라이즈 ARPU**에 달렸고(무료 도달 24만 사는 포화, 재무는 완전 자본잠식), 엔터프라이즈를 여는 열쇠는 **알프v2(업무 자동화) 배포**다. 그런데 이 배포는 스코핑·지식정비·시스템 연동·변화관리·지표설계를 다루는 **IT-컨설팅형 고난도 작업**이고, 그 현장 학습이 **본진 프로덕트로 환류되지 못한다.** 실제로 "커맨드(실제 처리) 기능이 필요하다"는 고객 요구가 알프v2 태스크로 제품화된 궤적이 있다 — 현장 신호가 로드맵이 되는 이 루프를 **수작업에서 자동화**한다.
근거·출처: [`../02_problem-definition_enterprise-gtm.md`](../02_problem-definition_enterprise-gtm.md), [`../01_research_channeltalk.md`](../01_research_channeltalk.md).

## 3. 어떻게 작동하나

```
[고객 현업]  ──ElevenLabs 음성 링크/CLI──▶  intake
                                             ├ grill-me 인터뷰(4롤×3축): 페인을 대놓고 묻지 않고 일화로 유도
                                             └ transcript → deployment-discovery.json (validate 게이트)
                                                     │
                                                     ▼  handoff
                                             ├▶ deployment-brief.md   (배포 계획서: 적합성/자동화 범위/연동 진단/지식/롤아웃/지표/변화관리/미해결)
                                             └▶ product-input.prd.md  (본진 PRD: Problem/Solution/User Stories/… + 제품 갭 태그)
```
- **절차·지식·판단 기준**: 인터뷰어는 고정 질문지가 아니라 discovery 슬롯(빈칸)을 채우는 **목표 주도**. 롤(cs_lead/exec/agent/it)에 따라 강조 축(업무·병목 / 시스템·연동 / 성과·임팩트)이 달라진다.
- **정보 부족 시**: 확보 못 한 슬롯은 상상하지 않고 `"unknown"` 또는 `open_questions`로 남긴다. discovery가 스키마 검증에 실패하면 렌더를 거부하고 인터뷰 보강으로 되돌린다.
- **연동 진단이 핵심**: Task별 tier(`no_integration`/`workflow`/`system_task`)가 해결률 상한을 가른다. 배포 브리프가 이를 전면에 둔다.
- **해결률 함정**: 성과 지표는 자동해결률 단독이 아니라 재인입률·응답시간·인력·CSAT 묶음(이스타항공 74%→50% 사례 반영).

## 4. AI를 어떻게 썼나

- **AI 담당**: 음성 인터뷰 진행(ElevenLabs + Claude), 대화에서 discovery 슬롯 채우기, 두 보고서 문장 합성.
- **사람/코드 담당**: 자동화 범위·연동 스코핑 판단은 배포 담당자, 계약 검증(`validate_discovery.py`)·보고서 렌더(`build_reports.py`)는 **결정적 stdlib 코드**(LLM 비의존). AI 산출과 결정적 렌더를 분리해 재현성을 확보.

## 5. 어떻게 검증했나

- **입력→결과 예시**: `skills/intake/assets/sample-discovery.json`(가상 패션 이커머스 CS리더 인터뷰) → `build_reports.py` → `sample-deployment-brief.md` + `sample-product-input.prd.md`.
- **테스트**: `pytest`로 스키마 검증(enum·필수키·경고) 6건, 두 보고서 렌더(섹션·인용·태그) 5건, transcript 캡처 8건 = 총 19건 통과.
- **예외 처리**: 잘못된 enum/누락 키는 검증에서 걸러 렌더 거부. 미확보 슬롯은 "확인 불가"로 표기.

```bash
# 데모
python3 skills/handoff/scripts/build_reports.py skills/intake/assets/sample-discovery.json --out-dir /tmp/onramp
# 테스트
python3 -m pytest skills/intake/tests skills/handoff/tests -q
```

---

## 빠른 시작 (음성 인터뷰)
`skills/intake/README.md` 참조. 요약: `uv pip install -r skills/intake/requirements.txt` → `.env`에 `ELEVENLABS_API_KEY` → `setup_agent.py --write-env` → `serve_browser.py`.

## 구조
- `skills/intake/` — 음성 인터뷰 → discovery.json (scout `distillery` 포크)
- `skills/handoff/` — discovery.json → 두 보고서
- 설계 정본: [`../03_solution-scope_channeltalk.md`](../03_solution-scope_channeltalk.md)

## 라이선스
MIT. 인터뷰 페이지는 채널톡 브랜드(Channel Blue `#6157EA`, Pretendard, Bezier 톤)를 참고했고, Meta Astryx의 CSS 토큰/모션 패턴(MIT)을 차용했다.
