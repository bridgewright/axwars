# 코퍼스 정합성(청커·메타) + 답변 고도화 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development(권장) 또는 executing-plans로 task 단위 구현. 실제 구현은 **ultracode Workflow + claude-fable-5** 서브에이전트로 병렬. Steps use checkbox(`- [ ]`).

**Goal:** 4개 GAAP 코퍼스의 verbatim 무결성 결함(헤딩 혼입·페이지푸터 혼입·헤딩전용 레코드·K-GAAP 공백소실)과 출처/기준일 부정확을 제거하고, 검색 위에서 원문+해석+GAAP비교를 계층 분리로 내놓는 답변 고도화까지 완성한다.

**Architecture:** 두 층으로 분리한다. (1) **데이터 층**(`tools/ingest/`): 청커가 문단 span에서 페이지푸터를 제거하고 후행 절/장 제목을 문단 text에서 분리해 `heading` 필드로 재귀속하며, 새 검증 게이트가 이를 강제한다. (2) **에이전트 층**(`skills/gaap-standards-qa/SKILL.md`): 다중검색 + 계층형(원문/해석/실무/GAAP비교) 답변. 두 층은 독립이며 데이터 층 완료 후 에이전트 층을 검증한다. MCP 서버 인터페이스(4 도구)는 유지, 필요 시 교차GAAP 비교 도구만 추가.

**Tech Stack:** Python 3.11, 기존 `tools/ingest/`(extract·segment·chunk·fidelity·sources·run_ingest·embed_index·pack), `gaap_standards_mcp/`, faiss, sentence-transformers(multilingual-e5-small), pytest.

## Global Constraints

- **정공법:** 원문은 verbatim 적재·인용. 효율을 위한 임의 요약·해석·범위축소 금지. 허용 제약은 하드요건(zip ≤100MB 등)뿐.
- **무손실 재배치:** 페이지푸터는 정당 제거(coverage 회계에 반영), 헤딩은 버리지 않고 `heading` 필드로 이동. 원문 문장은 한 글자도 변경·삭제 금지.
- **점진 실행(필수):** 각 Phase = 수정 → 소수만 재청킹 → MCP 직접호출 + 게이트로 검증 → **체크포인트 커밋** → 문제 남으면 그 Phase에서 재수정 후 다음. 전량 일괄 재작업 금지.
- **트랙1 불간섭:** `gaap-ifrs/`는 건드리지 않는다.
- **커밋:** `git add -A -- .`를 03-ax-wars-pwc 경로한정(형제 프로젝트 오염 금지). git 루트는 상위 모노레포.
- **문서 스타일:** 강조는 bold만. 이탤릭 금지.
- **답변 안전:** 원문 층 불변, 해석·비교는 검색결과에만 근거, 미검색은 "근거 없음"/"대응 규정 미검색" 명시.

## 결함 근거(전수 스캔 2026-07-08, 11,083문단)

| 결함 | K-IFRS | K-GAAP | CAS | VAS |
|---|---|---|---|---|
| 후행 헤딩 혼입 | 24.5% | 30.4% | ~9.6%(章) | 9.4% |
| 페이지푸터 혼입 | 31.4% | 30.0% | 0.5% | 0% |
| 헤딩전용/파편 | 0.1% | 2.1% | 9.6% | 2.2% |
| 띄어쓰기 소실 | — | 전체 | — | — |
| source_url | 목록페이지 | 빈값 | per-std(양호) | kreston(firm) |
| as_of | 2025-01-01(오류) | 수집일 | per-std(양호) | per-std(양호) |

단일 원인: `chunk.py:_chunk_region` L313 `text[m.start():end]` — 번호 마커 사이 전부를 앞 문단에 흡수.

## Phase 구조 (각 Phase 독립 커밋 · 검증 후 진행)

