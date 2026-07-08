# 스킬 2(변환) 근거 grounding 구현 계획

> **For agentic workers:** 이 계획은 **Codex CLI가 구현**한다(CLAUDE.md 워크플로: Claude 기획 → Codex 구현 → Claude 리뷰). Steps use checkbox(`- [ ]`). 각 태스크는 독립 테스트 사이클로 끝난다.

**Goal:** 컨버터가 각 조정의 근거를 손으로 쓴 패러프레이즈 대신 **코퍼스 원문(verbatim)** 으로 grounding한 `difference_analysis.md`를 결정론적으로 산출한다. 코퍼스 미조회/부재 시 라벨된 폴백.

**Architecture:** `ifrs_ref`(포인터) → `gaap_standards_mcp.corpus.get_paragraph`(정확 주소 조회) → verbatim 삽입. 규정 텍스트 단일 원천 = 코퍼스. 엔진-side·결정론.

**Tech Stack:** Python 3.11, 기존 `gaap-ifrs/gaap_ifrs/`, 읽기 전용 재사용 `gaap_standards_mcp.corpus`.

**설계 문서:** `docs/superpowers/specs/2026-07-08-skill2-basis-grounding-design.md`.

## Global Constraints

- **MCP/스킬 1 절대 보존(최우선):** `gaap_standards_mcp/**`는 **0줄 변경**. `corpus.load_corpus`/`get_paragraph`만 **읽기 전용**으로 import. 완료 시 **트랙 2 pytest 130 전량 통과 + MCP 스모크 검색 정상**을 반드시 확인한다.
- **트랙 1 standalone 불변:** `gaap_standards_mcp`/`zstandard` 미설치 또는 `corpus/` 부재 시 예외 없이 **전량 폴백**으로 정상 산출. 코퍼스 로드는 `try/except`로 가드.
- **계산·데이터 불변:** 숫자·조정 로직·`data/*.json`(ifrs_ref 포함) 변경 금지. grounding은 **표시(렌더)만** 바꾼다.
- **결정론:** 정확 주소 조회(검색 아님). 같은 입력 → `difference_analysis.md` 바이트 동일.
- **테스트 실행 위치:** 트랙 1 테스트는 **`gaap-ifrs/`를 cwd로** 실행(상대경로 픽스처). 트랙 2는 리포 루트에서.
- **커밋:** `git add`는 03-ax-wars-pwc 경로한정. 각 태스크 끝에 커밋. 문서 강조는 bold만.

## File Structure

- 신규 `gaap-ifrs/gaap_ifrs/basis_grounding.py` — ifrs_ref 파서 + 코퍼스 리졸버(가드).
- 수정 `gaap-ifrs/gaap_ifrs/difference_report.py` — `_basis_block` grounding+폴백, `build_markdown(result, corpus=None)`.
- 수정 `gaap-ifrs/gaap_ifrs/report.py` — `write_all(result, outdir, corpus_dir=None)`, 코퍼스 1회 로드.
- 수정 `gaap-ifrs/gaap_ifrs/cli.py` — `--corpus-dir` 추가.
- 수정 `gaap-ifrs/SKILL.md` — description 진화.
- 신규 `gaap-ifrs/tests/test_basis_grounding.py` — 파서·리졸버·렌더·통합·결정론.

---

### Task 1: ifrs_ref 파서 (`basis_grounding.py`)

**Files:**
- Create: `gaap-ifrs/gaap_ifrs/basis_grounding.py`
- Test: `gaap-ifrs/tests/test_basis_grounding.py`

**Interfaces (Produces):**
- `parse_ifrs_ref(ref: str) -> tuple[str|None, str|None, list[str]]` — (gaap, standard_no, [문단]). 파싱 불가 → (None, None, []).
- `_expand_range(tok: str) -> list[str]` — "4.1.1-4.1.4" → ["4.1.1","4.1.2","4.1.3","4.1.4"].
- `DEFAULT_CORPUS_DIR: Path`.

- [ ] **Step 1: 실패 테스트 작성** — `gaap-ifrs/tests/test_basis_grounding.py`

