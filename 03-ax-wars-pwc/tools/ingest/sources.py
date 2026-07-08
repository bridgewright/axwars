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
        # 출처/기준일(2026-07-08 메타 정정): KASB는 기준서·문단 단위 GET 딥링크가
        # 없어(문서는 POST fileDownload.do), 공식 '시행중' 목록 페이지를 출처로 둔다.
        # as_of는 그 페이지가 명시하는 시행중 vintage(2026-01-01) — 이전 빌드의
        # 2025-01-01 잔재를 정정. GAAP-level 기본값(개별 std가 없을 때 run_ingest가
        # src.get으로 폴백).
        "as_of": "2026-01-01",
        "url": "https://www.kasb.or.kr/front/board/ingAccountingList.do",
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
    "K-GAAP": {
        # 소스=HWP(2026-07-08 정정): K-GAAP PDF는 한글 단어 사이 공백이 없는
        # 텍스트 레이어라 PyMuPDF 어떤 모드로도 복원 불가(Phase 0 실측). HWP는
        # 공백 보존(hwp5txt) → 소스를 HWP로 전환. 트레이드오프: hwp5txt는 표를
        # <표> 플레이스홀더로 떨궈 표 내용은 손실(본문 규정 텍스트가 우선). 번호 뒤
        # 공백('9.1이')은 normalize_missing_space가 처리. url=공식 List3003 목록.
        "lang": "ko", "format": "hwp", "base_url": "https://www.kasb.or.kr",
        "url": "https://www.kasb.or.kr/front/board/List3003.do",
        # Unlike K-IFRS's own listing page (which states "시행중 회계기준은
        # 2026년 1월 1일 현재 시행중인 회계..."), List3003.do prints no
        # single canonical "현재 시행중" vintage sentence at all -- each 장
        # instead carries its OWN "의결 YYYY.M.D." enactment/amendment date
        # in its title block (ranging 2009-2023 across the 33 장 sampled).
        # This GAAP-level default records the scrape date itself (2026-07-06)
        # as the as_of used by ingest_gaap when a standard doesn't specify
        # its own -- "this is what was live on kasb.or.kr as of this date" --
        # rather than fabricating a single vintage claim the source page
        # itself never makes.
        "as_of": "2026-07-06",
        # Complete enumeration of the KASB 일반기업회계기준 listing at
        # https://www.kasb.or.kr/front/board/List3003.do -- scraped 2026-07-06
        # by parsing every <tr> of the 기준명/다운로드 table (37 rows, 0
        # unparsed, no pagination on the page). Reached from the site's own
        # nav: sitemap.do's "일반기업회계기준" menu item resolves to
        # fn_goMenu('/front/board/List3003.do') -- a SEPARATE board from
        # K-IFRS's own ingAccountingList.do, with no early/current-tab split
        # (single always-current list; no "현재 시행중" vintage sentence is
        # printed on this page the way K-IFRS's own listing has one, unlike
        # that registry's as_of this one is dated to the scrape itself).
        #
        # 33 rows carry a "제NN장" chapter number (1-33, contiguous, none
        # superseded/missing unlike K-IFRS's gappy 1xxx range) + 4 rows with
        # no chapter number: 재무회계개념체계 (conceptual framework,
        # tagged "개념체계" mirroring the K-IFRS registry's own non-numbered-
        # item convention), 일반기업회계기준 시행일 및 경과규정 (effective-
        # date/transitional-provisions, tagged "시행일-경과규정"),
        # 보험업회계처리준칙 (a pre-2011 "종전 기업회계기준" grandfathered
        # into the 일반기업회계기준 category until superseded per its own
        # in-document editorial note -- tagged by its own title, legacy
        # "N. <heading>"/"(N-M)" numbering, no "의결 YYYY" title block), and
        # 일반기업회계기준 재무제표 영문양식 (tagged "영문양식") -- the ONLY
        # HWP-only row on the whole board (no PDF attachment at all; file
        # confirmed via hwp5txt to be blank English-language financial-
        # statement FORM exhibits with placeholder tables, no 문단-numbered
        # regulatory text at all, so it is excluded at the ingestion step --
        # see the ingestion report -- but kept here, per 정공법, as a
        # truthfully-cataloged registry entry with format="hwp" and
        # file_seq_pdf=None rather than silently omitted).
        #
        # PDF is preferred (file_seq_pdf) wherever it exists; HWP fileSeq is
        # kept alongside for completeness, same convention as K-IFRS's own
        # registry. fileNo/fileSeq->format mapping is NOT a fixed convention
        # (confirmed: rows 27/28 "특수활동"/"중단사업" have PDF at fileSeq
        # "1" and HWP at "2", the REVERSE of every other row) -- each row's
        # tokens below were read from its own down_pdf/down_hwp class
        # directly, never assumed from a global seq-number pattern (same
        # caution the K-IFRS registry's own docstring documents).
        "standards": [
            # -- non-chapter: conceptual framework --
            {"no": "개념체계", "title": "재무회계개념체계", "file_no": "4813",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            # -- 장 1-33, ascending --
            {"no": "1", "title": "목적, 구성 및 적용", "file_no": "-49989942",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "2", "title": "재무제표의 작성과 표시Ⅰ", "file_no": "10512",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "3", "title": "재무제표의 작성과 표시Ⅱ", "file_no": "9222",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "4", "title": "연결재무제표", "file_no": "5339",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "5", "title": "회계정책, 회계추정의 변경 및 오류", "file_no": "-49949710",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "6", "title": "금융자산ㆍ금융부채", "file_no": "3831",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "7", "title": "재고자산", "file_no": "-49929594",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "8", "title": "지분법", "file_no": "10572",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            # PDF confirmed (2026-07-06) to be a raster SCAN with no text
            # layer at all: 17 pages, every page 0-7 extractable chars
            # (just a page-footer number) but 12-105 embedded raster image
            # tiles -- a legacy digitization artifact on KASB's own server,
            # not an extract.py/PyMuPDF issue (every other 장's PDF has a
            # real text layer). The HWP attachment for this SAME 기준 has
            # clean, complete native text (confirmed via hwp5txt: real
            # "9.1"/"9.2"/... paragraphs, same numbering convention as every
            # other 장). "format": "hwp" overrides the GAAP-level PDF
            # default for this one entry only -- see download_path/
            # ingest_gaap in run_ingest.py.
            {"no": "9", "title": "조인트벤처 투자", "file_no": "1590",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "format": "hwp", "tier": "본문"},
            {"no": "10", "title": "유형자산", "file_no": "2548",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "11", "title": "무형자산", "file_no": "2550",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "12", "title": "사업결합", "file_no": "3833",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "13", "title": "리스", "file_no": "3834",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "14", "title": "충당부채, 우발부채 및 우발자산", "file_no": "3835",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "15", "title": "자본", "file_no": "3852",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "16", "title": "수익", "file_no": "5340",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "17", "title": "정부보조금의 회계처리", "file_no": "9223",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "18", "title": "차입원가자본화", "file_no": "4816",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "19", "title": "주식기준보상", "file_no": "3839",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "20", "title": "자산손상", "file_no": "3840",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "21", "title": "종업원급여", "file_no": "3841",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "22", "title": "법인세회계", "file_no": "10513",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "23", "title": "환율변동효과", "file_no": "2552",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "24", "title": "보고기간후사건", "file_no": "-49758608",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "25", "title": "특수관계자 공시", "file_no": "6351",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "26", "title": "기본주당이익", "file_no": "3844",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "27", "title": "특수활동", "file_no": "-49728434",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "28", "title": "중단사업", "file_no": "-49718376",
             "file_seq_pdf": "1", "file_seq_hwp": "2", "tier": "본문"},
            {"no": "29", "title": "중간재무제표", "file_no": "6352",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "30", "title": "일반기업회계기준의 최초채택", "file_no": "5341",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "31", "title": "중소기업 회계처리 특례", "file_no": "6353",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "32", "title": "동일지배거래", "file_no": "10573",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "33", "title": "온실가스 배출권과 배출부채", "file_no": "-49537332",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            # -- non-chapter: administrative / legacy --
            {"no": "시행일-경과규정", "title": "일반기업회계기준 시행일 및 경과규정", "file_no": "10571",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "보험업회계처리준칙", "title": "보험업회계처리준칙", "file_no": "4240",
             "file_seq_pdf": "2", "file_seq_hwp": "1", "tier": "본문"},
            {"no": "영문양식", "title": "일반기업회계기준 재무제표 영문양식", "file_no": "1271",
             "file_seq_pdf": None, "file_seq_hwp": "1", "format": "hwp", "tier": "본문"},
        ],
    },
    # US GAAP (FASB ASC) -- 원격 확장점(§8). asc.fasb.org Basic View는 봇월(403)·로그인·
    # 전문파일 부재로 대량 verbatim 확보 불가 → zip 내장하지 않음. 정식 ASC 구독/라이선스
    # 피드 확보 시 MCP가 gaap='US-GAAP' 질의를 원격 백엔드로 라우팅하도록 확장한다.
    "US-GAAP": {"lang": "en", "format": "html", "base_url": "https://asc.fasb.org",
                "mode": "remote", "standards": []},
    # CAS (中国企业会计准则 / China ASBE) -- 财政部 회계사 own portal
    # (kjs.mof.gov.cn / tfs.mof.gov.cn) returns HTTP 502 from every IP this
    # environment has tried (confirmed 2026-07-06: consistent across repeated
    # retries with backoff, both the listing page and individual article
    # pages, on both http and https -- a WAF/geo block, not transient
    # flakiness; plain www.mof.gov.cn, the non-kjs parent domain, DOES
    # resolve, but does not itself host the standard texts). Two reachable
    # alternatives were used instead, both directly confirmed working from
    # this network:
    #   "official" = casc.org.cn (中国会计准则委员会 / China Accounting
    #     Standards Committee -- a sibling official body under 财政部, every
    #     page footer-attributed "版权所有财政部会计准则委员会" and every
    #     standard page headed "来源: 会计司"; casc.org.cn even lists
    #     kjs.mof.gov.cn as its own "友情链接"). Used for all 43 준칙 본문
    #     (기본준칙 + 42 구체준칙, latest promulgated version each) and for
    #     7 of the 20 interpretations (4-8, 19, 20) plus 3 more (16-18) via
    #     an official PDF attachment linked directly off the casc.org.cn
    #     notice page (hosted on upload-news.esnai.cn, casc's own credited
    #     tech-support CDN -- requires the "referer" URL below, or the CDN's
    #     anti-hotlink protection 404s).
    #   "mirror" = cas.xmu.edu.cn (厦门大学会计发展研究中心 / Xiamen
    #     University Accounting Development Research Center CAS database --
    #     the task's own suggested academic-mirror fallback). Used for ALL
    #     32 응용지침 (application guidance; casc.org.cn has no individual
    #     guidance pages at all) and for 10 of the 20 interpretations
    #     (1-3, 9-15; casc.org.cn's own notice for these is a transmittal
    #     memo pointing at a legacy .doc attachment, not cleanly
    #     re-extractable with the tools available here).
    # Enumeration: casc.org.cn's own /qykjzz/ listing (3 pages, 59 rows) was
    # scraped in full -- every one of the 42 구체준칙 plus 기본준칙 is on it,
    # several with multiple historical versions (e.g. 21 租赁 has both a 2006
    # and a 2018 promulgation); the LATEST version is selected per standard
    # (see as_of). Interpretations 1-20 come from casc.org.cn's own
    # /qykjzzjs/ listing (20 rows, current as of this scrape -- No.20 was
    # issued 2026-06-17, i.e. after this repo's own K-GAAP scrape date).
    # Guidance (응用指南) comes from cas.xmu.edu.cn's own CAS.htm index,
    # which lists 32 individually-promulgated guidance documents (not all 42
    # standards have one -- e.g. 15/25/26/29/32/36/39/40/41/42 never got a
    # separate 应用指南 of their own; nothing trimmed, this is the site's own
    # complete list).
    "CAS": {
        "lang": "zh", "format": "html", "base_url": "https://www.casc.org.cn",
        "standards": [
        # -- 기본준칙 + 42 구체준칙 (specific standards) -- casc.org.cn
        # (中国会计准则委员会/China Accounting Standards Committee, official
        # body under 财政部; kjs.mof.gov.cn itself 502s from this network).
        # Latest promulgated version picked per standard (see as_of).
        {"no": "기본준칙", "title": "基本准则", "url": "https://www.casc.org.cn/2018/0815/202818.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2014-01-01",
         "provenance": "official"},
        {"no": "1", "title": "存货", "url": "https://www.casc.org.cn/2018/0815/202816.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "2", "title": "长期股权投资", "url": "https://www.casc.org.cn/2018/0815/202815.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2014-01-01",
         "provenance": "official"},
        {"no": "3", "title": "投资性房地产", "url": "https://www.casc.org.cn/2018/0815/202813.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "4", "title": "固定资产", "url": "https://www.casc.org.cn/2018/0815/202812.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "5", "title": "生物资产", "url": "https://www.casc.org.cn/2018/0815/202811.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "6", "title": "无形资产", "url": "https://www.casc.org.cn/2018/0815/202810.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "7", "title": "非货币性资产交换", "url": "https://www.casc.org.cn/2018/0815/202809.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2019-01-01",
         "provenance": "official"},
        {"no": "8", "title": "资产减值", "url": "https://www.casc.org.cn/2018/0815/202807.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "9", "title": "职工薪酬", "url": "https://www.casc.org.cn/2018/0815/202806.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2014-01-01",
         "provenance": "official"},
        {"no": "10", "title": "企业年金基金", "url": "https://www.casc.org.cn/2018/0815/202804.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "11", "title": "股份支付", "url": "https://www.casc.org.cn/2018/0815/202803.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "12", "title": "债务重组", "url": "https://www.casc.org.cn/2018/0815/202802.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2019-01-01",
         "provenance": "official"},
        {"no": "13", "title": "或有事项", "url": "https://www.casc.org.cn/2018/0815/202800.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "14", "title": "收入", "url": "https://www.casc.org.cn/2018/0815/202799.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2017-01-01",
         "provenance": "official"},
        {"no": "15", "title": "建造合同", "url": "https://www.casc.org.cn/2018/0815/202797.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "16", "title": "政府补助", "url": "https://www.casc.org.cn/2018/0815/202796.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2017-01-01",
         "provenance": "official"},
        {"no": "17", "title": "借款费用", "url": "https://www.casc.org.cn/2018/0815/202794.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "18", "title": "所得税", "url": "https://www.casc.org.cn/2018/0815/202793.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "19", "title": "外币折算", "url": "https://www.casc.org.cn/2018/0815/202792.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "20", "title": "企业合并", "url": "https://www.casc.org.cn/2018/0815/202791.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "21", "title": "租赁", "url": "https://www.casc.org.cn/2018/0815/202790.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2018-01-01",
         "provenance": "official"},
        {"no": "22", "title": "金融工具确认和计量", "url": "https://www.casc.org.cn/2018/0815/202788.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2017-01-01",
         "provenance": "official"},
        {"no": "23", "title": "金融资产转移", "url": "https://www.casc.org.cn/2018/0815/202786.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2017-01-01",
         "provenance": "official"},
        {"no": "24", "title": "套期会计", "url": "https://www.casc.org.cn/2018/0815/202784.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2017-01-01",
         "provenance": "official"},
        {"no": "25", "title": "保险合同", "url": "https://www.casc.org.cn/2018/0815/213104.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2020-01-01",
         "provenance": "official"},
        {"no": "26", "title": "再保险合同", "url": "https://www.casc.org.cn/2018/0815/202781.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "27", "title": "石油天然气开采", "url": "https://www.casc.org.cn/2018/0815/202780.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "28", "title": "会计政策、会计估计变更和差错更正", "url": "https://www.casc.org.cn/2018/0815/202779.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "29", "title": "资产负债表日后事项", "url": "https://www.casc.org.cn/2018/0815/202778.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "30", "title": "财务报表列报", "url": "https://www.casc.org.cn/2018/0815/202777.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2014-01-01",
         "provenance": "official"},
        {"no": "31", "title": "现金流量表", "url": "https://www.casc.org.cn/2018/0814/202775.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "32", "title": "中期财务报告", "url": "https://www.casc.org.cn/2018/0814/202774.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "33", "title": "合并财务报表", "url": "https://www.casc.org.cn/2018/0814/202773.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2014-01-01",
         "provenance": "official"},
        {"no": "34", "title": "每股收益", "url": "https://www.casc.org.cn/2018/0814/202771.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "35", "title": "分部报告", "url": "https://www.casc.org.cn/2018/0814/202770.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "36", "title": "关联方披露", "url": "https://www.casc.org.cn/2018/0814/202769.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "37", "title": "金融工具列报", "url": "https://www.casc.org.cn/2018/0814/202768.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2017-01-01",
         "provenance": "official"},
        {"no": "38", "title": "首次执行企业会计准则", "url": "https://www.casc.org.cn/2018/0814/202765.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2006-01-01",
         "provenance": "official"},
        {"no": "39", "title": "公允价值计量", "url": "https://www.casc.org.cn/2018/0814/202764.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2014-01-01",
         "provenance": "official"},
        {"no": "40", "title": "合营安排", "url": "https://www.casc.org.cn/2018/0814/202763.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2014-01-01",
         "provenance": "official"},
        {"no": "41", "title": "在其他主体中权益的披露", "url": "https://www.casc.org.cn/2018/0814/202762.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2014-01-01",
         "provenance": "official"},
        {"no": "42", "title": "持有待售的非流动资产、处置组和终止经营", "url": "https://www.casc.org.cn/2018/0814/202761.shtml",
         "format": "html", "tier_hint": "본문", "as_of": "2017-01-01",
         "provenance": "official"},

        # -- 응용지침 (application guidance, tier=적용지침) -- Xiamen Univ.
        # mirror (cas.xmu.edu.cn); casc.org.cn has no individual guidance pages.
        # standard_no overrides `no` so guidance groups under its parent's number.
        {"no": "1-지침", "standard_no": "1", "title": "存货",
         "url": "https://cas.xmu.edu.cn/info/1823/4694.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "2-지침", "standard_no": "2", "title": "长期股权投资",
         "url": "https://cas.xmu.edu.cn/info/1833/4704.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "3-지침", "standard_no": "3", "title": "投资性房地产",
         "url": "https://cas.xmu.edu.cn/info/1843/4714.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "4-지침", "standard_no": "4", "title": "固定资产",
         "url": "https://cas.xmu.edu.cn/info/1853/4724.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "5-지침", "standard_no": "5", "title": "生物资产",
         "url": "https://cas.xmu.edu.cn/info/1863/4734.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "6-지침", "standard_no": "6", "title": "无形资产",
         "url": "https://cas.xmu.edu.cn/info/1873/4744.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "7-지침", "standard_no": "7", "title": "非货币性资产交换",
         "url": "https://cas.xmu.edu.cn/info/1883/4754.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "8-지침", "standard_no": "8", "title": "资产减值",
         "url": "https://cas.xmu.edu.cn/info/1893/4764.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "9-지침", "standard_no": "9", "title": "职工薪酬",
         "url": "https://cas.xmu.edu.cn/info/1903/4774.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "10-지침", "standard_no": "10", "title": "企业年金基金",
         "url": "https://cas.xmu.edu.cn/info/1913/4784.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "11-지침", "standard_no": "11", "title": "股份支付",
         "url": "https://cas.xmu.edu.cn/info/1923/4794.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "12-지침", "standard_no": "12", "title": "债务重组",
         "url": "https://cas.xmu.edu.cn/info/1933/4804.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "13-지침", "standard_no": "13", "title": "或有事项",
         "url": "https://cas.xmu.edu.cn/info/1943/4814.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "14-지침", "standard_no": "14", "title": "收入",
         "url": "https://cas.xmu.edu.cn/info/1953/4824.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "16-지침", "standard_no": "16", "title": "政府补助",
         "url": "https://cas.xmu.edu.cn/info/1963/4834.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "17-지침", "standard_no": "17", "title": "借款费用",
         "url": "https://cas.xmu.edu.cn/info/1973/4844.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "18-지침", "standard_no": "18", "title": "所得税",
         "url": "https://cas.xmu.edu.cn/info/1983/4854.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "19-지침", "standard_no": "19", "title": "外币折算",
         "url": "https://cas.xmu.edu.cn/info/1993/4864.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "20-지침", "standard_no": "20", "title": "企业合并",
         "url": "https://cas.xmu.edu.cn/info/2003/4874.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "21-지침", "standard_no": "21", "title": "租赁",
         "url": "https://cas.xmu.edu.cn/info/2013/4884.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "22-지침", "standard_no": "22", "title": "金融工具确认和计量",
         "url": "https://cas.xmu.edu.cn/info/2023/4894.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "23-지침", "standard_no": "23", "title": "金融资产转移",
         "url": "https://cas.xmu.edu.cn/info/2033/4904.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "24-지침", "standard_no": "24", "title": "套期会计",
         "url": "https://cas.xmu.edu.cn/info/2043/4914.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "27-지침", "standard_no": "27", "title": "石油天然气开采",
         "url": "https://cas.xmu.edu.cn/info/2053/4924.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "28-지침", "standard_no": "28", "title": "会计政策、会计估计变更和差错更正",
         "url": "https://cas.xmu.edu.cn/info/2063/4934.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "30-지침", "standard_no": "30", "title": "财务报表列报",
         "url": "https://cas.xmu.edu.cn/info/2073/4944.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "31-지침", "standard_no": "31", "title": "现金流量表",
         "url": "https://cas.xmu.edu.cn/info/2083/4954.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "33-지침", "standard_no": "33", "title": "合并财务报表",
         "url": "https://cas.xmu.edu.cn/info/2093/4964.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "34-지침", "standard_no": "34", "title": "每股收益",
         "url": "https://cas.xmu.edu.cn/info/2103/4974.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "35-지침", "standard_no": "35", "title": "分部报告",
         "url": "https://cas.xmu.edu.cn/info/2113/4984.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "37-지침", "standard_no": "37", "title": "金融工具列报",
         "url": "https://cas.xmu.edu.cn/info/2123/4994.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},
        {"no": "38-지침", "standard_no": "38", "title": "首次执行企业会计准则",
         "url": "https://cas.xmu.edu.cn/info/2133/5004.htm", "format": "html", "tier_hint": "적용지침",
         "para_style": "section", "as_of": "2022-08-05", "provenance": "mirror"},

        # -- 준칙해석 (interpretations 1-20, tier=본문) -- standalone standard_no,
        # same convention K-IFRS uses for its own 해석서 (not nested under a
        # parent 준칙 number). Mixed provenance -- see per-entry note above each.
        # mirror: casc.org.cn attachment for this one is a legacy .doc, not cleanly re-extractable
        {"no": "해석1", "title": "企业会计准则解释第1号", "url": "https://cas.xmu.edu.cn/info/1673/4544.htm",
         "format": "html", "tier_hint": "본문", "para_style": "section",
         "as_of": "2007-01-01", "provenance": "mirror"},
        # mirror: casc.org.cn attachment for this one is a legacy .doc, not cleanly re-extractable
        {"no": "해석2", "title": "企业会计准则解释第2号", "url": "https://cas.xmu.edu.cn/info/1683/4554.htm",
         "format": "html", "tier_hint": "본문", "para_style": "section",
         "as_of": "2008-01-01", "provenance": "mirror"},
        # mirror: casc.org.cn attachment for this one is a legacy .doc, not cleanly re-extractable
        {"no": "해석3", "title": "企业会计准则解释第3号", "url": "https://cas.xmu.edu.cn/info/1693/4564.htm",
         "format": "html", "tier_hint": "본문", "para_style": "section",
         "as_of": "2009-01-01", "provenance": "mirror"},
        # official: full text inline on the casc.org.cn notice page itself
        {"no": "해석4", "title": "企业会计准则解释第4号", "url": "https://www.casc.org.cn/2010/0809/203868.shtml",
         "format": "html", "tier_hint": "본문", "para_style": "section",
         "as_of": "2010-01-01", "provenance": "official"},
        # official: full text inline on the casc.org.cn notice page itself
        {"no": "해석5", "title": "企业会计准则解释第5号", "url": "https://www.casc.org.cn/2012/1130/203867.shtml",
         "format": "html", "tier_hint": "본문", "para_style": "section",
         "as_of": "2012-01-01", "provenance": "official"},
        # official: full text inline on the casc.org.cn notice page itself
        {"no": "해석6", "title": "企业会计准则解释第6号", "url": "https://www.casc.org.cn/2014/0124/203866.shtml",
         "format": "html", "tier_hint": "본문", "para_style": "section",
         "as_of": "2014-01-01", "provenance": "official"},
        # official: full text inline on the casc.org.cn notice page itself
        {"no": "해석7", "title": "企业会计准则解释第7号", "url": "https://www.casc.org.cn/2015/1113/203865.shtml",
         "format": "html", "tier_hint": "본문", "para_style": "section",
         "as_of": "2015-01-01", "provenance": "official"},
        # official: full text inline on the casc.org.cn notice page itself
        {"no": "해석8", "title": "企业会计准则解释第8号", "url": "https://www.casc.org.cn/2016/0104/203864.shtml",
         "format": "html", "tier_hint": "본문", "para_style": "section",
         "as_of": "2016-01-01", "provenance": "official"},
        # mirror: casc.org.cn attachment for this one is a legacy .doc, not cleanly re-extractable
        {"no": "해석9", "title": "关于权益法下投资净损失的会计处理", "url": "https://cas.xmu.edu.cn/info/1753/4624.htm",
         "format": "html", "tier_hint": "본문", "para_style": "section",
         "as_of": "2017-01-01", "provenance": "mirror"},
        # mirror: casc.org.cn attachment for this one is a legacy .doc, not cleanly re-extractable
        {"no": "해석10", "title": "关于以使用固定资产产生的收入为基础的折旧方法", "url": "https://cas.xmu.edu.cn/info/1763/4634.htm",
         "format": "html", "tier_hint": "본문", "para_style": "section",
         "as_of": "2017-01-01", "provenance": "mirror"},
        # mirror: casc.org.cn attachment for this one is a legacy .doc, not cleanly re-extractable
        {"no": "해석11", "title": "关于以使用无形资产产生的收入为基础的摊销方法", "url": "https://cas.xmu.edu.cn/info/1773/4644.htm",
         "format": "html", "tier_hint": "본문", "para_style": "section",
         "as_of": "2017-01-01", "provenance": "mirror"},
        # mirror: casc.org.cn attachment for this one is a legacy .doc, not cleanly re-extractable
        {"no": "해석12", "title": "关于关键管理人员服务的提供方与接受方是否为关联方", "url": "https://cas.xmu.edu.cn/info/1783/4654.htm",
         "format": "html", "tier_hint": "본문", "para_style": "section",
         "as_of": "2017-01-01", "provenance": "mirror"},
        # mirror: casc.org.cn attachment for this one is a legacy .doc, not cleanly re-extractable
        {"no": "해석13", "title": "企业会计准则解释第13号", "url": "https://cas.xmu.edu.cn/info/1793/4664.htm",
         "format": "html", "tier_hint": "본문", "para_style": "section",
         "as_of": "2020-01-01", "provenance": "mirror"},
        # mirror: casc.org.cn attachment for this one is a legacy .doc, not cleanly re-extractable
        {"no": "해석14", "title": "企业会计准则解释第14号", "url": "https://cas.xmu.edu.cn/info/1803/4674.htm",
         "format": "html", "tier_hint": "본문", "para_style": "section",
         "as_of": "2021-01-01", "provenance": "mirror"},
        # mirror: casc.org.cn attachment for this one is a legacy .doc, not cleanly re-extractable
        {"no": "해석15", "title": "企业会计准则解释第15号", "url": "https://cas.xmu.edu.cn/info/1813/4684.htm",
         "format": "html", "tier_hint": "본문", "para_style": "section",
         "as_of": "2021-01-01", "provenance": "mirror"},
        # official: PDF attachment linked directly from the casc.org.cn notice (via esnai.cn, casc's tech-support CDN)
        {"no": "해석16", "title": "企业会计准则解释第16号", "url": "https://upload-news.esnai.cn/2022/1213/1670930283740.pdf",
         "referer": "https://www.casc.org.cn/2022/1213/236476.shtml",
         "format": "pdf", "tier_hint": "본문", "para_style": "section",
         "as_of": "2022-01-01", "provenance": "official"},
        # official: PDF attachment linked directly from the casc.org.cn notice (via esnai.cn, casc's tech-support CDN)
        {"no": "해석17", "title": "企业会计准则解释第17号", "url": "https://upload-news.esnai.cn/2023/1109/1699509691161.pdf",
         "referer": "https://www.casc.org.cn/2023/1109/248252.shtml",
         "format": "pdf", "tier_hint": "본문", "para_style": "section",
         "as_of": "2023-01-01", "provenance": "official"},
        # official: PDF attachment linked directly from the casc.org.cn notice (via esnai.cn, casc's tech-support CDN)
        {"no": "해석18", "title": "企业会计准则解释第18号", "url": "https://upload-news.esnai.cn/2024/1231/1735613819864.pdf",
         "referer": "https://www.casc.org.cn/2024/1231/266612.shtml",
         "format": "pdf", "tier_hint": "본문", "para_style": "section",
         "as_of": "2024-01-01", "provenance": "official"},
        # official: full text inline on the casc.org.cn notice page itself
        {"no": "해석19", "title": "企业会计准则解释第19号", "url": "https://www.casc.org.cn/2025/1219/278496.shtml",
         "format": "html", "tier_hint": "본문", "para_style": "section",
         "as_of": "2025-01-01", "provenance": "official"},
        # official: full text inline on the casc.org.cn notice page itself
        {"no": "해석20", "title": "企业会计准则解释第20号", "url": "https://www.casc.org.cn/2026/0617/283026.shtml",
         "format": "html", "tier_hint": "본문", "para_style": "section",
         "as_of": "2026-01-01", "provenance": "official"},
        ],
    },
    # VAS (Chuẩn mực kế toán Việt Nam / Vietnamese Accounting Standards) --
    # docs.kreston.vn (Kreston Vietnam, a Kreston International member audit/
    # accounting firm's own "văn bản pháp luật" (legal-document) reference
    # library at docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-NN/), each
    # page a verbatim Vietnamese-language reproduction of the original Bộ Tài
    # chính (Ministry of Finance) Quyết định (Decision) text -- this is the
    # OFFICIAL Vietnamese original (per the task's explicit requirement:
    # verbatim official text, NOT a firm's English translation), confirmed by
    # every one of the 26 downloaded pages opening with its own "(Ban hành và
    # công bố theo Quyết định số .../QĐ-BTC ngày ... của Bộ trưởng Bộ Tài
    # chính...)" citation -- see tools/ingest/segment.py's VAS module comment
    # for the full structural writeup this registry was built against.
    #
    # Enumeration: the complete set of 26 issued VAS (numbers 01-30; 09/12/13/
    # 20 were never issued -- no gap in this registry, this is the complete
    # real set), scraped 2026-07-06, one page per standard. Every standard is
    # traceable to exactly one of 5 promulgating Decisions in 5 issuance
    # batches (đợt), cross-checked against each standard's own in-document
    # citation (and, for đợt 4, against VAS 29's own preamble text literally
    # reading "sáu (06) chuẩn mực kế toán Việt Nam (đợt 4)" -- 6 standards,
    # matching the 6 counted below):
    #   đợt 1 -- 149/2001/QĐ-BTC (2001-12-31): 02, 03, 04, 14            (4)
    #   đợt 2 -- 165/2002/QĐ-BTC (2002-12-31): 01, 06, 10, 15, 16, 24    (6)
    #   đợt 3 -- 234/2003/QĐ-BTC (2003-12-31): 05, 07, 08, 21, 25, 26    (6)
    #   đợt 4 -- 12/2005/QĐ-BTC  (2005-02-15): 17, 22, 23, 27, 28, 29    (6)
    #   đợt 5 -- 100/2005/QĐ-BTC (2005-12-25/28): 11, 18, 19, 30         (4)
    #                                                            total = 26
    # `decision_no`/`decision_date` record each standard's own promulgating
    # Decision. As of the 2026-07-08 source relabel, `decision_no` is what
    # run_ingest.ingest_vas composes into each record's `source_url` citation,
    # "Bộ Tài chính, Quyết định số <no>": the canonical primary-source legal
    # reference for the verbatim official text (Phase 0.2 confirmed the stored
    # text IS that Decision's official VBPL text; Vietnamese law is cited by
    # Decision number, not by URL). The mapping of each standard to its
    # Decision was triple-checked -- this registry (built against each
    # standard's own in-document citation), the kreston page's own self-
    # declared "Ban hành ... theo Quyết định số ..." header, and an
    # independent web re-confirmation of all five đợt (batch) lists (149/2001
    # đợt1, 165/2002 đợt2, 234/2003 đợt3, 12/2005 đợt4, 100/2005 đợt5), all
    # agreeing on which standards each Decision promulgates.
    #   The day-level `decision_date` is deliberately NOT surfaced in the
    # citation: `decision_no` already carries the year and uniquely identifies
    # the Decision, whereas the promulgation day genuinely CONFLICTS across
    # sources -- đợt3 registry says 2003-12-31 but an official Bộ Tài chính
    # circular (via moit.gov.vn) cites "234/2003/QĐ-BTC ngày 30/12/2003", and
    # đợt5 is internally split (VAS 11 recorded 2005-12-25 vs VAS 18/19/30
    # 2005-12-28; the đợt5 note above already flags "2005-12-25/28"). With the
    # authoritative full text bot-blocked here, per 정공법/추측 금지 the
    # citation asserts only the certain identifier (Decision number) and does
    # not commit to a contested day. `decision_date` stays below as recorded
    # provenance (what each source page stated), not as a claim of fact.
    #   The `url` below (docs.kreston.vn/vbpl/... firm mirror) is kept ONLY as
    # retrieval/re-download provenance and is deliberately no longer surfaced
    # as the citation: a competitor audit firm's domain must not stand in for
    # the official issuing authority. (No government deep-link is pinned as
    # source_url either: vbpl.vn full-text pages bot-block this environment
    # and search-returned ItemIDs were noise, so the Decision citation --
    # itself the authoritative reference -- is used rather than an unverified
    # URL.)
    # `as_of` is that same standard's own stated effective date
    # ("có hiệu lực thi hành từ ...") wherever its own page states one. VAS 29
    # and VAS 30's own pages state a decision date but never separately state
    # an effective date anywhere in their own text (confirmed: 0 occurrences
    # of "hiệu lực" in either page's own extracted text referring to the
    # standard's own effective date) -- `as_of` falls back to `decision_date`
    # for exactly these two, noted per-entry below rather than silently
    # guessed from their own batch-mates. VAS 02's own page states an
    # effective date of 2003-01-01 despite being promulgated by the SAME
    # đợt-1 Decision as VAS 03/04/14 (each of which states 2002-01-01) --
    # recorded exactly as VAS 02's own page states it (per 정공법: no
    # cross-standard "correction" of what one standard's own source text
    # actually says), flagged here as a known cross-standard inconsistency in
    # the source rather than silently normalized to match its batch-mates.
    #
    # `format` is "html" (not this GAAP dict's own stale "pdf" default from
    # before this registry was filled in -- every real entry below overrides
    # it) since every VAS source page is trafilatura-extracted HTML, same
    # extract.py path CAS already uses.
    "VAS": {
        "lang": "vi", "format": "html", "base_url": "https://docs.kreston.vn",
        # 발행기관(모든 VAS 공통) — source_url 인용 구성에 사용(ingest_vas).
        "publisher": "Bộ Tài chính",
        "standards": [
            {"no": "01", "title": "Chuẩn mực chung",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-01/",
             "format": "html", "tier": "본문",
             "decision_no": "165/2002/QĐ-BTC", "decision_date": "2002-12-31", "as_of": "2003-01-01"},
            {"no": "02", "title": "Hàng tồn kho",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-02/",
             "format": "html", "tier": "본문",
             "decision_no": "149/2001/QĐ-BTC", "decision_date": "2001-12-31", "as_of": "2003-01-01"},
            {"no": "03", "title": "Tài sản cố định hữu hình",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-03/",
             "format": "html", "tier": "본문",
             "decision_no": "149/2001/QĐ-BTC", "decision_date": "2001-12-31", "as_of": "2002-01-01"},
            {"no": "04", "title": "Tài sản cố định vô hình",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-04/",
             "format": "html", "tier": "본문",
             "decision_no": "149/2001/QĐ-BTC", "decision_date": "2001-12-31", "as_of": "2002-01-01"},
            {"no": "05", "title": "Bất động sản đầu tư",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-05/",
             "format": "html", "tier": "본문",
             "decision_no": "234/2003/QĐ-BTC", "decision_date": "2003-12-31", "as_of": "2004-02-15"},
            {"no": "06", "title": "Thuê tài sản",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-06/",
             "format": "html", "tier": "본문",
             "decision_no": "165/2002/QĐ-BTC", "decision_date": "2002-12-31", "as_of": "2003-01-01"},
            {"no": "07", "title": "Kế toán khoản đầu tư vào công ty liên kết",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-07/",
             "format": "html", "tier": "본문",
             "decision_no": "234/2003/QĐ-BTC", "decision_date": "2003-12-31", "as_of": "2004-02-15"},
            {"no": "08", "title": "Thông tin tài chính về những khoản vốn góp liên doanh",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-08/",
             "format": "html", "tier": "본문",
             "decision_no": "234/2003/QĐ-BTC", "decision_date": "2003-12-31", "as_of": "2004-02-15"},
            {"no": "10", "title": "Ảnh hưởng của việc thay đổi tỷ giá hối đoái",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-10/",
             "format": "html", "tier": "본문",
             "decision_no": "165/2002/QĐ-BTC", "decision_date": "2002-12-31", "as_of": "2003-01-01"},
            {"no": "11", "title": "Hợp nhất kinh doanh",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-11/",
             "format": "html", "tier": "본문",
             "decision_no": "100/2005/QĐ-BTC", "decision_date": "2005-12-25", "as_of": "2006-02-05"},
            {"no": "14", "title": "Doanh thu và thu nhập khác",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-14/",
             "format": "html", "tier": "본문",
             "decision_no": "149/2001/QĐ-BTC", "decision_date": "2001-12-31", "as_of": "2002-01-01"},
            {"no": "15", "title": "Hợp đồng xây dựng",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-15/",
             "format": "html", "tier": "본문",
             "decision_no": "165/2002/QĐ-BTC", "decision_date": "2002-12-31", "as_of": "2003-01-01"},
            {"no": "16", "title": "Chi phí đi vay",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-16/",
             "format": "html", "tier": "본문",
             "decision_no": "165/2002/QĐ-BTC", "decision_date": "2002-12-31", "as_of": "2003-01-01"},
            {"no": "17", "title": "Thuế thu nhập doanh nghiệp",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-17/",
             "format": "html", "tier": "본문",
             "decision_no": "12/2005/QĐ-BTC", "decision_date": "2005-02-15", "as_of": "2005-03-23"},
            {"no": "18", "title": "Các khoản dự phòng, tài sản và nợ tiềm tàng",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-18/",
             "format": "html", "tier": "본문",
             "decision_no": "100/2005/QĐ-BTC", "decision_date": "2005-12-28", "as_of": "2006-02-05"},
            {"no": "19", "title": "Hợp đồng bảo hiểm",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-19/",
             "format": "html", "tier": "본문",
             "decision_no": "100/2005/QĐ-BTC", "decision_date": "2005-12-28", "as_of": "2006-02-05"},
            {"no": "21", "title": "Trình bày Báo cáo tài chính",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-21/",
             "format": "html", "tier": "본문",
             "decision_no": "234/2003/QĐ-BTC", "decision_date": "2003-12-31", "as_of": "2004-02-15"},
            {"no": "22", "title": "Trình bày bổ sung báo cáo tài chính của các ngân hàng và tổ chức tài chính tương tự",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-22/",
             "format": "html", "tier": "본문",
             "decision_no": "12/2005/QĐ-BTC", "decision_date": "2005-02-15", "as_of": "2005-03-23"},
            {"no": "23", "title": "Các sự kiện phát sinh sau ngày kết thúc kỳ kế toán năm",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-23/",
             "format": "html", "tier": "본문",
             "decision_no": "12/2005/QĐ-BTC", "decision_date": "2005-02-15", "as_of": "2005-03-23"},
            {"no": "24", "title": "Báo cáo lưu chuyển tiền tệ",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-24/",
             "format": "html", "tier": "본문",
             "decision_no": "165/2002/QĐ-BTC", "decision_date": "2002-12-31", "as_of": "2003-01-01"},
            {"no": "25", "title": "Báo cáo tài chính hợp nhất và kế toán khoản đầu tư vào công ty con",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-25/",
             "format": "html", "tier": "본문",
             "decision_no": "234/2003/QĐ-BTC", "decision_date": "2003-12-31", "as_of": "2004-02-15"},
            {"no": "26", "title": "Thông tin về các bên liên quan",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-26/",
             "format": "html", "tier": "본문",
             "decision_no": "234/2003/QĐ-BTC", "decision_date": "2003-12-31", "as_of": "2004-02-15"},
            {"no": "27", "title": "Báo cáo tài chính giữa niên độ",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-27/",
             "format": "html", "tier": "본문",
             "decision_no": "12/2005/QĐ-BTC", "decision_date": "2005-02-15", "as_of": "2005-03-23"},
            {"no": "28", "title": "Báo cáo bộ phận",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-28/",
             "format": "html", "tier": "본문",
             "decision_no": "12/2005/QĐ-BTC", "decision_date": "2005-02-15", "as_of": "2005-03-23"},
            # own page states no separate effective date anywhere in its own
            # text -- as_of falls back to decision_date (see registry note above)
            {"no": "29", "title": "Thay đổi chính sách kế toán, ước tính kế toán và các sai sót",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-29/",
             "format": "html", "tier": "본문",
             "decision_no": "12/2005/QĐ-BTC", "decision_date": "2005-02-15", "as_of": "2005-02-15"},
            # own page states no separate effective date anywhere in its own
            # text -- as_of falls back to decision_date (see registry note above)
            {"no": "30", "title": "Lãi trên cổ phiếu",
             "url": "https://docs.kreston.vn/vbpl/ke-toan/chuan-muc-ke-toan/vas-30/",
             "format": "html", "tier": "본문",
             "decision_no": "100/2005/QĐ-BTC", "decision_date": "2005-12-28", "as_of": "2005-12-28"},
        ],
    },
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

def download_cas_url(url, dest, referer=None):
    """Plain GET-download a single CAS source document (casc.org.cn or
    cas.xmu.edu.cn page, or an esnai.cn PDF attachment) to `dest`. Unlike
    KASB, both CAS sources serve every document off an ordinary GET URL --
    no form-POST handler -- so this is a much smaller helper than
    download_kasb. `referer` must be supplied for esnai.cn PDF attachments
    specifically: that CDN 404s on a bare GET with no Referer header
    (anti-hotlink protection) -- every CAS registry entry that needs one
    carries its own "referer" key (the casc.org.cn notice page that links to
    the attachment). Not called during normal test/ingest runs, same
    on-demand-fetching role as download_kasb."""
    import requests  # local import: keep `requests` off the hot import path
    headers = {"User-Agent": "Mozilla/5.0"}
    if referer:
        headers["Referer"] = referer
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        f.write(resp.content)
    return dest