| Phase | 내용 | 완료 기준(검증) |
|---|---|---|
| 0 | 조사: K-GAAP 공백 원인(PDF/HWP·복원가능?), VAS kreston vs 공식 VBPL 대조 | 조사 리포트 → P4·P6 세부 확정 |
| 1 | 프리미티브: 푸터제거·헤딩탐지·새 게이트 3종 + 단위테스트 | 픽스처 단위테스트 통과, 재적재 없음 |
| 2 | 파일럿: K-IFRS 1116만 재청킹 | 문단 22/39 MCP 육안 clean + 게이트 통과. **끊고 확인** |
| 3 | K-IFRS 전량(63) 재청킹·재적재 | 전수스캔 헤딩·푸터 0, 기존 테스트 무회귀 |
| 4 | K-GAAP(+공백 P0결과 반영) | 전수스캔 clean |
| 5 | CAS 章제목 경계 | 전수스캔 clean |
| 6 | VAS(+출처 P0결과 반영) | 전수스캔 clean |
| 7 | 메타: K-IFRS url/as_of(2026-01-01)·K-GAAP url·VAS 출처 재라벨 | 메타분포 재확인 |
| 8 | 통합: 재임베딩·재팩·제출zip·전체 pytest·최종 전수스캔 | 결함 0, ≤100MB, 전체 테스트 통과 |
| 9 | 답변 고도화: SKILL.md 계층형 + (선택)compare 도구 + 프롬프트 배터리 검증 | 배터리 단순~복잡 답변 육안 통과 |

> Phase 3~9의 태스크 세부는 Phase 0 결과 확정 후 이 문서에 채운다(공백·출처 처리가 범위를 바꾸므로). 아래는 Phase 0~2 상세 + 9(설계) + 게이트 코드.

---

## Phase 0: 조사 (수정 없음, 결정용)

**Files:** 조사 스크립트는 scratchpad. 결과는 본 문서 "Phase 0 결과" 절에 기록.

- [ ] **0.1 K-GAAP 공백 원인** — `downloads/`의 K-GAAP 제13장 PDF/HWP 확인. `extract(pdf)` vs `extract(hwp)` 텍스트의 공백 보존 비교. PyMuPDF 다른 추출모드(`get_text("words"/"blocks")`)로 공백 복원되는지 시험. 판정: (a) PDF 재추출로 복원 가능 → extract.py 개선, (b) 불가 → HWP 사용 or 대체소스.
- [ ] **0.2 VAS 공식 대조** — thuvienphapluat.vn 또는 MoF 결정문(QĐ 149 등)에서 VAS 01 표본 문단을 받아 kreston 텍스트와 문자 단위 대조. 판정: (a) 동일 → 출처만 공식으로 재라벨(P7), (b) 상이 → 공식으로 재수집(P6 확장).
- [ ] **0.3 결과 기록** 후 P4·P6·P7 태스크 확정.

### Phase 0 결과 (2026-07-08)

- **0.1 K-GAAP 공백 = 확정.** K-GAAP PDF는 한글 단어 사이 공백이 없는 텍스트 레이어(PyMuPDF text·words 모드 모두 복원 불가). HWP는 공백 보존(코퍼스 실측: 제9장 HWP 적재분 `9.1 이 장의 목적은…` 정상 vs 제13장 PDF 적재분 `13.1 이장의목적은…` 소실). **해법: K-GAAP 소스를 HWP로 전환**(sources.py에 `format: "hwp"` GAAP-level 또는 per-std 지정; `file_seq_hwp` 기존 보유). HWP 재다운로드 필요(현재 캐시는 kgaap_9·영문양식만). 아티팩트: 번호 뒤 공백(`9.1이`)은 `normalize_missing_space`가 처리. **트레이드오프: HWP는 표를 `<표>`로 떨굼 → 표 있는 장은 PDF 표를 별도 보완하거나 표 손실을 로깅**(P4에서 처리). → **P4 = K-GAAP 청커 + HWP 재추출**로 확정.
- **0.2 VAS 공식 대조 = 확정.** kreston 페이지가 스스로 "toàn văn pháp luật chính thức"(공식 법령 전문)임을 명시: 문서 Quyết định 165/2002/QĐ-BTC(2002.12.31), 발행 Bộ Tài chính. 공식 đoạn 02 = 우리 저장 텍스트와 **동일 문자열**(thuvienphapluat.vn van-ban은 403 봇차단이라 kreston 자기명시 메타 + 원문 대조로 확인). **결론: 텍스트는 이미 공식 VBPL verbatim → 재수집 불필요, 출처만 재라벨.** → **P7 = 각 VAS standard의 source_url/인용을 발행 QĐ(149/2001·165/2002·234/2003·12/2005·100/2005) + Bộ Tài chính로 재표기**(텍스트 불변). P6 VAS는 청커 경계만.

**Phase 0 종료 — 확정 사항:** P4=K-GAAP HWP 재추출, P6=VAS 청커만, P7=VAS 출처 재라벨(재수집 없음)·K-IFRS as_of 2026-01-01·K-GAAP url 채움.

## Phase 1: 청커 프리미티브 + 게이트 (TDD, 재적재 없음)

