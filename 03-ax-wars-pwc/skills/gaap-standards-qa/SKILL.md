---
name: gaap-standards-qa
description: 회계기준(K-IFRS·일반기준·US GAAP·중국 CAS·베트남 VAS) 원문 질의응답. "이 계정 IFRS에서 어떻게", "리스 어떻게 인식", "US GAAP과 차이", "CAS 규정" 등 회계기준 규정을 물으면 반드시 이 스킬로 MCP를 검색해 원문 인용으로 답한다.
---

# 회계기준 원문 Q&A (grounded)

회계기준 규정 질문에는 **반드시 아래 계약을 지킨다. 추측·학습지식으로 답하지 않는다.**

1. **선(先)검색:** 먼저 MCP `search_standards(query, gaap?, tier?, top_k)`를 호출한다. (MCP 불가 시 `python -m gaap_standards_mcp.entry corpus "<질문>"`.)
2. **원문만 근거:** 반환된 문단의 `text`(원어 원문 그대로)만 근거로 답한다. 인용은 verbatim, 인용 끝에 `[출처: {gaap} 제{standard_no}호 문단 {paragraph_no} · {source_url}]`.
3. **한국어 답변 + 번역병기:** 설명은 한국어. 원어 인용에 한국어 번역을 달 때 **"비공식 번역(원문 우선)"** 라벨을 붙인다.
4. **근거 없음(근거를 찾지 못함):** 검색 결과가 없거나 무관하면 **"원문에서 근거를 찾지 못했습니다(근거 없음)"** 라고 답하고 지어내지 않는다.
5. **다관할 비교:** 여러 GAAP을 물으면 각 GAAP 원문을 나란히 인용한다.
6. **caveat:** 결과에 `extract_flag=true`인 문단이 있으면 "추출 검증 필요" 꼬리표를, `mode`가 `degraded`/`no-mcp`면 "키워드(BM25) 검색만 동작 중"임을 고지한다.
7. **커버리지 정직:** 특정 기준서가 적재됐는지 물으면 `list_standards`로 확인해 답한다.
