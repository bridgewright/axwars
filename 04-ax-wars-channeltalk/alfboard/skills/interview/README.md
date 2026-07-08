# 🎙️ Interview — 도입 준비 음성 인터뷰

> 말로 캐내는 배포 준비.

채널톡 알프 도입을 앞둔 **고객사 현업**을 실제 사람과 대화하듯 음성으로 인터뷰해, "이 고객에 알프를 어떻게 깔지"에 필요한 정보를 막연한 형용사가 아니라 **구체적인 일화**로 끌어내는 스킬. ElevenLabs Agents Platform + Claude로 동작하며 인터뷰는 **한국어**, 실행은 **로컬→브라우저 음성 단일 경로**.

배포 파이프라인 ①단계 — 대화에서 **`deployment-discovery.json`(계약)**을 도출해 ②단계(report)로 넘긴다.

## 최종 산출물
- **transcript** (`_samples/transcript.jsonl` / `interview-notes.md`) — 음성 대화 turn 기록.
- **`deployment-discovery.json`** — 배포 결정 슬롯(맥락·병목·자동화 범위·연동·지식·조직·성과·제품 갭·미해결). 스키마: `references/discovery-spec.md`.

## 왜 음성인가 + grill-me
사람은 말할 때 더 구체적인 일화를 꺼낸다. 인터뷰어는 "가장 큰 문제가 뭐예요?"를 **묻지 않고**, "어제 제일 손이 많이 간 문의가 뭐였어요?"처럼 장면부터 꺼내게 한 뒤 일화 → 빈도 → 왜 안 고쳐졌나 → 원하는 것 순으로 파고든다. 인터뷰어는 첫 질문으로 상대의 **역할**(CS 리더/경영진/상담사/IT)을 스스로 확인하고 해당 흐름으로 진행한다.

## 빠른 시작
```bash
# 0) 최초 1회 — .env 준비 (ElevenLabs 대시보드 → Agents 에서 API 키)
cp skills/interview/.env.example skills/interview/.env   # ELEVENLABS_API_KEY 입력

# 1) 최초 1회 — 설치 + 인터뷰어 에이전트 생성 (venv + deps + AGENT_ID 기록)
bash skills/interview/setup.sh

# 2) 인터뷰 실행 — 로컬에서 브라우저 음성 (자동 오픈 + URL 출력)
bash skills/interview/launch.sh
```
> `launch.sh` 는 venv·에이전트·서버를 알아서 처리한다. `.env` 만 있으면 첫 실행에서 설치까지 한 번에 한다. `.env`·`_samples/`·`output/`(실제 대화록)은 gitignore.

## 다음 단계
transcript → `output/deployment-discovery.json` 조립 → `validate_discovery.py` 게이트 → **report**가 두 문서(배포 계획서, 제품 인풋)를 에이전트가 각 포맷 레퍼런스대로 집필.

## 구성
| 파일 | 역할 |
|---|---|
| `launch.sh` | 즉시 실행(venv 보장 → 에이전트 확인 → 브라우저 서버 + URL) |
| `setup.sh` | 최초 1회 설치(venv + deps + 에이전트 생성) |
| `prompt/interviewer-system-prompt.md` | 인터뷰어 페르소나(SSOT, 4롤 자기라우팅, grill-me) |
| `references/discovery-spec.md` | discovery.json 스키마(계약 정본) |
| `scripts/setup_agent.py` | ElevenLabs 에이전트 생성/갱신(HJ 보이스·speed 1.1 기본) |
| `scripts/serve_browser.py` | signed URL + 채널톡 인터뷰 페이지(WebRTC AEC) |
| `scripts/fetch_transcript.py` | 브라우저 인터뷰 transcript 저장 |
| `scripts/validate_discovery.py` | discovery.json 게이트 |
| `assets/talk_template.html` | 채널톡 룩 UI · `assets/channel-logo.webp` |
| `assets/sample-discovery.json` | 가상 데모 입력 |
| `tests/test_discovery.py` | validate 단위테스트 |

## 주의
실제 인터뷰 transcript는 PII를 포함할 수 있으니 `_samples/`·`output/`(gitignore) 밖으로 내보내지 말 것. 커밋되는 예시는 모두 가상이다.