**Files:**
- Modify: `tools/ingest/chunk.py`(푸터제거·헤딩분리를 `_chunk_region`에 통합)
- Modify: `tools/ingest/fidelity.py`(새 게이트 3종 + coverage에 푸터 정당제거 반영)
- Test: `tests/test_chunk_boundary.py`(신규)

**Interfaces (Produces):**
- `strip_page_footers(text: str) -> tuple[str, int]` — 푸터 줄 제거한 text와 제거 문자수
- `split_trailing_headings(body_lines: list[str], lang: str) -> tuple[list[str], list[str]]` — (문단본문 줄, 후행헤딩 줄)
- `assert_no_trailing_heading(recs)`, `assert_no_page_footer(recs)`, `assert_no_orphan_heading(recs)` — FidelityError on violation

- [ ] **1.1 실패 테스트: 페이지푸터 제거**

```python
from tools.ingest.chunk import strip_page_footers
def test_strip_page_footers_removes_dashed_and_bare():
    t = "22\n리스이용자는 …인식한다.\n- 19 -\n측정"
    out, removed = strip_page_footers(t)
    assert "- 19 -" not in out
    assert "인식한다." in out and "측정" in out
    assert removed >= 1
```

- [ ] **1.2 구현: `strip_page_footers`**

```python
import re
_PAGE_FOOTER_RE = re.compile(r'^[ \t]*[-–—][ \t]*\d{1,4}[ \t]*[-–—][ \t]*$')  # "- 19 -"
_BARE_PAGENUM_RE = re.compile(r'^[ \t]*\d{1,4}[ \t]*$')                       # 단독 숫자줄
def strip_page_footers(text):
    """대시형 '- N -'는 무조건 제거. 단독 숫자줄은 문단 마커일 수 있어
    여기서는 대시형만 제거하고, 단독 숫자줄은 _chunk_region이 '마커 줄' 판정
    후(=마커가 아닌 경우) 별도로 제거한다(1.3)."""
    kept, removed = [], 0
    for ln in text.split("\n"):
        if _PAGE_FOOTER_RE.match(ln):
            removed += len(ln); continue
        kept.append(ln)
    return "\n".join(kept), removed
```

- [ ] **1.3 실패 테스트 + 구현: 후행 헤딩 분리** — 문단 span의 마지막 줄들이 "문장종결·리스트·표·번호가 아닌 짧은 줄"이면 헤딩으로 분리. 언어별 종결부호 표(ko/zh/vi). 리스트(⑴·-·第N条)·표(|)·번호는 본문. 반환: (본문줄, 헤딩줄).

```python
_SENT_END = {"ko": tuple(".다라함음됨”\")]"), "zh": tuple("。”）】"), "vi": tuple(".”)")}
def _is_heading_line(s, lang):
    s = s.strip()
    if not s or len(s) > 22: return False
    if s[-1] in _SENT_END.get(lang, (".",)): return False
    if re.match(r'^([⑴-⿃()（）0-9①-⑳•·\-]|第[〇零一二三四五六七八九十百千0-9]+[条章节])', s): return False
    if "|" in s: return False
    return True
def split_trailing_headings(body_lines, lang):
    body = list(body_lines); heads = []
    while body:
        last = body[-1]
        if last.strip() == "": body.pop(); continue
        if _is_heading_line(last, lang): heads.insert(0, body.pop().strip())
        else: break
    return body, heads
```

- [ ] **1.4 통합: `_chunk_region`이 span마다 푸터제거→헤딩분리, 헤딩은 다음 문단 `heading`으로** — L299~324 개편. 마커가 아닌 단독 숫자줄도 여기서 제거. 각 piece를 (para_no, body_text, heading_for_next) 형태로 만들고, 직전 piece의 heading을 현재 레코드의 heading에 채운다. `_mk`의 `heading=""` → 전달값.

- [ ] **1.5 실패 테스트 + 구현: 새 게이트 3종** (`fidelity.py`)

```python
def assert_no_trailing_heading(recs):
    from tools.ingest.chunk import _is_heading_line
    bad = [r.id for r in recs
           if (ls:=[l for l in r.text.split("\n") if l.strip()]) and _is_heading_line(ls[-1], r.lang)]
    if bad: raise FidelityError(f"trailing heading in text: {bad[:8]}")
def assert_no_page_footer(recs):
    bad = [r.id for r in recs if _PAGE_FOOTER_RE.search(r.text) is not None
           or any(_BARE_PAGENUM_RE.match(l) for l in r.text.split("\n")[1:])]
    if bad: raise FidelityError(f"page footer in text: {bad[:8]}")
def assert_no_orphan_heading(recs):
    from tools.ingest.chunk import _is_heading_line
    bad=[r.id for r in recs if (b:=" ".join(r.text.split("\n")[1:]).strip()) and len(b)<=18
         and not any(c in b for c in ".。")]
    if bad: raise FidelityError(f"orphan heading record: {bad[:8]}")
```

