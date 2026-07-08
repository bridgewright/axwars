# 트랙2 (회계기준 원문 RAG 챗봇) — 재개 문서

**최종 갱신:** 2026-07-08 (4개 소스 GAAP 전량 적재 완료 — Phase E 종료)

## 현재 상태 — ✅ 완료
- **4개 소스 GAAP 원문 코퍼스** (모두 커밋됨)
  - K-IFRS 6,137(63기준서) · 일반기업회계기준 2,101(36장) · 중국 CAS 1,665(95문서) · 베트남 VAS 1,180(26기준서) = **11,083문단**, leak 0·id충돌 0
  - 벡터: `corpus/vectors/index.faiss` (IndexFlatIP, 11,083, 17MB), 교차언어 검색 실측(한국어→K-IFRS/K-GAAP, 중국어→CAS, 베트남어→VAS)
  - US GAAP = 원격 확장점(§8, asc.fasb.org 봇월 차단; `sources.py` mode=remote)
- **제출본:** `~/Desktop/submission-pwc.zip` (17.25MB, ≤100MB) — 트랙1+트랙2, 추출 후 pytest 119 + 검색 스모크 통과
- **테스트:** 트랙2 119 통과 · 트랙1 34 통과
- **워킹트리 clean** (마지막 커밋 `4d55a63`)

**남은 것(선택):** US GAAP 정식 ASC 피드(라이선스 확보 시 원격 연결) · 검색 품질 미세조정(표 뒤섞임 #N siblings) · 실제 Codex 플러그인 로드 테스트. (아래 Pending 섹션은 완료된 이력.)

## Git 체크포인트 (모노레포, 03-ax-wars-pwc 경로한정 커밋)
- `74f905d` READMEs → 3-GAAP + zip 15.5MB (최신)
- `6da6e7d` CAS 코퍼스 · `7410f37` K-GAAP · `d4e96f7` E6 zip · `fcecfe6` E5 벡터(flat) · `e106f32` 세그멘터 일반화+게이트

## 잠긴 결정
- **VAS = 공식 베트남어 원문**(펌 영문 번역본 아님 — verbatim 원칙). 소스: thuvienphapluat.vn(법령DB)/MoF 결정문(QĐ 149·165·234·12·100).
- **제출 폼 글자수 제한 없음** → README 그대로.
- **US GAAP = 원격 확장점**(asc.fasb.org 봇월 차단, zip 내장 불가).

## Pending (순서대로)

### 1. VAS(베트남) 코퍼스 — 4번째 내장 GAAP
- **캐시 있음:** `downloads/vas_*` 26개 파일 이미 다운로드됨(gitignore) → 재다운로드 불필요.
- **알려진 버그(중단 원인):** VAS 세그멘터의 **표 행(table-row) 정규화기가 과하게 동작** — 진짜 불릿 목록 행(예: VAS 21 đoạn 51 재무상태표 line-item 목록)의 파이프(|)까지 제거해, **목록 마커를 문단 마커로 오인**함. 재실행 시 **표 행 vs 목록 행을 구분**하도록 수정해야 함.
- 재실행: 이전 VAS 에이전트 프롬프트 재사용(공식 베트남어·성조부호 보존·모지바케 검출·VAS 세그멘터·leak/shadow 게이트·exclude-don't-ship-broken·무회귀). 산출 `corpus/vas.jsonl.zst`, lang="vi", id `vas:<no>:<đoạn>`.

### 2. VAS 후 통합 마무리
- 전 코퍼스 재임베딩(≈10.6k → 1만 초과라 **PQ 자동 전환**, 학습 충분). `build_vectors(load_corpus('corpus'),'corpus/vectors')`.
- 제출 zip 재빌드(`python tools/build_submission.py`) + README(submission/README.md·README.md) 4-GAAP로 갱신.

### 3. E4 — US GAAP ASC 원격 확장점 문서화(작음)
- `sources.py`에 US-GAAP remote 플래그 + MCP 훅 문서화 + 스펙 §8 반영.

## 핵심 경로
- 스펙: `docs/superpowers/specs/2026-07-05-track2-standards-rag-chatbot-design.md`
- 계획: `docs/superpowers/plans/2026-07-05-track2-standards-rag-chatbot.md`
- 엔진: `gaap_standards_mcp/` (MCP·검색·폴백) · 수집: `tools/ingest/` (extract·segment·chunk·fidelity·sources·embed_index·pack)
- 코퍼스: `corpus/{kifrs,kgaap,cas}.jsonl.zst` + `vectors/` + `manifest.json`
- 세그멘터: `segment.py`는 GAAP별 경로(`*_kgaap`/`*_cas`); VAS 경로는 재실행 시 추가. 게이트: `fidelity.py`의 `assert_no_leak`/`detect_shadows`.

## 재개 시 주의
- 커밋은 항상 `git add -A -- .`(03-ax-wars-pwc 경로한정, 형제 프로젝트 오염 금지). git 루트는 상위 모노레포.
- 서브에이전트는 correctness-critical이라 Sonnet(또는 상위) 권장. 각 GAAP은 게이트가 품질 보호(leak 실패→NEEDS-REVIEW 제외).
