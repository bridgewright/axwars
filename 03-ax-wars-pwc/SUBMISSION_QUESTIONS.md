# 제출 문항 (README.md 반영용) — 삼일PwC

이 파일은 해커톤(AX 인재전쟁, 대상=삼일PwC) 제출 시 답해야 하는 문항과, 세션 중 문항별로 반영할 핵심 포인트를 보관한다. 나중에 이 노트를 근거로 README.md를 작성한다.

---

## 문항 및 글자수 제한

### 1. 무엇을, 누가, 어떤 상황에서 쓰나요? (800자)
만든 플러그인을 한 문장으로 요약. 이어서 선언한 기업(삼일PwC)의 **누가, 어떤 상황에서, 어디서 막혀** 이 플러그인을 쓰게 되는지 구체적으로.

### 2. 왜 이 문제를 선택했나요? (800자)
이 문제를 고른 이유와, 그 기업의 **직원이나 고객, 또는 해당 산업의 사용자가 실제로 어디서 왜 막히는지**.
- **+ 출처 URL 리스트 필수**

### 3. 플러그인은 어떻게 작동하나요? (1000자)
플러그인이 어떻게 동작하는지, **절차, 지식, 판단 기준**을 어떻게 가져가는지. **정보가 부족하거나 잘 안 풀리는 상황에서의 동작**도 함께.
- 세부 내용은 zip 파일의 **README.md에도** 적혀 있어야 함.

### 4. AI를 어떻게 썼나요? (800자)
AI에게 맡긴 작업과 **직접 판단한 부분을 구분**해서. 막혔던 지점, 해결 과정, **받아들이지 않은 AI 제안과 그 이유**도.

### 5. 어떻게 검증했나요? (800자)
**입력→결과로 이어지는 예시를 하나 이상**. 정상/예외 상황 확인, 무엇을 의심했고 무엇이 아직 부족한지, 테스트하며 고친 점.

---

## 작성 시 반영할 핵심 방향성 (세션 진행 중 기록)

### 전략 방향성 — 왜 "감사 비용절감"이 아니라 "고마진 자문의 자동화"인가 (문항 2 근거)

삼일PwC Assurance LOS의 구조적 문제:
- 감사 수임료 하락(평균 감사보수 −4.5%) + 인건비 증가(매출의 약 73%, 매출 증가율(+15%)보다 인건비 증가율(+18%)이 빠름) → **영업이익률 붕괴(제52기 4.29% → 제54기 1.60%)**. (근거: `01_problem-definition_pwc.md` §2.1, §2.5)

이를 극복하는 전략 방향성 **(이번 세션 결론)**:
- **법정감사 자체의 비용을 줄이는 것을 목표로 삼지 않는다.** 감사는 커모디티화된 저마진 base이고, 이미 엑셀 매크로·자체 AI스택(AURA 등)으로 상당히 최적화돼 AX 여지가 제한적이다. (근거: `02_workflow-automation-gap_pwc.md` — 매크로는 "포맷 고정 반복"을 이미 해결)
- 대신 **Assurance LOS 내 수익성 높은 자문 용역(비감사 용역)의 비중을 높이고**, 그 자문 용역을 **AI/에이전트로 훨씬 낮은 비용에 수행**하는 것을 방향성으로 삼는다.
- 즉 삼일PwC에게 AX의 의미 = "저마진 감사 방어"가 아니라 **"고마진 지식 자문의 레버리지(1인당 산출) 극대화 + 희소 전문가 의존 축소"**. 이는 인재전쟁 테마(시니어 전문성의 민주화)와 정합한다.

### 현재 유력 후보 (문항 1·3)

- **로컬 GAAP → IFRS 전환 자문을 "변환 엔진 + 근거인용 챗봇"으로.**
  - 입력: 로컬 GAAP 재무제표(숫자) → 매핑 규칙 적용(기준서·비교가이드 근거) → 출력: IFRS 재무제표 + 전환조정 명세서 + 손익·자본 영향분석.
  - 병목: "로컬 GAAP + IFRS를 둘 다 깊게 아는 희소 시니어" → 도구로 민주화.
  - 사촌 문제: 연결 재무제표의 이종 계정 매핑(자회사별 다른 ERP·계정과목 → 모회사 IFRS 기준 재분류).
