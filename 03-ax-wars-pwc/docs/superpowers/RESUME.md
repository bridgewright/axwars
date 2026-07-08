# 트랙2 (회계기준 원문 RAG 챗봇) — 재개 문서

**최종 갱신:** 2026-07-08 (청커 대개편 + VAS 재라벨 + 답변 스킬 + **트랙1 근거 grounding** + zip 재빌드 완료. 남은 것: 선택적 US-GAAP 원격 확장 문서화뿐)

## 현재 상태 — ✅ 코퍼스·출처·답변스킬·근거 grounding 완료 (커밋 `3a381f0`까지)

### 트랙1 근거 grounding 완료 (2026-07-08, 커밋 `2e4dc99`→`074be90`→`b0c1a85`→`3a381f0`)
- **무엇:** 컨버터 `difference_analysis.md`의 IFRS 조항 근거를 손으로 쓴 패러프레이즈 대신 **로컬 코퍼스 원문(verbatim)** 으로 grounding(엔진-side·결정론). 아키텍처 정리: 규정 텍스트 단일 원천=코퍼스, `data/*.json`엔 포인터(`ifrs_ref`)만 primary.
- **어떻게:** 신규 `gaap-ifrs/gaap_ifrs/basis_grounding.py`(파서+리졸버, `_ensure_importable`로 설치상태 무관 `gaap_standards_mcp.corpus` **읽기전용** 재사용) → `difference_report._basis_block(basis,corpus)` 원문 삽입/폴백 → `report.write_all(...,corpus_dir)` · `cli --corpus-dir`(자동탐색). 미조회/코퍼스 부재 → "큐레이션 요약 — 코퍼스 원문 미확인" 라벨 폴백(지어내지 않음).
- **MCP/스킬1 불변:** `gaap_standards_mcp/**` 0줄. **회귀 게이트 통과: 트랙1 47 · 트랙2 130 · MCP 스모크 · standalone 폴백 · 결정론.** (게이트가 Task2 유입 계약회귀 `근거를 찾지 못함`도 잡아 `3a381f0`로 수정.)
- **설계·계획:** `docs/superpowers/specs/2026-07-08-skill2-basis-grounding-design.md` · `plans/2026-07-08-skill2-basis-grounding.md`. 제출 zip 재빌드 **17.17MB**.
- **다음 확장(선택):** prev_gaap도 포인터 추가 시 grounding, 미지원 조정 MCP 폴백, 대화형(스킬-side) 층.

### 이번 세션 완료 (2026-07-08, 커밋 `220bc57`→`723bc2f`→`4c750fa`)
- **Task 1 — VAS 출처 재라벨(`220bc57`):** VAS source_url을 kreston 펌 URL → 공식 발행결정문 `"Bộ Tài chính, Quyết định số N/Y/QĐ-BTC"`로 전환(1180문단, 텍스트·id·벡터 불변=메타만). decision_no 삼중검증(레지스트리·kreston헤더·웹 đợt1~5 일치). day-level 날짜는 출처충돌(đợt3 30/31, 100/2005 25/28)로 인용에서 생략(추측 금지), decision_date는 provenance 보존. `run_ingest.ingest_vas`가 decision_no로 source_url 구성. 벡터 재빌드 불필요 확인(스모크 검색 정합).
- **Task 2 — 답변 고도화 스킬(`723bc2f`):** `skills/gaap-standards-qa/SKILL.md` 계층형 개편. §0 안전 2단 분리(사실층=검색 원문만 / 해설층=라벨 붙인 해석), §2 다중검색, §3 계층 템플릿([원문]+[해석]+[실무]+[GAAP비교]+[유의]), §4 상호작용, §5 정직, §6 예시. 프롬프트 배터리 6계층 MCP 실증 통과.
- **마무리(`4c750fa`):** README·submission/README 통계 11,083→10,922·테스트 130 동기화. 제출 zip 재빌드 `~/Desktop/submission-pwc.zip` **17.12MB**(4코퍼스+갱신 SKILL+유효 벡터 포함).

### 그 이전 (커밋 `4dfebf9`까지) — 청커/코퍼스 대개편
- **전 GAAP 재적재(정합 코드):** K-IFRS 6,115 · **K-GAAP 2,001(HWP)** · CAS 1,626 · VAS 1,180 = **10,922문단**
  - **전수 결함 0**: 페이지푸터·후행헤딩·헤딩전용·leak 모두 0. **내용 손실 0**(전 GAAP coverage 통과 = 정공법 핵심).
  - **K-GAAP은 PDF→HWP 전환**: PDF 공백소실 복원(`13.1 이 장의 목적은…`) + **실무지침 tier 보존**(적용지침 612). 표 내용은 HWP 한계로 생략(`<표>` 제거, 문서화).
  - 벡터 재빌드: `corpus/vectors/index.faiss`(IndexFlatIP, 10,922, 16MB, **gitignore — 제출 zip엔 포함**). 제출본 `~/Desktop/submission-pwc.zip` 17.11MB(≤100MB).
  - 테스트: 트랙2 **130** · 트랙1 **34** 통과.
- **청커 수정 기법(모두 무손실, `chunk.py`/`fidelity.py`/`segment.py`):** 페이지푸터 제거 · 후행 절/장 제목을 문단 text→다음 문단 heading으로 재귀속 · 목차(TOC) 화이트리스트(`extract_toc_headings`) · 종결부호 가드 · K-GAAP 접두어 폴백(`split_sections_kgaap`의 실N·결N·사례N·소N) · `<표>`/`附件` chrome 일관 제거 · 구역 끝 dangling 헤딩을 마지막 레코드 heading에 보존.
- **남은 긴 헤딩 꼬리(무손실):** 목차 미등재 17~24자 절 제목 일부가 문단에 남을 수 있음(내용 손실 아님). 폰트로도 구분 불가 확인. 필요시만 추가 정밀화.
- 계획서: `docs/superpowers/plans/2026-07-08-corpus-chunker-answer-quality.md`.

## ▶ 다음 작업 — Task 1·2 완료. 남은 것은 선택적 US-GAAP 확장뿐

- **Task 1(VAS 출처 재라벨)·Task 2(답변 고도화 스킬) = 완료**(위 "이번 세션 완료" 참조, 커밋 `220bc57`/`723bc2f`/`4c750fa`). 제출 zip 재빌드까지 끝.
- **선택 잔여:** US-GAAP 원격 확장점 문서화(아래 Pending §3, 작음·비필수). 그 외 미착수 필수 작업 없음.
- 재개 시: 코퍼스·스킬·zip 모두 최신이므로 새 요청부터 시작. 통계는 10,922문단·테스트 130 기준.

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

### 1·2. VAS 코퍼스 + 통합 마무리 — ✅ 완료 (더 이상 할 일 없음)
- VAS 4번째 GAAP 적재(1180문단)·재임베딩·제출 zip·README 4-GAAP 갱신 모두 완료됨. 표행 vs 목록행 세그멘터 버그도 해결. 출처는 2026-07-08 Task 1에서 공식 QĐ로 재라벨. **재실행 금지(이미 최신).**

### 3. E4 — US GAAP ASC 원격 확장점 문서화(작음, 선택) — 유일한 잔여
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
