# 트랙2 (회계기준 원문 RAG 챗봇) — 재개 문서

**최종 갱신:** 2026-07-08 (청커 대개편 + 전 GAAP 재적재 완료. 남은 것: VAS 출처 재라벨, 답변 고도화 스킬)

## 현재 상태 — ✅ 청커/코퍼스 대개편 완료 (커밋 `4dfebf9`까지)
- **전 GAAP 재적재(정합 코드):** K-IFRS 6,115 · **K-GAAP 2,001(HWP)** · CAS 1,626 · VAS 1,180 = **10,922문단**
  - **전수 결함 0**: 페이지푸터·후행헤딩·헤딩전용·leak 모두 0. **내용 손실 0**(전 GAAP coverage 통과 = 정공법 핵심).
  - **K-GAAP은 PDF→HWP 전환**: PDF 공백소실 복원(`13.1 이 장의 목적은…`) + **실무지침 tier 보존**(적용지침 612). 표 내용은 HWP 한계로 생략(`<표>` 제거, 문서화).
  - 벡터 재빌드: `corpus/vectors/index.faiss`(IndexFlatIP, 10,922, 16MB, **gitignore — 제출 zip엔 포함**). 제출본 `~/Desktop/submission-pwc.zip` 17.11MB(≤100MB).
  - 테스트: 트랙2 **130** · 트랙1 **34** 통과.
- **청커 수정 기법(모두 무손실, `chunk.py`/`fidelity.py`/`segment.py`):** 페이지푸터 제거 · 후행 절/장 제목을 문단 text→다음 문단 heading으로 재귀속 · 목차(TOC) 화이트리스트(`extract_toc_headings`) · 종결부호 가드 · K-GAAP 접두어 폴백(`split_sections_kgaap`의 실N·결N·사례N·소N) · `<표>`/`附件` chrome 일관 제거 · 구역 끝 dangling 헤딩을 마지막 레코드 heading에 보존.
- **남은 긴 헤딩 꼬리(무손실):** 목차 미등재 17~24자 절 제목 일부가 문단에 남을 수 있음(내용 손실 아님). 폰트로도 구분 불가 확인. 필요시만 추가 정밀화.
- 계획서: `docs/superpowers/plans/2026-07-08-corpus-chunker-answer-quality.md`.

## ▶ 다음 작업 (사용자 지시: 1 → 2 순서로 진행)

### 1. VAS 출처 QĐ 재라벨 (메타만, 텍스트 불변)
- **확정 사실:** VAS 저장 텍스트 = 공식 VBPL 법령 원문 verbatim(kreston `/vbpl/`는 정확한 미러). kreston 페이지가 "toàn văn pháp luật chính thức" 명시. VAS 01 = QĐ 165/2002/QĐ-BTC, 발행 Bộ Tài chính. **재수집 불필요, 출처 표기만 공식 QĐ로.**
- **할 일:** `sources.py`의 VAS 각 표준 `url`(현 `docs.kreston.vn/...`)을 발행 결정문(QĐ 149/2001·165/2002·234/2003·12/2005·100/2005) + Bộ Tài chính로 재라벨. **QĐ별 표준 매핑은 각 kreston 페이지의 자기명시 메타를 WebFetch로 확인해 정확히**(추측 금지). 그 후 `run_ingest --gaap VAS --no-vectors` 재적재 + 벡터 재빌드.
- 주의: `run_ingest`는 `std.get("url", src.get("url",""))` 폴백 지원(K-IFRS서 추가). VAS도 GAAP-level url 또는 per-std url 가능.

### 2. 답변 고도화 스킬 (Phase 9 — `skills/gaap-standards-qa/SKILL.md`)
- **설계(계획서 Phase 9):** 계층형 답변 = [원문 verbatim+출처] + [해석(검색근거·라벨)] + [실무(적용지침 tier 검색)] + [GAAP 비교(각 GAAP 실제 검색·인용, 미검색은 명시)] + [유의]. **원문 층 불변, 해석은 검색결과에만 근거, 미검색은 "근거 없음".**
- 다중검색 전략 + 상호작용(단순조회=원문+간단해석+심화옵션 제안 / 분석요청=전체 계층 / 모호=의도 1개 질문). 선택: MCP `compare_across_gaap` 도구.
- 검증: 프롬프트 배터리(단순 원문조회~복잡 분석~근거없음).

**커밋 규칙:** `git add -A -- .` 03-ax-wars-pwc 경로한정(형제 프로젝트 오염 금지). 재적재는 `run_ingest --gaap <G> --no-vectors` 후 마지막에 벡터 통합 재빌드(`build_vectors(load_corpus('corpus'),'corpus/vectors')`).

**Codex 라이브 검증(2026-07-08 완료):** MCP 등록·서버·검색 모두 정상 확인. `codex mcp list` enabled, Codex가 tool_search로 도구 발견·라우팅, 동일 env 단독 stdio 왕복은 K-IFRS 1116.22 원문 정확 반환. **첫 호출 콜드스타트(~8s)는 서버 시작 시 임베딩 모델 백그라운드 프리워밍으로 제거**(`__main__.py`+`vectors.py`, 7.8s→1.55s, 커밋 `db84874`, 테스트 119 통과). **단, `codex exec`(비대화형)는 approval=never 강제라 MCP 승인프롬프트가 즉시 취소**됨("user cancelled", duration 0) → MCP 데모는 **대화형 `codex` TUI**로. 상세: 메모리 [[codex-exec-cannot-invoke-mcp]].

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
