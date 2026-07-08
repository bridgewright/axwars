#!/usr/bin/env python3
"""distillery (voice) — 로컬 음성 인터뷰 러너.

ElevenLabs Agents Platform 에이전트와 마이크로 실시간 음성 인터뷰를 진행하고,
주고받은 발화를 turn 기반 transcript 로 저장한다.

  라이브:    uv run python scripts/run_interview.py
  드라이런:  uv run python scripts/run_interview.py --text-only   (오디오/네트워크 없이 캡처·렌더 점검)

채점/criteria 산출은 이 스크립트의 책임이 아니다(v1 범위 밖). 여기선 '대화 + transcript'만.
elevenlabs/pyaudio 는 run_live() 안에서만 import 한다 → 의존성 없이도 --text-only·테스트 가능.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

_ISO = "%Y-%m-%dT%H:%M:%SZ"


def _now() -> str:
    return datetime.now(timezone.utc).strftime(_ISO)


class TranscriptRecorder:
    """순수 파이썬 transcript 기록기. SDK·오디오와 분리 → 오디오 없이 단위테스트 가능.

    - transcript.jsonl : 한 줄에 한 턴(append, 크래시에도 부분 보존)
    - interview-notes.md : 사람이 읽는 렌더(매 턴 재작성)
    """

    AGENT, USER, CORRECTION = "agent", "user", "correction"

    def __init__(self, out_dir, *, title: str = "distillery 음성 인터뷰", clock=_now):
        self.out_dir = Path(out_dir)
        self.title = title
        self._clock = clock
        self.turns: list[dict] = []
        self.conversation_id = None
        self._lock = threading.Lock()
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = self.out_dir / "transcript.jsonl"
        self.notes_path = self.out_dir / "interview-notes.md"

    # --- recording API (콜백이 호출) ---
    def record_agent(self, text: str) -> None:
        self._add({"ts": self._clock(), "role": self.AGENT, "text": (text or "").strip()})

    def record_user(self, text: str) -> None:
        self._add({"ts": self._clock(), "role": self.USER, "text": (text or "").strip()})

    def record_correction(self, original: str, corrected: str) -> None:
        self._add({"ts": self._clock(), "role": self.CORRECTION,
                   "from": (original or "").strip(), "to": (corrected or "").strip()})

    def set_conversation_id(self, cid) -> None:
        with self._lock:
            self.conversation_id = cid
        self._write_notes()

    def _add(self, turn: dict) -> None:
        with self._lock:
            self.turns.append(turn)
            with self.jsonl_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(turn, ensure_ascii=False) + "\n")
        self._write_notes()

    # --- rendering ---
    def _write_notes(self) -> None:
        with self._lock:
            turns = list(self.turns)
            cid = self.conversation_id
        spoken = [t for t in turns if t["role"] in (self.AGENT, self.USER)]
        lines = [f"# {self.title}", ""]
        lines.append(f"- 시작(UTC): {turns[0]['ts'] if turns else _now()}")
        if cid:
            lines.append(f"- conversation_id: `{cid}`")
        lines.append(f"- 발화 턴 수: {len(spoken)}")
        lines.append("")
        lines.append("> 실제 인터뷰 메모는 PII 포함 가능 — `_samples/`(gitignore) 밖으로 내보내지 말 것.")
        lines.append("")
        for t in turns:
            if t["role"] == self.AGENT:
                lines.append(f"**면접관:** {t['text']}")
            elif t["role"] == self.USER:
                lines.append(f"**나(PM):** {t['text']}")
            else:  # correction
                lines.append(f"_(인식 수정: “{t['from']}” → “{t['to']}”)_")
            lines.append("")
        self.notes_path.write_text("\n".join(lines), encoding="utf-8")

    def summary(self) -> dict:
        with self._lock:
            spoken = len([t for t in self.turns if t["role"] in (self.AGENT, self.USER)])
        return {"turns": spoken, "jsonl": str(self.jsonl_path),
                "notes": str(self.notes_path), "conversation_id": self.conversation_id}


def _build_audio_interface(prefer: str = "auto"):
    """로컬 마이크/스피커 인터페이스를 만든다.

    - 'sd'/'auto' : sounddevice 기반(휠에 PortAudio 번들 → brew 불필요). 기본.
    - 'pyaudio'   : ElevenLabs 기본 인터페이스(system portaudio 필요).
    반환: (audio_interface, backend_name)
    """
    scripts_dir = str(Path(__file__).resolve().parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    if prefer in ("auto", "sd"):
        try:
            from sd_audio import SoundDeviceAudioInterface
            return SoundDeviceAudioInterface(), "sounddevice"
        except Exception:
            if prefer == "sd":
                raise
    from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface
    return DefaultAudioInterface(), "pyaudio"


def run_live(recorder: TranscriptRecorder, *, api_key: str, agent_id: str,
             audio_backend: str = "auto") -> str:
    """실제 ElevenLabs 에이전트와 마이크로 음성 인터뷰."""
    import signal

    from elevenlabs.client import ElevenLabs
    from elevenlabs.conversational_ai.conversation import Conversation

    audio_interface, backend = _build_audio_interface(audio_backend)
    client = ElevenLabs(api_key=api_key)

    def on_agent(resp: str) -> None:
        print(f"\n면접관: {resp}")
        recorder.record_agent(resp)

    def on_user(tr: str) -> None:
        print(f"나(PM): {tr}")
        recorder.record_user(tr)

    conversation = Conversation(
        client,
        agent_id,
        requires_auth=True,
        audio_interface=audio_interface,
        callback_agent_response=on_agent,
        callback_agent_response_correction=lambda o, c: recorder.record_correction(o, c),
        callback_user_transcript=on_user,
    )

    print(f"음성 인터뷰를 시작합니다 (오디오: {backend}). 마이크에 대고 PM 역할로 답해주세요. (종료: Ctrl-C)\n")
    conversation.start_session()
    signal.signal(signal.SIGINT, lambda *_: conversation.end_session())
    cid = conversation.wait_for_session_end()
    recorder.set_conversation_id(cid)
    return cid


# 오프라인 드라이런용 데모 대화(에이전트 지능 없음 — 캡처/직렬화/렌더 경로만 점검).
_DEMO_SCRIPT = [
    ("agent", "안녕하세요. 어떤 RA를 뽑고 싶으신지 같이 구체적으로 정리해볼게요. 먼저, 지금 어떤 프로젝트에서 RA가 필요하세요?"),
    ("user", "리테일 클라이언트 비용절감 프로젝트인데, 데이터 정리하고 분석을 빨리 돌려줄 사람이 필요해요."),
    ("agent", "‘분석을 빨리 돌린다’가 구체적으로 어떤 장면인지 궁금해요. 최근에 RA가 그걸 정말 잘했던 순간 하나만 떠올려 주시겠어요?"),
    ("user", "예전에 한 친구가 하룻밤 사이에 매장별 마진 모델을 스스로 짜와서 다음 날 미팅에 바로 썼어요."),
    ("agent", "그 친구가 그걸 혼자 어떻게 해냈는지가 핵심일 것 같아요. 어떤 도구나 방식을 썼는지 보셨을까요?"),
]


def run_text_only(recorder: TranscriptRecorder) -> str:
    """오디오·네트워크 없이 캡처·직렬화·렌더만 점검하는 오프라인 드라이런."""
    print("[--text-only] 오프라인 드라이런: 데모 대화를 transcript 로 기록합니다(실제 에이전트 아님).\n")
    for role, text in _DEMO_SCRIPT:
        if role == "agent":
            print(f"면접관: {text}")
            recorder.record_agent(text)
        else:
            print(f"나(PM): {text}")
            recorder.record_user(text)
    recorder.set_conversation_id("dryrun-local")
    return "dryrun-local"


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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="distillery 음성 인터뷰 러너")
    parser.add_argument("--out", default=None, help="transcript 저장 폴더(기본: <skill>/_samples)")
    parser.add_argument("--text-only", action="store_true",
                        help="오디오·네트워크 없이 캡처·렌더 점검(오프라인 드라이런)")
    parser.add_argument("--title", default="distillery 음성 인터뷰")
    parser.add_argument("--audio", choices=["auto", "sd", "pyaudio"], default="auto",
                        help="오디오 백엔드(기본 auto=sounddevice, brew 불필요)")
    args = parser.parse_args(argv)

    skill_dir = Path(__file__).resolve().parent.parent
    out_dir = Path(args.out) if args.out else (skill_dir / "_samples")
    _load_env(skill_dir)

    recorder = TranscriptRecorder(out_dir, title=args.title)

    if args.text_only:
        run_text_only(recorder)
    else:
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        agent_id = os.environ.get("AGENT_ID")
        if not api_key or not agent_id:
            print("ERROR: ELEVENLABS_API_KEY / AGENT_ID 가 없습니다. "
                  "skills/distillery/.env 를 채우거나 --text-only 로 점검하세요.", file=sys.stderr)
            return 2
        try:
            run_live(recorder, api_key=api_key, agent_id=agent_id, audio_backend=args.audio)
        except ModuleNotFoundError as e:
            print(f"ERROR: 의존성 누락({e.name}). `uv pip install -r requirements.txt` 로 설치하세요 "
                  "(기본 오디오 백엔드 sounddevice 는 brew 불필요).", file=sys.stderr)
            return 3

    s = recorder.summary()
    print(f"\n저장됨 → {s['notes']}  /  {s['jsonl']}  (발화 턴 {s['turns']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
