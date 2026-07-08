# 05 — interview 스킬 즉시 실행(30초 내) 리팩터 플랜

**목표**: 새 세션에서 `/alfboard:interview` 한 번 → **30초 내 브라우저 음성 인터뷰 라이브**. 파일 뜯어보기, 롤 질문(AskUserQuestion), 에이전트 PATCH, CLI 선택지 전부 제거. 실행 경로는 **로컬→브라우저(WebRTC) 단일**.

**근거 로그**: `logs/exports/session-7e2e3090-2026-07-08.md` (새 세션이 `/alfboard:interview` 첫 실행). 브라우저를 띄우기까지 **파일 7개 Read + bash 10회+ + AskUserQuestion 1회 + 에이전트 PATCH 3회** = 약 27개 도구 액션 소요.

---

## 1. 단계별 시간 소모 분석 (로그 액션 → 원인)

**Phase 1 — 위치 파악·이해 (액션 1~10, 도구 ~10회)**
커맨드가 실행 절차를 담지 않고 SKILL.md를 가리키기만 함 → SKILL.md를 Read → SKILL.md가 서술형이고 **두 경로(browser/CLI)+셋업+스키마**가 섞임 → `discovery-spec.md`, `interviewer-system-prompt.md`, `serve_browser.py`, `setup_agent.py`까지 연쇄 Read. 이 읽기의 대부분은 **"롤이 에이전트에 어떻게 들어가는가"**를 이해하려던 것.

**Phase 2 — 환경 프로비전 (액션 11~12)**
`.venv` 없음 → `uv venv` + `uv pip install` 라이브 실행. `requirements.txt`에 무거운 **CLI 전용 deps(`elevenlabs`, `sounddevice`)** 포함 → 설치가 김.

**Phase 3 — 에이전트 수선 (액션 13~17 + AskUserQuestion)**
라이브 에이전트에 **치환 안 된 `{{role_label}}`/`{{role}}`/`{{opener}}`** 발견(그대로면 "{{opener}}"를 소리내어 읽음) → 롤·경로 AskUserQuestion(사람 대기로 정지) → 플레이스홀더 임시 치환(즉석 bash) → 라이브 에이전트 PATCH → 검증.

**Phase 4 — 실제 실행 (액션 18~19)**
`serve_browser.py` 백그라운드 기동 + URL 확보. **유일하게 반드시 필요한 부분이며, 빠름.**

정리: 27개 액션 중 실제 "실행"에 필요한 건 ~2개(서버 기동+URL). 나머지 전부 오버헤드.

---

## 2. 근본 원인 (임팩트순)

- **RC1 — {{role}}/{{opener}} 플레이스홀더 설계.** 에이전트가 바로 쓸 수 있는 상태가 아님. 매 실행마다 롤 선택 → 치환 → 라이브 PATCH → 검증 필요. `setup_agent.py`는 프롬프트를 **그대로 게시**하고 치환하지 않음 → 라이브에 `{{ }}`가 박힘. **읽기·API 왕복·AskUserQuestion의 최대 발생원.**
- **RC2 — 환경 미프로비전 + 무거운 의존성.** `.venv`가 첫 실행의 임계경로에 있음. `requirements.txt`가 CLI 전용 `elevenlabs`·`sounddevice`까지 설치. (브라우저 경로는 `httpx`+`python-dotenv`만 씀.)
- **RC3 — 커맨드가 런북이 아니라 포인터.** `commands/interview.md`가 "SKILL.md를 따르라"고만 함.
- **RC4 — SKILL.md가 실행·스키마·가드 혼재.** 실행에 필요한 최소 절차가 스키마·가드레일과 섞여 한눈에 안 들어옴.
- **RC5 — 두 경로 + 롤 질문.** browser/CLI 분기와 롤 선택이 결정 지점을 만들어 대화형 정지 유발. (CLI는 WebRTC 미지원이라 실제로 대화도 안 됨 → 존재 이유 없음.)

---

## 3. 타깃 설계

