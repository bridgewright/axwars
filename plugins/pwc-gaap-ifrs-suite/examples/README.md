# 예제 — 소스 GAAP별 K-IFRS 변환 (입력 + 출력)

각 폴더는 하나의 소스 회계기준 변환 사례다. **입력과 출력이 함께** 들어 있어 그대로 열어볼 수 있다. 재생성: `python3 examples/build_examples.py`.

| 폴더 | 소스 GAAP | 이 사례에서 드러나는 GAAP 차이 |
|---|---|---|
| `kgaap/` | 일반기업회계기준(K-GAAP) | 6개 측정조정(ECL·재평가·개발비·리스·확정급여·금융상품) 전부 계산 → 자본 50,000,000 → 56,341,074 |
| `usgaap/` | US GAAP | LIFO 금지·재평가모형 불가·개발비 비용화 등 미국 차이. 대손충당금 보유 → **ECL 환입 +160,000** |
| `vas/` | 베트남 VAS | 공정가치·ECL 개념 제한. 충당금 없음 → **ECL 신규인식 −140,000** |
| `cas/` | 중국 CAS(ASBE) | 원가모형 원칙·수익 인식시점 차이 |

## 각 폴더 파일

**입력**
- `input_trial_balance.csv` — 소스 GAAP 시산표
- `input_adjustments.json` — Layer 2 보조자료(연령표·재평가·개발비 등)

**출력**
- `ifrs_financials.xlsx` — 변환된 K-IFRS 재무상태표·손익계산서
- `reconciliation.xlsx` — 전환조정 명세서(재분류·조정별 **기준서 출처 인용** + 자본 브릿지)
- `impact_analysis.xlsx` — 자산·부채·자본 소스 vs IFRS 델타
- **`difference_analysis.md`** — 계정별 "이전 GAAP은 이렇고 IFRS는 이러니 챙겨야 한다" 분석 보고서
- `result.json` — 기계판독용

## 실기업 검증에 대해 (정직 고지)

예제 입력은 **대표 시나리오**다. 특정 기업의 실제 전/후(previous GAAP ↔ IFRS) 대조표는 비공개(또는 첫 K-IFRS 주석에만 존재)라, **숫자까지 맞춘 실기업 검증**은 그 기업의 IFRS 1101 전환조정 정답셋을 확보하면 `gaap_ifrs.validate.validate_against`로 수행한다(다조정 전환 실증: `gaap-ifrs/tests/fixtures/transition_*` + `analysis/validate_transition_demo.py`). US/VAS/CAS도 동일 — 차이 지식은 공개 비교가이드로 근거화돼 있으나, 개별 기업의 숫자 대조표는 공개 데이터 한계가 있다.