- [ ] **1.6 coverage 회계 갱신** — `assert_retained_coverage`가 푸터 제거분을 "정당 제거"(frontmatter처럼)로 집계해 coverage 1.0 유지. 헤딩은 `heading` 필드로 남으므로 손실 아님(재구성 검증 시 text+heading 합산).
- [ ] **1.7 전체 단위테스트 + 커밋**

## Phase 2: 파일럿 — K-IFRS 1116만

- [ ] **2.1** 1116만 재청킹하는 임시 스크립트로 recs 생성, 새 게이트 4종(+기존 leak/shadow) 통과 확인.
- [ ] **2.2** MCP 직접호출(scratchpad 스크립트)로 문단 21/22/23/39 원문이 clean한지 육안: 22 = "리스이용자는 리스개시일에 사용권자산과 리스부채를 인식한다." 만, heading="측정"류 별도, "- 19 -" 없음.
- [ ] **2.3** 문제 있으면 Phase 1 프리미티브 재수정 후 반복. **clean 확정 시에만** 커밋하고 Phase 3.

## Phase 3~8 (Phase 0 후 상세화)

- P3 K-IFRS 전량 → P4 K-GAAP(+공백) → P5 CAS(章) → P6 VAS(+출처) → P7 메타 → P8 통합(재임베딩·zip·pytest·최종 스캔). 각 Phase: 재적재 → 전수스캔(해당 GAAP 결함 0) → 커밋.

## Phase 9: 답변 고도화 (에이전트 층, 코퍼스 clean 이후)

**Files:** Modify `skills/gaap-standards-qa/SKILL.md`; (선택) `gaap_standards_mcp/server.py`에 `compare_across_gaap` 도구.

**답변 템플릿(스킬에 명문화):**
```
[원문] "<verbatim>" — [출처: {gaap} 제{no}호 문단 {para}]   (필요 시 복수)
[해석] <검색된 정의·인접문단 근거로 평이하게>  ← "해석" 라벨
[실무] <적용지침 tier 검색 근거>                ← 없으면 생략
[GAAP 비교] K-IFRS: … / K-GAAP: … / CAS: … / VAS: …  ← 각 GAAP 실제 검색·인용, 미검색은 "대응 규정 미검색"
[유의] 전문가 검토용 초안, 감사의견 아님
```

- [ ] **9.1 다중검색 전략 명문화** — 질의 1건에 대해 (핵심조항)+(정의어 검색)+(적용지침 tier 검색)+(gaap별 대응조항 검색). 각 층 사실주장은 반환된 text에만 근거.
- [ ] **9.2 상호작용 규칙** — 단순조회: 원문+2~3줄 해석+"더 깊이: 실무/GAAP비교/사례?" 제안. 분석요청: 전체 계층. 모호: 의도 1개만 질문.
- [ ] **9.3 (선택) `compare_across_gaap(query, top_k=1)`** — 4개 GAAP 각 top 문단을 한 번에 반환(서버가 gaap별 검색 수행). grounded 비교 지원.
- [ ] **9.4 프롬프트 배터리 검증** — 단순 원문조회 / 정의 / 실무적용 / 교차언어(CAS·VAS) / GAAP비교 / 복합분석 / 근거없음 — 각 답변이 원문 불변·해석 라벨·근거 명시·미검색 명시를 지키는지 육안 검토.

## 검증 전략(공통)

- **1차:** 새 게이트 4종 + 기존 leak/shadow/coverage (재적재 halt-on-fail).
- **2차:** 전수 결함 스캔 재실행(해당 GAAP 헤딩·푸터·헤딩전용 0).
- **3차:** MCP 직접호출로 대표 문단 육안(모델 배제).
- **4차(P9):** 프롬프트 배터리로 답변 층·근거·라벨 검토.

## Self-Review 체크

- 스펙 커버리지: 5개 결함(헤딩·푸터·헤딩전용·공백·메타) 전부 Phase 매핑됨(공백=P0→P4, 메타=P7). ✓
- 점진성: 각 Phase 소수 재청킹→검증→커밋, 파일럿(P2) 후 확대. ✓
- 정공법: 원문 무변경, 헤딩 재귀속(무손실), 해석 층 라벨·근거. ✓
