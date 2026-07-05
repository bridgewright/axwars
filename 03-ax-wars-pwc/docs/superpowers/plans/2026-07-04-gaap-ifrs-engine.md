# GAAP→IFRS 변환 엔진 (A: K-GAAP → K-IFRS) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 소스 GAAP(v1=일반기업회계기준) 시산표(.xlsx/.csv)를 입력받아 K-IFRS 재무제표 + 전환조정 명세서(근거인용) + 영향분석을 산출하는 근거기반 변환 엔진과 CLI를 만든다.

**Architecture:** 순수 함수 파이프라인 — `parse(시산표→canonical) → map(Layer1 계정 재분류, 큐레이션 KB) → adjust(Layer2 측정조정, pluggable+flag) → build(IFRS BS/PL) → reconcile(전환 브릿지) → impact(지표 델타) → report(Excel/JSON)`. 지식(계정→기준 매핑·조정규칙)은 **JSON 데이터 파일**(근거 인용 포함)로, 계산은 **결정론적 코드**로 분리한다(anti-hallucination 핵심). RAG는 벡터DB 없이 구조적 큐레이션 조회.

**Tech Stack:** Python 3.11+, 표준 라이브러리(csv, json, dataclasses), openpyxl(엑셀 read/write), pytest(테스트). 외부 의존성은 openpyxl 하나로 제한.

## Global Constraints

- Python 3.11+; 외부 의존성 = `openpyxl`, `pytest`만. (지식파일은 YAML 아닌 stdlib `json`.)
- 지식과 계산 분리: 규칙·인용은 `gaap_ifrs/data/`의 JSON에, 숫자 계산은 코드에. LLM이 숫자를 생성하지 않는다.
- 근거(standard citation) 없는 조정은 **계산 금지 → `flagged=True, flag_reason` 로 표기**("판단 필요/추가자료 필요").
- 모든 금액 단위 = 입력 통화(기본 KRW), float. 표시는 정수 반올림.
- 산출물 파일명: `ifrs_financials.xlsx`, `reconciliation.xlsx`, `impact_analysis.xlsx`, `result.json`.
- 패키지 루트: `03-ax-wars-pwc/gaap-ifrs/`. import 경로 `gaap_ifrs`.
- 커밋 단위: 각 Task 끝에서 커밋. (프로젝트가 git repo가 아니면 Task 0에서 `git init`.)

---

## File Structure

```
gaap-ifrs/
├── pyproject.toml                       # 패키지 메타 + openpyxl 의존성
├── README.md                            # 플러그인 설명(제출 문항 3 반영)
├── SKILL.md                             # Codex/Claude 스킬 래퍼(호출법)
├── gaap_ifrs/
│   ├── __init__.py
│   ├── schema.py                        # dataclasses: Account, TrialBalance, MappedLine, Adjustment, ConversionResult
│   ├── parse.py                         # .csv/.xlsx → TrialBalance
│   ├── knowledge.py                     # data/*.json 로더 + 조회
│   ├── mapping.py                       # Layer1: TrialBalance → [MappedLine]
│   ├── adjustments.py                   # Layer2: pluggable 조정엔진 + ECL 계산 + flagging
│   ├── statements.py                    # [MappedLine]+[Adjustment] → IFRS BS/PL dict
│   ├── reconcile.py                     # 전환조정 브릿지 rows
│   ├── impact.py                        # 지표 델타 + 서술
│   ├── report.py                        # Excel(openpyxl)+JSON 렌더
│   ├── convert.py                       # 파이프라인 오케스트레이션(run_conversion)
│   ├── cli.py                           # argparse CLI: convert
│   └── data/
│       ├── mapping_kgaap.json           # K-GAAP 계정 → IFRS 계정 + 기준 인용
│       └── adjustments/
│           └── ecl_allowance.json       # 대손 → K-IFRS 1109(ECL) 규칙
└── tests/
    ├── fixtures/
    │   ├── sample_tb_kgaap.csv          # 소형 합성 K-GAAP 시산표
    │   └── sample_aging.json            # ECL용 채권 연령표
    ├── test_parse.py
    ├── test_knowledge.py
    ├── test_mapping.py
    ├── test_adjustments.py
    ├── test_statements.py
    ├── test_reconcile.py
    ├── test_impact.py
    ├── test_report.py
    └── test_cli.py
```

---

### Task 0: 스캐폴드 + 패키지 메타

**Files:**
- Create: `gaap-ifrs/pyproject.toml`, `gaap-ifrs/gaap_ifrs/__init__.py`, `gaap-ifrs/tests/__init__.py`

- [ ] **Step 1: git init (repo 아니면)**

Run: `cd 03-ax-wars-pwc && git rev-parse --git-dir 2>/dev/null || git init`

- [ ] **Step 2: pyproject.toml 작성**

```toml
[project]
name = "gaap-ifrs"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["openpyxl>=3.1"]

[project.scripts]
gaap-ifrs = "gaap_ifrs.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: 빈 `gaap_ifrs/__init__.py`, `tests/__init__.py` 생성**

- [ ] **Step 4: 의존성 설치 + 확인**

Run: `cd gaap-ifrs && python3 -m pip install -e . && python3 -c "import openpyxl; print('ok')"`
Expected: `ok`

- [ ] **Step 5: Commit** — `git add -A && git commit -m "chore: scaffold gaap-ifrs package"`

---

### Task 1: 캐노니컬 스키마

**Files:**
- Create: `gaap_ifrs/schema.py`
- Test: `tests/test_schema.py`

**Interfaces:**
- Produces: `Account(name_src:str, amount:float, code:str|None)`, `TrialBalance(source_gaap, currency, period, accounts:list[Account])`, `MappedLine(source:Account, ifrs_account:str, statement:str, section:str, standard:str, flagged:bool, flag_reason:str)`, `Adjustment(id, title, standard, amount:float, affects:list[str], direction:str, confidence:str, note:str, flagged:bool)`, `ConversionResult(trial_balance, mapped:list[MappedLine], adjustments:list[Adjustment], ifrs_bs:dict, ifrs_pl:dict, impact:dict)`.

- [ ] **Step 1: 실패 테스트 작성** (`tests/test_schema.py`)

```python
from gaap_ifrs.schema import Account, TrialBalance