- 할루시네이션 차단: 답변에 **반드시 기준서/가이드 출처 인용**.
- 스코프 조건: **한 GAAP 쌍으로 좁힘**(수요 리서치로 확정 예정).

### 리서치 결과 (문항 2 근거 + 출처)

**1. 삼일은 실제로 이 서비스를 한다 (확인).**
- 삼일 **"재무제표 작성 및 회계기준 전환 지원 서비스"**(Private Accounting) — 일반기업회계기준·K-IFRS·US GAAP 등 **기준별 분석** 명시.
- **IFRS 18 도입 자문**(2027 전후 신기준) — "중견·중소 골든타임" 플랫폼 운영. CoA 세분화·ERP 자동분개·잔액이관 이슈 → 시스템·데이터 헤비 = 우리 엔진과 정합, 타이밍 좋음.
- K-IFRS 기준별 해설 코퍼스(SAMILi.com) 자체 보유.

**2. GAAP 쌍 수요 — 두 포켓 (해외 자회사 가설 검증됨).**
- **(A) K-GAAP(일반기업회계기준) → K-IFRS, 상장(IPO) 전환:** 최대 볼륨(모든 비상장 상장준비사). 공개 가이드 풍부. 임팩트 지표 구체적("K-IFRS 전환 후 재무상태표 계정 53%↓, 손익 59%↓") → "계정 오르내림·수익성 변화" 분석에 그대로 매핑. **데모 최적.**
- **(B) 해외 자회사 로컬 GAAP → K-IFRS 연결 [당신 가설 = 검증됨]:** 2022년부터 한국 지배회사 외감 대상이면 **해외 자회사 포함 연결 의무.** 플래그십 = **베트남(VAS)** — 삼성·LG 등 진출 밀집. 삼일 **동남아 투자자문** 서비스 별도 운영. 기능통화 환산·계정 재분류가 핵심 노가다. 차별화 큼(VAS→K-IFRS 툴 없음) 단 코퍼스는 A보다 희소.

**3. 비교가이드 코퍼스 밀도.**
- **짙음:** IFRS↔US GAAP(PwC "Similarities and Differences" 공개 PDF, 임팩트 평가 포함), K-GAAP↔K-IFRS(다수 국내 가이드), K-IFRS 기준별(SAMILi).
- **옅음:** VAS 등 신흥국 로컬 GAAP(현지어·자료 희소).

**→ 잠정 결론:** 엔진 코어는 **코퍼스 짙은 K-GAAP→K-IFRS(IPO 전환)로 데모**, 아키텍처는 **corpus-pluggable로 설계해 VAS 등 해외 자회사(진짜 상금)로 확장**. "국내 IPO 전환으로 증명 → 해외 자회사 연결로 확장"이 서사.

**출처 (문항 2 URL 리스트용):**
- 삼일 회계기준 전환 서비스: https://www.pwc.com/kr/ko/assurance/private-accounting.html
- 삼일 IFRS 허브: https://www.pwc.com/kr/ko/ifrs.html
- 삼일 IFRS 18 자문(CPA뉴스): https://news.kicpa.or.kr/news/articleView.html?idxno=2837
- 삼일 동남아 투자자문(PDF): https://www.pwc.com/kr/ko/publications/service/samilpwc_south-east-asia-invest-kr.pdf
- 베트남 VAS 연결 의무(인사이드비나): https://www.insidevina.com/news/articleView.html?idxno=20386
- 해외 종속기업 연결 절차(조이회계): https://joy-accounting.netlify.app/2025-08-01-consolidation-overseas/
- K-GAAP↔K-IFRS 전환 가이드: https://clobe.ai/blog/k-ifrs-vs-k-gaap-startup-guide , https://clobe.ai/blog/k-gaap-vs-k-ifrs-ipo-financial-indicators
- K-GAAP→K-IFRS 전환기(afinit): https://blog.afinit.com/K-GAAP-to-IFRS
- PwC IFRS vs US GAAP 가이드(PDF): https://viewpoint.pwc.com/dt/us/en/pwc/accounting_guides/ifrs_and_us_gaap_sim/assets/pwcifrsusgaap0326.pdf
- K-IFRS vs 일반기업회계기준(택스가이드): https://taxguide.im/blog/k-ifrs-vs-k-gaap-comparison
