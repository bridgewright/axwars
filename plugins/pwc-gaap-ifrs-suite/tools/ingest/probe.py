#!/usr/bin/env python3
"""Task 22 source-availability probe (Track 2 standards RAG chatbot).

Light reachability checker for the canonical standards source of each GAAP
(K-IFRS, K-GAAP, CAS, VAS, US-GAAP). Per unique URL it sends at most one
HEAD and, only if HEAD is rejected or fails, one GET (headers only,
streamed and closed immediately). Short timeouts, graceful failure per
source. It never downloads standard texts or scrapes at scale — format
expectations come from the registry below, confirmed manually later.

A control URL (example.com) is probed first so that "every source down"
can be distinguished from "network blocked in this environment".

Usage:
    python tools/ingest/probe.py             # human-readable table
    python tools/ingest/probe.py --json      # machine-readable JSON
    python tools/ingest/probe.py --timeout 5 # seconds (connect and read)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

try:
    import requests
except ImportError:  # pragma: no cover - environment without requests
    requests = None  # type: ignore[assignment]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "gaap-source-probe/0.1 (research; single reachability request)"
)

CONTROL = {"gaap": "_control", "url": "https://example.com/"}

# One canonical entry point per GAAP. `expected_format` / `access_path`
# encode prior research and are what Tasks 23-26 should start from.
PROBES = [
    {
        "gaap": "K-IFRS",
        "url": "https://www.kasb.or.kr/",
        "expected_format": "PDF/HWP (기준서별 첨부파일)",
        "access_path": "KASB 한국회계기준원 > 회계기준 > 한국채택국제회계기준(K-IFRS) 기준서/해석서 목록",
    },
    {
        "gaap": "K-GAAP",
        "url": "https://www.kasb.or.kr/",
        "expected_format": "PDF/HWP (장별 첨부파일)",
        "access_path": "KASB 동일 호스트 > 일반기업회계기준(장별) + 중소기업회계기준",
    },
    {
        "gaap": "CAS",
        "url": "http://kjs.mof.gov.cn/",
        "expected_format": "PDF/Word(.doc/.wps) 첨부",
        "access_path": "财政部会计司(kjs.mof.gov.cn) 企业会计准则 고시문 첨부 + 보조: 厦门大学 CAS DB 통합본",
    },
    {
        "gaap": "VAS",
        "url": "https://mof.gov.vn/",
        "expected_format": "베트남어 원문 HTML/DOC + 영역본은 회계법인 PDF",
        "access_path": "베트남 MoF 결정문(149/2001/QD-BTC 등, VAS 26종) + Circular 200/2014/TT-BTC; 영문은 Deloitte/KPMG 등 통합 번역 PDF",
    },
    {
        "gaap": "US-GAAP",
        "url": "https://asc.fasb.org/",
        "expected_format": "HTML (Basic View 화면 전용, 벌크 파일 없음)",
        "access_path": "FASB ASC Basic View(무료 가입, 화면 열람만) — 스크래핑 HIGH RISK, 실패 시 플랜 §8 원격 백엔드 예비안",
    },
]


def probe_url(url: str, timeout: float) -> dict:
    """Probe one URL with HEAD, falling back to a headers-only GET.

    Never raises; always returns a result dict.
    """
    result = {
        "url": url,
        "reachable": False,
        "method": None,
        "status": None,
        "content_type": None,
        "final_url": None,
        "error": None,
    }
    if requests is None:
        result["error"] = "requests not installed"
        return result

    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    for method in ("HEAD", "GET"):
        try:
            resp = requests.request(
                method,
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True,
                stream=True,  # headers only; body never read
            )
            result.update(
                method=method,
                status=resp.status_code,
                content_type=resp.headers.get("Content-Type"),
                final_url=resp.url,
                error=None,
            )
            resp.close()
            if method == "HEAD" and resp.status_code in (400, 403, 405, 501):
                continue  # server dislikes HEAD; one GET retry
            result["reachable"] = 200 <= resp.status_code < 400
            return result
        except requests.RequestException as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
            continue  # one GET retry after a failed HEAD
    return result


def run(timeout: float) -> dict:
    cache: dict[str, dict] = {}

    def cached_probe(url: str) -> dict:
        if url not in cache:
            cache[url] = probe_url(url, timeout)
        return cache[url]

    control = cached_probe(CONTROL["url"])
    rows = []
    for spec in PROBES:
        r = dict(spec)
        r.update(cached_probe(spec["url"]))
        rows.append(r)

    return {
        "probed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "timeout_s": timeout,
        "network_available": bool(control["reachable"]),
        "control": control,
        "results": rows,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--timeout", type=float, default=6.0, help="per-request timeout in seconds")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = ap.parse_args(argv)

    report = run(args.timeout)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    net = "OK" if report["network_available"] else "BLOCKED/DOWN"
    print(f"probed_at={report['probed_at_utc']}  control(example.com)={net}")
    print(f"{'GAAP':<8} {'reach':<5} {'HTTP':<5} {'content-type':<28} url / error")
    for r in report["results"]:
        ct = (r["content_type"] or "-")[:27]
        status = r["status"] if r["status"] is not None else "-"
        tail = r["url"] if r["error"] is None else f"{r['url']}  !! {r['error'][:90]}"
        print(f"{r['gaap']:<8} {str(r['reachable']):<5} {status!s:<5} {ct:<28} {tail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
