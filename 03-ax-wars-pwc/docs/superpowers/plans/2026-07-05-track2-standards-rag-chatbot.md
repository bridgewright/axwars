# 회계기준 원문 grounded RAG 챗봇 (트랙 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 로컬 GAAP/IFRS 규정 원문을 하이브리드(BM25+벡터) 검색으로 서빙하는 로컬 MCP와, Codex가 원문 인용으로 할루시네이션 없이 답하는 grounded QA 스킬을 Codex 플러그인에 추가한다(트랙 1 변환엔진은 불간섭).

**Architecture:** 빌드타임 수집 파이프라인(`tools/ingest/`)이 원문을 문단 JSON + PQ 벡터 인덱스로 만들어 `corpus/`에 동봉한다. 런타임 로컬 MCP 서버(`gaap_standards_mcp/`)가 stdio로 `search_standards` 등 4개 도구를 노출하고, 스킬(`skills/gaap-standards-qa/`)이 Codex를 grounded QA 계약으로 진입시킨다. 모델/서버 불가 시 내장 BM25로 3단계 폴백한다.

**Tech Stack:** Python 3.11+, `mcp`(FastMCP, stdio), `rank_bm25`+numpy, `faiss-cpu`(PQ), `sentence-transformers`(multilingual-e5-small, 최초실행 다운로드), `zstandard`(코퍼스 압축), 추출: `pdfplumber`/`PyMuPDF`·`pyhwp`/`hwp5`·`python-docx`·`trafilatura`.

## Global Constraints

- 작업 루트: `03-ax-wars-pwc/`. 트랙 1(`gaap-ifrs/`)은 읽지도 고치지도 않는다.
- 제출 zip **≤100MB**(압축 기준). 임베딩 모델은 zip에 넣지 않는다(최초 실행 시 캐시로 다운로드).
- **원문 임의 요약·해석·범위축소 금지.** 인용·표시는 항상 verbatim `text` 필드. 검색·임베딩만 `text_norm` 사용.
- 코퍼스 깊이 = **규정 본문 + 적용지침**. BC·예시 제외.
- 언어: 교차언어 검색, 원어 원문 인용, 한국어 답변, 번역은 "비공식(원문 우선)" 라벨.
- 문서 강조는 bold만(이탤릭 금지).
- 커밋: `03-ax-wars-pwc/`를 독립 git 저장소로 두고 이 폴더 안에서만 커밋(상위 레포 오염 금지).
- TDD: 각 스텝은 실패 테스트 → 확인 → 최소구현 → 통과 → 커밋.

## Parallelization for ultracode

- **Phase A(코어 검색 라이브러리)** Task 2–8: 서로 독립 → 병렬 가능(공유 계약은 Task 1 schema).
- **Phase B(수집 파이프라인)** Task 9–14: 대부분 독립 → 병렬 가능.
- **Phase C(MCP·폴백)** Task 15–18: Phase A에 의존, 내부는 순차.
- **Phase D(스킬·플러그인 배선)** Task 19–21: Phase C에 의존.
- **Phase E(실데이터 코퍼스 빌드)** Task 22–26: Phase B에 의존, GAAP별 병렬(단 ASC는 후순위).
- **Phase F(패키징·통합)** Task 27–29: 전부 의존, 순차.

## File Structure

```
03-ax-wars-pwc/
├── gaap_standards_mcp/            # 런타임 MCP 서버 패키지
│   ├── __init__.py
│   ├── __main__.py                # python -m gaap_standards_mcp → stdio MCP
│   ├── schema.py                  # Record 데이터클래스 + 상수
│   ├── normalize.py               # text_norm + 문자 n-gram 토크나이저
│   ├── corpus.py                  # *.jsonl.zst 로드/조회
│   ├── bm25.py                    # BM25 인덱스(기동 시 구축)
│   ├── vectors.py                 # faiss PQ 로드 + 질의 임베딩(lazy) + available 플래그
│   ├── fusion.py                  # RRF 병합
│   ├── search.py                  # 하이브리드 검색 오케스트레이션 + 임계
│   ├── server.py                  # FastMCP 도구 4종
│   └── fallback.py                # No-MCP 경량 BM25 검색기(CLI/함수)
├── tools/ingest/                  # 빌드타임 파이프라인
│   ├── __init__.py
│   ├── sources.py                 # GAAP별 소스 레지스트리
│   ├── extract.py                 # 형식별 추출 → Page(text, page_no, locator)
│   ├── chunk.py                   # 문단정렬 청킹 → Record
│   ├── fidelity.py                # 라운드트립 커버리지·모지바케·이중추출 diff
│   ├── embed_index.py             # 임베딩 + faiss PQ 빌드
│   ├── pack.py                    # corpus/*.jsonl.zst + vectors/ + manifest.json
│   └── run_ingest.py              # GAAP별 CLI 오케스트레이터
├── corpus/                        # 빌드 산출(동봉 아티팩트)
│   ├── {kifrs,kgaap,cas,vas,usgaap}.jsonl.zst
│   ├── vectors/{index.faiss,id_map.json}
│   └── manifest.json
├── skills/gaap-standards-qa/SKILL.md
├── viewer/index.html              # (선택) 정적 인용 뷰어
├── .mcp.json
├── .codex-plugin/plugin.json      # 갱신
├── pyproject.toml                 # gaap-standards-mcp 패키지 + deps
└── tests/                         # pytest + fixtures
```

---

## Phase A — 코어 검색 라이브러리

### Task 1: 패키지 스캐폴드 + Record 스키마

**Files:**
- Create: `gaap_standards_mcp/__init__.py`, `gaap_standards_mcp/schema.py`
- Create: `pyproject.toml`, `tests/__init__.py`
- Test: `tests/test_schema.py`

**Interfaces:**
- Produces: `Record` dataclass, `GAAPS: list[str]`, `TIERS: list[str]`, `Record.from_dict`, `Record.to_dict`.

- [ ] **Step 1: git init(최초 1회) + 실패 테스트**

```bash
cd 03-ax-wars-pwc && [ -d .git ] || git init
```

`tests/test_schema.py`:
```python
from gaap_standards_mcp.schema import Record, GAAPS, TIERS

def test_record_roundtrip():
    r = Record(id="kifrs:1116:22", gaap="K-IFRS", standard_no="1116",
               standard_title="리스", paragraph_no="22", heading="인식",
               text="리스이용자는 리스개시일에 사용권자산과 리스부채를 인식한다.",
               text_norm="리스이용자는 리스개시일에 사용권자산과 리스부채를 인식한다",
               lang="ko", tier="본문", source_url="https://kasb.or.kr/x",
               as_of="2025-01-01", extract_flag=False)
    assert Record.from_dict(r.to_dict()) == r
    assert r.gaap in GAAPS and r.tier in TIERS
```

- [ ] **Step 2: 실패 확인** — Run: `cd 03-ax-wars-pwc && python -m pytest tests/test_schema.py -v` · Expected: FAIL(ImportError)

- [ ] **Step 3: 최소구현**

`gaap_standards_mcp/__init__.py`: (빈 파일)

`gaap_standards_mcp/schema.py`:
```python
from dataclasses import dataclass, asdict

GAAPS = ["K-IFRS", "K-GAAP", "US-GAAP", "CAS", "VAS"]
TIERS = ["본문", "적용지침"]

@dataclass(frozen=True)
class Record:
    id: str
    gaap: str
    standard_no: str
    standard_title: str
    paragraph_no: str
    heading: str
    text: str          # 원문 verbatim — 인용·표시 전용
    text_norm: str     # 정규화 — 검색·임베딩 전용
    lang: str
    tier: str
    source_url: str
    as_of: str
    extract_flag: bool = False

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)
```

`pyproject.toml`:
```toml
[project]
name = "gaap-standards-mcp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["mcp>=1.2", "rank-bm25>=0.2.2", "numpy>=1.26",
                "faiss-cpu>=1.8", "sentence-transformers>=3.0", "zstandard>=0.22"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_schema.py -v` · Expected: PASS

- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat(track2): package scaffold + Record schema"`

### Task 2: 정규화 + 문자 n-gram 토크나이저

**Files:** Create `gaap_standards_mcp/normalize.py` · Test `tests/test_normalize.py`

