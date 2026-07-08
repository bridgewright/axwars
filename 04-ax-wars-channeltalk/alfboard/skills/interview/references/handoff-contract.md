# intake → brief 계약 (다운스트림 핸드오프)

intake 음성 인터뷰 ①단계의 **산출물**이자, ②단계(brief)의 **입력**이다.

## 다운스트림(brief)이 읽을 것

| 파일 | 용도 | 누가 읽나 |
|------|------|-----------|
| **`output/deployment-discovery.json`** | **기계 입력(계약)** — 배포 결정 슬롯(맥락, 병목, 자동화 범위, 연동, IT 여력, 지식, 조직, 성과, 제품 갭, 미해결). 스키마 정본 = `discovery-spec.md` | **brief (에이전트 집필)** |
| `output/transcript.jsonl` / `interview-notes.md` | 원천 인터뷰(turn 기록) — 근거 추적용 | 감사/추적 |

> 실제 인터뷰 산출물은 `output/`(gitignore)에 쌓인다(PII). 커밋되는 가상 예시는 `assets/sample-discovery.json` + `samples/무브온/`.

## brief가 만드는 것

`deployment-discovery.json` 하나로 두 문서를 **에이전트가 직접 집필**한다:
- **`deployment-brief.md`** — 배포 계획서(고객 C레벨용). 포맷: `brief/references/deployment-brief-format.md`. 7섹션(Executive Summary/현황/페인포인트/도입 우선순위/기술 고려/원가/추가 세일즈).
- **`product-input.md`** — 제품 인풋(본진 프로덕트팀용). 고객 페인/니즈 + 제품 개발 시 고려사항. 포맷: `brief/references/product-input-format.md`.

## 검증·집필
`deployment-discovery.json`은 `scripts/validate_discovery.py` 게이트를 통과한 것이며, `brief` 스킬을 호출하면 에이전트가 두 포맷 레퍼런스대로 두 문서를 집필한다.
