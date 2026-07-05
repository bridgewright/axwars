# 트랙 2 — 회계기준 원문 grounded RAG 챗봇

로컬 GAAP/IFRS 규정 원문(K-IFRS · K-GAAP(일반기업회계기준) · US-GAAP · CAS · VAS)을 하이브리드(BM25+벡터) 검색으로 서빙하는 **로컬 MCP 서버**와, Codex가 **원문 인용으로만** 답하는 grounded QA 스킬. 트랙 1 변환엔진(`gaap-ifrs/`)과는 독립이다.

## 아키텍처

```
[빌드타임]  tools/ingest/  : 원문 다운로드 → 형식별 추출 → 문단정렬 청킹
                             → 충실도 검증(라운드트립 ≥99.5%) → 임베딩 + faiss PQ
                             → corpus/ 산출(동봉 아티팩트)
[산출물]    corpus/        : {kifrs,kgaap,cas,vas,usgaap}.jsonl.zst
                             + vectors/{index.faiss,id_map.json} + manifest.json
[런타임]    gaap_standards_mcp/ : stdio MCP 서버 — BM25 + 벡터(RRF 융합) 하이브리드 검색
[스킬]      skills/gaap-standards-qa/SKILL.md : grounded QA 계약(원문 verbatim 인용)
```

- **검색:** BM25(문자 n-gram, 기동 시 구축) + faiss PQ 벡터(`intfloat/multilingual-e5-small`, 교차언어)를 RRF로 병합.
- **원문 충실도:** 인용·표시는 항상 verbatim `text` 필드. 검색·임베딩만 `text_norm` 사용. 원문 임의 요약·해석 금지.
- **MCP 도구 4종:** `search_standards`(하이브리드 검색), `get_paragraph`(특정 문단 원문), `get_context`(앞뒤 인접 문단), `list_standards`(적재 커버리지).

## 설치

Python 3.11+ 필요.

```bash
pip install -e .
```

의존성: `mcp`(FastMCP), `rank-bm25`, `numpy`, `faiss-cpu`, `sentence-transformers`, `zstandard`. 수집(빌드타임)에는 추가로 `PyMuPDF`/`pdfplumber`, `pyhwp`, `python-docx`, `trafilatura`를 쓴다.

## 코퍼스 빌드 (빌드타임, 선택)

동봉된 `corpus/`가 이미 있으면 이 단계는 생략한다. 재빌드는 GAAP별로:

```bash
python -m tools.ingest.run_ingest --gaap K-IFRS --download-dir downloads --corpus-dir corpus
```

추출 → 문단정렬 청킹 → 충실도 게이트(라운드트립 커버리지·모지바케) → `corpus/*.jsonl.zst` + `corpus/vectors/` + `corpus/manifest.json` 패킹까지 수행한다.

## MCP 서버 실행

stdio MCP 서버 기동:

```bash
python -m gaap_standards_mcp
```

코퍼스 위치는 환경변수 `GAAP_CORPUS_DIR`로 지정(기본: 패키지 옆 `corpus/`). 클라이언트 등록은 `.mcp.json`에 선언되어 있다:

```json
{
  "mcpServers": {
    "gaap-standards": {
      "command": "python",
      "args": ["-m", "gaap_standards_mcp"],
      "env": {"GAAP_CORPUS_DIR": "corpus"}
    }
  }
}
```

Codex에서는 `skills/gaap-standards-qa` 스킬이 `search_standards`를 먼저 호출해 원문 문단을 확보한 뒤, verbatim 인용 + 출처(`[출처: {gaap} 제{standard_no}호 문단 {paragraph_no} · {source_url}]`)로 답한다. 근거가 없으면 "근거 없음"으로 답하고 지어내지 않는다.

## 폴백 3단계

| 단계 | 조건 | 동작 |
|---|---|---|
| **full** | MCP + 벡터 인덱스 + 임베딩 모델 정상 | BM25 + 벡터 하이브리드(RRF) 검색 |
| **degraded** | 임베딩 모델/벡터 인덱스 불가 | BM25 단독 검색(교차언어 리콜 저하 고지) |
| **no-mcp** | MCP 서버 자체 불가 | 내장 경량 BM25 검색기 직접 호출 |

no-mcp 경로(스킬이 부르는 진입 스크립트, `mode`를 함께 반환):

```bash
python -m gaap_standards_mcp.entry corpus "리스부채 인식"
```

BM25 단독 검색기 직접 호출:

```bash
python -m gaap_standards_mcp.fallback corpus "리스부채 인식"
```

## 용량

- 제출 zip **≤100MB**(압축 기준).
- 코퍼스는 zstd 압축(`corpus/*.jsonl.zst`), 벡터 인덱스는 faiss **PQ 양자화**로 소형화.
- 임베딩 모델(`intfloat/multilingual-e5-small`)은 zip에 **넣지 않는다** — 최초 실행 시 캐시로 다운로드하며, 다운로드 불가 환경에서는 자동으로 **degraded**(BM25 단독)로 동작한다.

## 테스트

```bash
python -m pytest -q
```
