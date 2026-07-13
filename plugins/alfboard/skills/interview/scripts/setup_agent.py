#!/usr/bin/env python3
"""alfboard interview (voice) — ElevenLabs 인터뷰어 에이전트 생성/갱신.

prompt/interviewer-system-prompt.md (SSOT)를 읽어 ElevenLabs Agents Platform 에이전트의
system prompt / first message / 언어 / LLM 로 등록한다. 프롬프트를 고치면 --agent-id 로 갱신.

  생성:   uv run python scripts/setup_agent.py --write-env
  갱신:   uv run python scripts/setup_agent.py --agent-id <id>
  미리보기: uv run python scripts/setup_agent.py --dry-run   (호출 없이 요청 바디만 출력)

REST: POST /v1/convai/agents/create , PATCH /v1/convai/agents/{agent_id}
httpx 는 실제 호출 경로에서만 import 한다 → --dry-run 은 의존성 없이 동작.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

API_BASE = "https://api.elevenlabs.io"
FIRST_MSG_MARKER = "=== FIRST MESSAGE ==="


def _load_env(skill_dir: Path) -> None:
    env_path = skill_dir / ".env"
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except Exception:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def split_prompt(text: str):
    """프롬프트 파일을 (system_prompt, first_message) 로 분리(구분자 마지막 출현 기준)."""
    body = text.strip()
    if FIRST_MSG_MARKER in body:
        sys_p, first = body.rsplit(FIRST_MSG_MARKER, 1)
        return sys_p.strip(), first.strip()
    return body, ""


def build_conversation_config(system_prompt, first_message, *, llm, temperature,
                              language, voice_id, tts_model, turn_timeout=None, speed=None):
    agent = {
        "language": language,
        "prompt": {"prompt": system_prompt, "llm": llm, "temperature": temperature},
    }
    if first_message:
        agent["first_message"] = first_message
    # 비영어(예: ko) 에이전트는 TTS 모델이 turbo/flash v2_5 여야 함 → 항상 model_id 지정.
    tts = {"model_id": tts_model}
    if voice_id:
        tts["voice_id"] = voice_id
    # 말하기 속도(0.7~1.2, 1.0 기본). 클수록 빠름.
    if speed is not None:
        tts["speed"] = speed
    cfg = {"agent": agent, "tts": tts}
    # 사용자 침묵 후 에이전트가 응답하기까지 대기(초). 낮을수록 응답이 빠름.
    if turn_timeout is not None:
        cfg["turn"] = {"turn_timeout": turn_timeout}
    return cfg


def _verify():
    """Zscaler 등 사내 프록시 TLS 재서명 대응: CA 번들이 있으면 사용."""
    for env in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        v = os.environ.get(env)
        if v and Path(v).exists():
            return v
    z = Path.home() / ".config/certs/zscaler-root-ca.pem"
    return str(z) if z.exists() else True


def create_agent(api_key, name, conversation_config):
    import httpx
    body = {"name": name, "conversation_config": conversation_config}
    with httpx.Client(timeout=60.0, verify=_verify()) as c:
        r = c.post(f"{API_BASE}/v1/convai/agents/create",
                   headers={"xi-api-key": api_key, "Content-Type": "application/json"},
                   json=body)
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code}: {r.text}")
    return r.json()


def update_agent(api_key, agent_id, conversation_config):
    import httpx
    with httpx.Client(timeout=60.0, verify=_verify()) as c:
        r = c.patch(f"{API_BASE}/v1/convai/agents/{agent_id}",
                    headers={"xi-api-key": api_key, "Content-Type": "application/json"},
                    json={"conversation_config": conversation_config})
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code}: {r.text}")
    return r.json()


def write_env_agent_id(skill_dir: Path, agent_id: str) -> None:
    env_path = skill_dir / ".env"
    out, found = [], False
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("AGENT_ID="):
                out.append(f"AGENT_ID={agent_id}")
                found = True
            else:
                out.append(line)
    if not found:
        out.append(f"AGENT_ID={agent_id}")
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    skill_dir = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="alfboard interview 인터뷰어 에이전트 생성/갱신")
    p.add_argument("--prompt-file", default=str(skill_dir / "prompt/interviewer-system-prompt.md"))
    p.add_argument("--name", default="alfboard-interviewer")
    p.add_argument("--agent-id", default=None, help="주면 생성 대신 갱신")
    p.add_argument("--llm", default="claude-sonnet-4-6",
                   help="에이전트 LLM (예: claude-sonnet-4-6, claude-opus-4-7, gpt-4o)")
    p.add_argument("--temperature", type=float, default=0.4)
    p.add_argument("--language", default="ko")
    p.add_argument("--voice-id", default="eI3jlA17XYDwAIY4lo0y",
                   help="한국어 보이스 ID (기본: HJ 여성 eI3jlA17XYDwAIY4lo0y)")
    p.add_argument("--tts-model", default="eleven_turbo_v2_5")
    p.add_argument("--speed", type=float, default=1.1,
                   help="말하기 속도(0.7~1.2, 1.0 기본, 클수록 빠름. 기본 1.1)")
    p.add_argument("--turn-timeout", type=float, default=None,
                   help="사용자 침묵 후 에이전트 응답까지 대기(초). 낮을수록 빠름(예: 2)")
    p.add_argument("--write-env", action="store_true", help="결과 agent_id 를 .env 에 기록")
    p.add_argument("--dry-run", action="store_true", help="호출 없이 요청 바디만 출력")
    args = p.parse_args(argv)

    _load_env(skill_dir)
    system_prompt, first_message = split_prompt(Path(args.prompt_file).read_text(encoding="utf-8"))
    if not system_prompt:
        print("ERROR: 프롬프트가 비어 있습니다.", file=sys.stderr)
        return 2
    cfg = build_conversation_config(
        system_prompt, first_message,
        llm=args.llm, temperature=args.temperature, language=args.language,
        voice_id=args.voice_id, tts_model=args.tts_model, turn_timeout=args.turn_timeout,
        speed=args.speed,
    )

    if args.dry_run:
        print(json.dumps({"name": args.name, "conversation_config": cfg}, ensure_ascii=False, indent=2))
        return 0

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("ERROR: ELEVENLABS_API_KEY 없음. skills/interview/.env 를 채우세요.", file=sys.stderr)
        return 2

    try:
        if args.agent_id:
            update_agent(api_key, args.agent_id, cfg)
            agent_id = args.agent_id
            print(f"갱신됨: agent_id={agent_id}")
        else:
            resp = create_agent(api_key, args.name, cfg)
            agent_id = resp.get("agent_id") or resp.get("agentId")
            print(f"생성됨: agent_id={agent_id}")
    except ModuleNotFoundError as e:
        print(f"ERROR: 의존성 누락({e.name}). uv pip install -r requirements.txt", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"ERROR: API 호출 실패: {e}", file=sys.stderr)
        return 4

    if args.write_env and agent_id:
        write_env_agent_id(skill_dir, agent_id)
        print("→ .env 에 AGENT_ID 기록함")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
