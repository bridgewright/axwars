#!/usr/bin/env python3
"""국내 대규모기업집단 대표사의 해외 자회사 국가 분포 랭킹 (OpenDART).

목적: 로컬 GAAP → K-IFRS 변환 엔진(B)의 국가 우선순위 근거.
방법: 각 사 최신 사업보고서 원문에서 법인 접미사(Co.,Ltd/Inc/GmbH/㈜ 등) 주변의
      국가·주요도시 키워드를 매칭해 자회사 소재국을 추론·집계.
한계: 대기업은 자회사를 '지역(미주/유럽)'으로 묶거나 이름에 국가를 인코딩 → 추론 기반.
      'total'은 언급빈도 프록시(노이즈 있음), 'companies'(몇 개 집단에 존재)가 더 견고.
사용: .env의 API_K_DART 사용. python3 analysis/dart_subsidiary_ranking.py
"""
import urllib.request, zipfile, io, re, json, time, os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_key():
    for line in open(os.path.join(ROOT, ".env")):
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() == "API_K_DART":
                return v.strip().strip('"').strip("'")
    raise SystemExit("API_K_DART not found in .env")

KEY = load_key()
TARGETS = ["삼성전자","SK하이닉스","현대자동차","기아","LG전자","LG화학","LG에너지솔루션",
           "삼성SDI","POSCO홀딩스","현대모비스","한화솔루션","롯데케미칼","CJ제일제당",
           "삼성전기","SK이노베이션","HD현대중공업","삼성바이오로직스","LG디스플레이","한온시스템"]

CITY2C = {"shanghai":"중국","suzhou":"중국","shenzhen":"중국","guangzhou":"중국","tianjin":"중국",
  "chengdu":"중국","beijing":"중국","dongguan":"중국","wuxi":"중국","nanjing":"중국","qingdao":"중국",
  "weihai":"중국","yantai":"중국","xian":"중국","wuhan":"중국","chongqing":"중국","hangzhou":"중국",
  "dalian":"중국","kunshan":"중국","huizhou":"중국","langfang":"중국",
  "hanoi":"베트남","chi minh":"베트남","hcmc":"베트남","bac ninh":"베트남","thai nguyen":"베트남",
  "hai phong":"베트남","dong nai":"베트남","binh duong":"베트남",
  "chennai":"인도","bangalore":"인도","bengaluru":"인도","mumbai":"인도","noida":"인도","gurgaon":"인도",
  "pune":"인도","delhi":"인도","jakarta":"인도네시아","cikarang":"인도네시아","bekasi":"인도네시아",
  "bangkok":"태국","kuala lumpur":"말레이시아","penang":"말레이시아","manila":"필리핀",
  "singapore":"싱가포르","tokyo":"일본","osaka":"일본","yokohama":"일본"}

CTRY = {"vietnam":"베트남","베트남":"베트남","china":"중국","중국":"중국","india":"인도","인도":"인도",
  "indonesia":"인도네시아","인도네시아":"인도네시아","japan":"일본","일본":"일본","germany":"독일","독일":"독일",
  "deutschland":"독일","poland":"폴란드","폴란드":"폴란드","hungary":"헝가리","헝가리":"헝가리",
  "slovakia":"슬로바키아","슬로바키아":"슬로바키아","czech":"체코","체코":"체코","romania":"루마니아",
  "france":"프랑스","프랑스":"프랑스","u.k":"영국","united kingdom":"영국","england":"영국","영국":"영국",
  "netherlands":"네덜란드","네덜란드":"네덜란드","italy":"이탈리아","이탈리아":"이탈리아","spain":"스페인",
  "turkey":"튀르키예","türkiye":"튀르키예","튀르키예":"튀르키예","터키":"튀르키예","russia":"러시아","러시아":"러시아",
  "mexico":"멕시코","멕시코":"멕시코","brazil":"브라질","브라질":"브라질","thailand":"태국","태국":"태국",
  "malaysia":"말레이시아","말레이시아":"말레이시아","philippines":"필리핀","필리핀":"필리핀",
  "singapore":"싱가포르","싱가포르":"싱가포르","canada":"캐나다","australia":"호주",
  "u.s.a":"미국","usa":"미국","america":"미국","미국":"미국","u.s.":"미국"}

