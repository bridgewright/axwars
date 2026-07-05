#!/usr/bin/env python3
"""Layer 1 매핑 실검증 — 우리 K-GAAP→K-IFRS 매핑의 IFRS 타깃 계정이 실제 상장사
K-IFRS 공시(OpenDART fnlttSinglAcntAll)에 존재하는지 대조한다.

전환조정 '숫자'는 입력 시산표가 비공개라 end-to-end 재현이 어렵지만, 매핑이 향하는
IFRS 계정 체계는 실제 공시로 검증 가능하다. 여러 회사를 합쳐, 각 타깃이 최소 한 곳의
실제 공시에 나타나면 '검증됨'으로 본다.

사용: python3 analysis/validate_mapping_vs_dart.py
"""
import os
import sys
import json
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "gaap-ifrs"))
from gaap_ifrs.knowledge import load_mappings          # noqa: E402

# 우리 IFRS 타깃 계정 → 실제 공시 계정명에서 찾을 핵심 토큰
CORE_TOKENS = {
    "현금및현금성자산": "현금및현금성", "매출채권및기타유동채권": "매출채권",
    "재고자산": "재고자산", "유형자산": "유형자산", "무형자산": "무형자산",
    "영업권": "영업권", "투자부동산": "투자부동산", "관계기업및공동기업투자": "관계기업",
    "이연법인세자산": "이연법인세자산", "이연법인세부채": "이연법인세부채",
    "매입채무및기타유동부채": "매입채무", "계약부채": "계약부채", "차입금": "차입금",
    "사채": "사채", "순확정급여부채": "확정급여", "자본금": "자본금",
    "자본잉여금": "자본잉여금", "이익잉여금": "이익잉여금",
    "기타포괄손익누계액": "기타포괄손익", "당기손익-공정가치측정금융자산": "당기손익",
    "기타포괄손익-공정가치측정금융자산": "공정가치측정금융자산", "단기금융상품": "금융상품",
    "상각후원가측정금융자산": "상각후원가", "수익(매출)": "매출", "매출원가": "매출원가",
    "판매비와관리비": "판매비", "금융수익": "금융수익", "금융원가": "금융원가",
    "법인세비용": "법인세비용", "손상차손": "손상",
}

COMPANIES = {"한온시스템": "00161125", "삼성전기": "00126371", "CJ제일제당": "00635134"}


def _key():
    for line in open(os.path.join(ROOT, ".env")):
        if line.startswith("API_K_DART="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("API_K_DART not in .env")


def real_accounts(key, corp, year=2023):
    names = set()
    for fs in ("CFS", "OFS"):
        u = (f"https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json?crtfc_key={key}"
             f"&corp_code={corp}&bsns_year={year}&reprt_code=11011&fs_div={fs}")
        try:
            d = json.load(urllib.request.urlopen(u, timeout=30))
        except Exception:
            continue
        for r in d.get("list", []):
            nm = (r.get("account_nm") or "").replace(" ", "")
            if nm:
                names.add(nm)
    return names


def main():
    key = _key()
    targets = sorted({m["ifrs_account"] for m in load_mappings("K-GAAP")})
    real = set()
    for nm, cc in COMPANIES.items():
        got = real_accounts(key, cc)
        print(f"  {nm}: 실제 K-IFRS 공시 계정 {len(got)}개 수집")
        real |= got
    print(f"\n실제 공시 계정 합집합: {len(real)}개  (대조 회사 {len(COMPANIES)}곳)\n")

    matched, unmatched = [], []
    for t in targets:
        token = CORE_TOKENS.get(t, t).replace(" ", "")
        if any(token in r for r in real):
            matched.append(t)
        else:
            unmatched.append(t)
    print(f"=== Layer 1 매핑 타깃 실검증 ===")
    print(f"우리 IFRS 타깃 {len(targets)}개 중 실제 공시에서 확인: {len(matched)}개 "
          f"({len(matched)/len(targets)*100:.0f}%)")
    print(f"\n✅ 확인됨: {', '.join(matched)}")
    print(f"\n❔ 실제 공시에서 미발견(표시 통합·요약 등): {', '.join(unmatched) or '없음'}")


if __name__ == "__main__":
    main()