**Interfaces:**
- Produces: `normalize_text(s: str) -> str`, `char_ngrams(s: str, n_min=2, n_max=3) -> list[str]`, `tokenize(s: str) -> list[str]`(라틴 단어는 공백분해, CJK는 n-gram).

- [ ] **Step 1: 실패 테스트**

```python
from gaap_standards_mcp.normalize import normalize_text, char_ngrams, tokenize

def test_normalize_collapses_ws_and_strips_punct_tail():
    assert normalize_text("리스부채를  인식한다.\n") == "리스부채를 인식한다"

def test_char_ngrams_cjk():
    assert "리스" in char_ngrams("리스부채")
    assert "리스부" in char_ngrams("리스부채")

def test_tokenize_mixes_latin_words_and_cjk_ngrams():
    toks = tokenize("ASC 842 리스")
    assert "asc" in toks and "842" in toks and "리스" in toks
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_normalize.py -v` · Expected: FAIL

- [ ] **Step 3: 최소구현**

```python
import re, unicodedata

_WS = re.compile(r"\s+")
_CJK = re.compile(r"[　-鿿가-힯]")
_LATIN = re.compile(r"[A-Za-z0-9]+")

def normalize_text(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = _WS.sub(" ", s).strip()
    return s.rstrip(".。·").strip()

def char_ngrams(s: str, n_min=2, n_max=3) -> list[str]:
    cjk = "".join(ch for ch in s if _CJK.match(ch))
    out = []
    for n in range(n_min, n_max + 1):
        out += [cjk[i:i+n] for i in range(len(cjk) - n + 1)]
    return out

def tokenize(s: str) -> list[str]:
    s = normalize_text(s).lower()
    return _LATIN.findall(s) + char_ngrams(s)
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_normalize.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat(track2): normalize + cjk ngram tokenizer"`

### Task 3: BM25 인덱스

**Files:** Create `gaap_standards_mcp/bm25.py` · Test `tests/test_bm25.py`

**Interfaces:**
- Consumes: `Record`, `tokenize`.
- Produces: `BM25Index(records: list[Record])`, `.search(query: str, top_k=8, gaap=None, tier=None) -> list[tuple[int, float]]`(반환 idx는 records 인덱스, 점수 내림차순).

- [ ] **Step 1: 실패 테스트**

```python
from gaap_standards_mcp.schema import Record
from gaap_standards_mcp.bm25 import BM25Index

def _r(i, gaap, text):
    return Record(id=str(i), gaap=gaap, standard_no="x", standard_title="",
                  paragraph_no=str(i), heading="", text=text, text_norm=text,
                  lang="ko", tier="본문", source_url="", as_of="", extract_flag=False)

def test_bm25_ranks_and_filters():
    recs = [_r(0,"K-IFRS","사용권자산과 리스부채를 인식한다"),
            _r(1,"K-IFRS","재고자산은 저가법으로 측정한다"),
            _r(2,"US-GAAP","operating lease right-of-use asset")]
    idx = BM25Index(recs)
    top = idx.search("리스부채 인식", top_k=2)
    assert top[0][0] == 0
    only_us = idx.search("lease", top_k=5, gaap="US-GAAP")
    assert all(recs[i].gaap == "US-GAAP" for i, _ in only_us)
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_bm25.py -v` · Expected: FAIL

- [ ] **Step 3: 최소구현**

```python
from rank_bm25 import BM25Okapi
from .normalize import tokenize

class BM25Index:
    def __init__(self, records):
        self.records = records
        self._tok = [tokenize(r.text_norm) for r in records]
        self._bm25 = BM25Okapi(self._tok) if records else None

    def search(self, query, top_k=8, gaap=None, tier=None):
        if not self._bm25:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        cand = []
        for i, s in enumerate(scores):
            r = self.records[i]
            if gaap and r.gaap != gaap:
                continue
            if tier and r.tier != tier:
                continue
            if s > 0:
                cand.append((i, float(s)))
        cand.sort(key=lambda x: x[1], reverse=True)
        return cand[:top_k]
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_bm25.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat(track2): BM25 index with gaap/tier filter"`

### Task 4: RRF 병합

**Files:** Create `gaap_standards_mcp/fusion.py` · Test `tests/test_fusion.py`

**Interfaces:**
- Produces: `rrf_merge(rankings: list[list[int]], k=60) -> list[tuple[int, float]]`(각 ranking은 idx의 순위 리스트, 융합점수 내림차순 반환).

- [ ] **Step 1: 실패 테스트**

```python
from gaap_standards_mcp.fusion import rrf_merge

def test_rrf_rewards_agreement():
    # idx 5는 두 랭킹 모두 상위 → 1위
    bm = [5, 1, 2]
    vec = [5, 9, 1]
    merged = rrf_merge([bm, vec], k=60)
    assert merged[0][0] == 5
    assert [i for i, _ in merged].count(5) == 1  # 중복 없음
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_fusion.py -v` · Expected: FAIL

- [ ] **Step 3: 최소구현**

```python
def rrf_merge(rankings, k=60):
    scores = {}
    for ranking in rankings:
        for rank, idx in enumerate(ranking):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_fusion.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat(track2): reciprocal rank fusion"`

### Task 5: 코퍼스 로더 (jsonl.zst)

**Files:** Create `gaap_standards_mcp/corpus.py` · Test `tests/test_corpus.py`

**Interfaces:**
- Consumes: `Record`.
- Produces: `write_jsonl_zst(records, path)`, `load_corpus(corpus_dir) -> list[Record]`, `get_paragraph(records, gaap, standard_no, paragraph_no) -> Record|None`, `get_context(records, id, window=2) -> list[Record]`, `list_standards(records, gaap=None) -> list[dict]`.

- [ ] **Step 1: 실패 테스트**

```python
from gaap_standards_mcp.schema import Record
from gaap_standards_mcp import corpus

def _r(gaap, std, para, text):
    return Record(id=f"{gaap}:{std}:{para}", gaap=gaap, standard_no=std,
                  standard_title="t", paragraph_no=para, heading="", text=text,
                  text_norm=text, lang="ko", tier="본문", source_url="",
                  as_of="2025-01-01", extract_flag=False)

def test_write_load_and_queries(tmp_path):
    recs = [_r("K-IFRS","1116",str(p),f"문단 {p}") for p in (21,22,23)]
    corpus.write_jsonl_zst(recs, tmp_path / "kifrs.jsonl.zst")
    loaded = corpus.load_corpus(tmp_path)
    assert len(loaded) == 3
    assert corpus.get_paragraph(loaded, "K-IFRS", "1116", "22").text == "문단 22"
    ctx = corpus.get_context(loaded, "K-IFRS:1116:22", window=1)
    assert [r.paragraph_no for r in ctx] == ["21", "22", "23"]
    ls = corpus.list_standards(loaded, "K-IFRS")
    assert ls[0]["standard_no"] == "1116" and ls[0]["paragraphs"] == 3
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_corpus.py -v` · Expected: FAIL

- [ ] **Step 3: 최소구현**

```python
import json, glob, os
import zstandard as zstd
from .schema import Record

def write_jsonl_zst(records, path):
    data = "\n".join(json.dumps(r.to_dict(), ensure_ascii=False) for r in records)
    with open(path, "wb") as f:
        f.write(zstd.ZstdCompressor(level=19).compress(data.encode("utf-8")))

def load_corpus(corpus_dir):
    out = []
    for p in sorted(glob.glob(os.path.join(corpus_dir, "*.jsonl.zst"))):
        with open(p, "rb") as f:
            raw = zstd.ZstdDecompressor().decompress(f.read()).decode("utf-8")
        out += [Record.from_dict(json.loads(line)) for line in raw.splitlines() if line]
    return out

def get_paragraph(records, gaap, standard_no, paragraph_no):
    for r in records:
        if r.gaap == gaap and r.standard_no == standard_no and r.paragraph_no == paragraph_no:
            return r
    return None

def get_context(records, id, window=2):
    idx = next((i for i, r in enumerate(records) if r.id == id), None)
    if idx is None:
        return []
    base = records[idx]
    same = [r for r in records if r.gaap == base.gaap and r.standard_no == base.standard_no]
    pos = same.index(base)
    return same[max(0, pos - window): pos + window + 1]

def list_standards(records, gaap=None):
    agg = {}
    for r in records:
        if gaap and r.gaap != gaap:
            continue
        key = (r.gaap, r.standard_no)
        a = agg.setdefault(key, {"gaap": r.gaap, "standard_no": r.standard_no,
                                 "standard_title": r.standard_title, "as_of": r.as_of,
                                 "paragraphs": 0})
        a["paragraphs"] += 1
    return sorted(agg.values(), key=lambda x: (x["gaap"], x["standard_no"]))
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_corpus.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat(track2): corpus loader + paragraph/context/list queries"`

