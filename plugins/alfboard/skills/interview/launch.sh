#!/usr/bin/env bash
# alfboard interview — 로컬 브라우저 음성 인터뷰 즉시 실행 (목표: 30초 내).
# venv 보장 → 에이전트(AGENT_ID) 확인 → serve_browser 기동(브라우저 자동 오픈 + URL 출력).
# 셋업 로그는 stderr, 최종 URL 은 stdout 으로 나간다.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ_ROOT="$(cd "$SKILL_DIR/../../.." && pwd)"   # 04-ax-wars-channeltalk
VENV="$PROJ_ROOT/.venv"
PY="$VENV/bin/python"

# 1) venv 보장 (없으면 최초 1회 생성·설치)
if [ ! -x "$PY" ]; then
  echo "[launch] .venv 없음 → 생성·설치 (최초 1회)" >&2
  ( cd "$PROJ_ROOT" && uv venv --python 3.12 .venv && uv pip install -r "$SKILL_DIR/requirements.txt" ) >&2
fi

# 2) .env / AGENT_ID 확인
if [ ! -f "$SKILL_DIR/.env" ]; then
  echo "[launch] ERROR: $SKILL_DIR/.env 없음. 'cp skills/interview/.env.example skills/interview/.env' 후 ELEVENLABS_API_KEY 입력." >&2
  exit 2
fi
if ! grep -qE '^AGENT_ID=.+' "$SKILL_DIR/.env"; then
  echo "[launch] AGENT_ID 없음 → 인터뷰어 에이전트 1회 생성" >&2
  "$PY" "$SKILL_DIR/scripts/setup_agent.py" --write-env >&2
fi

# 3) 브라우저 음성 인터뷰 서버 (자동 오픈 + URL stdout, 포그라운드 유지 → 백그라운드로 호출)
echo "[launch] 인터뷰 서버 기동 — 잠시 후 브라우저가 열립니다." >&2
exec "$PY" "$SKILL_DIR/scripts/serve_browser.py" "$@"