```python
from gaap_ifrs.basis_grounding import parse_ifrs_ref


def test_parse_single():
    assert parse_ifrs_ref("K-IFRS 제1109호 문단 4.1.2") == ("K-IFRS", "1109", ["4.1.2"])


def test_parse_comma():
    assert parse_ifrs_ref("K-IFRS 제1002호 문단 9, 25") == ("K-IFRS", "1002", ["9", "25"])


def test_parse_range():
    assert parse_ifrs_ref("K-IFRS 제1109호 문단 4.1.1-4.1.4") == \
        ("K-IFRS", "1109", ["4.1.1", "4.1.2", "4.1.3", "4.1.4"])


def test_parse_range_plus_single():
    g, s, p = parse_ifrs_ref("K-IFRS 제1109호 문단 4.1.1-4.1.4, 5.2.1")
    assert (g, s) == ("K-IFRS", "1109")
    assert p[-1] == "5.2.1" and "4.1.3" in p


def test_parse_unparseable():
    assert parse_ifrs_ref("") == (None, None, [])
    assert parse_ifrs_ref("그냥 텍스트") == (None, None, [])
```

- [ ] **Step 2: 실패 확인** — `cd gaap-ifrs && python -m pytest tests/test_basis_grounding.py -v` → FAIL(ModuleNotFoundError: basis_grounding).

- [ ] **Step 3: 구현** — `gaap-ifrs/gaap_ifrs/basis_grounding.py`

```python
"""ifrs_ref(포인터) 파싱 + 코퍼스 원문 grounding.

규정 텍스트의 단일 원천은 코퍼스이며, 이 모듈은 gaap_standards_mcp.corpus를
'읽기 전용'으로 재사용한다(MCP 서버·검색·데이터는 건드리지 않는다). 코퍼스
미가용 시 전량 폴백해 트랙 1 standalone 동작을 보존한다.
"""
import re
from pathlib import Path

DEFAULT_CORPUS_DIR = Path(__file__).resolve().parents[2] / "corpus"

_REF_RE = re.compile(r"\s*(\S+)\s+제\s*([0-9]+)\s*호\s+문단\s+(.+)")


def _expand_range(tok):
    """'4.1.1-4.1.4' -> ['4.1.1','4.1.2','4.1.3','4.1.4']. 공통 접두 + 마지막 점
    세그먼트만 정수 확장. 확장 불가하면 양 끝점만."""
    a, _, b = tok.partition("-")
    a, b = a.strip(), b.strip()
    if not b:
        return [a] if a else []
    pa, pb = a.rsplit(".", 1), b.rsplit(".", 1)
    if len(pa) == 2 and len(pb) == 2 and pa[0] == pb[0] and pa[1].isdigit() and pb[1].isdigit():
        return [f"{pa[0]}.{i}" for i in range(int(pa[1]), int(pb[1]) + 1)]
    return [a, b]


def parse_ifrs_ref(ref):
    """'K-IFRS 제1109호 문단 4.1.1-4.1.4, 5.2.1'
       -> ('K-IFRS', '1109', ['4.1.1','4.1.2','4.1.3','4.1.4','5.2.1']).
    파싱 불가 -> (None, None, [])."""
    if not ref:
        return None, None, []
    m = _REF_RE.match(ref)
    if not m:
        return None, None, []
    gaap, std, paras_str = m.group(1), m.group(2), m.group(3)
    out, seen = [], set()
    for tok in paras_str.split(","):
        tok = tok.strip()
        if not tok:
            continue
        for p in (_expand_range(tok) if "-" in tok else [tok]):
            if p and p not in seen:
                seen.add(p)
                out.append(p)
    return gaap, std, out
```

- [ ] **Step 4: 통과 확인** — `cd gaap-ifrs && python -m pytest tests/test_basis_grounding.py -v` → 5 PASS.

- [ ] **Step 5: 커밋**

```bash
git add gaap-ifrs/gaap_ifrs/basis_grounding.py gaap-ifrs/tests/test_basis_grounding.py
git commit -m "feat(track1): ifrs_ref 파서 — 근거 grounding 1단계"
```

---

### Task 2: 코퍼스 리졸버 (가드 로드 + ground_ref)

**Files:**
- Modify: `gaap-ifrs/gaap_ifrs/basis_grounding.py`
- Test: `gaap-ifrs/tests/test_basis_grounding.py`