### Task 6: 벡터 인덱스 (faiss PQ, lazy 모델)

**Files:** Create `gaap_standards_mcp/vectors.py` · Test `tests/test_vectors.py`

**Interfaces:**
- Produces: `VectorIndex(index_path, id_map_path, model_name="intfloat/multilingual-e5-small")`, 속성 `.available: bool`, 메서드 `.search(query: str, top_k=8) -> list[tuple[str, float]]`(반환은 record **id**, 점수). 모델/인덱스 없으면 `.available=False`, `.search` → `[]`. 질의는 e5 규약 `"query: "` 프리픽스.
- Produces(빌드용): `embed_passages(texts: list[str], model_name) -> np.ndarray`(패시지엔 `"passage: "` 프리픽스), `build_pq_index(vecs: np.ndarray) -> faiss.Index`.

- [ ] **Step 1: 실패 테스트** (모델 없이도 도는 폴백 경로 우선 검증)

```python
from gaap_standards_mcp.vectors import VectorIndex

def test_missing_index_is_unavailable(tmp_path):
    vi = VectorIndex(tmp_path / "nope.faiss", tmp_path / "nope.json")
    assert vi.available is False
    assert vi.search("리스") == []
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_vectors.py -v` · Expected: FAIL

- [ ] **Step 3: 최소구현**

```python
import json, os
import numpy as np

_MODEL_CACHE = {}

def _load_model(name):
    if name not in _MODEL_CACHE:
        from sentence_transformers import SentenceTransformer  # lazy: 최초 실행 시 다운로드
        _MODEL_CACHE[name] = SentenceTransformer(name)
    return _MODEL_CACHE[name]

def embed_passages(texts, model_name="intfloat/multilingual-e5-small"):
    m = _load_model(model_name)
    return np.asarray(m.encode([f"passage: {t}" for t in texts], normalize_embeddings=True), dtype="float32")

def build_pq_index(vecs):
    import faiss
    d = vecs.shape[1]
    m = 48 if d % 48 == 0 else 32
    index = faiss.index_factory(d, f"PQ{m}", faiss.METRIC_INNER_PRODUCT)
    index.train(vecs)
    index.add(vecs)
    return index

class VectorIndex:
    def __init__(self, index_path, id_map_path, model_name="intfloat/multilingual-e5-small"):
        self.model_name = model_name
        self._index = None
        self._ids = None
        self.available = False
        try:
            if os.path.exists(index_path) and os.path.exists(id_map_path):
                import faiss
                self._index = faiss.read_index(str(index_path))
                self._ids = json.load(open(id_map_path, encoding="utf-8"))
                self.available = True
        except Exception:
            self.available = False

    def search(self, query, top_k=8):
        if not self.available:
            return []
        try:
            m = _load_model(self.model_name)
            q = np.asarray(m.encode([f"query: {query}"], normalize_embeddings=True), dtype="float32")
            D, I = self._index.search(q, top_k)
            return [(self._ids[i], float(d)) for d, i in zip(D[0], I[0]) if i >= 0]
        except Exception:
            return []
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_vectors.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat(track2): faiss PQ vector index with lazy model + graceful unavailable"`

### Task 7: 하이브리드 검색 오케스트레이션

**Files:** Create `gaap_standards_mcp/search.py` · Test `tests/test_search.py`

**Interfaces:**
- Consumes: `BM25Index`, `VectorIndex`, `rrf_merge`, `Record`.
- Produces: `HybridSearcher(records, bm25, vectors, threshold=0.0)`, `.search(query, gaap=None, tier=None, top_k=8) -> list[dict]`. 각 dict = record.to_dict() + `{"bm25":float,"vec":float,"fused":float}`. 벡터 unavailable이면 BM25 단독. 융합 최고점이 `threshold` 미만이면 `[]`(근거없음).

- [ ] **Step 1: 실패 테스트**

```python
from gaap_standards_mcp.schema import Record
from gaap_standards_mcp.bm25 import BM25Index
from gaap_standards_mcp.search import HybridSearcher

class _StubVec:
    available = True
    def __init__(self, ranked): self.ranked = ranked
    def search(self, q, top_k=8): return self.ranked

def _r(i, text):
    return Record(id=str(i), gaap="K-IFRS", standard_no="1116", standard_title="",
                  paragraph_no=str(i), heading="", text=text, text_norm=text,
                  lang="ko", tier="본문", source_url="", as_of="", extract_flag=False)

def test_hybrid_merges_bm25_and_vectors():
    recs = [_r(0,"리스부채 인식"), _r(1,"재고 저가법"), _r(2,"사용권자산")]
    bm = BM25Index(recs)
    vec = _StubVec([("2", 0.9), ("0", 0.8)])
    hs = HybridSearcher(recs, bm, vec)
    hits = hs.search("리스부채", top_k=3)
    assert hits and "fused" in hits[0] and hits[0]["bm25"] >= 0

def test_bm25_only_when_vectors_unavailable():
    recs = [_r(0,"리스부채 인식")]
    class _Off: available = False; search = lambda self,q,top_k=8: []
    hs = HybridSearcher(recs, BM25Index(recs), _Off())
    assert hs.search("리스부채")[0]["id"] == "0"
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_search.py -v` · Expected: FAIL

- [ ] **Step 3: 최소구현**

```python
from .fusion import rrf_merge

class HybridSearcher:
    def __init__(self, records, bm25, vectors, threshold=0.0):
        self.records = records
        self.bm25 = bm25
        self.vectors = vectors
        self.threshold = threshold
        self._id_to_idx = {r.id: i for i, r in enumerate(records)}

    def search(self, query, gaap=None, tier=None, top_k=8):
        pool = max(top_k * 4, 20)
        bm_hits = self.bm25.search(query, top_k=pool, gaap=gaap, tier=tier)
        bm_rank = [i for i, _ in bm_hits]
        bm_score = {i: s for i, s in bm_hits}
        rankings = [bm_rank]
        vec_score = {}
        if self.vectors.available:
            for rid, s in self.vectors.search(query, top_k=pool):
                idx = self._id_to_idx.get(rid)
                if idx is None:
                    continue
                r = self.records[idx]
                if gaap and r.gaap != gaap:
                    continue
                if tier and r.tier != tier:
                    continue
                vec_score[idx] = s
            rankings.append(list(vec_score.keys()))
        fused = rrf_merge(rankings)
        if not fused or fused[0][1] < self.threshold:
            return []
        out = []
        for idx, fs in fused[:top_k]:
            d = self.records[idx].to_dict()
            d.update(bm25=bm_score.get(idx, 0.0), vec=vec_score.get(idx, 0.0), fused=fs)
            out.append(d)
        return out
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_search.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat(track2): hybrid searcher (bm25+vectors+rrf, threshold, filters)"`

### Task 8: 폴백 검색기 (No-MCP)

**Files:** Create `gaap_standards_mcp/fallback.py` · Test `tests/test_fallback.py`

**Interfaces:**
- Consumes: `load_corpus`, `BM25Index`.
- Produces: `fallback_search(corpus_dir, query, gaap=None, tier=None, top_k=8) -> list[dict]`(BM25 단독, record.to_dict()+`bm25`), CLI `python -m gaap_standards_mcp.fallback <corpus_dir> "<query>"`.

- [ ] **Step 1: 실패 테스트**

```python
from gaap_standards_mcp.schema import Record
from gaap_standards_mcp import corpus, fallback

def test_fallback_bm25_only(tmp_path):
    recs = [Record(id="K-IFRS:1116:22", gaap="K-IFRS", standard_no="1116",
                   standard_title="리스", paragraph_no="22", heading="", 
                   text="사용권자산과 리스부채를 인식한다",
                   text_norm="사용권자산과 리스부채를 인식한다", lang="ko",
                   tier="본문", source_url="", as_of="", extract_flag=False)]
    corpus.write_jsonl_zst(recs, tmp_path / "kifrs.jsonl.zst")
    hits = fallback.fallback_search(tmp_path, "리스부채", top_k=3)
    assert hits[0]["id"] == "K-IFRS:1116:22" and "bm25" in hits[0]
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_fallback.py -v` · Expected: FAIL