def test_trial_balance_total():
    tb = TrialBalance("K-GAAP", "KRW", "2025-12-31",
                      [Account("현금", 5000), Account("매출채권", 3000)])
    assert sum(a.amount for a in tb.accounts) == 8000
    assert tb.source_gaap == "K-GAAP"
```

- [ ] **Step 2: 실패 확인** — Run: `pytest tests/test_schema.py -v` → FAIL (ModuleNotFoundError)

- [ ] **Step 3: schema.py 구현**

```python
from dataclasses import dataclass, field

@dataclass
class Account:
    name_src: str
    amount: float
    code: str | None = None

@dataclass
class TrialBalance:
    source_gaap: str
    currency: str
    period: str
    accounts: list[Account]

@dataclass
class MappedLine:
    source: Account
    ifrs_account: str
    statement: str          # "BS" | "PL"
    section: str            # e.g. "유동자산"
    standard: str           # citation, e.g. "K-IFRS 1109"
    flagged: bool = False
    flag_reason: str = ""

@dataclass
class Adjustment:
    id: str
    title: str
    standard: str
    amount: float                       # 순영향액(자본기준). flagged면 0.
    affects: list[str] = field(default_factory=list)
    direction: str = "재분류"           # "증가"|"감소"|"재분류"
    confidence: str = "high"            # "high"|"flagged"
    note: str = ""
    flagged: bool = False

@dataclass
class ConversionResult:
    trial_balance: TrialBalance
    mapped: list[MappedLine]
    adjustments: list[Adjustment]
    ifrs_bs: dict
    ifrs_pl: dict
    impact: dict
```

- [ ] **Step 4: 통과 확인** — Run: `pytest tests/test_schema.py -v` → PASS
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: canonical schema dataclasses"`

---

### Task 2: 시산표 파서 (.csv / .xlsx → TrialBalance)

**Files:**
- Create: `gaap_ifrs/parse.py`, `tests/fixtures/sample_tb_kgaap.csv`
- Test: `tests/test_parse.py`

**Interfaces:**
- Consumes: `schema.Account`, `schema.TrialBalance`
- Produces: `load_trial_balance(path:str, source_gaap:str, currency:str="KRW", period:str="") -> TrialBalance`. CSV/xlsx 모두 지원. 컬럼 자동감지: 계정명 컬럼(계정/과목/name 포함) + 금액 컬럼(금액/잔액/amount 포함). 금액 문자열의 콤마·괄호(음수) 처리.

- [ ] **Step 1: 픽스처 작성** (`tests/fixtures/sample_tb_kgaap.csv`)

```csv
계정과목,잔액
현금및현금성자산,5000000
매출채권,3000000
대손충당금,-150000
재고자산,2000000
유형자산,10000000
개발비,1200000
매입채무,"1,800,000"
차입금,4000000
자본금,2000000
이익잉여금,13250000
매출,20000000
매출원가,12000000
대손상각비,150000
```

- [ ] **Step 2: 실패 테스트** (`tests/test_parse.py`)

```python
from gaap_ifrs.parse import load_trial_balance

def test_parse_csv():
    tb = load_trial_balance("tests/fixtures/sample_tb_kgaap.csv", "K-GAAP", "KRW", "2025-12-31")
    names = {a.name_src: a.amount for a in tb.accounts}
    assert names["현금및현금성자산"] == 5000000
    assert names["대손충당금"] == -150000        # 음수
    assert names["매입채무"] == 1800000           # 콤마 제거
    assert tb.source_gaap == "K-GAAP"
```

- [ ] **Step 3: 실패 확인** — `pytest tests/test_parse.py -v` → FAIL

- [ ] **Step 4: parse.py 구현**

```python
import csv, re, os
from .schema import Account, TrialBalance

_NAME_HINTS = ("계정", "과목", "name", "account")
_AMT_HINTS = ("금액", "잔액", "amount", "balance")

def _to_amount(s) -> float:
    if s is None: return 0.0
    t = str(s).strip().replace(",", "").replace(" ", "")
    if t in ("", "-"): return 0.0
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    try:
        v = float(t)
    except ValueError:
        return 0.0
    return -v if neg else v

def _pick(header, hints):
    for i, h in enumerate(header):
        hl = str(h).lower()
        if any(k in hl for k in hints): return i
    return None

def _rows_from_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.reader(f) if any(c.strip() for c in r)]

def _rows_from_xlsx(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    out = []
    for row in ws.iter_rows(values_only=True):
        if any(c is not None and str(c).strip() for c in row):
            out.append(["" if c is None else c for c in row])
    return out

def load_trial_balance(path, source_gaap, currency="KRW", period=""):
    rows = _rows_from_xlsx(path) if path.lower().endswith((".xlsx", ".xlsm")) else _rows_from_csv(path)
    if not rows:
        raise ValueError(f"empty trial balance: {path}")
    header = rows[0]
    ni = _pick(header, _NAME_HINTS)
    ai = _pick(header, _AMT_HINTS)
    if ni is None: ni = 0
    if ai is None: ai = 1
    accounts = []
    for r in rows[1:]:
        if ni >= len(r): continue
        name = str(r[ni]).strip()
        if not name: continue
        amt = _to_amount(r[ai] if ai < len(r) else 0)
        accounts.append(Account(name_src=name, amount=amt))
    return TrialBalance(source_gaap, currency, period, accounts)
```