**Interfaces (Produces):**
- `load_corpus_for_grounding(corpus_dir=None) -> list|None` — 가드·캐시 로드. 미가용 시 None.
- `ground_ref(ref: str, records) -> tuple[list[dict], list[str]]` — (found[{label,text}], missing[문단]). records=None/파싱실패 → ([], []).

**Interfaces (Consumes):** `parse_ifrs_ref`(Task 1), `gaap_standards_mcp.corpus.load_corpus`/`get_paragraph`(읽기 전용).

- [ ] **Step 1: 실패 테스트 추가** — `tests/test_basis_grounding.py`에 append

```python
from types import SimpleNamespace
from gaap_ifrs.basis_grounding import ground_ref, load_corpus_for_grounding


def _rec(std, pn, text):
    return SimpleNamespace(gaap="K-IFRS", standard_no=std, paragraph_no=pn, text=text)


def test_ground_ref_found():
    recs = [_rec("1109", "4.1.2", "4.1.2 상각후원가로 측정한다.")]
    found, missing = ground_ref("K-IFRS 제1109호 문단 4.1.2", recs)
    assert len(found) == 1 and "상각후원가" in found[0]["text"]
    assert found[0]["label"] == "K-IFRS 제1109호 문단 4.1.2" and missing == []


def test_ground_ref_partial_missing():
    recs = [_rec("1002", "9", "9 취득원가와 순실현가능가치 중 낮은 금액.")]
    found, missing = ground_ref("K-IFRS 제1002호 문단 9, 25", recs)
    assert len(found) == 1 and missing == ["25"]


def test_ground_ref_no_corpus():
    assert ground_ref("K-IFRS 제1109호 문단 4.1.2", None) == ([], [])


def test_load_corpus_missing_dir_returns_none():
    assert load_corpus_for_grounding("/nonexistent/path/xyz-does-not-exist") is None
```

- [ ] **Step 2: 실패 확인** — `cd gaap-ifrs && python -m pytest tests/test_basis_grounding.py -v` → 새 4개 FAIL.

- [ ] **Step 3: 구현** — `basis_grounding.py`에 append

```python
_CORPUS_CACHE = {}


def load_corpus_for_grounding(corpus_dir=None):
    """코퍼스 레코드 로드(가드·캐시). gaap_standards_mcp/zstandard 미설치 또는
    corpus/ 부재 시 None -> 사용측 전량 폴백. 트랙 1 standalone 보존."""
    import os
    d = str(corpus_dir) if corpus_dir else str(DEFAULT_CORPUS_DIR)
    if d in _CORPUS_CACHE:
        return _CORPUS_CACHE[d]
    records = None
    try:
        if os.path.exists(os.path.join(d, "manifest.json")):
            from gaap_standards_mcp.corpus import load_corpus
            records = load_corpus(d)
    except Exception:
        records = None
    _CORPUS_CACHE[d] = records
    return records


def ground_ref(ref, records):
    """ifrs_ref -> (found, missing). found=[{'label','text'}] 정확 조회 문단 verbatim,
    missing=[조회 실패 문단번호]. records=None/파싱실패 -> ([], [])."""
    gaap, std, paras = parse_ifrs_ref(ref)
    if records is None or not gaap or not paras:
        return [], []
    from gaap_standards_mcp.corpus import get_paragraph
    found, missing = [], []
    for pn in paras:
        r = get_paragraph(records, gaap, std, pn)
        if r:
            found.append({"label": f"{gaap} 제{std}호 문단 {pn}", "text": r.text.strip()})
        else:
            missing.append(pn)
    return found, missing
```

- [ ] **Step 4: 통과 확인** — `cd gaap-ifrs && python -m pytest tests/test_basis_grounding.py -v` → 9 PASS.

- [ ] **Step 5: 커밋**

```bash
git add gaap-ifrs/gaap_ifrs/basis_grounding.py gaap-ifrs/tests/test_basis_grounding.py
git commit -m "feat(track1): 코퍼스 리졸버(가드 로드+ground_ref) — 근거 grounding 2단계"
```

---

### Task 3: 렌더러 grounding (`_basis_block` + `build_markdown`)

**Files:**
- Modify: `gaap-ifrs/gaap_ifrs/difference_report.py`
- Test: `gaap-ifrs/tests/test_basis_grounding.py`