- [ ] **Step 3: 최소구현**

```python
import sys, json
from .corpus import load_corpus
from .bm25 import BM25Index

def fallback_search(corpus_dir, query, gaap=None, tier=None, top_k=8):
    records = load_corpus(str(corpus_dir))
    bm = BM25Index(records)
    out = []
    for i, s in bm.search(query, top_k=top_k, gaap=gaap, tier=tier):
        d = records[i].to_dict()
        d["bm25"] = s
        out.append(d)
    return out

if __name__ == "__main__":
    corpus_dir, query = sys.argv[1], sys.argv[2]
    print(json.dumps(fallback_search(corpus_dir, query), ensure_ascii=False, indent=2))
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_fallback.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat(track2): No-MCP fallback bm25 search"`

---

## Phase B — 수집 파이프라인 (빌드타임)

### Task 9: 소스 레지스트리

**Files:** Create `tools/ingest/__init__.py`, `tools/ingest/sources.py` · Test `tests/test_sources.py`

**Interfaces:**
- Produces: `SOURCES: dict[str, dict]` — GAAP별 `{lang, format, base_url, standards: list[{no,title,url,tier_hint}]}`. `get_source(gaap) -> dict`.

- [ ] **Step 1: 실패 테스트**

```python
from tools.ingest.sources import SOURCES, get_source

def test_sources_cover_all_gaaps():
    assert set(SOURCES) == {"K-IFRS","K-GAAP","US-GAAP","CAS","VAS"}
    assert get_source("K-IFRS")["lang"] == "ko"
    assert all("standards" in v for v in SOURCES.values())
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_sources.py -v` · Expected: FAIL

- [ ] **Step 3: 최소구현** — 각 GAAP 레지스트리 초기 골격(실 URL은 Task 22 probe에서 채움; 지금은 lang/format/base_url + 빈 standards 리스트 허용, K-IFRS는 예시 1건 포함).

```python
SOURCES = {
    "K-IFRS": {"lang": "ko", "format": "pdf", "base_url": "https://www.kasb.or.kr",
               "standards": [{"no": "1116", "title": "리스", "url": "", "tier_hint": "본문"}]},
    "K-GAAP": {"lang": "ko", "format": "pdf", "base_url": "https://www.kasb.or.kr", "standards": []},
    "US-GAAP": {"lang": "en", "format": "html", "base_url": "https://asc.fasb.org", "standards": []},
    "CAS": {"lang": "zh", "format": "pdf", "base_url": "http://kjs.mof.gov.cn", "standards": []},
    "VAS": {"lang": "vi", "format": "pdf", "base_url": "", "standards": []},
}

def get_source(gaap):
    return SOURCES[gaap]
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_sources.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat(track2): source registry skeleton"`

### Task 10: 형식별 추출기

**Files:** Create `tools/ingest/extract.py` · Test `tests/test_extract.py` · Fixtures `tests/fixtures/sample.{pdf,html}`

**Interfaces:**
- Produces: `@dataclass Page(text, page_no, locator)`, `extract(path, fmt) -> list[Page]`. fmt in {pdf, hwp, docx, html}. PDF는 PyMuPDF, HTML은 trafilatura, docx는 python-docx, hwp는 hwp5. 빈 텍스트+비어있지 않은 원본 페이지는 `Page.text=""`로 두되 상위(fidelity)가 플래그.

- [ ] **Step 1: 실패 테스트** (HTML 픽스처로 결정론 검증; PDF/HWP는 통합단계에서 실파일)

```python
from tools.ingest.extract import extract, Page

def test_extract_html(tmp_path):
    p = tmp_path / "s.html"
    p.write_text("<html><body><p>리스부채를 인식한다</p></body></html>", encoding="utf-8")
    pages = extract(p, "html")
    assert isinstance(pages[0], Page)
    assert "리스부채" in pages[0].text
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_extract.py -v` · Expected: FAIL

- [ ] **Step 3: 최소구현**

```python
from dataclasses import dataclass

@dataclass
class Page:
    text: str
    page_no: int
    locator: str

def extract(path, fmt):
    path = str(path)
    if fmt == "pdf":
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        return [Page(page.get_text("text"), i + 1, f"page={i+1}") for i, page in enumerate(doc)]
    if fmt == "html":
        import trafilatura
        html = open(path, encoding="utf-8").read()
        txt = trafilatura.extract(html, include_tables=True) or ""
        return [Page(txt, 1, path)]
    if fmt == "docx":
        import docx
        d = docx.Document(path)
        txt = "\n".join(p.text for p in d.paragraphs)
        return [Page(txt, 1, path)]
    if fmt == "hwp":
        import subprocess
        txt = subprocess.run(["hwp5txt", path], capture_output=True, text=True).stdout
        return [Page(txt, 1, path)]
    raise ValueError(f"unknown fmt: {fmt}")
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_extract.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat(track2): per-format extractors"`

### Task 11: 문단정렬 청킹

**Files:** Create `tools/ingest/chunk.py` · Test `tests/test_chunk.py`

**Interfaces:**
- Consumes: `Page`, `Record`, `normalize_text`.
- Produces: `chunk_pages(pages, gaap, standard_no, standard_title, lang, source_url, as_of, tier="본문", para_pattern=DEFAULT_PARA_RE) -> list[Record]`. 문단번호 정규식 경계로 분할, 각 조각 `text`(verbatim)·`text_norm` 채움, `id=f"{gaap_slug}:{standard_no}:{paragraph_no}"`. 번호 없는 선두 텍스트는 `paragraph_no="0"`.

- [ ] **Step 1: 실패 테스트**

```python
from tools.ingest.extract import Page
from tools.ingest.chunk import chunk_pages

def test_chunk_splits_on_paragraph_numbers():
    text = "22 리스이용자는 사용권자산을 인식한다.\n23 리스부채는 현재가치로 측정한다."
    recs = chunk_pages([Page(text, 1, "p1")], "K-IFRS", "1116", "리스", "ko",
                       "https://x", "2025-01-01")
    assert [r.paragraph_no for r in recs] == ["22", "23"]
    assert recs[0].text.startswith("22") and "사용권자산" in recs[0].text
    assert recs[0].id == "kifrs:1116:22"
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_chunk.py -v` · Expected: FAIL

- [ ] **Step 3: 최소구현**

```python
import re
from gaap_standards_mcp.schema import Record
from gaap_standards_mcp.normalize import normalize_text

DEFAULT_PARA_RE = re.compile(r"(?m)^\s*((?:\d+[A-Z]?)(?:\.\d+)*)\s+")
_SLUG = {"K-IFRS": "kifrs", "K-GAAP": "kgaap", "US-GAAP": "usgaap", "CAS": "cas", "VAS": "vas"}

def chunk_pages(pages, gaap, standard_no, standard_title, lang, source_url, as_of,
                tier="본문", para_pattern=DEFAULT_PARA_RE):
    full = "\n".join(p.text for p in pages)
    marks = list(para_pattern.finditer(full))
    recs = []
    slug = _SLUG[gaap]
    if not marks:
        text = full.strip()
        if text:
            recs.append(_mk(slug, gaap, standard_no, standard_title, "0", text, lang, tier, source_url, as_of))
        return recs
    if marks[0].start() > 0:
        lead = full[:marks[0].start()].strip()
        if lead:
            recs.append(_mk(slug, gaap, standard_no, standard_title, "0", lead, lang, tier, source_url, as_of))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(full)
        para_no = m.group(1)
        text = full[m.start():end].strip()
        recs.append(_mk(slug, gaap, standard_no, standard_title, para_no, text, lang, tier, source_url, as_of))
    return recs

def _mk(slug, gaap, std, title, para, text, lang, tier, url, as_of):
    return Record(id=f"{slug}:{std}:{para}", gaap=gaap, standard_no=std, standard_title=title,
                  paragraph_no=para, heading="", text=text, text_norm=normalize_text(text),
                  lang=lang, tier=tier, source_url=url, as_of=as_of, extract_flag=False)
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_chunk.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat(track2): paragraph-aligned chunking"`

