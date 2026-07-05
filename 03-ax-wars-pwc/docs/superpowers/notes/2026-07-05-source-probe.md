# Task 22 — 소스 입수 가능성 probe 결과 (2026-07-05)

**목적**: GAAP별(K-IFRS, K-GAAP, CAS, VAS, US-GAAP) 기준서 원문이 실제로 내려받아지는지, 어떤 포맷(PDF/HWP/HTML)인지, 구체 접근 경로가 무엇인지 판정한다.

**방법**: `tools/ingest/probe.py` — 소스당 HEAD 1회(거부 시 GET 1회, 헤더만) + 컨트롤 URL(example.com) 1회. 타임아웃 6초, 소스별 graceful failure. **대량 스크래핑·본문 다운로드는 하지 않음**(오케스트레이터 지침: reachability 한정). 따라서 플랜 원안의 "표본 1건 다운로드→extract→chunk→assert_coverage 라운드트립"은 이번 probe에서 **미실시**이며, 각 GAAP 코퍼스 빌드 착수 시(Task 23–26) 첫 단계로 수행한다.

**재실행**: `python tools/ingest/probe.py --json` (03-ax-wars-pwc 루트에서)

## 실측 결과 (2026-07-05 13:20 UTC)

네트워크: **가용** (control example.com → 200)

| GAAP | Probe URL | 도달 | HTTP | Content-Type | 비고 |
|---|---|---|---|---|---|
| K-IFRS | https://www.kasb.or.kr/ | O | 200 | text/html;charset=UTF-8 | HEAD 정상 응답 |
| K-GAAP | https://www.kasb.or.kr/ | O | 200 | text/html;charset=UTF-8 | K-IFRS와 동일 호스트 |
| CAS | http://kjs.mof.gov.cn/ | X | 502 | text/html | https도 동일 502, CDN edge(Cdn Cache Server) 응답 — 호스트 자체는 살아있음 |
| VAS | https://mof.gov.vn/ | O | 200 | text/html | HEAD 정상 응답 |
| US-GAAP | https://asc.fasb.org/ | X | 403 | text/html; charset=UTF-8 | HEAD·GET 모두 403 — 봇 차단 확인 |

## GAAP별 판정

### K-IFRS — 입수 가능 (PDF/HWP)

- **경로**: 한국회계기준원(KASB) `www.kasb.or.kr` > 회계기준 > 한국채택국제회계기준(K-IFRS). 기준서(제1001호~제1117호 등)·해석서가 항목별 목록으로 제공되고, 각 항목에 **PDF(주력)·HWP 첨부파일**이 붙는다.
- **실측**: 호스트 200 정상. 목록/첨부 상세 URL 확정과 로그인 요구 여부(일부 자료)는 Task 23 착수 시 표본 1건(제1116호 리스)으로 확인.
- **Ingest 관점**: 기준서 단위 PDF 다운로드 → `extract.py` PDF 경로. HWP가 유일한 포맷인 항목은 hwp 스킬(kordoc) 경유 변환 검토.

### K-GAAP — 입수 가능 (PDF/HWP)

- **경로**: KASB 동일 호스트 > 일반기업회계기준. **장(章)별 PDF/HWP 첨부**(제1장~제33장 + 부록). 중소기업회계기준도 같은 사이트에서 별도 제공.
- **실측**: K-IFRS와 동일 호스트 200. 리스크 낮음.

### CAS — 입수 가능하나 접속 불안정 (PDF/Word)

- **경로(1차)**: 财政部会计司 `kjs.mof.gov.cn` — 企业会计准则 基本准则 + 42개 具体准则 + 应用指南이 고시문(通知) 페이지의 **PDF/DOC/WPS 첨부**로 제공.
- **경로(2차, 미러)**: 厦门大学 회계 관련 CAS DB(통합본), 中国会计准则委员会 표면. 1차 실패 시 대체.
- **실측**: probe 시점 http/https 모두 **502** (CDN edge가 응답 — DNS/TCP/TLS는 정상, 게이트웨이만 실패). gov.cn 계열의 해외 IP 대상 간헐 차단/불안정으로 판단. **판정: 포맷·경로는 확정, 단 재시도 로직 + 미러 폴백을 ingest에 내장할 것.** 지속 502면 중국 내 접속 경유 또는 미러로 전환.

### VAS — 입수 가능 (영문 PDF 주력 + 베트남어 원문 보조)

- **경로(원문)**: 베트남 MoF — VAS 26종은 2001–2005년 결정문(Decision 149/2001/QD-BTC, 165/2002, 234/2003, 12/2005, 100/2005)으로 공포. 베트남어 원문은 mof.gov.vn 및 법령포털(vbpl.vn, thuvienphapluat.vn)에서 **HTML/DOC**.
- **경로(영문)**: Deloitte·KPMG 등 회계법인이 배포하는 **26 VAS 통합 영문 번역 PDF**(공개 다운로드). 실무 회계제도는 Circular 200/2014/TT-BTC(+133/2016 SME)도 포함 필요.
- **실측**: mof.gov.vn 200 정상. **판정: 영문 통합 PDF를 1차 코퍼스로, 베트남어 원문 HTML을 보조로.**

### US-GAAP (ASC) — 벌크 입수 불가, HIGH RISK 확정

- **경로**: FASB `asc.fasb.org` — Basic View(무료 가입) 로그인 후 **화면 열람 전용 HTML**. 섹션 단위 탐색만 가능, **PDF·벌크 파일 없음**, Professional View는 유료 라이선스.
- **실측**: 비브라우저 요청에 HEAD·GET 모두 **403** — 봇 차단(WAF)이 실제로 걸려 있음을 확인. ToS상 자동수집 금지와 겹쳐 **기술적+법적 이중 차단**.
- **판정**: Basic View 스크래핑은 채택 불가. **플랜 §8 원격 백엔드 예비안 발동 조건 충족** — US-GAAP은 (a) 라이선스/원격 백엔드 경유, (b) 공개 파생자료(XBRL US-GAAP Taxonomy 정의문, SEC 규정) 부분 대체 중 택일. Task 26(ASC)은 이 결정 전까지 후순위 유지.

## 요약 및 후속

| GAAP | 입수 | 포맷 | 다음 액션 |
|---|---|---|---|
| K-IFRS | 가능 | PDF/HWP | 표본 라운드트립 + 목록 URL로 sources.py 채우기 (Task 23) |
| K-GAAP | 가능 | PDF/HWP | 장별 첨부 URL 확정 (Task 24) |
| CAS | 가능(불안정) | PDF/Word | 재시도+미러 폴백 내장, 502 지속 시 미러 전환 (Task 25) |
| VAS | 가능 | PDF(영문)/HTML(원문) | 회계법인 영문 통합 PDF 확보 (Task 25/26 병행) |
| US-GAAP | **불가(벌크)** | HTML 화면 전용 | §8 예비안 결정 후 착수 (Task 26 후순위) |

- probe는 reachability까지만 실측했다. **첫 다운로드 표본의 extract→chunk→assert_coverage 라운드트립**이 각 GAAP 빌드 태스크의 게이트다.
- 이 노트와 `tools/ingest/probe.py`는 커밋하지 않은 상태로 남겨둔다(Task 22 Step 3 커밋은 오케스트레이터 지침에 따라 보류).
