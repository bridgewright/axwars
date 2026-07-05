# 트랙 2: 회계기준 원문 grounded RAG 챗봇 — 설계 스펙

**날짜:** 2026-07-05
**상태:** 설계 확정(사용자 승인 대기 → writing-plans)
**대상 대회:** AX 인재전쟁 · 삼일PwC · Codex 플러그인

## 배경 · 목표

로컬 GAAP/IFRS **규정 원문**을 근거로, Codex가 **할루시네이션 없이 원문 인용으로** 답하는 다국어 회계기준 Q&A를 Codex 플러그인 안에 구현한다.

기존 트랙 1(시산표 → K-IFRS 변환 엔진: Layer 1 계정매핑 + Layer 2 조정)은 **그대로 유지**하되 이번 작업 범위에서 제외한다. 트랙 2는 트랙 1과 **독립된 별도 스킬 + MCP**로 추가한다.

핵심 원칙(사용자 지시): **효율을 위한 임의 요약·해석·범위축소 금지.** 규정은 **원문 그대로 적재·인용**하며, 유일하게 허용되는 제약은 해커톤 하드요건(제출 zip ≤100MB)뿐이다.

## 결정 요약 (확정 로그)

1. **챗봇 = Codex 에이전트 자체 + 로컬 MCP.** 별도 LLM/API키 없음. 스킬이 Codex를 grounded QA 모드로 진입시키고 MCP를 자동 호출.
2. **로컬 MCP.** 전체 원문 + BM25(런타임 생성) + **PQ 압축 벡터 인덱스**를 플러그인에 동봉. 다국어 임베딩 모델은 zip 밖에서 최초 실행 시 다운로드·캐시(런타임엔 질의 1건만 인코딩). 모델 불가 시 BM25 폴백.
3. **100MB = 압축(zip) 기준.** 위 구성으로 ~40–65MB, 여유 있게 충족.
4. **코퍼스 깊이 = 규정 본문 + 적용지침.** 결론도출근거(BC)·예시는 제외("규정 원문"의 정의에 충실 + 검색 정확도).
5. **언어 정책 = 교차언어 검색 + 원어 원문 verbatim 인용 + 한국어 답변, 번역은 "비공식(원문 우선)" 병기.**
6. **저장 형식 = 문단 JSON**(verbatim `text` + 검색용 `text_norm`, 표는 구조보존). MD 강제 아님, 감사용 MD 렌더링은 부가 산출.

## 대상 GAAP (전량)

K-IFRS · 일반기업회계기준(K-GAAP) · US GAAP(ASC) · 중국 CAS(ASBE) · 베트남 VAS. 깊이는 각 기준서의 **본문 + 적용지침**.

## 아키텍처 개요

**컴포넌트(6):**
1. **수집 파이프라인**(빌드타임 1회, `tools/ingest/`): 원문 다운로드 → 추출(PDF/HWP/DOCX/HTML→text) → 문단 청킹 → 메타 포함 정규화 JSON → 임베딩 → PQ 벡터 인덱스.
2. **코퍼스 아티팩트**(동봉, `corpus/`): `*.jsonl.zst`(문단+메타) + `vectors/`(PQ 인덱스 + id맵).
3. **로컬 MCP 서버**(`gaap_standards_mcp/`, stdio): 하이브리드 검색(BM25 런타임 + 벡터 PQ + RRF) 노출.
4. **챗봇 스킬**(`skills/gaap-standards-qa/SKILL.md`): Codex grounded QA 계약.
5. **폴백 검색기**(`gaap_standards_mcp/fallback.py`): 모델/서버 불가 시 내장 BM25 경량 스크립트.
6. **(선택) 인용 뷰어:** 검색된 원문·출처를 보여주는 정적 로컬 페이지.

**질의 흐름:** 한국어 질문 → 스킬이 MCP `search_standards` 호출 → (질의 1건 임베딩 + BM25) → RRF 병합 top-k 원문 문단 → Codex가 그 문단만으로 한국어 답변 + 원어 원문 인용 + 번역병기 → 근거 없으면 "근거 없음".

**빌드 흐름:** 원문 수집 → 청킹 → 임베딩 → PQ 압축 → 동봉. 규정 개정 시 재수집·재색인(각 문단 `as_of` 기록).

## §1. 코퍼스 & 수집

**청킹 = 문단 단위**(인용의 자연 단위). 문단 레코드 스키마:
```
{ id, gaap, standard_no, standard_title, paragraph_no,
  heading, text, text_norm, lang, tier("본문"|"적용지침"),
  source_url, as_of, extract_flag }
```
- `text` = **원문 verbatim**(인용·표시에만 사용). `text_norm` = 정규화(BM25·임베딩 전용).
- 인용 문자열 예: `K-IFRS 제1116호 문단 22`, `ASC 842-20-25-1`, `CAS 제21호`.