### Task 12: 충실도 가드레일

**Files:** Create `tools/ingest/fidelity.py` · Test `tests/test_fidelity.py`

**Interfaces:**
- Consumes: `Page`, `Record`.
- Produces: `roundtrip_coverage(raw_text, records) -> float`(재결합 문자 커버리지 0~1), `detect_mojibake(text) -> bool`, `detect_empty_pages(pages) -> list[int]`, `assert_coverage(raw_text, records, min_cov=0.995)`(미달 시 `FidelityError`), `dual_extract_diff(a: str, b: str) -> float`.

- [ ] **Step 1: 실패 테스트**

```python
import pytest
from tools.ingest.extract import Page
from tools.ingest.chunk import chunk_pages
from tools.ingest.fidelity import roundtrip_coverage, detect_mojibake, assert_coverage, FidelityError

def test_roundtrip_full_coverage():
    text = "22 사용권자산을 인식한다.\n23 리스부채를 측정한다."
    recs = chunk_pages([Page(text,1,"p")], "K-IFRS","1116","리스","ko","u","2025-01-01")
    assert roundtrip_coverage(text, recs) >= 0.995
    assert_coverage(text, recs)  # no raise

def test_mojibake_and_low_coverage():
    assert detect_mojibake("리스�부채") is True
    with pytest.raises(FidelityError):
        assert_coverage("가"*1000, [])
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_fidelity.py -v` · Expected: FAIL

- [ ] **Step 3: 최소구현**

```python
import re

class FidelityError(Exception):
    pass

_WS = re.compile(r"\s+")

def _canon(s):
    return _WS.sub("", s)

def roundtrip_coverage(raw_text, records):
    raw = _canon(raw_text)
    if not raw:
        return 1.0
    joined = _canon("".join(r.text for r in records))
    # 멀티셋 교집합 근사: 재결합 길이 / 원문 길이(정규화 공백 제거)
    return min(len(joined), len(raw)) / len(raw)

def detect_mojibake(text):
    return "�" in text or text.count("�") > 0

def detect_empty_pages(pages):
    return [p.page_no for p in pages if not p.text.strip()]

def assert_coverage(raw_text, records, min_cov=0.995):
    cov = roundtrip_coverage(raw_text, records)
    if cov < min_cov:
        raise FidelityError(f"coverage {cov:.4f} < {min_cov}")

def dual_extract_diff(a, b):
    ca, cb = _canon(a), _canon(b)
    if not ca and not cb:
        return 0.0
    import difflib
    return 1.0 - difflib.SequenceMatcher(None, ca, cb).ratio()
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_fidelity.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat(track2): fidelity guardrails (roundtrip/mojibake/dual-diff)"`

### Task 13: 임베딩 + PQ 인덱스 빌드

**Files:** Create `tools/ingest/embed_index.py` · Test `tests/test_embed_index.py`

**Interfaces:**
- Consumes: `Record`, `embed_passages`, `build_pq_index`.
- Produces: `build_vectors(records, out_dir, model_name=...)` → `out_dir/index.faiss` + `out_dir/id_map.json`(records 순서의 id 리스트). 임베딩은 `record.text_norm` 대상.

- [ ] **Step 1: 실패 테스트** (모델 무거우니 monkeypatch로 embed 대체)

```python
import numpy as np, json
from gaap_standards_mcp.schema import Record
from tools.ingest import embed_index

def _r(i):
    return Record(id=f"K-IFRS:1116:{i}", gaap="K-IFRS", standard_no="1116", standard_title="",
                  paragraph_no=str(i), heading="", text=f"문단{i}", text_norm=f"문단{i}",
                  lang="ko", tier="본문", source_url="", as_of="", extract_flag=False)

def test_build_vectors(tmp_path, monkeypatch):
    recs = [_r(i) for i in range(40)]
    monkeypatch.setattr(embed_index, "embed_passages",
                        lambda texts, model_name=None: np.random.RandomState(0).rand(len(texts), 96).astype("float32"))
    embed_index.build_vectors(recs, tmp_path)
    assert (tmp_path / "index.faiss").exists()
    ids = json.load(open(tmp_path / "id_map.json", encoding="utf-8"))
    assert ids[0] == "K-IFRS:1116:0" and len(ids) == 40
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_embed_index.py -v` · Expected: FAIL

- [ ] **Step 3: 최소구현**

```python
import json, os
import faiss
from gaap_standards_mcp.vectors import embed_passages, build_pq_index

def build_vectors(records, out_dir, model_name="intfloat/multilingual-e5-small"):
    os.makedirs(out_dir, exist_ok=True)
    vecs = embed_passages([r.text_norm for r in records], model_name=model_name)
    index = build_pq_index(vecs)
    faiss.write_index(index, os.path.join(str(out_dir), "index.faiss"))
    json.dump([r.id for r in records], open(os.path.join(str(out_dir), "id_map.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_embed_index.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat(track2): embed + PQ index build"`

### Task 14: 패킹 + manifest + 오케스트레이터

**Files:** Create `tools/ingest/pack.py`, `tools/ingest/run_ingest.py` · Test `tests/test_pack.py`

**Interfaces:**
- Consumes: `write_jsonl_zst`, `build_vectors`, `Record`.
- Produces: `pack(records_by_gaap: dict[str, list[Record]], corpus_dir)` → GAAP별 `*.jsonl.zst`, 전체 합쳐 `vectors/`, `manifest.json`({as_of, gaap별 standard·문단수}). `run_ingest.py`는 CLI(`python -m tools.ingest.run_ingest --gaap K-IFRS`)로 추출→청킹→충실도검증→누적.

- [ ] **Step 1: 실패 테스트**

```python
import json
from gaap_standards_mcp.schema import Record
from gaap_standards_mcp import corpus
from tools.ingest import pack as packmod

def _r(g, p):
    return Record(id=f"{g}:1:{p}", gaap=g, standard_no="1", standard_title="t", paragraph_no=str(p),
                  heading="", text=f"t{p}", text_norm=f"t{p}", lang="ko", tier="본문",
                  source_url="", as_of="2025-01-01", extract_flag=False)

def test_pack_writes_corpus_and_manifest(tmp_path, monkeypatch):
    import numpy as np
    from tools.ingest import embed_index
    monkeypatch.setattr(embed_index, "embed_passages",
                        lambda texts, model_name=None: np.random.RandomState(0).rand(len(texts),96).astype("float32"))
    data = {"K-IFRS": [_r("K-IFRS", p) for p in range(40)]}
    packmod.pack(data, tmp_path)
    assert corpus.load_corpus(tmp_path)  # jsonl.zst 로드됨
    man = json.load(open(tmp_path / "manifest.json", encoding="utf-8"))
    assert man["gaaps"]["K-IFRS"]["paragraphs"] == 40
    assert (tmp_path / "vectors" / "index.faiss").exists()
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_pack.py -v` · Expected: FAIL

- [ ] **Step 3: 최소구현**

`tools/ingest/pack.py`:
```python
import os, json
from gaap_standards_mcp.corpus import write_jsonl_zst
from gaap_standards_mcp.schema import Record  # noqa: F401
from .embed_index import build_vectors

_SLUG = {"K-IFRS": "kifrs", "K-GAAP": "kgaap", "US-GAAP": "usgaap", "CAS": "cas", "VAS": "vas"}

def pack(records_by_gaap, corpus_dir):
    os.makedirs(corpus_dir, exist_ok=True)
    all_records = []
    manifest = {"gaaps": {}}
    for gaap, recs in records_by_gaap.items():
        write_jsonl_zst(recs, os.path.join(str(corpus_dir), f"{_SLUG[gaap]}.jsonl.zst"))
        all_records += recs
        stds = {r.standard_no for r in recs}
        manifest["gaaps"][gaap] = {"standards": sorted(stds), "paragraphs": len(recs),
                                   "as_of": recs[0].as_of if recs else ""}
    build_vectors(all_records, os.path.join(str(corpus_dir), "vectors"))
    json.dump(manifest, open(os.path.join(str(corpus_dir), "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
```