### 3.1 프롬프트를 롤-불문 자기라우팅으로 (RC1 해소, 핵심)
`prompt/interviewer-system-prompt.md`에서 **모든 플레이스홀더 제거**하고, 인터뷰어가 **첫 턴에 역할을 스스로 확인**하게 바꾼다.
- 49행 `이번 인터뷰 대상은 **{{role_label}}**({{role}}) ... '{{role}}' 흐름으로` → `대화 첫머리에 상대의 역할(CS/CX 리더 · 경영진 · 현장 상담사 · IT 담당)을 자연스럽게 확인하고, 아래 해당 흐름으로 진행하세요. 여러 역할이 섞이면 자연스럽게 오갑니다.`
- 100행 FIRST MESSAGE `... {{opener}}` → 구체 오프너로 교체(역할도 함께 확인): 예) `먼저, 오늘 말씀 나눠 주실 분이 팀에서 어떤 역할을 맡고 계신지 여쭤봐도 될까요? 편하게 말씀해 주시면 거기에 맞춰 여쭙겠습니다.`
- 4개 롤 흐름(cs_lead/exec/agent/it)은 **인터뷰어의 내부 라우팅 가이드로 그대로 유지** → 인터뷰 품질·grill-me 손실 없음.
- 효과: `setup_agent.py`가 파일을 그대로 게시해도 라이브 에이전트가 **즉시 사용 가능**. 이후 **치환·PATCH 영구 불필요.**

### 3.2 단일 엔트리포인트 `launch.sh` (RC3/RC4 해소)
`skills/interview/launch.sh` 하나가 순서대로:
1. `.venv` 보장 — 없으면 `uv venv` + `uv pip install -r requirements.txt`, 있으면 no-op(빠른 통과).
2. `.env`의 `AGENT_ID` 확인 — 있으면 그대로 사용(핫패스, 에이전트 안 건드림). 없으면 `setup_agent.py`로 1회 생성.
3. `uv run python scripts/serve_browser.py` 백그라운드 기동 → **URL 한 줄 출력** → 브라우저 자동 오픈.

→ 에이전트가 필요로 하는 도구 액션: **launch.sh 실행 1회 + URL 확인.** 파일 Read 0, AskUserQuestion 0, PATCH 0.

### 3.3 환경 슬림 + 선프로비전 (RC2 해소)
- `requirements.txt`를 브라우저 경로 최소셋으로: **`httpx` + `python-dotenv` + `socksio`**. `elevenlabs`·`sounddevice` **삭제**. (주의: `httpx`는 현재 `elevenlabs`에 딸려오는 전이 의존성 → **명시적으로 추가** 필수. 버전 핀 유지.)
- `setup.sh`(설치 시 1회): venv+deps 설치 + 에이전트 생성(3.1의 플레이스홀더 없는 프롬프트, HJ 보이스 + speed 1.1) + `AGENT_ID` 기록. 이후 실행은 이 결과를 재사용.

### 3.4 CLI 완전 제거 (RC5 해소)
- 삭제: `scripts/run_interview.py`, `scripts/sd_audio.py`.
- 참조 제거: `SKILL.md`, `commands/interview.md`, `requirements.txt` 주석, `tests/test_transcript.py`(CLI/`distillery` 참조).
- SKILL.md의 "두 가지 실행 경로" 섹션 → **브라우저 단일 경로**로 축소.

### 3.5 커맨드를 런북으로 (RC3 해소)
`commands/interview.md` 본문을 결정론적 절차로:
```
1) 실행: bash skills/interview/launch.sh
2) URL이 출력되면 사용자에게 "🎙️ 인터뷰 시작" 클릭을 안내한다. (실행을 위해 다른 파일을 읽지 마라.)
3) 사용자가 "끝났어"라고 하면 그때 fetch_transcript.py로 transcript 확보 →
   references/discovery-spec.md 스키마대로 deployment-discovery.json 조립 → validate_discovery.py 게이트.
```