**Interfaces (Produces):** `_basis_block(basis, corpus=None, indent="")`, `build_markdown(result, corpus=None)`.
**Interfaces (Consumes):** `ground_ref`(Task 2).

- [ ] **Step 1: 실패 테스트 추가** — `tests/test_basis_grounding.py`에 append

```python
from gaap_ifrs.difference_report import _basis_block


def test_basis_block_grounded():
    recs = [SimpleNamespace(gaap="K-IFRS", standard_no="1109", paragraph_no="4.1.2",
                            text="4.1.2 상각후원가로 측정한다.")]
    basis = {"ifrs_ref": "K-IFRS 제1109호 문단 4.1.2", "ifrs_requires": "요약문"}
    out = "\n".join(_basis_block(basis, corpus=recs))
    assert "코퍼스 원문" in out and "상각후원가로 측정한다." in out
    assert "요약문" not in out


def test_basis_block_fallback_when_no_corpus():
    basis = {"ifrs_ref": "K-IFRS 제1109호 문단 4.1.2", "ifrs_requires": "요약문"}
    out = "\n".join(_basis_block(basis, corpus=None))
    assert "큐레이션 요약 — 코퍼스 원문 미확인" in out and "요약문" in out
```

- [ ] **Step 2: 실패 확인** — `cd gaap-ifrs && python -m pytest tests/test_basis_grounding.py -k basis_block -v` → 2 FAIL(현행 `_basis_block`은 corpus 인자 없음).

- [ ] **Step 3: 구현** — `difference_report.py`

`_basis_block`(28~38행) 전체를 아래로 교체:

```python
def _basis_block(basis, corpus=None, indent=""):
    L = []
    ref = basis.get("ifrs_ref")
    if ref:
        from .basis_grounding import ground_ref
        found, missing = ground_ref(ref, corpus)
        if found:
            L.append(f"{indent}- **IFRS 근거 (코퍼스 원문)**:")
            for f in found:
                L.append(f'{indent}    - [{f["label"]}] "{f["text"]}"')
            if missing:
                L.append(f"{indent}    - (일부 문단 미확인: {', '.join(missing)} — 코퍼스 미적재)")
        else:
            L.append(f"{indent}- **IFRS 근거 (큐레이션 요약 — 코퍼스 원문 미확인)**: "
                     f"{ref} — {basis.get('ifrs_requires', '')}")
    if basis.get("prev_gaap"):
        L.append(f"{indent}- **이전 GAAP (큐레이션 요약)**: {basis['prev_gaap']}")
    if basis.get("difference"):
        L.append(f"{indent}- **핵심 차이**: {basis['difference']}")
    if basis.get("reasoning"):
        L.append(f"{indent}- **판단·작업(엔진)**: {basis['reasoning']}")
    return L
```

`build_markdown` 시그니처(41행)를 `def build_markdown(result, corpus=None):`로 바꾸고, `_basis_block` 두 호출(71·81행)을 `_basis_block(ml.basis, corpus)` / `_basis_block(a.basis, corpus)`로, 93행 캐비앗을 아래로 교체:

```python
        L.append("- ⚠️ *조항 인용은 코퍼스 원문 기준(‘큐레이션 요약’ 표시 항목은 코퍼스 미적재분이라 공식 원문 대조 필요).*\n")
```

- [ ] **Step 4: 통과 확인** — `cd gaap-ifrs && python -m pytest tests/test_basis_grounding.py -v` → 11 PASS.

- [ ] **Step 5: 커밋**

```bash
git add gaap-ifrs/gaap_ifrs/difference_report.py gaap-ifrs/tests/test_basis_grounding.py
git commit -m "feat(track1): 렌더러 grounding+폴백 — 근거 grounding 3단계"
```

---

### Task 4: CLI·report 배선 + 통합/결정론 테스트

**Files:**
- Modify: `gaap-ifrs/gaap_ifrs/report.py`, `gaap-ifrs/gaap_ifrs/cli.py`
- Test: `gaap-ifrs/tests/test_basis_grounding.py`

**Interfaces (Produces):** `write_all(result, outdir, corpus_dir=None)`, cli `--corpus-dir`.

