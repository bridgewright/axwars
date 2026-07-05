---
name: gaap-ifrs-converter
description: 소스 GAAP(일반기업회계기준·베트남 VAS·중국 CAS·미국 US GAAP) 시산표를 K-IFRS로 변환해 IFRS 재무제표·전환조정 명세서(기준서 인용)·계정별 상세 차이분석·영향분석을 산출한다. 회계기준 전환 자문, GAAP→IFRS 변환, 상장전환/해외자회사 연결 전환, "이 계정이 IFRS에서 어떻게 바뀌고 수익성·자본에 어떤 영향" 류 요청에 사용.
---

# GAAP → K-IFRS 변환 스킬

## 언제 쓰나
- 로컬 GAAP(한국 일반기업회계기준·베트남 VAS·중국 CAS·미국 US GAAP) 재무제표를 K-IFRS로 전환해야 할 때.
- 계정 재분류·측정조정과 그 **기준서 근거**, 그리고 **손익·자본 파급효과**를 함께 원할 때.

## 입력
1. **시산표** — `.csv`/`.xlsx` (계정명 + 금액). 콤마·괄호(음수) 자동 처리.
2. (선택) **보조자료 JSON** — Layer 2 측정조정용. 예: 채권 연령표(`aging_schedule`)·리스 스케줄(`lease_schedule`)·재평가(`revaluation`)·개발비(`dev_capitalization`)·확정급여(`defined_benefit`)·금융상품(`financial_instruments`).

## 출력
`out/` 에:
- `ifrs_financials.xlsx` — 변환된 K-IFRS 재무상태표·손익계산서
- `reconciliation.xlsx` — 전환조정 명세서(재분류·조정별 소스→IFRS계정·금액·방향·**기준서 출처**·confidence + 자본 전환 브릿지)
- **`difference_analysis.md`** — 회계사용 상세 보고서: 계정(Layer 1)·조정(Layer 2)마다 **IFRS/이전 GAAP 조항 근거(문단) + 핵심 차이 + 판단 논리 + 분개 파급효과(자산·부채·자본·당기순이익이 얼마 움직이는지)** 를 **단위와 함께** 설명
- `impact_analysis.xlsx`, `result.json`

조항 근거는 `gaap_ifrs/data/*.json`의 `basis`(ifrs_ref/requires·prev_gaap·difference·reasoning)에서 온다. 인용 조항 번호·요건은 확립된 기준서 기준이며, 최종 제출 시 공식 원문과 대조해야 한다.

## 실행
```bash
cd gaap-ifrs && pip install -e .        # 최초 1회 (openpyxl만 의존)
gaap-ifrs convert \
  --input <시산표.csv|xlsx> \
  --source-gaap K-GAAP \
  --extra <보조자료.json> \             # 선택
  --out out/
```
설치 없이 실행:
```bash
cd gaap-ifrs && python3 -m gaap_ifrs.cli convert --input <시산표> --source-gaap K-GAAP --out out/
```
코드에서:
```python
from gaap_ifrs.convert import run_conversion
from gaap_ifrs.report import write_all
res = run_conversion("tb.xlsx", "K-GAAP", extra_inputs={...})
write_all(res, "out/")
```

바로 볼 수 있는 완성 예제는 `examples/<kgaap|usgaap|vas|cas>/` — 입력(시산표·보조자료)과 출력(재무제표·명세서·`difference_analysis.md`)이 한 폴더에 있다. 재생성: `python3 examples/build_examples.py`.

## 판단 기준 / 안전장치
- **지식 = 근거, 계산 = 코드 (분리).** 규칙(어떤 IFRS 기준·조항)은 데이터 JSON에서 인용하고, **숫자는 결정론적 파이썬**이 계산 → 재현·검증 가능. LLM은 숫자를 생성하지 않는다.
- 각 조정은 **복식부기 `entries`** 로 자산·부채·자본을 정확히 이동(자산=부채+자본 균형을 코드가 강제).
- 매핑 규칙 없는 계정, 보조자료 부족한 조정은 **금액을 지어내지 않고 `flagged`("판단/추가자료 필요")** 로 표기. 사용자는 flagged 항목을 사람이 검토해야 한다.

## 지원 범위
- **Layer 1(재분류·매핑): 전면 자동** — 시산표만으로 전 계정 IFRS 표시체계 매핑(K-GAAP 49·US GAAP 26·CAS 17·VAS 14 계정). 주요 계정 10종은 조항 근거(`basis`) 포함.
- **Layer 2(인식·측정): 6개 자동** — ECL(1109)·운용리스(1116)·유형자산 재평가(1016)·개발비 자본화 요건(1038)·확정급여(1019)·금융상품 공정가치(1109 FVPL/FVOCI). 보조자료 없으면 flag.

## 한계
수익인식(1115)·자산손상(1036)·연결 다자회사 매핑·XBRL/DSD 출력은 규칙 파일로 확장 가능한 향후 범위. 산출물은 **전문가 검토용 초안**이며 감사의견·법적 효력을 갖지 않는다.