`tools/ingest/run_ingest.py`:
```python
import argparse, os
from .sources import get_source
from .extract import extract
from .chunk import chunk_pages
from .fidelity import assert_coverage
from .pack import pack

def ingest_gaap(gaap, download_dir):
    src = get_source(gaap)
    records = []
    for std in src["standards"]:
        path = os.path.join(download_dir, f"{gaap}_{std['no']}.{src['format']}")
        if not os.path.exists(path):
            continue
        pages = extract(path, src["format"])
        recs = chunk_pages(pages, gaap, std["no"], std["title"], src["lang"],
                           std["url"], std.get("as_of", ""), tier=std.get("tier_hint", "본문"))
        assert_coverage("\n".join(p.text for p in pages), recs)
        records += recs
    return records

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gaap", required=True)
    ap.add_argument("--download-dir", default="downloads")
    ap.add_argument("--corpus-dir", default="corpus")
    a = ap.parse_args()
    recs = ingest_gaap(a.gaap, a.download_dir)
    pack({a.gaap: recs}, a.corpus_dir)
    print(f"{a.gaap}: {len(recs)} paragraphs")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_pack.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat(track2): pack + manifest + ingest orchestrator"`

---

## Phase C — MCP 서버 + 배선

### Task 15: MCP 서버 (FastMCP 도구 4종)

**Files:** Create `gaap_standards_mcp/server.py`, `gaap_standards_mcp/__main__.py` · Test `tests/test_mcp_tools.py`

**Interfaces:**
- Consumes: `load_corpus`, `BM25Index`, `VectorIndex`, `HybridSearcher`, `get_paragraph`, `get_context`, `list_standards`.
- Produces: 순수 함수 `make_app(corpus_dir) -> (app, ctx)` 및 내부 핸들러 `_search/_get_paragraph/_get_context/_list`(테스트는 핸들러 직접 호출). `__main__`은 stdio 실행.

- [ ] **Step 1: 실패 테스트** (핸들러 로직만 검증, stdio 미기동)

```python
from gaap_standards_mcp.schema import Record
from gaap_standards_mcp import corpus, server

def _seed(tmp_path):
    recs = [Record(id="K-IFRS:1116:22", gaap="K-IFRS", standard_no="1116", standard_title="리스",
                   paragraph_no="22", heading="", text="사용권자산과 리스부채를 인식한다",
                   text_norm="사용권자산과 리스부채를 인식한다", lang="ko", tier="본문",
                   source_url="u", as_of="2025-01-01", extract_flag=False)]
    corpus.write_jsonl_zst(recs, tmp_path / "kifrs.jsonl.zst")

def test_handlers(tmp_path):
    _seed(tmp_path)
    ctx = server.Context(str(tmp_path))
    hits = ctx.search("리스부채", top_k=3)
    assert hits[0]["standard_no"] == "1116"
    assert ctx.get_paragraph("K-IFRS","1116","22")["text"].startswith("사용권자산")
    assert ctx.list_standards("K-IFRS")[0]["paragraphs"] == 1
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_mcp_tools.py -v` · Expected: FAIL

- [ ] **Step 3: 최소구현**

`gaap_standards_mcp/server.py`:
```python
import os
from .corpus import load_corpus, get_paragraph, get_context, list_standards
from .bm25 import BM25Index
from .vectors import VectorIndex
from .search import HybridSearcher

class Context:
    def __init__(self, corpus_dir):
        self.records = load_corpus(corpus_dir)
        bm = BM25Index(self.records)
        vec = VectorIndex(os.path.join(corpus_dir, "vectors", "index.faiss"),
                          os.path.join(corpus_dir, "vectors", "id_map.json"))
        self.searcher = HybridSearcher(self.records, bm, vec)
        self.vectors_available = vec.available

    def search(self, query, gaap=None, tier=None, top_k=8):
        return self.searcher.search(query, gaap=gaap, tier=tier, top_k=top_k)

    def get_paragraph(self, gaap, standard_no, paragraph_no):
        r = get_paragraph(self.records, gaap, standard_no, paragraph_no)
        return r.to_dict() if r else None

    def get_context(self, id, window=2):
        return [r.to_dict() for r in get_context(self.records, id, window)]

    def list_standards(self, gaap=None):
        return list_standards(self.records, gaap)

def make_app(corpus_dir):
    from mcp.server.fastmcp import FastMCP
    ctx = Context(corpus_dir)
    app = FastMCP("gaap-standards")

    @app.tool()
    def search_standards(query: str, gaap: str = None, tier: str = None, top_k: int = 8) -> list:
        """회계기준 원문을 하이브리드 검색해 문단(원문 verbatim)+출처를 반환."""
        return ctx.search(query, gaap, tier, top_k)

    @app.tool()
    def get_paragraph(gaap: str, standard_no: str, paragraph_no: str) -> dict:
        """특정 기준서 문단의 원문을 정확히 반환."""
        return ctx.get_paragraph(gaap, standard_no, paragraph_no)

    @app.tool()
    def get_context(id: str, window: int = 2) -> list:
        """해당 문단의 앞뒤 인접 문단을 반환."""
        return ctx.get_context(id, window)

    @app.tool()
    def list_standards(gaap: str = None) -> list:
        """적재된 기준서·문단수·as_of(커버리지 투명성)를 반환."""
        return ctx.list_standards(gaap)

    return app, ctx
```

`gaap_standards_mcp/__main__.py`:
```python
import os
from .server import make_app

if __name__ == "__main__":
    corpus_dir = os.environ.get("GAAP_CORPUS_DIR",
                                os.path.join(os.path.dirname(__file__), "..", "corpus"))
    app, _ = make_app(corpus_dir)
    app.run()  # stdio
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_mcp_tools.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat(track2): FastMCP server with 4 tools"`

### Task 16: `.mcp.json` + `.codex-plugin/plugin.json` 갱신

**Files:** Create `.mcp.json` · Modify `.codex-plugin/plugin.json`(없으면 트랙1 zip에서 재사용) · Test `tests/test_manifests.py`

**Interfaces:** Produces: 유효한 JSON 매니페스트.

- [ ] **Step 1: 실패 테스트**

```python
import json
def test_mcp_json_declares_stdio():
    m = json.load(open(".mcp.json", encoding="utf-8"))
    s = m["mcpServers"]["gaap-standards"]
    assert s["command"] == "python" and s["args"] == ["-m", "gaap_standards_mcp"]

def test_plugin_json_valid():
    p = json.load(open(".codex-plugin/plugin.json", encoding="utf-8"))
    assert p["name"] and "keywords" in p
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_manifests.py -v` · Expected: FAIL

- [ ] **Step 3: 최소구현**

`.mcp.json`:
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

`.codex-plugin/plugin.json`:
```json
{
  "name": "pwc-gaap-ifrs-suite",
  "version": "0.2.0",
  "description": "삼일PwC GAAP→IFRS 스위트: (트랙1) 시산표 K-IFRS 변환 엔진 + (트랙2) 회계기준 원문 grounded RAG 챗봇(로컬 MCP 하이브리드 검색). 원문 인용으로 할루시네이션 없이 답한다.",
  "author": {"name": "AX 인재전쟁 · 삼일PwC 세션"},
  "keywords": ["IFRS","K-IFRS","GAAP전환","회계기준","RAG","MCP","원문검색","삼일PwC"]
}
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_manifests.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat(track2): mcp.json + plugin.json manifests"`

### Task 17: MCP stdio 스모크 테스트

**Files:** Test `tests/test_mcp_smoke.py`

**Interfaces:** Consumes: `make_app`. 실제 stdio 왕복 대신 FastMCP in-memory 클라이언트로 도구 호출 확인.

- [ ] **Step 1: 실패 테스트**