- [ ] **Step 1: 실패 테스트 추가** — `tests/test_basis_grounding.py`에 append. `write_all`이 코퍼스를 실제로 관통시키는지(배선)를 red-green으로 잡는다.

```python
import json
from gaap_ifrs.convert import run_conversion
from gaap_ifrs.difference_report import build_markdown
from gaap_ifrs.report import write_all
from gaap_ifrs.basis_grounding import load_corpus_for_grounding, DEFAULT_CORPUS_DIR

_TB = "../examples/kgaap/input_trial_balance.csv"
_EXTRA = "../examples/kgaap/input_adjustments.json"


def _result():
    extra = json.load(open(_EXTRA, encoding="utf-8"))
    return run_conversion(_TB, "K-GAAP", extra, "KRW", "")


def test_write_all_threads_corpus_into_md(tmp_path):
    # 배선: write_all(result, outdir, corpus_dir) 3번째 인자로 코퍼스를 관통.
    # 현행 write_all은 2-인자라 이 호출 자체가 TypeError → red.
    paths = write_all(_result(), str(tmp_path), str(DEFAULT_CORPUS_DIR))
    md = open(paths["difference"], encoding="utf-8").read()
    if load_corpus_for_grounding(DEFAULT_CORPUS_DIR) is not None:
        assert "IFRS 근거 (코퍼스 원문)" in md
        assert "상각후원가로 측정한다" in md  # 1109:4.1.2 원문 일부
    else:
        assert "큐레이션 요약 — 코퍼스 원문 미확인" in md


def test_determinism_bytewise():
    corpus = load_corpus_for_grounding(DEFAULT_CORPUS_DIR)
    assert build_markdown(_result(), corpus) == build_markdown(_result(), corpus)
```

- [ ] **Step 2: 실패 확인** — `cd gaap-ifrs && python -m pytest tests/test_basis_grounding.py -k "write_all or determinism" -v` → `test_write_all_threads_corpus_into_md` FAIL(현행 `write_all`은 2-인자 → `TypeError`).

- [ ] **Step 3: 구현**

`report.py` — import에 추가하고 `write_all`을 수정:

```python
from .basis_grounding import load_corpus_for_grounding
```

```python
def write_all(result, outdir, corpus_dir=None):
    os.makedirs(outdir, exist_ok=True)
    corpus = load_corpus_for_grounding(corpus_dir)
    paths = {
        "financials": os.path.join(outdir, "ifrs_financials.xlsx"),
        "reconciliation": os.path.join(outdir, "reconciliation.xlsx"),
        "impact": os.path.join(outdir, "impact_analysis.xlsx"),
        "difference": os.path.join(outdir, "difference_analysis.md"),
        "json": os.path.join(outdir, "result.json"),
    }
    _write_financials(result, paths["financials"])
    _write_reconciliation(result, paths["reconciliation"])
    _write_impact(result, paths["impact"])
    with open(paths["difference"], "w", encoding="utf-8") as f:
        f.write(build_markdown(result, corpus))
    with open(paths["json"], "w", encoding="utf-8") as f:
        json.dump({
            "ifrs_bs": result.ifrs_bs,
            "ifrs_pl": result.ifrs_pl,
            "adjustments": [asdict(a) for a in result.adjustments],
            "impact": result.impact,
        }, f, ensure_ascii=False, indent=2, default=str)
    return paths
```

`cli.py` — convert 파서에 인자 추가(18행 `--out` 다음)하고 호출 수정:

```python
    c.add_argument("--corpus-dir", default=None,
                   help="코퍼스 디렉토리(기본 자동탐색). 근거 원문 grounding용")
```

```python
    paths = write_all(result, args.out, args.corpus_dir)
```

- [ ] **Step 4: 통과 + 실변환 확인**

```bash
cd gaap-ifrs && python -m pytest tests/test_basis_grounding.py -v
python -m gaap_ifrs.cli convert --input ../examples/kgaap/input_trial_balance.csv \
  --source-gaap K-GAAP --extra ../examples/kgaap/input_adjustments.json --out /tmp/t1g
grep -c "IFRS 근거 (코퍼스 원문)" /tmp/t1g/difference_analysis.md   # >=1 기대
grep -c "상각후원가로 측정한다" /tmp/t1g/difference_analysis.md      # >=1 기대(원문 박힘)
```
Expected: 전체 PASS, grep 양쪽 ≥1.