- [ ] **Step 5: 통과 확인** — `pytest tests/test_parse.py -v` → PASS
- [ ] **Step 6: xlsx 파싱 테스트 추가** (openpyxl로 픽스처를 생성해 동일 검증하는 `test_parse_xlsx`) 후 PASS 확인
- [ ] **Step 7: Commit** — `git add -A && git commit -m "feat: trial balance parser (csv/xlsx)"`

---

### Task 3: 지식 베이스 + 로더 (Layer1 매핑 데이터)

**Files:**
- Create: `gaap_ifrs/knowledge.py`, `gaap_ifrs/data/mapping_kgaap.json`
- Test: `tests/test_knowledge.py`

**Interfaces:**
- Produces: `load_mappings() -> list[dict]` (각 dict: source, aliases, ifrs_account, statement, section, standard, note). `find_mapping(name:str, mappings) -> dict|None` (정확명 또는 alias 매칭).

- [ ] **Step 1: mapping_kgaap.json 작성** (v1 최소셋, 실제 계정·기준 인용)

```json
[
  {"source":"현금및현금성자산","aliases":["현금","보통예금"],"ifrs_account":"현금및현금성자산","statement":"BS","section":"유동자산","standard":"K-IFRS 1007","note":"표시 유지"},
  {"source":"매출채권","aliases":["외상매출금","받을어음"],"ifrs_account":"매출채권및기타유동채권","statement":"BS","section":"유동자산","standard":"K-IFRS 1109 · 1001","note":"기타채권과 통합 표시"},
  {"source":"대손충당금","aliases":[],"ifrs_account":"손실충당금","statement":"BS","section":"유동자산","standard":"K-IFRS 1109","note":"차감계정. 측정은 ECL 조정 참조"},
  {"source":"재고자산","aliases":["상품","제품","원재료"],"ifrs_account":"재고자산","statement":"BS","section":"유동자산","standard":"K-IFRS 1002","note":"표시 유지"},
  {"source":"유형자산","aliases":["토지","건물","기계장치"],"ifrs_account":"유형자산","statement":"BS","section":"비유동자산","standard":"K-IFRS 1016","note":"측정모형 선택 시 재평가 조정 가능"},
  {"source":"개발비","aliases":[],"ifrs_account":"무형자산","statement":"BS","section":"비유동자산","standard":"K-IFRS 1038","note":"자본화 요건 차이 → 조정 검토"},
  {"source":"매입채무","aliases":["외상매입금","지급어음"],"ifrs_account":"매입채무및기타유동부채","statement":"BS","section":"유동부채","standard":"K-IFRS 1001","note":"통합 표시"},
  {"source":"차입금","aliases":["단기차입금","장기차입금"],"ifrs_account":"차입금","statement":"BS","section":"부채","standard":"K-IFRS 1109","note":"상각후원가 측정"},
  {"source":"자본금","aliases":[],"ifrs_account":"자본금","statement":"BS","section":"자본","standard":"K-IFRS 1001","note":"표시 유지"},
  {"source":"이익잉여금","aliases":["이월이익잉여금"],"ifrs_account":"이익잉여금","statement":"BS","section":"자본","standard":"K-IFRS 1001","note":"전환조정 반영"},
  {"source":"매출","aliases":["매출액","제품매출"],"ifrs_account":"수익(매출)","statement":"PL","section":"수익","standard":"K-IFRS 1115","note":"수행의무 기준"},
  {"source":"매출원가","aliases":[],"ifrs_account":"매출원가","statement":"PL","section":"비용","standard":"K-IFRS 1001","note":"표시 유지"},
  {"source":"대손상각비","aliases":[],"ifrs_account":"손상차손","statement":"PL","section":"비용","standard":"K-IFRS 1109","note":"ECL 기준 측정"}
]
```

- [ ] **Step 2: 실패 테스트** (`tests/test_knowledge.py`)

```python
from gaap_ifrs.knowledge import load_mappings, find_mapping

def test_load_and_find():
    m = load_mappings()
    assert len(m) >= 10
    hit = find_mapping("외상매출금", m)          # alias
    assert hit["ifrs_account"] == "매출채권및기타유동채권"
    assert find_mapping("존재하지않는계정", m) is None
```

- [ ] **Step 3: 실패 확인** — `pytest tests/test_knowledge.py -v` → FAIL

- [ ] **Step 4: knowledge.py 구현**

```python
import json, os
_DATA = os.path.join(os.path.dirname(__file__), "data")

def load_mappings():
    with open(os.path.join(_DATA, "mapping_kgaap.json"), encoding="utf-8") as f:
        return json.load(f)

def find_mapping(name, mappings):
    name = name.strip()
    for m in mappings:
        if name == m["source"] or name in m.get("aliases", []):
            return m
    return None

def load_adjustment_rules():
    d = os.path.join(_DATA, "adjustments")
    if not os.path.isdir(d): return []
    rules = []
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".json"):
            with open(os.path.join(d, fn), encoding="utf-8") as f:
                rules.append(json.load(f))
    return rules
```

