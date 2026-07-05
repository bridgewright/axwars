#!/usr/bin/env python3
"""IFRS 1101(최초채택) 전환조정 주석 페처 — 실데이터 검증(문항 5) 보조 도구.

전환 상장사의 첫 K-IFRS 공시(사업보고서/감사보고서)를 DART에서 받아, 과거 회계기준
(일반기업회계기준) → K-IFRS 전환이 '자본/손익에 미치는 영향' 주석 구간을 키워드로 찾아
후보 숫자를 추출한다. 문서 구조가 회사·연도마다 달라 best-effort이며, 추출 결과는
사람이 확인 후 gaap_ifrs.validate 의 ground_truth 로 사용한다.

사용: python3 analysis/fetch_ifrs1_note.py <corp_code> <bgn_de> <end_de>
예:  python3 analysis/fetch_ifrs1_note.py 00126380 20120101 20120601
"""
import os
import re
import io
import sys
import json
import zipfile
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYWORDS = [
    "최초채택", "한국채택국제회계기준으로의 전환", "과거회계기준", "일반기업회계기준",
    "전환일", "자본에 미치는 영향", "당기순이익에 미치는 영향", "조정내역", "K-GAAP",
]


def _key():
    for line in open(os.path.join(ROOT, ".env")):
        line = line.strip()
        if line.startswith("API_K_DART="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("API_K_DART not in .env")


def _clean(s):
    return re.sub(r"\s+", " ", re.sub(r"&[a-z#0-9]+;", " ", re.sub(r"<[^>]+>", " ", s)))


def _reports(key, corp, bgn, end):
    out = []
    for ty in ("A001", "F001"):   # 사업보고서, 감사보고서
        u = (f"https://opendart.fss.or.kr/api/list.json?crtfc_key={key}"
             f"&corp_code={corp}&bgn_de={bgn}&end_de={end}&pblntf_detail_ty={ty}&page_count=30")
        try:
            d = json.load(urllib.request.urlopen(u, timeout=30))
        except Exception:
            continue
        out += d.get("list", [])
    return out


def _docs(key, rcept):
    raw = urllib.request.urlopen(
        f"https://opendart.fss.or.kr/api/document.xml?crtfc_key={key}&rcept_no={rcept}",
        timeout=120).read()
    z = zipfile.ZipFile(io.BytesIO(raw))
    return {fn: _clean(z.read(fn).decode("utf-8", "replace")) for fn in z.namelist()}


def scan(corp, bgn, end):
    key = _key()
    findings = []
    for rep in _reports(key, corp, bgn, end):
        try:
            docs = _docs(key, rep["rcept_no"])
        except Exception as e:
            print(f"  skip {rep['rcept_no']}: {e}")
            continue
        for fn, text in docs.items():
            hits = {k: text.count(k) for k in KEYWORDS if text.count(k)}
            if len(hits) >= 2:                       # 전환 주석일 가능성
                anchor = text.find("자본에 미치는 영향")
                if anchor < 0:
                    anchor = text.find("최초채택")
                snippet = text[anchor:anchor + 1200] if anchor >= 0 else text[:600]
                findings.append({"report": rep["report_nm"], "rcept": rep["rcept_no"],
                                 "file": fn, "hits": hits, "snippet": snippet})
    return findings


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    for f in scan(sys.argv[1], sys.argv[2], sys.argv[3]):
        print(f"\n### {f['report']} / {f['file']} hits={f['hits']}")
        print(f["snippet"])