- [ ] **Step 5: 커밋**

```bash
git add gaap-ifrs/gaap_ifrs/report.py gaap-ifrs/gaap_ifrs/cli.py gaap-ifrs/tests/test_basis_grounding.py
git commit -m "feat(track1): CLI --corpus-dir + report 배선 + 통합/결정론 테스트 — 근거 grounding 4단계"
```

---

### Task 5: SKILL.md description 진화

**Files:** Modify `gaap-ifrs/SKILL.md`(frontmatter description).

- [ ] **Step 1: 수정** — description 끝에 근거 grounding 문구 추가(이름 `gaap-ifrs-converter` 유지). 예: 기존 description 뒤에 " 각 조정의 조항 근거는 로컬 코퍼스 원문(verbatim)으로 grounding하며, 코퍼스에 없으면 '큐레이션 요약'으로 명시한다." 를 덧붙인다. 본문에 grounding 동작 1~2줄 설명 추가(원문 근거는 코퍼스에서, 미조회는 라벨).

- [ ] **Step 2: 커밋**

```bash
git add gaap-ifrs/SKILL.md
git commit -m "docs(track1): SKILL.md — 근거=코퍼스 원문 grounded 명시"
```

---

### Task 6: 전체 회귀 + MCP/스킬 1 보존 검증 (게이트)

**Files:** 없음(검증만).

- [ ] **Step 1: 트랙 1 전체** — `cd gaap-ifrs && python -m pytest tests/ -q` → 기존 34 + 신규 전량 PASS(숫자 무회귀).
- [ ] **Step 2: 트랙 2 전체(MCP/스킬 1 무영향 증명)** — 리포 루트에서 `python -m pytest tests/ -q` → **130 전량 PASS**.
- [ ] **Step 3: MCP 스모크(스킬 1 정상)** — 리포 루트에서:

```bash
python -c "from gaap_standards_mcp.server import Context; c=Context('corpus'); print(c.search('리스이용자 인식', gaap='K-IFRS', top_k=1)[0]['paragraph_no'])"
```
Expected: `22`(스킬 1 검색 정상, MCP 무손상).

- [ ] **Step 4: standalone 폴백 확인** — 코퍼스 없이도 산출되는지:

```bash
cd gaap-ifrs && python -m gaap_ifrs.cli convert --input ../examples/kgaap/input_trial_balance.csv \
  --source-gaap K-GAAP --extra ../examples/kgaap/input_adjustments.json \
  --out /tmp/t1fallback --corpus-dir /nonexistent
grep -c "큐레이션 요약 — 코퍼스 원문 미확인" /tmp/t1fallback/difference_analysis.md   # >=1 기대
```
Expected: 예외 없이 생성, 폴백 라벨 ≥1.

- [ ] **Step 5: 결정론 재확인** — `cd gaap-ifrs && python -m pytest tests/test_basis_grounding.py::test_determinism_bytewise -q` → PASS.

- [ ] **Step 6: 최종 커밋(있으면)** — 검증만이면 생략. 필요 시 문서/노트 커밋.

---

## Self-Review 체크

- **스펙 커버리지:** grounding(파서 T1·리졸버 T2·렌더 T3·배선 T4)·폴백(T2/T3)·이름(T5)·MCP보존(T6)·결정론(T4/T6)·standalone(T2/T6) 전부 태스크 매핑. ✓
- **타입 정합:** `parse_ifrs_ref→(gaap,std,[para])`, `ground_ref→(found[{label,text}],missing[str])`, `_basis_block(basis,corpus,indent)`, `build_markdown(result,corpus)`, `write_all(result,outdir,corpus_dir)` — 태스크 간 일관. ✓
- **비목표 준수:** `gaap_standards_mcp/**`·`data/*.json`·계산 로직 불변. ✓
- **점진성:** 각 태스크 독립 테스트+커밋, T6 게이트에서 두 트랙 회귀. ✓

## Codex 핸드오프

이 계획이 Claude↔Codex 인터페이스다(CLAUDE.md). Codex가 태스크 순서대로 구현하고, 완료 후 Claude가 diff를 리뷰한다(특히 **트랙 2 130 통과·MCP 스모크**로 스킬 1 보존을 확인).