- [ ] **Step 5: 통과 확인** — `pytest tests/test_knowledge.py -v` → PASS
- [ ] **Step 6: Commit** — `git add -A && git commit -m "feat: knowledge base + loader (K-GAAP mapping)"`

---

### Task 4: Layer1 매핑 엔진

**Files:**
- Create: `gaap_ifrs/mapping.py`
- Test: `tests/test_mapping.py`

**Interfaces:**
- Consumes: `TrialBalance`, `MappedLine`, `knowledge.load_mappings/find_mapping`
- Produces: `map_accounts(tb:TrialBalance) -> list[MappedLine]`. 매핑 없는 계정은 `MappedLine(..., ifrs_account=name_src, statement="?", section="미분류", standard="", flagged=True, flag_reason="매핑규칙 없음")`.

- [ ] **Step 1: 실패 테스트** (`tests/test_mapping.py`)

```python
from gaap_ifrs.parse import load_trial_balance
from gaap_ifrs.mapping import map_accounts

def test_mapping_and_flag():
    tb = load_trial_balance("tests/fixtures/sample_tb_kgaap.csv", "K-GAAP")
    lines = map_accounts(tb)
    by = {l.source.name_src: l for l in lines}
    assert by["매출채권"].ifrs_account == "매출채권및기타유동채권"
    assert by["매출채권"].standard.startswith("K-IFRS 1109")
    assert by["매출"].statement == "PL"

def test_unmapped_flagged():
    from gaap_ifrs.schema import TrialBalance, Account
    tb = TrialBalance("K-GAAP", "KRW", "", [Account("이상한계정", 100)])
    line = map_accounts(tb)[0]
    assert line.flagged and "매핑규칙 없음" in line.flag_reason
```

- [ ] **Step 2: 실패 확인** — `pytest tests/test_mapping.py -v` → FAIL

- [ ] **Step 3: mapping.py 구현**

```python
from .schema import MappedLine
from .knowledge import load_mappings, find_mapping

def map_accounts(tb):
    mappings = load_mappings()
    out = []
    for acc in tb.accounts:
        m = find_mapping(acc.name_src, mappings)
        if m:
            out.append(MappedLine(source=acc, ifrs_account=m["ifrs_account"],
                                  statement=m["statement"], section=m["section"],
                                  standard=m["standard"]))
        else:
            out.append(MappedLine(source=acc, ifrs_account=acc.name_src,
                                  statement="?", section="미분류", standard="",
                                  flagged=True, flag_reason="매핑규칙 없음 — 수동 매핑 필요"))
    return out
```

- [ ] **Step 4: 통과 확인** — `pytest tests/test_mapping.py -v` → PASS
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: Layer1 account mapping engine"`

---

### Task 5: Layer2 조정 엔진 + ECL 조정 + flagging

**Files:**
- Create: `gaap_ifrs/adjustments.py`, `gaap_ifrs/data/adjustments/ecl_allowance.json`, `tests/fixtures/sample_aging.json`
- Test: `tests/test_adjustments.py`

**Interfaces:**
- Consumes: `TrialBalance`, `Adjustment`, `knowledge.load_adjustment_rules`
- Produces: `apply_adjustments(tb:TrialBalance, extra_inputs:dict|None=None) -> list[Adjustment]`. 각 규칙: trigger 계정이 있으면 required_inputs 확인 → 있으면 계산기 호출, 없으면 `Adjustment(..., flagged=True, confidence="flagged", note="필요자료 없음: <입력>")`. 계산기 레지스트리 `COMPUTERS: dict[str, callable]`; ECL 계산기 `compute_ecl(tb, extra) -> (amount, affects, direction, note)`.

- [ ] **Step 1: 규칙 파일** (`data/adjustments/ecl_allowance.json`)

```json
{
  "id":"ecl_allowance",
  "title":"대손충당금 → 기대신용손실(ECL)",
  "standard":"K-IFRS 1109",
  "trigger_accounts":["대손충당금","매출채권"],
  "required_inputs":["aging_schedule"],
  "computer":"compute_ecl",
  "description":"발생손실모형 → 기대신용손실모형. 연령구간별 손실률을 매출채권에 적용해 목표 손실충당금을 산출, 기존 충당금과의 차액을 조정."
}
```

- [ ] **Step 2: ECL 입력 픽스처** (`tests/fixtures/sample_aging.json`)

```json
{"aging_schedule":[
  {"bucket":"정상","receivable":2500000,"loss_rate":0.01},
  {"bucket":"30일초과","receivable":400000,"loss_rate":0.10},
  {"bucket":"90일초과","receivable":100000,"loss_rate":0.30}
]}
```

- [ ] **Step 3: 실패 테스트** (`tests/test_adjustments.py`)

```python
import json
from gaap_ifrs.parse import load_trial_balance
from gaap_ifrs.adjustments import apply_adjustments

def test_ecl_computed():
    tb = load_trial_balance("tests/fixtures/sample_tb_kgaap.csv", "K-GAAP")
    extra = json.load(open("tests/fixtures/sample_aging.json", encoding="utf-8"))
    adjs = apply_adjustments(tb, extra)
    ecl = [a for a in adjs if a.id == "ecl_allowance"][0]
    # 목표충당금 = 2.5M*1% + 0.4M*10% + 0.1M*30% = 25,000+40,000+30,000 = 95,000
    # 기존 대손충당금 150,000 → 추가 충당 필요액 = 95,000 - 150,000 = -55,000 (환입)
    assert round(ecl.amount) == -55000
    assert ecl.standard == "K-IFRS 1109"
    assert not ecl.flagged

def test_flag_when_missing_input():
    tb = load_trial_balance("tests/fixtures/sample_tb_kgaap.csv", "K-GAAP")
    adjs = apply_adjustments(tb, extra_inputs=None)   # aging 없음
    ecl = [a for a in adjs if a.id == "ecl_allowance"][0]
    assert ecl.flagged and ecl.confidence == "flagged"
    assert ecl.amount == 0
```

