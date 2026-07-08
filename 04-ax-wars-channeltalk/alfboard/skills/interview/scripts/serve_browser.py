#!/usr/bin/env python3
"""alfboard interview (voice) — 브라우저(WebRTC AEC) 음성 인터뷰 데모.

ElevenLabs 에이전트용 signed URL 을 발급받아, 브라우저에서 @elevenlabs/client 로 대화하는
로컬 페이지를 띄운다.

왜 브라우저인가: 브라우저 getUserMedia 는 **에코 제거(AEC)** 가 기본 내장이라,
**스피커로 열린 환경**에서도 (1) 에이전트가 자기 목소리를 듣고 자가대화하지 않고
(2) 사용자가 말하면 끼어들기(barge-in)가 정상 동작한다 → 해커톤 시연용.

  uv run python skills/interview/scripts/serve_browser.py
"""
from __future__ import annotations

import argparse
import functools
import http.server
import os
import socketserver
import sys
import threading
import webbrowser
from pathlib import Path

API_BASE = "https://api.elevenlabs.io"


def _load_env(skill_dir: Path) -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(skill_dir / ".env")
    except Exception:
        env = skill_dir / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def _verify():
    for env in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        v = os.environ.get(env)
        if v and Path(v).exists():
            return v
    z = Path.home() / ".config/certs/zscaler-root-ca.pem"
    return str(z) if z.exists() else True


def get_signed_url(api_key: str, agent_id: str) -> str:
    import httpx
    r = httpx.get(
        f"{API_BASE}/v1/convai/conversation/get-signed-url",
        params={"agent_id": agent_id},
        headers={"xi-api-key": api_key},
        timeout=30.0,
        verify=_verify(),
    )
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code}: {r.text}")
    return r.json()["signed_url"]


