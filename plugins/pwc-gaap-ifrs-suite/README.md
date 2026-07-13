# pwc-gaap-ifrs-suite — GAAP ↔ K-IFRS 전환·조회 스위트

여러 나라 회계기준의 시산표를 한국채택국제회계기준(K-IFRS)으로 바꾸는 자문 실무를 돕는 Claude Code / Codex 플러그인. 독립적인 두 트랙을 한 플러그인에 묶었다.

| 트랙 | 무엇을 하나 | 핵심 디렉터리 |
|---|---|---|
| **트랙 1** | 소스 GAAP(K-GAAP·US GAAP·CAS·VAS) 시산표 → K-IFRS 변환 엔진. 재무제표·전환조정 명세서(조항 근거를 코퍼스 원문으로 grounding)·손익 및 자본 영향분석을 산출 | `gaap-ifrs/`, `skills/gaap-ifrs-converter/`, `examples/` |
| **트랙 2** | 회계기준 원문 grounded RAG 챗봇. 로컬 MCP 하이브리드(BM25+벡터) 검색으로, 검색된 문단의 verbatim 인용 없이는 답하지 않음 | `gaap_standards_mcp/`, `tools/ingest/`, `corpus/`, `skills/gaap-standards-qa/` |

두 트랙은 같은 문제 — **회계기준 전환·조회 실무가 로컬 GAAP과 K-IFRS를 둘 다 아는 희소한 시니어에 의존하는 병목** — 를 다른 각도로 푼다. 트랙 1은 정해진 6개 측정조정을 확정 답으로 자동화하고, 트랙 2는 정해지지 않은 어떤 조항이든 원문 검색으로 대응한다. 두 트랙은 한 코퍼스를 공유한다 — 트랙 1의 각 조정 근거는 트랙 2 코퍼스의 원문(verbatim)으로 grounding된다(엔진 측 결정론, 코퍼스에 없으면 "큐레이션 요약"으로 명시).

> 삼일PwC의 회계기준 전환 자문 서비스를 사례로 설계했지만, 이 저장소는 해당 법인과 무관한 개인 프로젝트이며 모든 수치와 기준 원문은 공개 자료에 근거한다.

## 누가, 어떤 상황에서 쓰나

회계법인 감사본부에서 회계기준 전환 자문을 맡는 담당자, 주로 주니어부터 매니저까지. 두 상황을 겨냥한다.

1. 비상장 회사가 상장을 준비하며 일반기업회계기준(K-GAAP)을 K-IFRS로 바꿔야 하는 경우
2. 국내 대기업이 베트남·중국 등 해외 자회사의 현지 기준(VAS·CAS)을 모회사 K-IFRS로 합쳐 연결 재무제표를 만드는 경우

타겟 페인포인트는 받은 시산표를 K-IFRS 계정으로 다시 나누고 대손·리스·자산 재평가 같은 측정 차이를 조정하는 일이다. 지금은 현지 기준과 K-IFRS를 모두 아는 드문 시니어에게만 일이 몰려, 시니어의 검토를 기다리는 동안 진도가 정체된다. 특히 상장 전환에서는 계정과 손익 구조가 크게 바뀌어 한 곳만 잘못 조정해도 뒤 단계까지 재작업이 발생한다.

이 플러그인이 있으면 주니어가 명령어 한 줄로 초안과 조항 근거, 손익 및 자본 영향을 바로 확보한다. 자료가 없는 항목은 '판단 필요'로 표시되어 실수를 예방하고, 챗봇은 산출물에 틀린 조항 번호나 문구가 들어가는 위험을 차단한다. 사람은 검토와 판단이라는 더 가치 높은 일에 집중한다.

## 왜 이 문제인가

- **감사의 범용화**: 감사 수임료는 내려가는데 인건비는 매출보다 빠르게 늘어, 대형 회계법인의 영업이익률이 몇 년 만에 4.29%에서 1.60%로 하락했다. 감사는 이미 값이 낮고 엑셀 매크로와 자체 도구로 자동화도 많이 된 영역이다.
- **방향**: 그래서 목표를 감사 원가 절감이 아니라 **고마진 자문의 확대 — 드문 시니어의 전문성을 누구나 쓰게 만드는 것**으로 잡았다.
- **왜 회계기준 전환 자문인가**: 첫째, 회계법인이 실제로 판매 중인 서비스다. 둘째, 양쪽 기준을 다 아는 전문가가 희소해 AI의 레버리지가 크다. 셋째, 기준 원문과 비교 자료가 공개되어 있어 지어내지 않고 근거를 제시할 수 있다.
- **수요**: 2022년부터 해외 자회사까지 묶어 연결 재무제표를 만들 의무가 생겨, 자회사가 많은 중국·베트남 기준의 전환 수요가 늘고 있다.