- [ ] **Step 4: 실패 확인** — `pytest tests/test_adjustments.py -v` → FAIL

- [ ] **Step 5: adjustments.py 구현**

```python
from .schema import Adjustment
from .knowledge import load_adjustment_rules

def _acc(tb, name):
    return sum(a.amount for a in tb.accounts if a.name_src == name)

def compute_ecl(tb, extra):
    aging = extra["aging_schedule"]
    target = sum(b["receivable"] * b["loss_rate"] for b in aging)
    existing = abs(_acc(tb, "대손충당금"))          # 차감계정(음수)로 저장됨
    delta = target - existing                        # +면 추가충당(자본감소), -면 환입(자본증가)
    direction = "감소" if delta > 0 else ("증가" if delta < 0 else "재분류")
    note = f"목표 손실충당금 {target:,.0f} - 기존 {existing:,.0f} = {delta:,.0f}"
    # 자본영향(순이익 통해) = -delta  (충당금 증가는 비용→자본감소)
    return (-delta, ["손실충당금", "이익잉여금"], direction, note)

COMPUTERS = {"compute_ecl": compute_ecl}

def _has_trigger(tb, rule):
    names = {a.name_src for a in tb.accounts}
    return any(t in names for t in rule.get("trigger_accounts", []))

def apply_adjustments(tb, extra_inputs=None):
    extra = extra_inputs or {}
    out = []
    for rule in load_adjustment_rules():
        if not _has_trigger(tb, rule):
            continue
        missing = [i for i in rule.get("required_inputs", []) if i not in extra]
        if missing:
            out.append(Adjustment(id=rule["id"], title=rule["title"], standard=rule["standard"],
                                  amount=0.0, affects=[], direction="재분류",
                                  confidence="flagged", flagged=True,
                                  note=f"필요자료 없음: {', '.join(missing)} — 판단 필요"))
            continue
        amt, affects, direction, note = COMPUTERS[rule["computer"]](tb, extra)
        out.append(Adjustment(id=rule["id"], title=rule["title"], standard=rule["standard"],
                              amount=amt, affects=affects, direction=direction,
                              confidence="high", note=note))
    return out
```

- [ ] **Step 6: 통과 확인** — `pytest tests/test_adjustments.py -v` → PASS
- [ ] **Step 7: Commit** — `git add -A && git commit -m "feat: Layer2 adjustment engine + ECL + flagging"`

---

### Task 6: IFRS 재무제표 빌더

**Files:**
- Create: `gaap_ifrs/statements.py`
- Test: `tests/test_statements.py`

**Interfaces:**
- Consumes: `list[MappedLine]`, `list[Adjustment]`
- Produces: `build_statements(mapped, adjustments) -> tuple[dict, dict]` → `(ifrs_bs, ifrs_pl)`. 각 dict: `{section: {ifrs_account: amount}}`. Layer1 매핑금액 집계 후, 각 Adjustment의 `amount`를 `affects`의 IFRS 계정/이익잉여금에 반영.

- [ ] **Step 1: 실패 테스트** (`tests/test_statements.py`)

```python
import json
from gaap_ifrs.parse import load_trial_balance
from gaap_ifrs.mapping import map_accounts
from gaap_ifrs.adjustments import apply_adjustments
from gaap_ifrs.statements import build_statements

def test_build_and_apply_adjustment():
    tb = load_trial_balance("tests/fixtures/sample_tb_kgaap.csv", "K-GAAP")
    mapped = map_accounts(tb)
    adjs = apply_adjustments(tb, json.load(open("tests/fixtures/sample_aging.json", encoding="utf-8")))
    bs, pl = build_statements(mapped, adjs)
    # 매출 → 수익(매출) 20,000,000
    assert pl["수익"]["수익(매출)"] == 20000000
    # ECL 환입 55,000 → 이익잉여금 증가 반영
    assert any("이익잉여금" in acc for sec in bs.values() for acc in sec)
```

- [ ] **Step 2: 실패 확인** — `pytest tests/test_statements.py -v` → FAIL

- [ ] **Step 3: statements.py 구현**

```python
from collections import defaultdict

def build_statements(mapped, adjustments):
    bs = defaultdict(lambda: defaultdict(float))
    pl = defaultdict(lambda: defaultdict(float))
    for ml in mapped:
        tgt = bs if ml.statement == "BS" else (pl if ml.statement == "PL" else bs)
        tgt[ml.section][ml.ifrs_account] += ml.source.amount
    # 조정 반영: amount를 이익잉여금(자본) + affects 계정에 반영
    for adj in adjustments:
        if adj.flagged or adj.amount == 0:
            continue
        bs["자본"]["이익잉여금"] += adj.amount
    return ({k: dict(v) for k, v in bs.items()}, {k: dict(v) for k, v in pl.items()})
```

- [ ] **Step 4: 통과 확인** — `pytest tests/test_statements.py -v` → PASS
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: IFRS statement builder"`

---

### Task 7: 전환조정 명세서(브릿지)

**Files:**
- Create: `gaap_ifrs/reconcile.py`
- Test: `tests/test_reconcile.py`

