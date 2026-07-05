# gaap-ifrs — 로컬 GAAP → K-IFRS 변환 엔진

소스 GAAP **시산표를 넣으면** → **K-IFRS 재무제표 + 전환조정 명세서(근거 인용) + 계정별 상세 차이분석 + 영향분석**을 산출하는, 근거기반 회계기준 변환 엔진. 지원 소스 GAAP: 일반기업회계기준(K-GAAP)·베트남(VAS)·중국(CAS)·미국(US GAAP) → K-IFRS.

## 누가·왜 쓰나

삼일PwC Assurance LOS의 **회계기준 전환 자문** 실무자. 병목 = "로컬 GAAP과 IFRS를 둘 다 깊게 아는 희소 시니어". 이 엔진이 반복적 재분류·조정 초안과 근거 인용을 자동 생성해 **주니어가 시니어 일을 하게** 만든다(전문성 민주화). 대상: 비상장 IPO 상장전환(A), 해외 자회사 로컬 GAAP→K-IFRS 연결(B, 향후).

## 입력

- **시산표** (`.csv` / `.xlsx`) — 계정명 + 금액 컬럼 자동감지, 콤마·괄호(음수) 처리.
- (선택) **Layer 2 보조자료** (`.json`) — 예: 채권 연령표(`aging_schedule`)가 있으면 ECL을 계산, 없으면 플래그.
- **XBRL은 입력이 아님** — 대상은 전환 前이라 DART XBRL이 없다. (XBRL 출력은 향후 확장.)

## 출력 (3종 + JSON)

1. `ifrs_financials.xlsx` — K-IFRS 재무상태표/손익계산서
2. `reconciliation.xlsx` — **전환조정 명세서**: 재분류·조정별 (소스→IFRS계정, 금액, 방향, **기준서 출처**, confidence, 비고) + 자본 전환 브릿지
3. `difference_analysis.md` — **회계사용 상세 보고서**: 계정·조정마다 IFRS/이전 GAAP **조항 근거(문단)** + 핵심 차이 + 엔진의 판단 논리 + **분개 파급효과(어떤 계정이 얼마 움직여 자산·부채·자본·손익이 어떻게 변하는지)** 를 **단위와 함께** 설명. 근거는 `data/*.json`의 `basis`에서 온다.
4. `impact_analysis.xlsx` — 자본총계·순이익 등 소스 vs IFRS 델타 + 서술
5. `result.json` — 기계판독용

## 실행

```bash
pip install -e .            # openpyxl만 의존
gaap-ifrs convert --input tb.xlsx --extra aging.json --out out/
# 또는: python3 -m gaap_ifrs.cli convert --input ... --out out/
```

## 동작 (절차·지식·판단)

파이프라인: `parse → map(Layer1) → adjust(Layer2) → build → reconcile → impact → report`.

- **지식/RAG = 벡터DB 없는 구조적 큐레이션.** 계정→IFRS 매핑과 조정 규칙은 `gaap_ifrs/data/*.json`에 **기준서 인용과 함께** 저장. 정확·인용가능·감사가능.
- **anti-hallucination = 검색과 계산의 분리.** 규칙(어떤 IFRS 기준)은 데이터에서 인용, **숫자는 결정론적 코드**가 계산. LLM이 숫자를 생성하지 않는다.
- **정보 부족 시 동작:** 매핑 없는 계정 → `flagged`("매핑규칙 없음"). 조정에 필요한 보조자료 없음 → `flagged`("판단/추가자료 필요"), **금액을 지어내지 않고 0으로 두고 표기**.

## 조정 범위 (Layer 정책)

- **Layer 1(재분류·매핑): 전면 자동** — 시산표만으로 가능. K-GAAP 매핑 KB 49개 계정(`data/mapping_kgaap.json`), 그중 주요 10개 계정은 조항 근거(`basis`) 포함.
- **Layer 2(인식·측정): 6개 구현 (선택 자동 + 플래그)** — 복식부기 `entries`로 자산·부채·자본을 정확히 이동:
  - **ECL** 대손충당금→기대신용손실 (K-IFRS 1109) — 채권 연령표 필요
  - **리스** 운용리스→사용권자산·리스부채 (K-IFRS 1116) — 리스료 PV 할인 + **다년 경과 P&L 패턴차(정액 감가상각 + 유효이자 vs 기존 정액 임차료)** 로 순이익 전진배분 반영
  - **유형자산 재평가** (K-IFRS 1016) — 공정가치 상승분→재평가잉여금(자산별 지원)
  - **개발비 자본화 요건** (K-IFRS 1038) — 요건 미충족분 비용화
  - **확정급여** 퇴직급여충당부채→순확정급여부채 (K-IFRS 1019) — PBO−사외적립자산
  - **금융상품 공정가치** (K-IFRS 1109) — FVPL→당기손익, FVOCI→기타포괄손익
  - 각 조정은 **보조자료 없으면 계산하지 않고 플래그**("판단/추가자료 필요").

## 검증

- **합성 회귀:** `pytest` 34 케이스 (파싱·매핑·조정 6종·명세·영향·리포트·CLI·VAS·CAS·US GAAP·KB·검증기).
- **검증기(`gaap_ifrs/validate.py`):** 엔진 산출 IFRS 자본·조정별 금액을 **IFRS 1101 전환조정 정답셋과 대조**(일치/불일치 판정). `validate_against(result, ground_truth)`.
- **실데이터 절차:** K-GAAP→K-IFRS **전환 상장사**의 마지막 K-GAAP 감사보고서를 입력으로, 첫 K-IFRS 주석의 **IFRS 1101 전환조정 명세**를 정답으로. 전환주석은 `analysis/fetch_ifrs1_note.py`로 DART에서 페치(best-effort — 문서구조 편차로 특정 전환사 지정 시 안정적). IFRS 1101이 해당 명세를 의무 공시하므로 정답셋이 공개 존재.

## 확장 로드맵 (corpus-pluggable)

소스 GAAP = "코퍼스+매핑 규칙" 플러그(`data/mapping_<gaap>.json`). `load_mappings(source_gaap)`로 전환.
- **구현:** K-GAAP(48계정) · **베트남 VAS(14계정)** · **중국 CAS/ASBE(17계정)** — `mapping_kgaap/vas/cas.json`. (중국 = 국내 대기업 해외자회사 밀집 1위 로컬GAAP, `analysis/overseas_subsidiary_country_ranking.md` 근거)
- **다음:** 미국 US GAAP(공개 비교가이드 짙음) → 인도네시아 PSAK → 일본 J-GAAP 등.

## 한계

수익인식(1115)·자산손상(1036) 등 잔여 조정 자동화·연결 다자회사 매핑·XBRL/DSD 출력·챗봇 인터페이스는 향후 범위. 산출물은 **전문가 검토용 초안**이며 감사의견·법적 효력을 갖지 않는다.
