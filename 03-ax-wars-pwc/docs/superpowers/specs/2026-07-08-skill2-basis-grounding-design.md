# 스킬 2(변환) 근거 grounding 설계 — 엔진-side, 결정론

**최종 갱신:** 2026-07-08

## Goal

컨버터(트랙 1)가 각 조정의 근거를 **손으로 쓴 패러프레이즈(`ifrs_requires`) 대신 코퍼스 원문(verbatim)** 으로 grounding한 `difference_analysis.md`를 결정론적으로 산출한다. 코퍼스에 없으면 라벨된 폴백. 규정 "텍스트"의 단일 원천을 코퍼스로 일원화하는 아키텍처 정리.

## 확정 결정 (2026-07-08 사용자 승인)

1. **Grounding 위치 = 엔진-side.** convert 엔진이 코퍼스를 직접 읽어 `ifrs_ref`→원문을 보고서 파일에 삽입. 결정론·재현가능·에이전트/ MCP서버 불필요.
2. **패러프레이즈 = 폴백 강등.** 코퍼스 원문 우선; 조회 실패/코퍼스 부재 시에만 `ifrs_requires`를 "(큐레이션 요약 — 코퍼스 원문 미확인)"으로 표시.
3. **이름 = `gaap-ifrs-converter` 유지**, description만 진화.
4. **범위 = ifrs_ref 근거 grounding만.** 계산 숫자·조정 로직·MCP 서버·의미검색은 불변. 미지원 조정 MCP 폴백은 다음 범위.

## Architecture

- **원천 단일화:** 규정 텍스트 = 코퍼스(`corpus/*.jsonl.zst`). `data/*.json`의 `basis`에서 **`ifrs_ref`(포인터)만 primary**로 쓴다.
- **정확 주소 조회(검색 아님):** `ifrs_ref`를 파싱해 `{gaap, standard_no, [문단]}`으로 만들고, `gaap_standards_mcp.corpus.get_paragraph`로 **정확 문단**을 인출한다. 같은 입력 → 바이트 동일(결정론).
- **읽기 전용 재사용:** `gaap_standards_mcp.corpus`의 `load_corpus`/`get_paragraph`를 **읽기 전용으로 재사용**한다. MCP 서버·검색·코퍼스 데이터·스키마는 **0줄 변경**(스킬 1/MCP 무영향이 최우선 제약).
- **가드된 의존:** 코퍼스 로더 import·로드는 `try/except`로 감싼다. `gaap_standards_mcp`/`zstandard` 미설치 또는 `corpus/` 부재 시 `None`→전량 폴백. **트랙 1은 코퍼스 없이도 항상 동작**(standalone 불변).

## Data model (현행, 불변)

`basis: dict` (schema.py `MappedLine`/`Adjustment`):
- `ifrs_ref`: 포인터 문자열. 예 `"K-IFRS 제1109호 문단 4.1.1-4.1.4"`. **← grounding 입구**
- `ifrs_requires`: IFRS 요건 패러프레이즈. **← 폴백으로 강등**
- `prev_gaap`: 이전 GAAP 처리 패러프레이즈(포인터 없음). **← "(큐레이션 요약)" 라벨 유지**
- `difference`, `reasoning`: 엔진의 차이·판단 서술(규정 인용 아님). **← 현행 유지**

데이터 파일은 이번 범위에서 **수정하지 않는다**(ifrs_ref가 이미 존재·정합).

## ifrs_ref 문법 (실측 전수, 14종)

패턴: `K-IFRS 제<std>호 문단 <목록>`
- `<목록>` = 콤마 구분 토큰. 각 토큰은:
  - 단일: `"9"`, `"22"`, `"106"`, `"4.1.2"`, `"4.1.2A"`
  - 범위: `"4.1.1-4.1.4"`, `"5.5.1-5.5.15"` (마지막 점 세그먼트만 증가)
- 예: `"9, 25"` · `"22, 23, 26"` · `"4.1.1-4.1.4, 5.2.1"` · `"4.1.2A, 5.7.5"`

파서 규약: 파싱 불가 → `(None, None, [])` → 폴백(에러 아님). 범위는 공통 접두 + 마지막 점 세그먼트 정수 확장; 확장 불가하면 양 끝점만. 존재하지 않는 문단은 `get_paragraph`가 `None`을 주므로 자동 제외.

## 렌더 규약 (`_basis_block`)