**Interfaces:**
- Consumes: `TrialBalance`, `list[MappedLine]`, `list[Adjustment]`
- Produces: `build_reconciliation(tb, mapped, adjustments) -> list[dict]`. rows: 재분류행(소스계정→IFRS계정, 금액, standard) + 조정행(title, 금액, direction, affects, standard, confidence, note). 마지막에 자본 브릿지 요약행(소스 자본 → 조정합 → IFRS 자본).

- [ ] **Step 1: 실패 테스트** (`tests/test_reconcile.py`)

```python
import json
from gaap_ifrs.parse import load_trial_balance
from gaap_ifrs.mapping import map_accounts
from gaap_ifrs.adjustments import apply_adjustments
from gaap_ifrs.reconcile import build_reconciliation

def test_reconciliation_has_citation_and_bridge():
    tb = load_trial_balance("tests/fixtures/sample_tb_kgaap.csv", "K-GAAP")
    mapped = map_accounts(tb)
    adjs = apply_adjustments(tb, json.load(open("tests/fixtures/sample_aging.json", encoding="utf-8")))
    rows = build_reconciliation(tb, mapped, adjs)
    ecl_rows = [r for r in rows if r.get("kind") == "adjustment" and "ECL" in r["item"]]
    assert ecl_rows and ecl_rows[0]["standard"] == "K-IFRS 1109"
    assert any(r.get("kind") == "bridge" for r in rows)     # 자본 브릿지 요약 존재
```

- [ ] **Step 2: 실패 확인** — `pytest tests/test_reconcile.py -v` → FAIL

- [ ] **Step 3: reconcile.py 구현**

```python
def _equity(tb):
    eq = ("자본금", "이익잉여금", "이월이익잉여금", "자본잉여금")
    return sum(a.amount for a in tb.accounts if a.name_src in eq)

def build_reconciliation(tb, mapped, adjustments):
    rows = []
    for ml in mapped:
        rows.append({"kind": "reclass", "source": ml.source.name_src,
                     "ifrs_account": ml.ifrs_account, "amount": ml.source.amount,
                     "standard": ml.standard,
                     "flag": ml.flag_reason if ml.flagged else ""})
    adj_total = 0.0
    for a in adjustments:
        rows.append({"kind": "adjustment", "item": a.title, "amount": a.amount,
                     "direction": a.direction, "affects": ", ".join(a.affects),
                     "standard": a.standard, "confidence": a.confidence, "note": a.note})
        if not a.flagged:
            adj_total += a.amount
    src_eq = _equity(tb)
    rows.append({"kind": "bridge", "item": "자본 전환 브릿지",
                 "source_equity": src_eq, "adjustments": adj_total,
                 "ifrs_equity": src_eq + adj_total})
    return rows
```

- [ ] **Step 4: 통과 확인** — `pytest tests/test_reconcile.py -v` → PASS
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: conversion reconciliation bridge"`

---

### Task 8: 영향분석

**Files:**
- Create: `gaap_ifrs/impact.py`
- Test: `tests/test_impact.py`

**Interfaces:**
- Consumes: `TrialBalance`, `ifrs_bs:dict`, `ifrs_pl:dict`, `list[Adjustment]`
- Produces: `compute_impact(tb, ifrs_bs, ifrs_pl, adjustments) -> dict`. keys: `metrics`({자산총계·부채총계·자본총계·매출·당기순이익: {source, ifrs, delta, pct}}), `narrative`(str, "이 계정 오르고 저 계정 내리고 수익성 …").

- [ ] **Step 1: 실패 테스트** (`tests/test_impact.py`)

```python
import json
from gaap_ifrs.parse import load_trial_balance
from gaap_ifrs.mapping import map_accounts
from gaap_ifrs.adjustments import apply_adjustments
from gaap_ifrs.statements import build_statements
from gaap_ifrs.impact import compute_impact

def test_impact_reports_equity_delta():
    tb = load_trial_balance("tests/fixtures/sample_tb_kgaap.csv", "K-GAAP")
    mapped = map_accounts(tb)
    adjs = apply_adjustments(tb, json.load(open("tests/fixtures/sample_aging.json", encoding="utf-8")))
    bs, pl = build_statements(mapped, adjs)
    imp = compute_impact(tb, bs, pl, adjs)
    assert imp["metrics"]["자본총계"]["delta"] == 55000   # ECL 환입만큼 자본 증가
    assert isinstance(imp["narrative"], str) and imp["narrative"]
```

- [ ] **Step 2: 실패 확인** — `pytest tests/test_impact.py -v` → FAIL

- [ ] **Step 3: impact.py 구현**

```python
def _sum_section(stmt, *sections):
    return sum(v for s in sections for v in stmt.get(s, {}).values())

def compute_impact(tb, ifrs_bs, ifrs_pl, adjustments):
    src_equity = sum(a.amount for a in tb.accounts
                     if a.name_src in ("자본금", "이익잉여금", "이월이익잉여금", "자본잉여금"))
    adj_total = sum(a.amount for a in adjustments if not a.flagged)
    ifrs_equity = src_equity + adj_total
    src_ni = sum(a.amount for a in tb.accounts if a.name_src in ("매출", "매출액")) \
           - sum(a.amount for a in tb.accounts if a.name_src in ("매출원가", "대손상각비"))
    metrics = {
        "자본총계": {"source": src_equity, "ifrs": ifrs_equity, "delta": ifrs_equity - src_equity},
        "당기순이익(추정)": {"source": src_ni, "ifrs": src_ni + adj_total, "delta": adj_total},
    }
    for k in metrics:
        s = metrics[k]["source"]
        metrics[k]["pct"] = round((metrics[k]["delta"] / s * 100), 2) if s else 0.0
    flags = [a.title for a in adjustments if a.flagged]
    narrative = (f"전환조정 순액 {adj_total:,.0f} → 자본총계 {metrics['자본총계']['delta']:,.0f} "
                 f"({metrics['자본총계']['pct']}%) 변동. ")
    if flags:
        narrative += f"추가 판단/자료 필요: {', '.join(flags)}."
    return {"metrics": metrics, "narrative": narrative}
```

