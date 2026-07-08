# Onramp — 채널톡 엔터프라이즈 배포 discovery

> 고객 현업을 음성으로 인터뷰해, **배포 계획서**와 **본진 프로덕트팀용 제품 인풋 문서(고객 페인/니즈 + 제품 고려사항)**를 자동으로 뽑는 Codex 플러그인.

`intake`(인터뷰 → `deployment-discovery.json`) → `brief`(→ 두 문서) 2-스킬 파이프라인.

---

## 1. 무엇을, 누가, 어떤 상황에서 쓰나

**채널톡 배포 담당자(CS매니저, AE, 인증 전문가)**가 엔터프라이즈 고객에게 알프(AI 상담 에이전트)를 도입하기 **전 discovery 단계**에서 쓴다. 고객사의 CS 리더, 경영진, 상담사, IT 담당에게 링크를 보내 **음성 인터뷰**하면, 그 대화 한 번에서 ① 고객 C레벨용 **배포 계획서**와 ② 본진 프로덕트팀용 **고객 페인/니즈와 제품 고려사항 문서**가 나온다.

## 2. 왜 이 문제인가

채널톡의 다음 성장은 **엔터프라이즈 ARPU**에 달렸고(무료 도달 24만 사는 포화, 재무는 완전 자본잠식), 엔터프라이즈를 여는 열쇠는 **알프v2(업무 자동화) 배포**다. 그런데 이 배포는 스코핑, 지식정비, 시스템 연동, 변화관리, 지표설계를 다루는 **IT-컨설팅형 고난도 작업**이고, 그 현장 학습이 **본진 프로덕트로 환류되지 못한다.** 실제로 "커맨드(실제 처리) 기능이 필요하다"는 고객 요구가 알프v2 태스크로 제품화된 궤적이 있다 — 현장 신호가 로드맵이 되는 이 루프를 **수작업에서 자동화**한다.
근거·출처: [`../02_problem-definition_enterprise-gtm.md`](../02_problem-definition_enterprise-gtm.md), [`../01_research_channeltalk.md`](../01_research_channeltalk.md).

## 3. 어떻게 작동하나

```
[고객 현업]  ──ElevenLabs 음성 링크/CLI──▶  intake
                                             ├ 페이지에서 역할 선택(모달) → 역할별 카피·오프너 (dynamic variable)
                                             ├ grill-me 인터뷰(4롤×3축): 페인을 대놓고 묻지 않고 일화로 유도
                                             └ transcript → deployment-discovery.json (validate 게이트)
                                                     │
                                                     ▼  brief (두 문서 모두 에이전트가 포맷 레퍼런스대로 집필)
                                             ├▶ deployment-brief.md   (배포 계획서: 고객 C레벨용, 7섹션)
                                             └▶ product-input.md      (제품 인풋: 본진 프로덕트팀용, 고객 페인/니즈 + 제품 고려사항)
```
- **두 문서 모두 에이전트가 집필**: 배포 계획서는 `references/deployment-brief-format.md`, 제품 인풋은 `references/product-input-format.md`를 따른다. 공통 작성 원칙 — 두괄식, 명사형, 각주·가운데점 금지, `[라벨]` 불렛, 짧은 문장.
- **정보 부족 시**: 확보 못 한 슬롯은 상상하지 않고 `"unknown"` 또는 `open_questions`로 남긴다. discovery가 스키마 검증에 실패하면 집필을 거부하고 인터뷰 보강으로 되돌린다.
- **연동 난이도 = 해결률 상한**: Task별 tier(`no_integration`/`workflow`/`system_task`)가 자동화 상한을 가른다. 배포 계획서 5장이 이를 진단한다.
- **해결률 함정**: 성과 지표는 자동해결률 단독이 아니라 재인입률, 응답시간, 인력, 상담 만족도 묶음(이스타항공 74%→50% 사례 반영).

## 4. AI를 어떻게 썼나

- **AI 담당**: 음성 인터뷰 진행(ElevenLabs + Claude), 대화에서 discovery 슬롯 채우기, **두 문서(배포 계획서, 제품 인풋)를 각 포맷 레퍼런스대로 집필**.
- **사람/코드 담당**: 자동화 범위·연동 스코핑 판단은 배포 담당자, 계약 검증(`validate_discovery.py`)은 **결정적 stdlib 코드**(LLM 비의존). 원가는 `costing-assumptions.md` 가정 × 인터뷰가 캐낸 공수로 산출. AI 저작(서사)과 결정적 계약(스키마·검증)을 분리해 재현성과 품질을 함께 확보.

## 5. 어떻게 검증했나

- **입력→결과 예시**: `samples/무브온/`(1개 회사 4개 그룹 9인 인터뷰) → `deployment-brief.md` + `product-input.md`(둘 다 새 포맷 exemplar). 단일 롤 최소 입력 예시는 `skills/intake/assets/sample-discovery.json`.
- **테스트**: `pytest`로 스키마 검증(enum·필수키·경고)과 transcript 캡처 = 총 14건 통과. 두 문서는 에이전트 집필이라 포맷 레퍼런스 준수로 품질을 관리.
- **예외 처리**: 잘못된 enum/누락 키는 검증에서 걸러 집필 거부. 미확보 슬롯은 "확인 필요"로 표기.

```bash
# discovery 검증 데모
python3 skills/intake/scripts/validate_discovery.py skills/intake/assets/sample-discovery.json
# 테스트
python3 -m pytest skills/intake/tests -q
```

---

## 빠른 시작 (음성 인터뷰)
`skills/intake/README.md` 참조. 요약: `uv pip install -r skills/intake/requirements.txt` → `.env`에 `ELEVENLABS_API_KEY` → `setup_agent.py --write-env` → `serve_browser.py`.

## 구조
- `skills/intake/` — 음성 인터뷰 → discovery.json (scout `distillery` 포크)
- `skills/brief/` — discovery.json → 두 문서 (배포 계획서, 제품 인풋 모두 에이전트가 포맷 레퍼런스대로 집필)
- 설계 정본: [`../03_solution-scope_channeltalk.md`](../03_solution-scope_channeltalk.md) · 포맷 개편: [`../04_report-format-redesign.md`](../04_report-format-redesign.md)

## 라이선스
MIT. 인터뷰 페이지는 채널톡 브랜드(Channel Blue `#6157EA`, Pretendard, Bezier 톤)를 참고했고, Meta Astryx의 CSS 토큰/모션 패턴(MIT)을 차용했다.
