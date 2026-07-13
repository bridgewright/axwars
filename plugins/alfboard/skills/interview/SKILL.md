---
name: interview
description: 채널톡 알프(AI 상담 에이전트) 도입을 앞둔 고객사의 현업(CS 리더·경영진·상담사·IT 담당)을 ElevenLabs 음성 에이전트로 "실제 사람과 대화하듯" 인터뷰해, 무엇을 어떻게 배포할지 정하는 데 필요한 정보를 막연한 형용사가 아니라 구체 일화로 끌어내고 그 대화를 turn 기반 transcript로 남긴다. 로컬에서 브라우저 음성(WebRTC 에코제거 + 끼어들기)으로 30초 내 실행. 인터뷰는 한국어. Use when 사용자가 "배포 인터뷰를 진행"하거나 "현업 음성 인터뷰", "interview 인터뷰", "알프 도입 discovery"를 요청할 때. transcript에서 deployment-discovery.json(계약)까지 도출해 report로 넘긴다.
version: 1.0.0
permissions:
  - file_read
  - file_write
  - env
  - network
---

# Interview — 도입 준비 음성 인터뷰 (①단계)

채널톡 배포 담당자가 **고객사 현업**을 ElevenLabs 음성 에이전트로 인터뷰한다. 목표는 "이 고객에 알프를 어떻게 깔지"에 필요한 사실을 실제 일화로 끌어내고 **깨끗한 transcript**를 남긴 뒤, 이를 **`deployment-discovery.json`(계약)**으로 정리해 다음 단계(report)로 넘기는 것. 인터뷰는 **한국어**, 실행은 **로컬→브라우저 음성 단일 경로**(WebRTC 에코제거 + 끼어들기).

## 즉시 실행 (목표: 30초 내 — 이 순서 그대로)
띄우기 위해 다른 파일을 읽지 마라. `launch.sh` 가 venv·에이전트·서버를 모두 처리한다(첫 실행이면 1회 설치까지).

1. **백그라운드로 실행**: `bash skills/interview/launch.sh` (run_in_background)
2. 출력의 `http://127.0.0.1:<port>/talk.html` 를 사용자에게 안내 — 브라우저가 자동으로 열린다. "🎙️ 인터뷰 시작" → 마이크 허용 → 한국어 음성 대화, 끝나면 "■ 종료".
3. 사용자가 "끝났어 / 인터뷰 끝"이라고 하면 아래 **조립**으로 넘어간다.

> 인터뷰어는 첫 질문으로 상대의 역할(CS 리더/경영진/상담사/IT)을 스스로 확인하고 해당 흐름으로 grill-me 한다. 롤을 미리 고르거나 에이전트를 수동 셋업하지 마라.

## 인터뷰 종료 후 — deployment-discovery.json 조립 (이때만 스키마를 읽는다)
1. transcript: `.venv/bin/python skills/interview/scripts/fetch_transcript.py` → `_samples/transcript.jsonl` + `interview-notes.md`.
2. `references/discovery-spec.md` 스키마대로 `output/deployment-discovery.json` 조립. 3축(A 업무·병목 / B 시스템·연동 / C 성과·임팩트)을 transcript의 **구체 일화**로 채우고, 미확보 슬롯은 상상 금지 → `"unknown"`/`open_questions`.
3. 게이트: `.venv/bin/python skills/interview/scripts/validate_discovery.py output/deployment-discovery.json` (ERROR면 인터뷰로 되돌아가 보강).
4. 연동 tier·자동화 우선순위·제품 갭을 요약 보고 → **report로 넘긴다**. 가상 예시: `assets/sample-discovery.json`.

## 셋업 (수동으로 할 필요 없음 — launch.sh 가 자동 처리)
최초 1회, 또는 프롬프트를 고쳤을 때만:
- 설치+에이전트 생성: `bash skills/interview/setup.sh` (venv + deps + 에이전트 생성 → `.env`에 `AGENT_ID` 기록).
- `.env`: `cp skills/interview/.env.example skills/interview/.env` 후 `ELEVENLABS_API_KEY` 입력(대시보드 → Agents).
- 프롬프트 수정 후 에이전트 갱신: `.venv/bin/python skills/interview/scripts/setup_agent.py --agent-id <id>` (HJ 여성 보이스·speed 1.1 기본 적용).

## 가드레일
- **음성 자연스러움 우선** — 한 번에 한 질문, 모호한 형용사엔 구체 장면을 되묻는다(프롬프트가 강제).
- **grill-me** — 페인포인트를 대놓고 묻지 않고 일화 → 빈도 → 왜 안 고쳐졌나 → 원하는 것 순으로.
- **증거 없이 채우지 않음** — 미확보 슬롯은 `open_questions`/`unknown`.
- **PII 보호** — 실제 transcript·API키는 `_samples/`·`output/`·`.env`(gitignore). 커밋 예시는 가상.
- **프롬프트 = SSOT** — 인터뷰어 행동은 `prompt/interviewer-system-prompt.md` 한 곳에서. 플레이스홀더 없이 롤을 스스로 확인한다.

## 파일
- `launch.sh` — 즉시 실행(venv 보장 → 에이전트 확인 → 브라우저 서버 + URL).
- `setup.sh` — 최초 1회 설치(venv + deps + 에이전트 생성).
- `prompt/interviewer-system-prompt.md` — 인터뷰어 페르소나(SSOT, 4롤 자기라우팅, grill-me).
- `references/discovery-spec.md` — `deployment-discovery.json` 스키마(계약 정본).
- `references/handoff-contract.md` — 다운스트림(report) 소비 계약.
- `scripts/setup_agent.py` — ElevenLabs 에이전트 생성/갱신(HJ 보이스·speed 1.1 기본).
- `scripts/serve_browser.py` — signed URL + 채널톡 인터뷰 페이지(WebRTC AEC).
- `scripts/fetch_transcript.py` — 브라우저 인터뷰 후 transcript 저장.
- `scripts/validate_discovery.py` — discovery.json 게이트.
- `assets/talk_template.html` — 채널톡 룩 UI. `assets/channel-logo.webp` — 로고.
- `assets/sample-discovery.json` — 가상 예시(데모).
- `tests/test_discovery.py` — validate 단위테스트.