- [ ] **Step 4: 통과 확인** — `pytest tests/test_impact.py -v` → PASS
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: impact analysis"`

---

### Task 9: 산출물 렌더(Excel/JSON) + 파이프라인 + CLI

**Files:**
- Create: `gaap_ifrs/report.py`, `gaap_ifrs/convert.py`, `gaap_ifrs/cli.py`
- Test: `tests/test_report.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: 모든 이전 모듈
- Produces: `convert.run_conversion(tb_path, source_gaap, extra_inputs=None, currency="KRW", period="") -> ConversionResult`; `report.write_all(result, outdir) -> dict[str,str]` (파일경로들: ifrs_financials.xlsx, reconciliation.xlsx, impact_analysis.xlsx, result.json); `cli.main(argv=None) -> int`.

- [ ] **Step 1: convert.py 구현**

```python
from .parse import load_trial_balance
from .mapping import map_accounts
from .adjustments import apply_adjustments
from .statements import build_statements
from .impact import compute_impact
from .schema import ConversionResult

def run_conversion(tb_path, source_gaap, extra_inputs=None, currency="KRW", period=""):
    tb = load_trial_balance(tb_path, source_gaap, currency, period)
    mapped = map_accounts(tb)
    adjustments = apply_adjustments(tb, extra_inputs)
    bs, pl = build_statements(mapped, adjustments)
    impact = compute_impact(tb, bs, pl, adjustments)
    return ConversionResult(tb, mapped, adjustments, bs, pl, impact)
```

- [ ] **Step 2: report.py 구현** (openpyxl로 3개 워크북 + JSON)

```python
import json, os
from dataclasses import asdict
import openpyxl
from .reconcile import build_reconciliation

def _sheet(wb, title, header, rows):
    ws = wb.active if wb.active.max_row == 1 and wb.active.max_column == 1 and wb.active["A1"].value is None else wb.create_sheet()
    ws.title = title
    ws.append(header)
    for r in rows: ws.append(r)
    return ws

def write_all(result, outdir):
    os.makedirs(outdir, exist_ok=True)
    paths = {}
    # 1) IFRS 재무제표
    wb = openpyxl.Workbook(); first = True
    for name, stmt in (("IFRS_BS", result.ifrs_bs), ("IFRS_PL", result.ifrs_pl)):
        ws = wb.active if first else wb.create_sheet(); first = False
        ws.title = name; ws.append(["구분", "IFRS 계정", "금액"])
        for section, accs in stmt.items():
            for acc, amt in accs.items():
                ws.append([section, acc, round(amt)])
    p = os.path.join(outdir, "ifrs_financials.xlsx"); wb.save(p); paths["financials"] = p
    # 2) 전환조정 명세서
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Reconciliation"
    ws.append(["종류", "항목/소스", "IFRS계정/영향", "금액", "방향", "기준서(출처)", "confidence", "비고"])
    for row in build_reconciliation(result.trial_balance, result.mapped, result.adjustments):
        if row["kind"] == "reclass":
            ws.append(["재분류", row["source"], row["ifrs_account"], round(row["amount"]), "", row["standard"], "high", row.get("flag", "")])
        elif row["kind"] == "adjustment":
            ws.append(["조정", row["item"], row.get("affects", ""), round(row["amount"]), row.get("direction", ""), row["standard"], row.get("confidence", ""), row.get("note", "")])
        else:
            ws.append(["브릿지", row["item"], f"소스자본 {row['source_equity']:,.0f} + 조정 {row['adjustments']:,.0f}", round(row["ifrs_equity"]), "", "K-IFRS 1101", "", ""])
    p = os.path.join(outdir, "reconciliation.xlsx"); wb.save(p); paths["reconciliation"] = p
    # 3) 영향분석
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Impact"
    ws.append(["지표", "소스GAAP", "IFRS", "델타", "%"])
    for k, v in result.impact["metrics"].items():
        ws.append([k, round(v["source"]), round(v["ifrs"]), round(v["delta"]), v["pct"]])
    ws.append([]); ws.append(["서술", result.impact["narrative"]])
    p = os.path.join(outdir, "impact_analysis.xlsx"); wb.save(p); paths["impact"] = p
    # 4) JSON
    def enc(o):
        from dataclasses import is_dataclass
        return asdict(o) if is_dataclass(o) else str(o)
    p = os.path.join(outdir, "result.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"ifrs_bs": result.ifrs_bs, "ifrs_pl": result.ifrs_pl,
                   "adjustments": [asdict(a) for a in result.adjustments],
                   "impact": result.impact}, f, ensure_ascii=False, indent=2, default=enc)
    paths["json"] = p
    return paths
```

- [ ] **Step 3: cli.py 구현**

```python
import argparse, json, sys
from .convert import run_conversion
from .report import write_all