```python
import anyio
from gaap_standards_mcp.schema import Record
from gaap_standards_mcp import corpus, server

def test_tool_listing(tmp_path):
    recs = [Record(id="K-IFRS:1116:22", gaap="K-IFRS", standard_no="1116", standard_title="리스",
                   paragraph_no="22", heading="", text="리스부채를 인식한다",
                   text_norm="리스부채를 인식한다", lang="ko", tier="본문",
                   source_url="u", as_of="2025-01-01", extract_flag=False)]
    corpus.write_jsonl_zst(recs, tmp_path / "kifrs.jsonl.zst")
    app, _ = server.make_app(str(tmp_path))

    async def go():
        tools = await app.list_tools()
        return {t.name for t in tools}
    names = anyio.run(go)
    assert {"search_standards","get_paragraph","get_context","list_standards"} <= names
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_mcp_smoke.py -v` · Expected: FAIL(도구 등록/네이밍 이슈 시)
- [ ] **Step 3: 최소구현** — Task 15의 `make_app`이 이미 도구를 등록. 실패 시 도구명·데코레이터만 조정.
- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_mcp_smoke.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "test(track2): mcp stdio tool-listing smoke"`

### Task 18: 폴백 감지 배선 (스킬이 부를 진입 스크립트)

**Files:** Create `gaap_standards_mcp/entry.py` · Test `tests/test_entry.py`

**Interfaces:**
- Produces: `answer_query(corpus_dir, query, gaap=None, top_k=8) -> dict` — MCP Context 생성 시도, 성공하면 `{"mode":"full"|"degraded","hits":[...]}` (degraded = 벡터 unavailable), Context 생성 실패(임포트/파일 오류) 시 `fallback_search`로 `{"mode":"no-mcp","hits":[...]}`.

- [ ] **Step 1: 실패 테스트**

```python
from gaap_standards_mcp.schema import Record
from gaap_standards_mcp import corpus, entry

def test_entry_degraded_without_vectors(tmp_path):
    recs = [Record(id="K-IFRS:1116:22", gaap="K-IFRS", standard_no="1116", standard_title="리스",
                   paragraph_no="22", heading="", text="리스부채를 인식한다",
                   text_norm="리스부채를 인식한다", lang="ko", tier="본문",
                   source_url="u", as_of="2025-01-01", extract_flag=False)]
    corpus.write_jsonl_zst(recs, tmp_path / "kifrs.jsonl.zst")  # vectors/ 없음
    res = entry.answer_query(str(tmp_path), "리스부채")
    assert res["mode"] in ("degraded", "no-mcp")
    assert res["hits"][0]["standard_no"] == "1116"
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_entry.py -v` · Expected: FAIL

- [ ] **Step 3: 최소구현**

```python
import json, sys
from .fallback import fallback_search

def answer_query(corpus_dir, query, gaap=None, top_k=8):
    try:
        from .server import Context
        ctx = Context(corpus_dir)
        hits = ctx.search(query, gaap=gaap, top_k=top_k)
        return {"mode": "full" if ctx.vectors_available else "degraded", "hits": hits}
    except Exception:
        return {"mode": "no-mcp", "hits": fallback_search(corpus_dir, query, gaap=gaap, top_k=top_k)}

if __name__ == "__main__":
    print(json.dumps(answer_query(sys.argv[1], sys.argv[2]), ensure_ascii=False, indent=2))
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_entry.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat(track2): entry with 3-tier degradation"`

---

## Phase D — 스킬 · 뷰어

### Task 19: grounding 스킬 `SKILL.md`

**Files:** Create `skills/gaap-standards-qa/SKILL.md` · Test `tests/test_skill_md.py`

**Interfaces:** Produces: 프론트매터(name/description) + grounding 계약 7조 본문.

- [ ] **Step 1: 실패 테스트**

```python
def test_skill_md_has_contract():
    t = open("skills/gaap-standards-qa/SKILL.md", encoding="utf-8").read()
    assert t.startswith("---") and "name: gaap-standards-qa" in t
    for kw in ["search_standards", "근거를 찾지 못함", "비공식 번역", "출처"]:
        assert kw in t
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_skill_md.py -v` · Expected: FAIL

- [ ] **Step 3: 최소구현** — `skills/gaap-standards-qa/SKILL.md`:
```markdown
---
name: gaap-standards-qa
description: 회계기준(K-IFRS·일반기준·US GAAP·중국 CAS·베트남 VAS) 원문 질의응답. "이 계정 IFRS에서 어떻게", "리스 어떻게 인식", "US GAAP과 차이", "CAS 규정" 등 회계기준 규정을 물으면 반드시 이 스킬로 MCP를 검색해 원문 인용으로 답한다.
---

# 회계기준 원문 Q&A (grounded)

회계기준 규정 질문에는 **반드시 아래 계약을 지킨다. 추측·학습지식으로 답하지 않는다.**

1. **선(先)검색:** 먼저 MCP `search_standards(query, gaap?, tier?, top_k)`를 호출한다. (MCP 불가 시 `python -m gaap_standards_mcp.entry corpus "<질문>"`.)
2. **원문만 근거:** 반환된 문단의 `text`(원어 원문 그대로)만 근거로 답한다. 인용은 verbatim, 인용 끝에 `[출처: {gaap} 제{standard_no}호 문단 {paragraph_no} · {source_url}]`.
3. **한국어 답변 + 번역병기:** 설명은 한국어. 원어 인용에 한국어 번역을 달 때 **"비공식 번역(원문 우선)"** 라벨을 붙인다.
4. **근거 없음:** 검색 결과가 없거나 무관하면 **"원문에서 근거를 찾지 못했습니다(근거 없음)"** 라고 답하고 지어내지 않는다.
5. **다관할 비교:** 여러 GAAP을 물으면 각 GAAP 원문을 나란히 인용한다.
6. **caveat:** 결과에 `extract_flag=true`인 문단이 있으면 "추출 검증 필요" 꼬리표를, `mode`가 `degraded`/`no-mcp`면 "키워드(BM25) 검색만 동작 중"임을 고지한다.
7. **커버리지 정직:** 특정 기준서가 적재됐는지 물으면 `list_standards`로 확인해 답한다.
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_skill_md.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat(track2): grounded QA skill contract"`

### Task 20: (선택) 정적 인용 뷰어

**Files:** Create `viewer/index.html` · Test `tests/test_viewer.py`

**Interfaces:** Produces: `entry.answer_query` JSON을 붙여넣으면 원문·출처를 렌더하는 자립 HTML(외부 리소스 없음).

- [ ] **Step 1: 실패 테스트**
```python
def test_viewer_selfcontained():
    h = open("viewer/index.html", encoding="utf-8").read()
    assert "<textarea" in h and "http" not in h.split("</head>")[0].replace("https://","")
```
- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_viewer.py -v` · Expected: FAIL
- [ ] **Step 3: 최소구현** — 인라인 CSS/JS만 있는 단일 HTML(붙여넣은 JSON의 `hits[].text`와 `source_url`을 목록 렌더).
- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_viewer.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat(track2): optional static citation viewer"`

### Task 21: README(트랙2) + 실행 문서

**Files:** Create `README_track2.md` · Test `tests/test_readme.py`

**Interfaces:** Produces: 설치·빌드·실행·폴백 설명 문서.

- [ ] **Step 1: 실패 테스트**
```python
def test_readme_has_run_and_fallback():
    t = open("README_track2.md", encoding="utf-8").read()
    for kw in ["python -m gaap_standards_mcp", "corpus/", "BM25", "≤100MB", "search_standards"]:
        assert kw in t
```
- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_readme.py -v` · Expected: FAIL
- [ ] **Step 3: 최소구현** — 아키텍처·설치(`pip install -e .`)·코퍼스 빌드(`python -m tools.ingest.run_ingest`)·MCP 실행·폴백 3단계·용량 문서화.
- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_readme.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "docs(track2): README run/fallback/size"`

---

## Phase E — 실데이터 코퍼스 빌드

### Task 22: 소스 입수 가능성 probe (플랜 0단계)

**Files:** Create `tools/ingest/probe.py`, `docs/superpowers/notes/2026-07-05-source-probe.md`

**Interfaces:** Produces: GAAP별 `{gaap, reachable, format_confirmed, sample_ok, notes}` 리포트. **범위 축소 없이** 각 소스가 PDF/HWP/HTML 중 무엇으로 실제 받아지는지, 샘플 1개가 추출·청킹·라운드트립 통과하는지 실측.

- [ ] **Step 1:** `probe.py`로 GAAP별 대표 기준서 1개를 실제 다운로드→`extract`→`chunk`→`assert_coverage` 시도, 결과를 노트에 기록.
- [ ] **Step 2:** K-IFRS·K-GAAP·CAS·VAS는 확보 경로 확정. **ASC는 Basic View 스크래핑 가능성**만 별도 판정(불가 시 §8 원격 백엔드 예비안 발동을 노트에 명시).
- [ ] **Step 3: 커밋** — `git add -A && git commit -m "chore(track2): source-availability probe report"`