- **코퍼스 조회 성공(1개 이상):**
  ```
  - **IFRS 근거 (코퍼스 원문)**:
      - [K-IFRS 제1109호 문단 4.1.2] "4.1.2 다음 두 가지 조건을 모두 충족한다면 금융자산을 상각후원가로 측정한다. …"
  ```
  일부 문단 미조회 시 말미에 `- (일부 문단 미확인: 5.2.1 — 코퍼스 미적재)`.
- **전량 실패/코퍼스 부재:**
  ```
  - **IFRS 근거 (큐레이션 요약 — 코퍼스 원문 미확인)**: K-IFRS 제1109호 문단 4.1.1-4.1.4 — <ifrs_requires>
  ```
- `prev_gaap` → `- **이전 GAAP (큐레이션 요약)**: <prev_gaap>` (포인터 없어 grounding 불가, 라벨만).
- `difference`/`reasoning` → 현행 유지.
- 코퍼스가 로드된 실행에서는 93행의 "공식 기준서 원문과 대조 필요" 캐비앗을, grounded 항목엔 "**코퍼스 원문 대조 완료**"로 대체(폴백 항목엔 기존 캐비앗 유지).

## Components / 변경 파일

| 범위 | 파일 | 내용 |
|---|---|---|
| 신규 | `gaap-ifrs/gaap_ifrs/basis_grounding.py` | `parse_ifrs_ref`, `_expand_range`, `load_corpus_for_grounding`(가드), `ground_ref` |
| 수정 | `gaap-ifrs/gaap_ifrs/difference_report.py` | `_basis_block(basis, corpus, indent)` grounding+폴백; `build_markdown(result, corpus=None)` |
| 수정 | `gaap-ifrs/gaap_ifrs/report.py` | 코퍼스 1회 로드해 `build_markdown`에 전달 |
| 수정 | `gaap-ifrs/gaap_ifrs/cli.py` | `--corpus-dir`(기본 자동탐색) 추가 |
| 수정 | `gaap-ifrs/SKILL.md` | description: 근거=코퍼스 원문 grounded |
| 신규 | `gaap-ifrs/tests/test_basis_grounding.py` | 파서·리졸버·통합·회귀·결정론 |
| **불변** | `gaap_standards_mcp/**` | **0줄**(읽기 전용 재사용) |
| **불변** | `gaap-ifrs/gaap_ifrs/data/**` | 규칙·계산·ifrs_ref 불변 |

## 코퍼스 위치 해석

기본값 = `Path(__file__).resolve().parents[2] / "corpus"` — dev(`03-ax-wars-pwc/corpus`)·번들(`src/corpus`) 양쪽에서 동일하게 해석됨. `--corpus-dir`로 오버라이드. `manifest.json` 없으면 `None`→전량 폴백.

## Data flow

```
시산표 → [계산: 결정론 엔진 (불변)] → 각 조정 {숫자 + ifrs_ref}
        → [grounding: ifrs_ref → 코퍼스 verbatim (실패 시 라벨 폴백)]
        → difference_analysis.md {숫자 + 원문근거 or 큐레이션 요약}
```

## Non-goals

- 계산 숫자·조정 로직 변경 ✗
- `gaap_standards_mcp/`(MCP 서버·검색) 수정 ✗ — **스킬 1/MCP는 핵심, 무조건 보존**
- 의미검색(정확 주소 조회만) ✗
- 미지원 조정 MCP 폴백 ✗ (다음 범위)
- `data/*.json`의 ifrs_ref/규칙 재작성 ✗
- prev_gaap 원문 grounding ✗ (포인터 부재 — 향후 prev_gaap_ref 추가 시)

## Verification (완료 기준)

1. **grounding 정확:** examples/kgaap 변환 시 grounded 근거가 코퍼스 원문과 **문자 일치**(예: 1109:4.1.2 원문 등장).
2. **폴백 라벨:** 미조회/부재 항목이 "(큐레이션 요약 — 코퍼스 원문 미확인)"으로 표시.
3. **숫자 불변:** 6개 조정 금액·순효과·자본총계(50,000,000→56,341,074) 동일.
4. **두 트랙 무회귀:** 트랙 1 기존 34 + 신규 통과, **트랙 2 130 전량 통과(MCP/스킬 1 무영향 증명)**, MCP 스모크 검색 정상.
5. **결정론:** 같은 입력 → difference_analysis.md 바이트 동일.
6. **standalone 불변:** 코퍼스 없이(또는 gaap_standards_mcp 미설치) 실행 시 전량 폴백으로 정상 산출.
