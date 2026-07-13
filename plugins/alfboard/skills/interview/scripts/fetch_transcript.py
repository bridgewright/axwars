#!/usr/bin/env python3
"""fetch_transcript.py — ElevenLabs에 기록된 에이전트 대화를 transcript 파일로 가져온다.

브라우저 인터뷰(serve_browser.py)는 대화를 파일로 저장하지 않는다(브라우저↔ElevenLabs).
대신 ElevenLabs가 모든 대화를 서버에 기록하므로, 이 스크립트가 최신(또는 지정) 대화를 받아
`_samples/transcript.jsonl` + `interview-notes.md` 로 떨군다. 이후 Step 4(criteria 도출)의 입력.

  uv run python scripts/fetch_transcript.py                  # 최신 'done' 대화
  uv run python scripts/fetch_transcript.py --conversation-id <id>
  uv run python scripts/fetch_transcript.py --list           # 최근 대화 목록만
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

API = "https://api.elevenlabs.io"


def _load_env(skill):
    try:
        from dotenv import load_dotenv
        load_dotenv(skill / ".env")
    except Exception:
        env = skill / ".env"
        if env.exists():
            for ln in env.read_text(encoding="utf-8").splitlines():
                ln = ln.strip()
                if ln and not ln.startswith("#") and "=" in ln:
                    k, v = ln.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def _verify():
    for e in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        v = os.environ.get(e)
        if v and Path(v).exists():
            return v
    z = Path.home() / ".config/certs/zscaler-root-ca.pem"
    return str(z) if z.exists() else True


def _get(url, key, params=None):
    import httpx
    r = httpx.get(url, headers={"xi-api-key": key}, params=params, timeout=30, verify=_verify())
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
    return r.json()


def main(argv=None):
    skill = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="ElevenLabs 대화 → transcript 파일")
    p.add_argument("--conversation-id", default=None, help="특정 대화 id(미지정 시 최신 done)")
    p.add_argument("--list", action="store_true", help="최근 대화 목록만 출력")
    p.add_argument("--out", default=None, help="출력 폴더(기본 <skill>/_samples)")
    a = p.parse_args(argv)

    _load_env(skill)
    key = os.environ.get("ELEVENLABS_API_KEY")
    aid = os.environ.get("AGENT_ID")
    if not key:
        print("ERROR: ELEVENLABS_API_KEY 없음 (.env)", file=sys.stderr)
        return 2

    try:
        if a.conversation_id:
            cid = a.conversation_id
        else:
            data = _get(f"{API}/v1/convai/conversations", key, {"agent_id": aid, "page_size": 30})
            convs = data.get("conversations", [])
            if a.list:
                for c in convs:
                    print(f"{c.get('conversation_id')} | msgs {c.get('message_count')} | "
                          f"{c.get('status')} | start {c.get('start_time_unix_secs')}")
                return 0
            done = sorted([c for c in convs if c.get("status") == "done"],
                          key=lambda c: c.get("start_time_unix_secs", 0), reverse=True)
            if not done:
                print("ERROR: 'done' 상태 대화가 없음 (인터뷰를 먼저 진행하세요)", file=sys.stderr)
                return 4
            cid = done[0]["conversation_id"]

        d = _get(f"{API}/v1/convai/conversations/{cid}", key)
        turns = []
        for t in d.get("transcript", []):
            msg = (t.get("message") or "").strip()
            if not msg:
                continue
            turns.append({"ts": t.get("time_in_call_secs"),
                          "role": "agent" if t.get("role") == "agent" else "user",
                          "text": msg})

        out = Path(a.out) if a.out else (skill / "_samples")
        out.mkdir(parents=True, exist_ok=True)
        with (out / "transcript.jsonl").open("w", encoding="utf-8") as f:
            for t in turns:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")
        L = [f"# alfboard 음성 인터뷰 — {cid}", "", f"- 발화 턴: {len(turns)}",
             "> 실제 인터뷰 메모는 PII 포함 가능 — `_samples/`(gitignore) 밖으로 내보내지 말 것.", ""]
        for t in turns:
            who = "면접관" if t["role"] == "agent" else "나(PM)"
            L += [f"**{who}:** {t['text']}", ""]
        (out / "interview-notes.md").write_text("\n".join(L), encoding="utf-8")
        print(f"가져옴: {cid} | {len(turns)}턴 → {out/'transcript.jsonl'} , {out/'interview-notes.md'}")
        return 0
    except ModuleNotFoundError as e:
        print(f"ERROR: 의존성 누락({e.name}). uv pip install -r requirements.txt", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