**근거 자료**

- [삼일PwC 회계기준 전환 서비스](https://www.pwc.com/kr/ko/assurance/private-accounting.html) · [삼일 IFRS 허브](https://www.pwc.com/kr/ko/ifrs.html)
- [빅4 매출과 감사보수 하락](https://www.asiae.co.kr/article/2025112410431116375) · [감사 가격 경쟁과 AI 저가입찰](https://www.investchosun.com/site/data/html_dir/2026/03/17/2026031780157.html)
- [해외 자회사 연결 의무](https://www.insidevina.com/news/articleView.html?idxno=20386)
- [PwC IFRS 대 US GAAP 가이드](https://viewpoint.pwc.com/dt/us/en/pwc/accounting_guides/ifrs_and_us_gaap_sim/assets/pwcifrsusgaap0326.pdf) · [K-GAAP 대 K-IFRS 전환 가이드](https://clobe.ai/blog/k-gaap-vs-k-ifrs-ipo-financial-indicators)

## 어떻게 작동하나

**트랙 1 (변환 엔진)** — 시산표를 받아 표준 형태로 정리하고(`parse`), 계정을 K-IFRS 체계로 다시 나누고(`map`), 대손·리스·유형자산 재평가·개발비·확정급여·금융상품 여섯 가지 측정 차이를 조정한다(`adjust`). 각 조정은 차변과 대변으로 나눠 자산=부채+자본 균형을 코드가 강제한다. 이어 K-IFRS 재무제표, 전환조정 명세서, 손익 및 자본 영향, 계정별 상세 보고서를 순서대로 산출한다(`build → reconcile → impact → report`). 어떤 기준의 어느 조항을 쓸지는 규칙 파일(`gaap-ifrs/gaap_ifrs/data/*.json`)에 정리해 두고, 그 조항의 실제 문장은 코퍼스 원문에서 그대로 가져와 보고서에 붙인다.

**트랙 2 (원문 챗봇)** — 질문이 오면 먼저 로컬 MCP 서버(`search_standards`·`get_paragraph`·`get_context`·`list_standards` 4개 도구)로 원문을 검색하고, 찾은 문단만 출처와 함께 verbatim 인용한다. 답변은 원문 인용을 먼저 두고 뜻풀이, 실무 적용, 다른 나라 기준 비교를 라벨로 나눠 단계적으로 확장한다. 검색은 단어 일치(BM25)와 의미 유사(벡터)를 함께 쓰되 점수 스케일이 달라 순위 기준으로 융합(rank fusion)한다.

**공통 원칙 — 추측 금지**

- 숫자와 조항 문장은 AI 생성 대상에서 제외한다. 숫자는 사람이 정한 규칙에 따라 코드가 계산하고, 조항은 코퍼스 원문에서만 가져온다.
- 필요한 자료가 없으면 금액을 지어내지 않고 '판단 필요'로 표시한다. 원문에서 근거를 못 찾으면 '근거 없음'으로 답한다. 코퍼스에 아직 없는 조항은 요약본임을 밝힌다.
- 검색 기능이 일부만 되는 환경에서도 자동으로 더 단순한 방식으로 전환해 계속 동작한다(하이브리드 → BM25 단독 → 내장 스크립트의 3단 폴백). 어떤 경로로 답했는지 항상 고지한다.

## 설치

Python 3.11+.

```bash
# Claude Code
claude plugin marketplace add bridgewright/axwars
claude plugin install pwc-gaap-ifrs-suite@axwars

# Codex — 저장소 클론 후
codex plugin marketplace add ./axwars
codex plugin add pwc-gaap-ifrs-suite@axwars

# Python 의존성
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

**샘플 산출물** — 실행 없이 기능을 이해하려면 `samples/`(트랙 1 변환 보고서 + 트랙 2 챗봇 답변 예시)부터 보면 된다.

## 코퍼스

`corpus/`에 4개 소스 GAAP **10,922문단** — K-IFRS(63기준서·6,115) · 일반기업회계기준(36장·2,001) · 중국 CAS(95문서·1,626) · 베트남 VAS(26기준서·1,180) — 이 zstd 압축 원문(`kifrs/kgaap/cas/vas.jsonl.zst`)으로 동봉되어 있다. 인용용 원문(`text`)과 검색용 정규화 텍스트(`text_norm`)를 이중 저장해, 인용이 원문과 한 글자도 달라지지 않게 했다. 다국어 임베딩으로 교차언어 검색이 가능하다(중국어 질의로 CAS 원문 검색 실측). 벡터 인덱스는 최초 실행 시 로컬에서 빌드하며, 재빌드는:
```bash
python -m tools.ingest.run_ingest --gaap K-IFRS --download-dir downloads --corpus-dir corpus
```

## 테스트

```bash
PYTHONPATH=. python -m pytest -q       # 트랙 2: 130 케이스 (BM25·벡터·RRF융합·MCP 4도구·3단 폴백·GAAP별 세그멘터·leak/shadow 게이트·경계 게이트·corpus·manifest 등)
cd gaap-ifrs && python -m pytest -q    # 트랙 1: 47 케이스 (파싱·매핑·조정 6종·명세·영향·CLI·근거 grounding·검증기)
```

## 어떻게 검증했나

**입력→결과 예시** — 트랙 1은 일반기업회계기준 시산표와 보조자료를 넣으면 여섯 개 조정을 계산해 자본총계를 5,000만에서 5,634만으로 산출하고, 각 조정의 원문 근거와 분개 효과를 보고서에 기록한다. 트랙 2는 리스 인식을 물으면 K-IFRS 제1116호 22문단 원문을 그대로 인용해 답한다.

**정상과 예외** — 보조자료가 없으면 계산 대신 '판단 필요'로 표시하는지, 검색 결과가 없으면 '근거 없음'으로 답하는지, 검색이 일부만 되는 환경에서 폴백이 동작하는지를 각각 미리 만든 상황으로 확인했다.

**되짚어서 고친 것** — 다 만들었다고 판단한 뒤 실제로 써 보니 인용 원문이 문단 단위로 제대로 나뉘지 않은 것을 발견했다. 처음에는 일부만 조사해 고치려 했으나 전수조사로 바꾸자 훨씬 많은 결함이 나왔고, 새 분할 방식으로 다시 나눌 때도 한 번에 끝내지 않고 조금씩 나눠 중간중간 확인하며 반영했다. 그 결과 원문에 페이지 번호나 절 제목이 섞이던 문제까지 제거했다. 최종적으로 자동 테스트 177건(트랙 1 47 + 트랙 2 130)으로 아웃풋을 고정했다.

**남은 한계** — 실제 회사 시산표는 구할 수 없어 회계기준과 일반 사례로 입력 예제를 직접 만들어 검증했다. 수익 인식·자산 손상 같은 나머지 측정 조정은 확장이 필요하다.

## 설계 노트

- **AI에 맡긴 것**: 대상 도메인의 사업·재무 조사(감사·딜·컨설팅 부문별 매출과 영업이익 변화), 지저분한 엑셀에서 계정 이름을 맞추는 초안, 문서에서 문단을 잘라내는 규칙 초안, 검색을 붙이는 반복 코드.
- **사람이 직접 판단한 것**: 리서치 결과에서 구조적 문제(수임료 하락 + 인력 증가로 수익성 붕괴)를 정의하고, 전략 방향과 세부 문제(회계기준 전환 자문)를 선정한 것. 최종 숫자도 AI가 아니라 사람이 정한 규칙과 코드가 계산한다.
- **설계를 뒤집은 지점**: 처음에는 시산표 변환 도구부터 만들었다. 만들수록 이 용역의 본질이 회계기준 원문을 오류나 지어냄 없이 그대로 가져와 분석하는 데 있음을 깨닫고, 원문을 검색해 인용하는 RAG 챗봇을 먼저 구축한 뒤 변환 도구도 그 원문 검색 기반 위에서 반드시 원문을 참조하도록 다시 설계했다.
- **채택하지 않은 대안**: ① 조정을 자본 영향 숫자 하나로만 두자는 안 — 차변/대변 분개로 나눠야 재무상태표 균형이 확보되므로 거부. ② 검색용 텍스트와 인용용 원문을 한 벌로 저장하자는 안 — 인용이 원문과 한 글자도 달라선 안 되므로 이중 저장. ③ 두 검색 점수를 단순 합산하자는 안 — 스케일이 달라 순위 융합(rank fusion) 채택.

## 정직한 스코프

- 트랙 1은 K-GAAP·US GAAP·CAS·VAS 4개 소스 GAAP의 계정 매핑·조정 규칙을 지원한다(`gaap-ifrs/gaap_ifrs/data/*.json`).
- 트랙 2의 원문 검색 코퍼스는 K-IFRS·일반기업회계기준·중국 CAS·베트남 VAS 4개 적재 완료(`corpus/manifest.json`, GAAP별 전용 세그멘터·leak/shadow 게이트 통과). US GAAP 원문만 원격 확장 지점(asc.fasb.org 봇월 차단)으로 남아 있으며, 계정 매핑까지만 지원한다.
- 임베딩 모델(`intfloat/multilingual-e5-small`)은 용량 문제로 저장소에 포함하지 않는다. 최초 실행 시 캐시로 내려받으며, 실패 시 자동으로 BM25 단독(degraded) 검색으로 동작한다.
- 두 트랙의 산출물은 모두 **전문가 검토용 초안**이며 감사의견·법적 효력을 갖지 않는다.