### 3.6 브랜딩 잔재 정리 (`distillery` → interview/alfboard)
잔재 위치: `requirements.txt`, `scripts/setup_agent.py`(에이전트 name 기본값 `distillery-interviewer` 포함), `scripts/serve_browser.py`, `scripts/fetch_transcript.py`, `scripts/run_interview.py`(삭제됨), `tests/test_transcript.py`. (`assets/talk_template.html` 타이틀은 이미 "채널톡 · 도입 인터뷰"로 정상.)

---

## 4. 파일별 변경 요약 (Codex 구현용)

| 파일 | 변경 |
|---|---|
| `prompt/interviewer-system-prompt.md` | 49행 롤-불문 자기라우팅, 100행 구체 오프너, `{{ }}` 3종 제거 |
| `skills/interview/launch.sh` | **신규** — venv 보장 → AGENT_ID 확인 → serve_browser 백그라운드 + URL |
| `skills/interview/setup.sh` | **신규** — 1회 설치(venv+deps+에이전트 생성, HJ 보이스+speed 1.1) |
| `requirements.txt` | `httpx`+`python-dotenv`+`socksio`만; `elevenlabs`·`sounddevice` 삭제; distillery 문구 정리 |
| `scripts/run_interview.py`, `scripts/sd_audio.py` | **삭제** |
| `scripts/setup_agent.py` | 기본값에 HJ 보이스·speed 1.1 반영(재실행 일관성), name `alfboard-interviewer`, distillery 문구 |
| `scripts/serve_browser.py` | distillery 문구 정리(동작 변경 없음) |
| `scripts/fetch_transcript.py` | distillery 문구 정리 |
| `commands/interview.md` | 런북화(3.5) |
| `SKILL.md` | 실행 절차를 최상단 단일 브라우저 경로로, 스키마·조립은 "인터뷰 종료 후" 섹션으로 분리 |
| `tests/test_transcript.py` | CLI/distillery 참조 제거, 통과 유지 |

---

## 5. 완료 기준 (Acceptance)

- 새 세션 `/alfboard:interview` → **30초 내 브라우저 오픈**. 실행 단계 도구 액션 ≤ 3, AskUserQuestion 0, 에이전트 PATCH 0, 파일 Read 0.
- 라이브 에이전트에 `{{ }}` 플레이스홀더 0 (검증: `setup_agent.py --dry-run` 출력에 `{{` 없음).
- `requirements.txt`에 `sounddevice`/`elevenlabs` 없음, `httpx` 있음. `uv pip install` 체감 단축.
- `run_interview.py`/`sd_audio.py` 부재. `pytest alfboard/skills` 통과.
- 인터뷰 종료 후에만 discovery 조립 단계 진입(스키마 읽기가 실행을 막지 않음).

## 6. 타이밍 예산 (선프로비전 후 핫패스)

venv 확인(≈0s, 이미 존재) + signed URL 발급(1~3s) + 로컬 서버(≈0.5s) + 브라우저 오픈 ≈ **3~8초.** 30초 목표 대비 충분한 여유.

## 7. 구현 순서 (Codex)

1. 프롬프트 롤-불문화(플레이스홀더 제거 + 오프너).
2. `requirements.txt` 슬림 + `httpx` 명시 추가.
3. CLI 삭제 + 전 참조 정리.
4. `setup.sh` + `launch.sh` 작성.
5. `commands/interview.md` 런북화 + `SKILL.md` 재구성.
6. distillery 브랜딩 정리 + `setup_agent.py` 기본값(보이스/speed).
7. `setup.sh` 1회 실행 → 플레이스홀더 없는 프롬프트로 에이전트 재생성 + `AGENT_ID` 기록. 검증: 깨끗한 리허설로 30초 계측, `pytest` 통과.

> 보안: `.env`(실제 키/AGENT_ID)는 커밋 금지 유지. 에이전트 재생성 시 HJ 보이스(`eI3jlA17XYDwAIY4lo0y`) + speed 1.1 보존.