**수집처·형식·난이도:**

| GAAP | 수집처 | 형식 | 난이도 |
|---|---|---|---|
| K-IFRS · 일반기준 | kasb.or.kr | PDF/HWP | 중(개별 다운로드) |
| 중국 CAS | 财政部 会计司 · 샤먼대 CAS DB | PDF/word | 낮음 |
| 베트남 VAS | MoF 결정문 · 영문본 | PDF/HTML | 낮음–중 |
| US GAAP ASC | asc.fasb.org Basic View | 온라인 HTML(전문파일 없음) | **높음(스크래핑·세션)** |

**추출 도구(형식별):** PDF=pdfplumber/PyMuPDF(표=pdfplumber/camelot, 스캔=OCR), HWP=hwp5/pyhwp(가능 시 HWPX(XML) 우선, 교차확인용 HWP→PDF), DOCX=python-docx/mammoth, HTML=DOM 타겟 파싱(trafilatura 등, 제너릭 스크래핑 지양).

**ASC 리스크 처리:** ASC만 대량 전문 소스가 없어 Basic View 스크래핑 필요. 구현 순서를 **① 다운로드 쉬운 4종(K-IFRS·일반기준·CAS·VAS)으로 파이프라인 완성·증명 → ② ASC 별도 워크스트림**으로 잡는다(범위 축소가 아니라 순서). ASC를 zip에 깨끗이 담기 어려우면 **그 코퍼스만** 원격 MCP 백엔드로 두는 것을 예비안으로 한다. **플랜 0단계에 각 소스 입수 가능성 실측 probe를 포함.**

## §2. 원문 충실도(fidelity) 가드레일

RAG는 원본파일이 아니라 추출 텍스트를 다루므로 손실 위험은 **추출 단계**와 **잘못된 청킹**에 있다(임베딩·정상 청킹은 저장 원문을 변형하지 않으며, 답변은 저장된 verbatim `text`를 인용). 다음 가드레일로 원문 충실도를 보장한다:

1. **verbatim 저장 + 저장 텍스트만 인용:** `text`(원문) / `text_norm`(검색용) 분리. 검색·임베딩은 `text_norm`, 인용·표시는 언제나 `text`. → 임베딩/청킹이 인용문을 바꿀 수 없게 구조로 강제.
2. **커버리지 라운드트립 대사:** 청킹 후 조각 재결합 vs 원추출 diff, **문자 커버리지 ≥99.5% assert**, 빠진 구간 실패·리포트.
3. **문단정렬 무손실 청킹:** 기준서 문단번호·제목 경계로만 분할. 고정크기 중간절단 금지, 짧은 조각 드롭 금지, 긴 문단은 이어짐 표시하며 둘 다 보존·링크.
4. **추출 품질 게이트:** 모지바케/치환문자() 탐지, 빈 텍스트+시각내용 페이지=스캔/폰트실패 플래그(→OCR), 표 셀 수 검증·구조보존, 머리말·꼬리말 제거 시 삭제 내용 로깅.
5. **이중 추출 교차검증:** 핵심/다인용 기준서는 추출기 2개로 뽑아 diff, 불일치 페이지만 사람이 확인.
6. **출처 딥링크 provenance:** 각 문단 `source_url`+위치+`as_of` → 챗봇 인용을 공식 원문으로 바로 대조 가능(최종 백스톱).
7. **저신뢰 조각 caveat:** `extract_flag`가 선 조각이 인용되면 "추출 검증 필요" 꼬리표.

## §3. 하이브리드 검색

- **BM25**(키워드, `text_norm`): 한국어·중국어는 문자 n-gram 토큰화(무거운 형태소분석기 회피). 동일언어 정확 매칭에 강함.
- **벡터**(의미): 다국어 임베딩으로 질의 런타임 인코딩 → PQ 압축 인덱스 검색. 교차언어(한국어→영·중·베) 담당.
- **병합 = RRF** `score = Σ 1/(k + rank_i)` (k=60 기본): 동일언어=BM25, 교차언어=벡터 기여를 자연 융합.
- **필터:** `gaap`, `standard_no`, `tier`. 기본 `top_k=8`.
- **근거없음 임계:** 최상위 융합점수 임계 미만이면 "무관" 처리 → 챗봇 "근거 없음".
- **임베딩 모델:** 다국어, zip 밖 최초 실행 다운로드·캐시. 기본 후보 **multilingual-e5-small(384d)**, 설정 가능. 못 받으면 벡터 비활성 → BM25-only. (cross-encoder 리랭커는 v1 제외, 향후 옵션.)

## §4. MCP 인터페이스 (로컬 stdio)

