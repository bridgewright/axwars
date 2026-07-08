# intake → brief 계약 (다운스트림 핸드오프)

intake 음성 인터뷰 ①단계의 **산출물**이자, ②단계(brief)의 **입력**이다.

## 다운스트림(brief)이 읽을 것

| 파일 | 용도 | 누가 읽나 |
|------|------|-----------|
| **`output/deployment-discovery.json`** | **기계 입력(계약)** — 배포 결정 슬롯(맥락·병목·자동화 범위·연동·IT 여력·지식·조직·성과·제품 갭·미해결). 스키마 정본 = `discovery-spec.md` | **brief (에이전트 집필 + build_reports.py)** |
| `output/transcript.jsonl` / `interview-notes.md` | 원천 인터뷰(turn 기록) — 근거 추적용 | 감사/추적 |

> 실제 인터뷰 산출물은 `output/`(gitignore)에 쌓인다(PII). 커밋되는 가상 예시는 `assets/sample-discovery.json` + `samples/무브온/`.

## brief가 만드는 것

`deployment-discovery.json` 하나로 두 문서를 만든다:
- **`deployment-brief.md`** — 배포 계획서(배포팀·고객 C레벨용). **에이전트가 `brief/references/deployment-brief-format.md`를 따라 직접 집필**. 7개 섹션(Executive Summary/현황/페인포인트/도입 우선순위/기술 고려/원가·제시가/추가 세일즈).
- **`product-input.prd.md`** — 고객 페인 + PRD 제언서(본진 프로덕트팀용). `brief/scripts/build_reports.py`가 렌더. to-prd 틀 + 제품 갭 태그 분류.

## 검증·재생성
`deployment-discovery.json`은 `scripts/validate_discovery.py` 게이트를 통과한 것이며,
`../brief/scripts/build_reports.py <discovery.json> --out-dir <dir>`로 PRD를 다시 렌더할 수 있다.
배포 계획서는 `brief` 스킬을 호출해 에이전트가 포맷 레퍼런스대로 다시 집필한다.
