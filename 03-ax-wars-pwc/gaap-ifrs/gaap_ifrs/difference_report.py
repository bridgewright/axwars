"""계정별 '이전 GAAP vs IFRS 차이·유의점' 상세 분석 보고서(Markdown) 생성.

회계사가 이 초안을 기준으로 실제 전환 작업을 하므로, 각 계정·조정마다
(1) 판단 근거가 되는 IFRS/이전 GAAP 조항, (2) 그 차이, (3) 엔진의 판단·작업 논리,
(4) 분개와 파급효과(어떤 계정이 얼마 움직여 자산·부채·자본·손익이 어떻게 변하는지)를
단위와 함께 상세히 적는다. 근거는 큐레이션 코퍼스(data/*.json의 basis)에서 온다.

주의: 조항 인용은 확립된 기준서 기준이나, 최종 제출 시 공식 기준서 원문과 대조해야 한다.
"""

_ASSET = {"유동자산", "비유동자산"}
_LIAB = {"유동부채", "부채"}
_EQUITY = {"자본"}


def _bs_entries(entries):
    return [e for e in entries if e.get("statement") != "PL"]


def _net(entries):
    a = sum(e["delta"] for e in entries if e.get("section") in _ASSET and e.get("statement") != "PL")
    l = sum(e["delta"] for e in entries if e.get("section") in _LIAB and e.get("statement") != "PL")
    q = sum(e["delta"] for e in entries if e.get("section") in _EQUITY and e.get("statement") != "PL")
    ni = sum(e["delta"] for e in entries if e.get("account") == "이익잉여금")
    return a, l, q, ni


def _basis_block(basis, corpus=None, indent=""):
    L = []
    ref = basis.get("ifrs_ref")
    if ref:
        from .basis_grounding import ground_ref
        found, missing = ground_ref(ref, corpus)
        if found:
            L.append(f"{indent}- **IFRS 근거 (코퍼스 원문)**:")
            for f in found:
                L.append(f'{indent}    - [{f["label"]}] "{f["text"]}"')
            if missing:
                L.append(f"{indent}    - (일부 문단 미확인: {', '.join(missing)} — 코퍼스 미적재)")
        else:
            L.append(f"{indent}- **IFRS 근거 (큐레이션 요약 — 코퍼스 원문 미확인)**: "
                     f"{ref} — {basis.get('ifrs_requires', '')}")
    if basis.get("prev_gaap"):
        L.append(f"{indent}- **이전 GAAP (큐레이션 요약)**: {basis['prev_gaap']}")
    if basis.get("difference"):
        L.append(f"{indent}- **핵심 차이**: {basis['difference']}")
    if basis.get("reasoning"):
        L.append(f"{indent}- **판단·작업(엔진)**: {basis['reasoning']}")
    return L


def build_markdown(result, corpus=None):
    src = result.trial_balance.source_gaap
    unit = result.trial_balance.currency or "통화단위"
    m_ok = sum(1 for m in result.mapped if not m.flagged)
    m_flag = sum(1 for m in result.mapped if m.flagged)
    a_ok = sum(1 for a in result.adjustments if not a.flagged)
    a_flag = sum(1 for a in result.adjustments if a.flagged)

    L = []
    L.append(f"# 회계기준 전환 차이 분석 보고서 — {src} → K-IFRS\n")
    L.append(f"**모든 금액 단위: {unit}** (각 절 머리에 단위를 다시 표기한다.)\n")
    L.append(f"입력 계정 {len(result.trial_balance.accounts)}개 · 재분류 매핑 {m_ok}개(미매핑 {m_flag}) · "
             f"측정조정 {a_ok}개 계산 / {a_flag}개 판단필요\n")

    # ---- Layer 1 ----
    L.append(f"## 1. 계정 재분류 (Layer 1) — 단위: {unit}\n")
    L.append("| 소스 계정 | → IFRS 계정 | 기준서 | 이전 GAAP 대비 IFRS 유의점 |")
    L.append("|---|---|---|---|")
    for ml in result.mapped:
        if ml.flagged:
            L.append(f"| {ml.source.name_src} | (미매핑) | — | ⚠️ {ml.flag_reason} |")
        else:
            L.append(f"| {ml.source.name_src} | {ml.ifrs_account} | {ml.standard} | {ml.note or '표시 유지'} |")

    L.append("")
    detailed = [ml for ml in result.mapped if ml.basis]
    if detailed:
        L.append("### 1-A. 주요 계정 상세 근거 (조항 인용)\n")
        for ml in detailed:
            L.append(f"#### {ml.source.name_src} → {ml.ifrs_account} ({ml.standard})")
            L.extend(_basis_block(ml.basis, corpus))
            L.append("")

    # ---- Layer 2 ----
    L.append(f"## 2. 인식·측정 조정 (Layer 2) — 단위: {unit}\n")
    if not result.adjustments:
        L.append("_트리거된 측정조정 없음._\n")
    for i, a in enumerate(result.adjustments, 1):
        status = "⚠️ 판단필요" if a.flagged else "✅ 계산됨"
        L.append(f"### 2.{i} {a.title} ({a.standard}) — {status}\n")
        L.extend(_basis_block(a.basis, corpus))
        if a.flagged:
            L.append(f"- **판단필요**: {a.note}")
        else:
            L.append(f"- **계산 결과 (단위: {unit})**: {a.note}")
            L.append(f"- **분개 및 파급효과 (단위: {unit})**:")
            for e in a.entries:
                where = "손익계산서" if e.get("statement") == "PL" else "재무상태표"
                L.append(f"    - {e['account']} {e.get('delta', 0):+,.0f} ({e.get('section', '')}, {where})")
            na, nl, nq, ni = _net(a.entries)
            L.append(f"    - **→ 순효과**: 자산총계 {na:+,.0f} · 부채총계 {nl:+,.0f} · "
                     f"자본총계 {nq:+,.0f} · 당기순이익 {ni:+,.0f} ({unit})")
        L.append("- ⚠️ *조항 인용은 코퍼스 원문 기준(‘큐레이션 요약’ 표시 항목은 코퍼스 미적재분이라 공식 원문 대조 필요).*\n")

    # ---- Impact ----
    L.append(f"## 3. 재무 영향 요약 — 단위: {unit}\n")
    for k, v in result.impact["metrics"].items():
        L.append(f"- **{k}**: {v['source']:,.0f} → {v['ifrs']:,.0f} "
                 f"(Δ {v['delta']:,.0f}, {v['pct']}%) {unit}")
    L.append(f"\n> {result.impact['narrative']}")
    L.append("\n---")
    L.append(f"*단위: {unit}. 산출물은 전문가 검토용 초안이다. ⚠️ 판단필요 항목은 보조자료·전문가 판단이 "
             "있어야 확정되며, 인용 조항은 공식 기준서 원문과 대조해야 한다.*")
    return "\n".join(L)