```
search_standards(query, gaap?=all, tier?, top_k=8)
  → [{id, gaap, standard_no, paragraph_no, heading,
      text, lang, source_url, as_of, bm25, vec, fused}]
get_paragraph(gaap, standard_no, paragraph_no)   # 정확 문단 원문
get_context(id, window=2)                         # 앞뒤 인접 문단
list_standards(gaap?)                             # 적재 기준서·as_of·문단수(커버리지 투명성)
```
- 서버 기동: `corpus/*.jsonl.zst` + PQ 인덱스 로드, BM25는 기동 시 메모리 구축, 임베딩 모델 캐시 로드(없으면 벡터 비활성 플래그).
- `.mcp.json`에 stdio 실행 커맨드(`python -m gaap_standards_mcp`) 선언 → Codex 자동 기동.

## §5. grounding 계약 (`skills/gaap-standards-qa/SKILL.md`)

Codex에 강제:
1. **선(先)검색:** 회계기준 질문이면 반드시 `search_standards` 먼저. 학습지식으로 답하거나 추측 금지.
2. **원문만 인용:** 반환된 `text`(원문 그대로)만 근거로. 원어 verbatim 인용 뒤 `[출처: K-IFRS 제1116호 문단 22 · source_url]`. 설명은 한국어.
3. **번역병기:** 한국어 번역에 "비공식 번역(원문 우선)" 라벨 — 번역은 참고, 원문이 authoritative.
4. **근거 없음:** 임계 미만·무관이면 "원문에서 근거를 찾지 못함" 명시, 지어내지 않음.
5. **다관할 비교:** 여러 GAAP 질의 시 각 GAAP 원문 나란히 인용(교차언어 그대로).
6. **caveat:** 추출 플래그된 조각·번역엔 꼬리표. BM25-only 폴백 중이면 고지.
7. **(선택) 인용 뷰어:** 검색된 원문·출처 링크 정적 로컬 페이지(선택 산출).

## §6. 패키징 · 용량 · 폴백

**zip 레이아웃:**
```
src/
├── .codex-plugin/plugin.json          # 갱신(스킬·MCP 추가)
├── .mcp.json                          # 로컬 stdio MCP 선언
├── skills/
│   ├── gaap-ifrs-converter/SKILL.md   # 트랙 1(유지)
│   └── gaap-standards-qa/SKILL.md     # 트랙 2(신규)
├── gaap-ifrs/                         # 트랙 1 엔진(유지)
├── gaap_standards_mcp/                # 트랙 2 MCP(server·search·index·fallback)
├── corpus/                            # *.jsonl.zst + vectors/(PQ)
└── tools/ingest/                      # 빌드타임 파이프라인
```
**용량(zip):** 텍스트(zstd) ~30–50MB + PQ 벡터 ~5–15MB + 코드 <2MB = **~40–65MB**. 모델은 zip 밖. **CI에서 zip ≤100MB assert.**

**폴백 3단계:**
1. **Full(기본):** MCP + 모델 → BM25+벡터 교차언어 하이브리드
2. **Degraded:** MCP + 모델 없음 → BM25-only(동일언어), 챗봇 고지
3. **No-MCP:** 서버 불가 → 내장 BM25 경량 스크립트 직접 실행(같은 corpus), 완전 자체완결

## §7. 테스트 · 검증

- **원문 무손실:** 기준서별 라운드트립 커버리지 ≥99.5% assert, 모지바케/빈페이지 탐지, 이중추출 diff, 알려진 문단 verbatim 스냅샷.
- **검색 품질:** known-item(동일언어 + 교차언어 한국어질의→영/중 원문 top-k), RRF가 단일 검색기 대비 개선 회귀.
- **grounding:** 답변이 인용 문단 밖 내용 없는지(인용 커버리지), "근거 없음" 경로, 임계 동작.
- **폴백:** 모델 없음/서버 없음 시뮬 → 각 tier 동작.
- **용량·MCP 계약:** zip ≤100MB, 도구 4종 입출력 스키마.

## §8. 범위 밖 / 향후

트랙 1 basis를 이 MCP 원문으로 대체(통합), BC·예시 적재, cross-encoder 리랭커, 원격 MCP 호스팅, 자체 LLM 웹챗봇 — 향후. ASC가 zip에 깨끗이 안 담기면 그 코퍼스만 원격 백엔드.

## 미해결 리스크

- **ASC 입수:** 대량 전문 소스 부재 → 스크래핑 필요(플랜 0단계 probe로 실측, 최악 시 원격 백엔드).
- **채점 환경 네트워크:** 최초 실행 모델 다운로드가 막히면 Degraded(BM25-only) 자동 동작 — 데모는 성립하되 교차언어 약화.
- **HWP 추출 품질:** 한글 문서 추출 신뢰도 편차 → 이중추출·라운드트립 게이트로 방어.
