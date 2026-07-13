# axwars — 실제 기업의 병목을 푸는 Claude Code / Codex 플러그인

서로 다른 산업의 실제 기업 세 곳을 골라, 공개 자료만으로 그 회사의 구조적 병목을 정의하고, 코딩 에이전트 플러그인으로 구현하고 검증한 프로젝트 모음. 각 플러그인은 "문제를 좁게 정의하고 → 작동하는 도구로 만들고 → 검증 하니스로 조인다"는 같은 방식으로 만들어졌다.

| 플러그인 | 도메인 | 무엇을 하나 | 검증 |
|---|---|---|---|
| [kakaopaysec-incident-response](plugins/kakaopaysec-incident-response/) | 증권 · 규제 대응 | 전자금융사고 발생 직후, 사고 입력 한 번으로 금감원 사고보고서(공식 서식 PDF)·고객 공지·이사회 보고·개인정보 유출 신고·대응 시한 대시보드를 생성 | 법적 시나리오 판정 14/14 일치, 실제 공개 장애 8건 재현, pytest 25건 |
| [pwc-gaap-ifrs-suite](plugins/pwc-gaap-ifrs-suite/) | 회계 · 자문 | 4개국 GAAP 시산표 → K-IFRS 변환 엔진 + 회계기준 원문 10,922문단 grounded RAG 챗봇(로컬 MCP 하이브리드 검색) | 자동 테스트 177건(변환 47 + 검색·인용 130) |
| [alfboard](plugins/alfboard/) | B2B SaaS · CX | AI 상담 에이전트 도입 전, 고객사 현업 4개 그룹을 음성 인터뷰해 배포 계획서와 제품 인풋 문서를 자동 생성 | 스키마 계약 결정적 검증, 9인 인터뷰 완성 예시, 콜드 스타트 약 2초 |

## 설치

**Claude Code**

```bash
claude plugin marketplace add bridgewright/axwars
claude plugin install kakaopaysec-incident-response@axwars   # 또는 pwc-gaap-ifrs-suite, alfboard
```

**Codex**

```bash
git clone https://github.com/bridgewright/axwars.git
codex plugin marketplace add ./axwars
codex plugin add alfboard@axwars                             # 또는 다른 플러그인
```

플러그인별 요구 사항(Python 의존성, API 키)과 사용법은 각 폴더의 README에 있다.

## 공통 설계 원칙

1. **문제는 공개 자료로 정의한다.** 각 기업의 사업·재무·규제 환경을 조사해 구조적 병목을 찾고, 그 병목 중 플러그인이라는 형태로 가장 잘 풀 수 있는 범위까지 문제를 좁힌다.
2. **LLM과 결정적 코드의 역할을 나눈다.** LLM은 자유텍스트에서 구조를 추출하고 문서를 집필한다. 날짜·금액·규정 판정 같은 틀리면 안 되는 계산은 결정적 코드가 수행한다.
3. **불확실하면 추측하지 않는다.** 확보하지 못한 값은 '미상'·'판단 필요'·'근거 없음'으로 표시하고, 스키마 검증에 실패한 데이터로는 산출을 거부한다.
4. **검증 하니스를 함께 만든다.** 시나리오 재현, 정합성 검증기, 자동 테스트가 설계를 고치게 한다. 각 README의 "어떻게 검증했나"에 과정을 남겼다.

## 안내

- 세 플러그인은 언급된 기업들과 무관한 개인 프로젝트이며, 모든 수치·규정·기준 원문은 공개 자료에 근거한다.
- 모든 산출물은 담당자·전문가 검토용 초안이며 법적 효력을 갖지 않는다.