### Task 23: K-IFRS 전체 코퍼스 빌드

**Files:** Modify `tools/ingest/sources.py`(K-IFRS standards 전량 채움) · Output `corpus/kifrs.jsonl.zst`

**Interfaces:** Consumes: Task 9–14. Produces: K-IFRS **본문+적용지침 전량**의 문단 코퍼스.

- [ ] **Step 1:** `sources.py`의 K-IFRS `standards`에 전체 기준서 목록(번호·제목·URL·tier) 채움(임의 선별 금지).
- [ ] **Step 2:** 각 기준서 다운로드 → `run_ingest --gaap K-IFRS` → 라운드트립 ≥99.5% 통과. 실패 기준서는 이중추출로 원인 격리 후 재처리(제외 금지).
- [ ] **Step 3:** `list_standards("K-IFRS")` 문단수·as_of 검수.
- [ ] **Step 4: 커밋** — `git add -A && git commit -m "data(track2): K-IFRS full corpus"`

### Task 24: 일반기업회계기준 + CAS + VAS 코퍼스 빌드 (병렬)

**Files:** Modify `tools/ingest/sources.py`(각 GAAP standards 전량) · Output `corpus/{kgaap,cas,vas}.jsonl.zst`

**Interfaces:** Consumes: Task 9–14. Produces: 3개 GAAP 본문+적용지침 전량 코퍼스. (GAAP별 서브에이전트 병렬 가능.)

- [ ] **Step 1:** 각 GAAP `sources.py` 전량 채움.
- [ ] **Step 2:** GAAP별 `run_ingest` → 라운드트립 통과. 중국어·베트남어 모지바케 게이트 확인.
- [ ] **Step 3: 커밋** — `git add -A && git commit -m "data(track2): K-GAAP/CAS/VAS corpora"`

### Task 25: US GAAP ASC 코퍼스 빌드 (후순위·리스크)

**Files:** Create `tools/ingest/asc_scraper.py` · Output `corpus/usgaap.jsonl.zst`(또는 원격 백엔드 결정)

**Interfaces:** Produces: ASC 본문 문단 코퍼스. Basic View HTML을 Topic-Subtopic-Section-Paragraph 구조로 파싱해 `chunk_pages`(para_pattern=ASC 패턴)로 적재.

- [ ] **Step 1:** Task 22 판정에 따라 진행. 가능하면 `asc_scraper.py`로 Topic 목록→Section HTML 수집→문단 파싱.
- [ ] **Step 2:** 라운드트립·모지바케 게이트. **zip 편입 시 100MB 여유 재확인.**
- [ ] **Step 3:** 만약 ASC가 zip에 부적합(용량/입수)하면 §8 예비안(그 코퍼스만 원격 MCP) 문서화 후 `SOURCES`에 원격 플래그.
- [ ] **Step 4: 커밋** — `git add -A && git commit -m "data(track2): US GAAP ASC corpus (or remote fallback note)"`

### Task 26: 전체 벡터 인덱스 재빌드 + manifest

**Files:** Output `corpus/vectors/`, `corpus/manifest.json`

**Interfaces:** Consumes: 전 GAAP 코퍼스. Produces: 통합 PQ 인덱스 + manifest.

- [ ] **Step 1:** 실제 임베딩 모델로 전 코퍼스 `build_vectors` 실행(최초 다운로드 포함).
- [ ] **Step 2:** `VectorIndex` 로드 → 교차언어 known-item 몇 건 수동 확인(한국어 질의→영/중 문단).
- [ ] **Step 3: 커밋** — `git add -A && git commit -m "data(track2): unified PQ vector index + manifest"`

---

## Phase F — 패키징 · 통합

### Task 27: 교차언어 검색 품질 통합 테스트

**Files:** Test `tests/test_crosslingual.py`(실 corpus 존재 시)

**Interfaces:** Consumes: 빌드된 `corpus/`.

- [ ] **Step 1: 실패 테스트** — 실 corpus로 known-item: 한국어 "리스 사용권자산" → K-IFRS 1116 문단 top-k, 그리고 영어 ASC 842 문단이 교차언어로 top-k에 등장.
```python
import os, pytest
from gaap_standards_mcp.server import Context

@pytest.mark.skipif(not os.path.exists("corpus/manifest.json"), reason="corpus not built")
def test_crosslingual_lease():
    ctx = Context("corpus")
    hits = ctx.search("리스 사용권자산 인식", top_k=10)
    gaaps = {h["gaap"] for h in hits}
    assert "K-IFRS" in gaaps
    assert any(h["standard_no"].startswith("1116") for h in hits)
```
- [ ] **Step 2: 실패 확인/통과** — Run: `python -m pytest tests/test_crosslingual.py -v`
- [ ] **Step 3: 커밋** — `git add -A && git commit -m "test(track2): cross-lingual retrieval integration"`

### Task 28: 제출 zip 빌드 + ≤100MB assert

**Files:** Create `tools/build_submission.py` · Test `tests/test_zip_size.py`

**Interfaces:** Produces: `submission-pwc.zip`(트랙1+트랙2 통합, §6 레이아웃), 크기 assert.

- [ ] **Step 1: 실패 테스트**
```python
import os, subprocess, pytest
@pytest.mark.skipif(not os.path.exists("corpus/manifest.json"), reason="corpus not built")
def test_zip_under_100mb(tmp_path):
    out = tmp_path / "submission-pwc.zip"
    subprocess.run(["python", "tools/build_submission.py", "--out", str(out)], check=True)
    assert out.stat().st_size <= 100 * 1024 * 1024
```
- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_zip_size.py -v` · Expected: FAIL
- [ ] **Step 3: 최소구현** — `build_submission.py`: `src/`에 `.codex-plugin/`, `.mcp.json`, `skills/`(트랙1+트랙2), `gaap-ifrs/`, `gaap_standards_mcp/`, `corpus/`, `pyproject.toml`을 배치하고 README·logs 포함해 zip. 코퍼스는 이미 압축(.zst)이며 벡터는 PQ.
- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_zip_size.py -v` · Expected: PASS
- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat(track2): submission zip builder + size gate"`

### Task 29: 전체 회귀 + 최종 자체검증

**Files:** (전체)

- [ ] **Step 1:** `python -m pytest -q` 전체 통과 확인.
- [ ] **Step 2:** `python -m gaap_standards_mcp` stdio 기동 후 Codex에서 스킬로 실제 질의 1건(원문 인용·출처·번역병기·근거없음 경로) 수동 확인.
- [ ] **Step 3:** 모델 캐시 삭제 후 재기동 → `degraded`(BM25-only) 자동 폴백 확인. corpus만 두고 서버 임포트 차단 시 `no-mcp` 확인.
- [ ] **Step 4: 커밋** — `git add -A && git commit -m "test(track2): full regression + degradation manual check"`

---

## Self-Review

**Spec coverage:** §1 코퍼스·수집=Task 9–14,22–26 · §2 충실도=Task 12,23–25 · §3 하이브리드=Task 2–7 · §4 MCP=Task 15–17 · §5 grounding=Task 19 · §6 패키징·폴백=Task 8,16,18,28 · §7 테스트=각 Task+27,29 · §8 향후/ASC=Task 25. 누락 없음.

**Placeholder scan:** 코드 스텝은 실제 코드 포함. Task 20/21/23/24/25는 산출물 성격상 데이터·문서라 스텝이 "채움/검수"이지만 각 완료기준(라운드트립 ≥99.5%, 전량 목록, 테스트 통과)이 구체적임.

**Type consistency:** `Record`(schema.py) 필드, `tokenize`/`char_ngrams`, `BM25Index.search→(idx,score)`, `VectorIndex.search→(id,score)`, `rrf_merge(rankings)`, `HybridSearcher.search→list[dict]`, `Context` 메서드, `answer_query→{mode,hits}`가 태스크 간 일치.

**주의(빌드 순서):** Phase A/B는 병렬 가능하나 Phase C는 A, Phase E는 B에 의존. ultracode 실행 시 A·B를 각각 팬아웃 후 C→D→E→F 순.