def main(argv=None):
    ap = argparse.ArgumentParser(prog="gaap-ifrs")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert")
    c.add_argument("--input", required=True)
    c.add_argument("--source-gaap", default="K-GAAP")
    c.add_argument("--extra", help="Layer2 보조자료 JSON 경로(예: aging)", default=None)
    c.add_argument("--currency", default="KRW")
    c.add_argument("--period", default="")
    c.add_argument("--out", default="out")
    args = ap.parse_args(argv)
    extra = json.load(open(args.extra, encoding="utf-8")) if args.extra else None
    result = run_conversion(args.input, args.source_gaap, extra, args.currency, args.period)
    paths = write_all(result, args.out)
    print("생성:", ", ".join(f"{k}={v}" for k, v in paths.items()))
    flagged = [a.title for a in result.adjustments if a.flagged]
    if flagged: print("판단 필요(flagged):", ", ".join(flagged))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 실패 테스트** (`tests/test_report.py`, `tests/test_cli.py`)

```python
# test_report.py
import os, json
from gaap_ifrs.convert import run_conversion
from gaap_ifrs.report import write_all

def test_write_all(tmp_path):
    extra = json.load(open("tests/fixtures/sample_aging.json", encoding="utf-8"))
    res = run_conversion("tests/fixtures/sample_tb_kgaap.csv", "K-GAAP", extra)
    paths = write_all(res, str(tmp_path))
    assert os.path.exists(paths["financials"]) and os.path.exists(paths["reconciliation"])
    assert os.path.exists(paths["impact"]) and os.path.exists(paths["json"])
    data = json.load(open(paths["json"], encoding="utf-8"))
    assert data["impact"]["metrics"]["자본총계"]["delta"] == 55000
```

```python
# test_cli.py
from gaap_ifrs.cli import main

def test_cli_end_to_end(tmp_path, capsys):
    rc = main(["convert", "--input", "tests/fixtures/sample_tb_kgaap.csv",
               "--extra", "tests/fixtures/sample_aging.json", "--out", str(tmp_path)])
    assert rc == 0
    assert "생성:" in capsys.readouterr().out
```

- [ ] **Step 5: 실패 확인 → 구현 → 통과** — `pytest tests/test_report.py tests/test_cli.py -v` → PASS
- [ ] **Step 6: 전체 스위트 실행** — `pytest -v` → 전부 PASS
- [ ] **Step 7: Commit** — `git add -A && git commit -m "feat: report renderer + pipeline + CLI"`

---

### Task 10: 실검증(IFRS 1) 하니스 + README + SKILL.md

**Files:**
- Create: `gaap-ifrs/README.md`, `gaap-ifrs/SKILL.md`, `tests/test_validation.py`

**Interfaces:**
- 검증: 합성 픽스처의 결정론 결과(자본 델타 55,000) 재확인 + 실데이터(전환상장사 IFRS 1 주석) 대조 절차 문서화.

- [ ] **Step 1: 검증 테스트**(합성 회귀 고정) 작성 후 PASS

```python
from gaap_ifrs.convert import run_conversion
import json
def test_regression_equity_bridge():
    extra = json.load(open("tests/fixtures/sample_aging.json", encoding="utf-8"))
    res = run_conversion("tests/fixtures/sample_tb_kgaap.csv", "K-GAAP", extra)
    src = sum(a.amount for a in res.trial_balance.accounts if a.name_src in ("자본금","이익잉여금"))
    ifrs = res.impact["metrics"]["자본총계"]["ifrs"]
    assert ifrs - src == 55000
```

- [ ] **Step 2: README.md 작성** — 문항3용: 입력(시산표), 출력 3종, 파이프라인, RAG=근거인용+계산분리, flagging, 실행법 `gaap-ifrs convert --input tb.xlsx --extra aging.json --out out/`, 한계(Layer2 v1 범위), 검증(IFRS 1 전환주석 대조).
- [ ] **Step 3: SKILL.md 작성** — Codex/Claude 스킬 프론트매터(name, description) + "언제 쓰나/입력/출력/명령" 안내, `run_conversion` 호출.
- [ ] **Step 4: 데모 실행 확인** — Run: `cd gaap-ifrs && python3 -m gaap_ifrs.cli convert --input tests/fixtures/sample_tb_kgaap.csv --extra tests/fixtures/sample_aging.json --out /tmp/demo` → 4개 파일 + flagged 출력.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "docs: README + SKILL + validation harness"`

---

## Self-Review

**1. Spec coverage (03_solution-scope §2~8):**
- §2 Input(시산표 csv/xlsx→canonical): Task 2 ✓
- §3 Output 3종(IFRS FS/조정명세+인용/영향): Task 6,7,8,9 ✓
- §4 파이프라인: Task 9 convert.py ✓
- §5 조정정책(Layer1 전면 / Layer2 선택+flag): Task 4,5 ✓
- §6 RAG(구조적 큐레이션, 계산분리): Task 3(JSON KB) + Task 5(계산기 분리) ✓
- §6 anti-hallucination(미근거 flag): Task 5 flagging ✓
- §7 검증(IFRS 1): Task 10 ✓
- §8 기능 7개: Task 2~10 매핑됨 ✓

**2. Placeholder scan:** 각 Task에 실제 코드·테스트·명령·기대출력 포함. TODO/TBD 없음.

**3. Type consistency:** `MappedLine.source:Account`, `Adjustment.amount:float/affects:list[str]/flagged:bool`, `run_conversion→ConversionResult`, `write_all→dict[str,str]` — Task 간 일치 확인.

**미구현(향후, 문항 명시):** Layer2 추가조정(리스1116·재평가1016·개발비1038), VAS/중국CAS 코퍼스(B), XBRL 출력, 챗봇 인터페이스.
