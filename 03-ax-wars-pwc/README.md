# pwc-gaap-ifrs-suite — GAAP↔K-IFRS 스위트 (AX 인재전쟁 · 삼일PwC)

삼일PwC Assurance의 회계기준 전환·조회 자문을 위한 Codex/Claude Code 플러그인. 한 플러그인에 독립적인 두 트랙을 묶는다.

| 트랙 | 무엇을 하나 | 핵심 디렉터리 |
|---|---|---|
| **트랙 1** | 소스 GAAP(K-GAAP·VAS·CAS·US GAAP) 시산표 → K-IFRS 변환 엔진. 재무제표·전환조정 명세서(기준서 인용)·영향분석을 산출 | `gaap-ifrs/`, `skills/gaap-ifrs-converter/`, `examples/` |
| **트랙 2** | K-IFRS 원문 grounded RAG 챗봇. 로컬 MCP 하이브리드(BM25+벡터) 검색으로, 검색된 문단 verbatim 인용 없이는 답하지 않음 | `gaap_standards_mcp/`, `tools/ingest/`, `corpus/`, `skills/gaap-standards-qa/` |

두 트랙은 독립 실행되지만 같은 문제 — "회계기준 전환·조회에서 로컬 GAAP과 IFRS를 둘 다 아는 희소 시니어에 의존"— 를 다른 각도로 푼다. 트랙 1은 정해진 6개 측정조정을 확정 답으로 자동화하고, 트랙 2는 정해지지 않은 어떤 조항이든 원문 검색으로 대응한다.

## 설치

Python 3.11+.

```bash
pip install -e .                    # 트랙 2 (gaap-standards-mcp): mcp, rank-bm25, faiss-cpu, sentence-transformers, zstandard
cd gaap-ifrs && pip install -e .    # 트랙 1 (gaap-ifrs): openpyxl만 의존
```

## 실행

**트랙 1 — 변환 엔진:**
```bash
gaap-ifrs convert --input tb.xlsx --source-gaap K-GAAP --extra adjustments.json --out out/
```
완성 예제는 `examples/{kgaap,usgaap,vas,cas}/`(입력+출력 동봉). 세부는 `gaap-ifrs/README.md`, `skills/gaap-ifrs-converter/SKILL.md` 참조.

**트랙 2 — 로컬 MCP 서버(stdio):**
```bash
python -m gaap_standards_mcp        # .mcp.json에 Codex/Claude Code용으로 등록되어 있음
```
MCP 클라이언트 없이 직접 조회(자동 full/degraded/no-mcp 판별):
```bash
python -m gaap_standards_mcp.entry corpus "리스 사용권자산 인식"
```
세부(코퍼스 빌드, 3단 폴백, 용량 제약)는 `README_track2.md`, `skills/gaap-standards-qa/SKILL.md` 참조.

## 코퍼스

`corpus/`에 K-IFRS 63개 기준서·6,137문단(`manifest.json`, 2025-01-01 기준)이 zstd 압축 원문(`kifrs.jsonl.zst`)과 faiss PQ 벡터 인덱스(`vectors/index.faiss` + `vectors/id_map.json`)로 동봉되어 있다. 재빌드:
```bash
python -m tools.ingest.run_ingest --gaap K-IFRS --download-dir downloads --corpus-dir corpus
```

## 테스트

```bash
PYTHONPATH=. python -m pytest -q       # 트랙 2: 60 케이스 (BM25·벡터·RRF융합·MCP 4도구·3단 폴백·corpus·manifest 등)
cd gaap-ifrs && python -m pytest -q    # 트랙 1: 34 케이스 (파싱·매핑·조정 6종·명세·영향·CLI·검증기)
```

## 정직한 스코프

- 트랙 1은 K-GAAP·US GAAP·CAS·VAS 4개 소스 GAAP의 **계정 매핑·조정 규칙**을 지원한다(`gaap-ifrs/gaap_ifrs/data/*.json`).
- 트랙 2의 **원문 검색 코퍼스는 현재 K-IFRS만** 적재되어 있다(`corpus/manifest.json`). K-GAAP(일반기업회계기준)·CAS·VAS 원문 코퍼스는 미착수 — 수집 파이프라인(`tools/ingest/`) 자체는 GAAP-무관으로 설계돼 확장 가능하지만, 실제 다운로드·추출·충실도 검증은 K-IFRS만 완료했다. US GAAP 원문은 별도 라이선스가 필요해 원격 확장 지점으로 남겨둔다.
- 임베딩 모델(`intfloat/multilingual-e5-small`)은 용량 문제로 zip에 포함하지 않는다. 최초 실행 시 캐시로 내려받으며, 실패 시 자동으로 BM25 단독(degraded) 검색으로 동작한다.
- 두 트랙의 산출물은 모두 **전문가 검토용 초안**이며 감사의견·법적 효력을 갖지 않는다.