HTML = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>채널톡 · 도입 인터뷰</title>
<style>
  :root { color-scheme: light; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         max-width: 760px; margin: 0 auto; padding: 48px 20px; color: #15171a; }
  h1 { font-size: 30px; margin: 0 0 4px; letter-spacing: -0.02em; }
  .sub { color: #6b7280; margin: 0 0 28px; font-size: 15px; }
  .controls { display: flex; gap: 12px; align-items: center; }
  button { font-size: 18px; padding: 14px 26px; border-radius: 12px; border: 0; cursor: pointer; font-weight: 600; }
  #start { background: #111418; color: #fff; }
  #start:disabled { opacity: .4; cursor: default; }
  #stop { background: #f1f2f4; color: #111; }
  #stop:disabled { opacity: .4; cursor: default; }
  #dot { width: 12px; height: 12px; border-radius: 50%; background: #cbd5e1; display: inline-block; margin-left: 6px; }
  #dot.live { background: #16a34a; box-shadow: 0 0 0 0 rgba(22,163,74,.6); animation: pulse 1.4s infinite; }
  @keyframes pulse { 0%{box-shadow:0 0 0 0 rgba(22,163,74,.5)} 70%{box-shadow:0 0 0 12px rgba(22,163,74,0)} 100%{box-shadow:0 0 0 0 rgba(22,163,74,0)} }
  #status { margin: 22px 0; color: #374151; font-size: 16px; min-height: 22px; }
  #log { margin-top: 18px; line-height: 1.65; font-size: 16px; }
  #log div { margin: 10px 0; padding: 10px 14px; border-radius: 12px; max-width: 88%; }
  .ai { background: #eef2f7; }
  .me { background: #e7f7ef; margin-left: auto; }
  .who { font-size: 12px; color: #6b7280; margin-bottom: 2px; }
  .tag { display:inline-block; font-size:12px; color:#16a34a; border:1px solid #bbf7d0; background:#f0fdf4; padding:2px 8px; border-radius:999px; margin-left:8px; }
</style>
</head>
<body>
  <h1>채널톡 · 도입 인터뷰 <span class="tag">열린 환경 · 에코제거 ON</span></h1>
  <p class="sub">스피커로 진행해도 됩니다. 면접관이 말하는 중에 끼어들면 멈춥니다(barge-in). 한국어 음성.</p>
  <div class="controls">
    <button id="start">🎙️ 인터뷰 시작</button>
    <button id="stop" disabled>■ 종료</button>
    <span id="dot"></span>
  </div>
  <p id="status">‘인터뷰 시작’을 누르고 마이크 사용을 허용하세요.</p>
  <div id="log"></div>

<script type="module">
import { Conversation } from "https://esm.sh/@elevenlabs/client";
const $ = (id) => document.getElementById(id);
let conv = null;
const setStatus = (t) => ($("status").textContent = t);
const setLive = (on) => $("dot").classList.toggle("live", on);
function add(role, text) {
  if (!text) return;
  const wrap = document.createElement("div");
  wrap.className = role === "ai" ? "ai" : "me";
  const who = document.createElement("div");
  who.className = "who";
  who.textContent = role === "ai" ? "면접관" : "나 (PM)";
  const body = document.createElement("div");
  body.textContent = text;
  wrap.appendChild(who); wrap.appendChild(body);
  $("log").appendChild(wrap);
  window.scrollTo(0, document.body.scrollHeight);
}

$("start").onclick = async () => {
  $("start").disabled = true;
  setStatus("연결 중…");
  try {
    conv = await Conversation.startSession({
      signedUrl: "__SIGNED_URL__",
      onConnect: () => { setStatus("연결됨 — 말씀하세요. (면접관 말하는 중 끼어들면 멈춥니다)"); setLive(true); $("stop").disabled = false; },
      onDisconnect: () => { setStatus("인터뷰 종료됨"); setLive(false); $("start").disabled = false; $("stop").disabled = true; },
      onError: (msg) => setStatus("에러: " + (msg?.message || msg)),
      onModeChange: (m) => setStatus(m.mode === "speaking" ? "면접관이 말하는 중…" : "듣는 중 — 말씀하세요"),
      onMessage: (p) => { if (p && p.message) add(p.source === "ai" ? "ai" : "me", p.message); },
    });
  } catch (e) {
    setStatus("시작 실패: " + (e?.message || e));
    $("start").disabled = false;
  }
};
$("stop").onclick = async () => { try { await conv?.endSession?.(); } catch (e) {} };
</script>
</body>
</html>
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="alfboard interview 브라우저 음성 인터뷰 서버")
    ap.add_argument("--port", type=int, default=8723, help="로컬 서버 포트(기본 8723)")
    args = ap.parse_args(argv)

    skill_dir = Path(__file__).resolve().parent.parent
    _load_env(skill_dir)
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    agent_id = os.environ.get("AGENT_ID")
    if not api_key or not agent_id:
        print("ERROR: ELEVENLABS_API_KEY / AGENT_ID 가 .env 에 없습니다.", file=sys.stderr)
        return 2

    try:
        signed = get_signed_url(api_key, agent_id)
    except ModuleNotFoundError as e:
        print(f"ERROR: 의존성 누락({e.name}). uv pip install -r requirements.txt", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"ERROR: signed URL 발급 실패: {e}", file=sys.stderr)
        return 4

    out = skill_dir / "_samples"
    out.mkdir(parents=True, exist_ok=True)
    # 채널톡 디자인 템플릿(assets/talk_template.html)을 우선 사용, 없으면 인라인 폴백.
    template_path = skill_dir / "assets" / "talk_template.html"
    template = template_path.read_text(encoding="utf-8") if template_path.exists() else HTML
    (out / "talk.html").write_text(template.replace("__SIGNED_URL__", signed), encoding="utf-8")
    # 로고 등 정적 에셋을 서빙 폴더로 복사
    logo = skill_dir / "assets" / "channel-logo.webp"
    if logo.exists():
        import shutil
        shutil.copy(logo, out / "channel-logo.webp")

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(out))
    socketserver.TCPServer.allow_reuse_address = True
    httpd = None
    for p in range(args.port, args.port + 12):
        try:
            httpd = socketserver.TCPServer(("127.0.0.1", p), handler)
            break
        except OSError:
            continue
    if httpd is None:
        print("ERROR: 포트 바인딩 실패(사용 중).", file=sys.stderr)
        return 5
    port = httpd.server_address[1]
    url = f"http://127.0.0.1:{port}/talk.html"
    print(f"브라우저에서 열기: {url}", flush=True)
    print("종료: 이 프로세스 Ctrl-C (또는 창 닫기).", flush=True)
    threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
