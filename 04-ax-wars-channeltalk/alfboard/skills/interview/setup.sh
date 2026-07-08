#!/usr/bin/env bash
# alfboard interview — 최초 1회 설치: venv + deps + 인터뷰어 에이전트 생성.
# 프롬프트를 고친 뒤 에이전트를 새로 만들고 싶을 때도 사용(새 AGENT_ID 를 .env 에 기록).
# 기존 에이전트를 그대로 두고 프롬프트만 갱신하려면:
#   .venv/bin/python skills/interview/scripts/setup_agent.py --agent-id <id>
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ_ROOT="$(cd "$SKILL_DIR/../../.." && pwd)"
VENV="$PROJ_ROOT/.venv"
PY="$VENV/bin/python"

cd "$PROJ_ROOT"
uv venv --python 3.12 .venv
uv pip install -r "$SKILL_DIR/requirements.txt"

if [ ! -f "$SKILL_DIR/.env" ]; then
  echo "먼저 $SKILL_DIR/.env 를 만들고 ELEVENLABS_API_KEY 를 넣으세요 (cp .env.example .env)." >&2
  exit 2
fi

# 에이전트 생성 → .env 에 AGENT_ID 기록 (HJ 여성 보이스 · speed 1.1 기본)
"$PY" "$SKILL_DIR/scripts/setup_agent.py" --write-env
echo "설치 완료. 이제 'bash skills/interview/launch.sh' 로 인터뷰를 띄우세요."
