KASB_DOWNLOAD_URL = "https://www.kasb.or.kr/commonFile/fileDownload.do"

# KASB has no stable per-standard GET URL: attachments are served through a
# single POST form handler keyed by {fileNo, fileSeq}. Each standard's PDF and
# HWP attachments share one fileNo but have different fileSeq values (probed
# by hand against the real site; see download_kasb below for how these are
# used). PDF is preferred over HWP: extraction from PDF is clean (see
# tools/ingest/extract.py), while hwp5txt drops the space after some leading
# paragraph numbers (e.g. "1이 기준서는..." vs the PDF's "1 이 기준서는...")
# and needs chunk.py's more permissive whitespace handling to compensate.
#
# This list is the COMPLETE enumeration of the KASB "시행중" (currently
# effective, as of the 2026-01-01 vintage shown on the page) K-IFRS listing at
# https://www.kasb.or.kr/front/board/ingAccountingList.do -- scraped
# 2026-07-06 by parsing every <tr> of the 구분/기준명/다운로드 table (63 rows,
# 0 unparsed) and pulling both fileDownload(fileNo, fileSeq) tokens (PDF +
# HWP) out of each row's download popup. Deliberately NOT scraped: the sibling
# "조기적용가능" tab (earlyAccountingList.do) -- that tab republishes nearly
# every standard a second time under a 2025-restated (IFRS 18 consequential
# amendments) text that is not yet mandatorily effective; it is a different
# corpus vintage, out of scope here (the task's URL points at the 시행중 tab
# specifically).
#
# 60 of the 63 rows carry a "제NNNN호" number: 41 기준서 (1001-1118 range --
# note some numbers are absent, e.g. 1004/1017/1104, because those standards
# have been fully superseded and so no longer appear on the *currently
# effective* listing) + 19 해석서 (2010-2123 range, KASB's translations of
# IFRIC/SIC interpretations). The remaining 3 rows have no standard number at
# all -- they are still genuine items on the same official list, just not
# 기준서/해석서: the Conceptual Framework itself, and two translated IASB
# Practice Statements (non-mandatory guidance). Per 정공법 (no arbitrary
# trimming) they are kept, tagged with a descriptive `no` instead of a
# 제NNNN호 number so they don't collide with real standard numbers; flag them
# separately if a consumer wants standards/interpretations only.
SOURCES = {
    "K-IFRS": {
        "lang": "ko", "format": "pdf", "base_url": "https://www.kasb.or.kr",
        "standards": [
            # -- 기준서 (1xxx), ascending --
            {"no": "1001", "title": "재무제표 표시", "file_no": "-49992026",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "1002", "title": "재고자산", "file_no": "9837",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1007", "title": "현금흐름표", "file_no": "-49992451",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "1008", "title": "회계정책, 회계추정치 변경과 오류", "file_no": "9843",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1010", "title": "보고기간후사건", "file_no": "9846",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1012", "title": "법인세", "file_no": "-49992027",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "1016", "title": "유형자산", "file_no": "9852",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1019", "title": "종업원급여", "file_no": "-49992028",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "1020", "title": "정부보조금의 회계처리와 정부지원의 공시", "file_no": "9857",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1021", "title": "환율변동효과", "file_no": "-49991568",
             "file_seq_pdf": "2", "file_seq_hwp": "3", "tier": "본문"},
            {"no": "1023", "title": "차입원가", "file_no": "9861",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1024", "title": "특수관계자공시", "file_no": "9864",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1026", "title": "퇴직급여제도에 의한 회계처리와 보고", "file_no": "-49990966",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1027", "title": "별도재무제표", "file_no": "-49992029",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "1028", "title": "관계기업과 공동기업에 대한 투자", "file_no": "-49990968",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1029", "title": "초인플레이션 경제에서의 재무보고", "file_no": "9871",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1032", "title": "금융상품: 표시", "file_no": "9873",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1033", "title": "주당이익", "file_no": "9874",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1034", "title": "중간재무보고", "file_no": "-49990969",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1036", "title": "자산손상", "file_no": "9876",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1037", "title": "충당부채, 우발부채, 우발자산", "file_no": "-49992030",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "1038", "title": "무형자산", "file_no": "-49992031",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "1039", "title": "금융상품: 인식과측정", "file_no": "9829",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1040", "title": "투자부동산", "file_no": "-49990970",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "1041", "title": "농림어업", "file_no": "-49992032",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "1101", "title": "한국채택국제회계기준의 최초채택", "file_no": "-49992448",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1102", "title": "주식기준보상", "file_no": "-49990973",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1103", "title": "사업결합", "file_no": "-49992033",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "1105", "title": "매각예정비유동자산과 중단영업", "file_no": "-49990975",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1106", "title": "광물자원의 탐사와 평가", "file_no": "-49990976",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1107", "title": "금융상품: 공시", "file_no": "-49992455",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "1108", "title": "영업부문", "file_no": "9848",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1109", "title": "금융상품", "file_no": "-49992454",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "1110", "title": "연결재무제표", "file_no": "-49992449",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1111", "title": "공동약정", "file_no": "-49990978",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1112", "title": "타 기업에 대한 지분의 공시", "file_no": "-49990979",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1113", "title": "공정가치 측정", "file_no": "-49990980",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1114", "title": "규제이연계정", "file_no": "9917",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1115", "title": "고객과의 계약에서 생기는 수익", "file_no": "9862",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "1116", "title": "리스", "file_no": "10510",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "1117", "title": "보험계약", "file_no": "-49992456",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            # -- 해석서 (2xxx), ascending --
            {"no": "2010", "title": "정부지원: 영업활동과 특정한 관련이 없는 경우", "file_no": "9867",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "2025", "title": "법인세: 기업이나 주주의 납세지위 변동", "file_no": "-49992036",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "2029", "title": "민간투자사업: 공시", "file_no": "-49990981",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "2032", "title": "무형자산: 웹 사이트 원가", "file_no": "9812",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "2101", "title": "사후처리 및 복구관련 충당부채의 변경", "file_no": "9813",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "2102", "title": "조합원 지분과 유사 지분", "file_no": "9815",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "2105", "title": "사후처리, 복구 및 환경정화를 위한 기금의 지분에 대한 권리", "file_no": "9816",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "2106", "title": "특정 시장에 참여함에 따라 발생하는 부채: 폐전기·전자제품", "file_no": "9817",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "2107", "title": "기업회계기준서 제1029호 ‘초인플레이션 경제에서의 재무보고’에 따른 재작성 방법의 적용", "file_no": "-49990982",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "2110", "title": "중간재무보고와 손상", "file_no": "-49990983",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "2112", "title": "민간투자사업", "file_no": "9820",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "2114", "title": "기업회계기준서 제1019호: 확정급여자산한도, 최소적립요건 및 그 상호작용", "file_no": "-49992037",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "2116", "title": "해외사업장순투자의 위험회피", "file_no": "-49992038",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "2117", "title": "소유주에 대한 비현금자산의 분배", "file_no": "9823",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "2119", "title": "지분상품에 의한 금융부채의 소멸", "file_no": "-49992039",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "2120", "title": "노천광산 생산단계의 박토원가", "file_no": "-49990985",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "2121", "title": "부담금", "file_no": "9828",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "2122", "title": "외화 거래와 선지급·선수취 대가", "file_no": "9853",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "2123", "title": "법인세 처리의 불확실성", "file_no": "9830",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            # -- non-numbered (framework / practice-statement translations) --
            {"no": "개념체계", "title": "재무보고를 위한 개념체계", "file_no": "-49990963",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "번역서-중요성판단", "title": "중요성에 대한 판단 번역서", "file_no": "-49992025",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "번역서-경영진설명서", "title": "경영진설명서 작성을 위한 개념체계 번역서", "file_no": "-49992024",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
        ],
    },
    "K-GAAP": {"lang": "ko", "format": "pdf", "base_url": "https://www.kasb.or.kr", "standards": []},
    "US-GAAP": {"lang": "en", "format": "html", "base_url": "https://asc.fasb.org", "standards": []},
    "CAS": {"lang": "zh", "format": "pdf", "base_url": "http://kjs.mof.gov.cn", "standards": []},
    "VAS": {"lang": "vi", "format": "pdf", "base_url": "", "standards": []},
}

def get_source(gaap):
    return SOURCES[gaap]

def download_kasb(file_no, file_seq, dest):
    """POST-download a single KASB attachment (fileNo/fileSeq form fields) to
    `dest`. KASB has no stable GET URL for standard attachments -- the
    download endpoint is a POST form handler. This is a small, explicit helper
    for on-demand fetching (e.g. by a human or a one-off script); it is NOT
    called during normal test/ingest runs and nothing in this repo bulk-
    downloads with it.
    """
    import requests  # local import: keep `requests` off the hot import path
    resp = requests.post(KASB_DOWNLOAD_URL, data={"fileNo": file_no, "fileSeq": file_seq},
                         timeout=30)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        f.write(resp.content)
    return dest
