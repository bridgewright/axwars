---
description: 고객 현업을 음성으로 인터뷰해 deployment-discovery.json을 만든다 (alfboard 도입 준비 ①단계, 브라우저 음성)
allowed-tools: [Bash, Read, Write]
---

# 목표: 30초 내에 브라우저 음성 인터뷰를 띄운다. 띄우기 위해 다른 파일을 읽지 마라.

## 실행 (이 순서 그대로)
1. **백그라운드로 실행**: `bash skills/interview/launch.sh` (run_in_background 로 띄운다)
2. 출력에서 `http://127.0.0.1:<port>/talk.html` URL을 읽어, 사용자에게 안내한다:
   - 브라우저가 자동으로 열린다. 안 열리면 그 URL을 직접 연다.
   - "🎙️ 인터뷰 시작" 클릭 → 마이크 허용 → 인터뷰어(한국어 음성)와 대화. 끝나면 "■ 종료".
   - 인터뷰어가 첫 질문으로 역할(CS 리더/경영진/상담사/IT)을 물으니 편하게 답하면 된다.
3. 사용자가 "끝났어 / 인터뷰 끝"이라고 하면 **그때** 아래 조립 단계로 넘어간다.

launch.sh 가 venv · 에이전트 · 서버를 모두 처리한다. 셋업을 수동으로 하지 마라. 첫 실행이면 launch.sh 가 1회 설치까지 알아서 한다.

## 인터뷰 종료 후 — discovery 조립 (이때만 스키마를 읽는다)
1. transcript 확보: `.venv/bin/python skills/interview/scripts/fetch_transcript.py`
2. `skills/interview/references/discovery-spec.md` 스키마대로 `skills/interview/output/deployment-discovery.json` 조립. 미확보 슬롯은 상상 금지 → `open_questions`/`unknown`.
3. 게이트: `.venv/bin/python skills/interview/scripts/validate_discovery.py skills/interview/output/deployment-discovery.json`
4. 연동 tier · 자동화 우선순위 · 제품 갭을 요약 보고 → report 단계로 넘긴다.
