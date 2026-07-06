---
name: intake
description: 채널톡 알프(AI 상담 에이전트) 도입을 앞둔 고객사의 현업(CS 리더·경영진·상담사·IT 담당)을 ElevenLabs 음성 에이전트로 "실제 사람과 대화하듯" 인터뷰해, 무엇을 어떻게 배포할지 정하는 데 필요한 정보를 막연한 형용사가 아니라 구체 일화로 끌어내고 그 대화를 turn 기반 transcript로 남긴다. 브라우저(WebRTC 에코제거 + 끼어들기 OK)와 로컬 CLI 두 경로. 인터뷰는 한국어. Use when 사용자가 "배포 인터뷰를 진행"하거나 "현업 음성 인터뷰", "intake 인터뷰", "알프 도입 discovery"를 요청할 때. transcript에서 deployment-discovery.json(계약)까지 도출해 handoff로 넘긴다.
version: 1.0.0
permissions:
  - file_read
  - file_write
  - env
  - network
---

# Intake — 배포 discovery 음성 인터뷰 (①단계)

채널톡 배포 담당자가 **고객사 현업**을 ElevenLabs 음성 에이전트로 인터뷰한다. 목표는 "이 고객에 알프를 어떻게 깔지"에 필요한 사실을 실제 일화로 끌어내고 **깨끗한 transcript**를 남긴 뒤, 이를 **`deployment-discovery.json`(계약)**으로 정리해 다음 단계(handoff)에 넘기는 것. 인터뷰는 **한국어**, UI는 채널톡 룩.

> **범위(end-to-end)**: 음성 인터뷰 → transcript → `deployment-discovery.json`. 다운스트림 계약: `references/handoff-contract.md`, 스키마: `references/discovery-spec.md`.

## 두 가지 실행 경로
- **브라우저 (권장·데모)** — `scripts/serve_browser.py`. signed URL을 발급해 로컬 페이지(`assets/talk_template.html`, 채널톡 스타일)를 띄운다. WebRTC 에코 제거 → 스피커 환경 + 끼어들기 동작.
- **로컬 CLI** — `scripts/run_interview.py`. 마이크 루프 + transcript 저장. `--text-only`로 오디오 없이 캡처 점검.

## 워크플로우

### Step 0 — 셋업 (최초 1회)
1. `uv venv --python 3.12 .venv` → `uv pip install -r skills/intake/requirements.txt`.
2. `skills/intake/.env`에 `ELEVENLABS_API_KEY`(대시보드 → Agents). `cp skills/intake/.env.example skills/intake/.env`.
3. 마이크 권한.

### Step 1 — 인터뷰어 에이전트 생성/갱신
`prompt/interviewer-system-prompt.md`(SSOT, grill-me + 4롤 스크립트)를 에이전트로 등록:
```bash
uv run python skills/intake/scripts/setup_agent.py --write-env      # 생성 → AGENT_ID 기록
uv run python skills/intake/scripts/setup_agent.py --agent-id <id>  # 프롬프트 수정 후 갱신
```

### Step 2 — 인터뷰 진행
- **인터뷰 대상 롤을 먼저 정한다**: `cs_lead`(CX/CS 리더·주 대상) / `exec`(경영진) / `agent`(현장 상담사) / `it`(IT 담당). 프롬프트가 첫 메시지에서 롤·회사 규모를 확인하고 해당 롤 흐름으로 진행.
- 브라우저: `uv run python skills/intake/scripts/serve_browser.py` → **Start** → 마이크 허용 → 대화. 답을 마치면 Enter/Space로 턴 종료.
- CLI: `uv run python skills/intake/scripts/run_interview.py`.
- `.env`·마이크·네트워크 때문에 **sandbox-off** 또는 사용자가 직접 실행.

### Step 3 — transcript 확보
- 브라우저: `python3 scripts/fetch_transcript.py --out output` → `output/transcript.jsonl` + `interview-notes.md`.
- CLI: 자동 저장.

### Step 4 — deployment-discovery.json 조립 (transcript → 계약)
인터뷰가 끝나면 transcript를 읽어 `references/discovery-spec.md` 스키마대로 **`output/deployment-discovery.json`**을 조립한다:
1. 3축(A 업무·병목 / B 시스템·연동 / C 성과·임팩트)의 슬롯을 transcript의 **구체 일화**에서 채운다. 확보 못 한 슬롯은 상상 금지 → `"unknown"` 또는 `open_questions`.
2. 게이트: `python3 scripts/validate_discovery.py output/deployment-discovery.json` (ERROR면 인터뷰로 되돌아가 보강).
3. 사용자에게 핵심(연동 tier, 자동화 우선순위, 제품 갭 태그)을 한눈에 보고하고 **handoff로 넘긴다**.

가상 예시: `assets/sample-discovery.json`.

## 가드레일
- **음성 자연스러움 우선** — 한 번에 한 질문, 모호한 형용사엔 구체 장면을 되묻는다(프롬프트가 강제).
- **grill-me** — 페인포인트를 대놓고 묻지 않고 일화 → 빈도 → 왜 안 고쳐졌나 → 원하는 것 순으로.
- **증거 없이 채우지 않음** — 미확보 슬롯은 `open_questions`/`unknown`.
- **PII 보호** — 실제 transcript·API키는 `output/`·`.env`(gitignore). 커밋 예시는 가상.
- **프롬프트 = SSOT** — 인터뷰어 행동은 `prompt/interviewer-system-prompt.md` 한 곳에서.

## 파일
- `prompt/interviewer-system-prompt.md` — 인터뷰어 페르소나(SSOT, 4롤, grill-me).
- `references/discovery-spec.md` — `deployment-discovery.json` 스키마(계약 정본).
- `references/handoff-contract.md` — 다운스트림(handoff) 소비 계약.
- `scripts/setup_agent.py` — ElevenLabs 에이전트 생성/갱신.
- `scripts/serve_browser.py` — signed URL + 로컬 채널톡 인터뷰 페이지(WebRTC AEC).
- `scripts/run_interview.py` — 로컬 마이크 음성 루프.
- `scripts/fetch_transcript.py` — 브라우저 인터뷰 후 transcript 저장.
- `scripts/sd_audio.py` — sounddevice 오디오 인터페이스.
- `scripts/validate_discovery.py` — discovery.json 게이트.
- `assets/talk_template.html` — 채널톡 룩 인터뷰 UI. `assets/channel-logo.webp` — 로고.
- `assets/sample-discovery.json` — 가상 예시(데모).
- `tests/test_discovery.py` — validate 단위테스트. `tests/test_transcript.py` — transcript 캡처.