SUFFIX = re.compile(r"(Co\.,?\s?Ltd|Ltd\.|Inc\.|Inc\b|GmbH|S\.A\.S|S\.A\b|B\.V\.|N\.V\.|Pte|Sdn\.?\s?Bhd|Ltda|LLC|Limited|㈜|\(유\)|S\.p\.A|S\.r\.l|Corp\.|Company)", re.I)

def api_json(url):
    return json.load(urllib.request.urlopen(url, timeout=60))

def corp_codes(names):
    raw = urllib.request.urlopen(f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={KEY}", timeout=120).read()
    xml = zipfile.ZipFile(io.BytesIO(raw)).read(zipfile.ZipFile(io.BytesIO(raw)).namelist()[0]).decode("utf-8","replace")
    import xml.etree.ElementTree as ET
    m = {}
    for e in ET.fromstring(xml).iter("list"):
        nm = (e.findtext("corp_name") or "").strip(); cc = (e.findtext("corp_code") or "").strip()
        if (e.findtext("stock_code") or "").strip() and nm and cc:
            m.setdefault(nm, cc)
    return {n: m[n] for n in names if n in m}

def latest_annual(cc):
    d = api_json(f"https://opendart.fss.or.kr/api/list.json?crtfc_key={KEY}&corp_code={cc}&bgn_de=20240101&end_de=20260701&pblntf_detail_ty=A001&page_count=100")
    best = None
    for r in d.get("list", []):
        if "사업보고서" in r.get("report_nm","") and (best is None or r["rcept_dt"] > best["rcept_dt"]):
            best = r
    return best

def clean(s):
    s = re.sub(r"<[^>]+>", " ", s); s = re.sub(r"&[a-z#0-9]+;", " ", s); return re.sub(r"\s+", " ", s)

def get_main_doc(rcept):
    raw = urllib.request.urlopen(f"https://opendart.fss.or.kr/api/document.xml?crtfc_key={KEY}&rcept_no={rcept}", timeout=120).read()
    z = zipfile.ZipFile(io.BytesIO(raw))
    return clean(z.read(z.namelist()[0]).decode("utf-8","replace"))

def detect(text):
    c = Counter(); low = text.lower()
    for m in SUFFIX.finditer(text):
        w = low[max(0, m.start()-45):m.end()+15]; hit = None
        for k, v in CTRY.items():
            if k in w: hit = v; break
        if not hit:
            for k, v in CITY2C.items():
                if k in w: hit = v; break
        if hit: c[hit] += 1
    return c

def main():
    codes = corp_codes(TARGETS)
    TOTAL, PRESENT, per = Counter(), Counter(), {}
    for name, cc in codes.items():
        try:
            rep = latest_annual(cc)
            if not rep:
                print(f"- {name}: no report"); continue
            c = detect(get_main_doc(rep["rcept_no"]))
            per[name] = dict(c.most_common(8))
            for k, v in c.items():
                TOTAL[k] += v; PRESENT[k] += 1
            print(f"- {name}: " + ", ".join(f"{k}:{v}" for k, v in c.most_common(5)))
            time.sleep(0.3)
        except Exception as e:
            print(f"- {name}: ERR {e}")
    out = {"total": dict(TOTAL), "present": dict(PRESENT), "per": per}
    json.dump(out, open(os.path.join(ROOT, "analysis", "ranking.json"), "w"), ensure_ascii=False, indent=2)
    print("\n=== RANKING (companies present / total mentions) ===")
    for k, v in sorted(TOTAL.items(), key=lambda x: (-PRESENT[x[0]], -x[1])):
        print(f"{k:8s} companies={PRESENT[k]:2d}  total={v}")

if __name__ == "__main__":
    main()
