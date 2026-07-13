"""ifrs_ref(포인터) 파싱 + 코퍼스 원문 grounding.

규정 텍스트의 단일 원천은 코퍼스이며, 이 모듈은 gaap_standards_mcp.corpus를
'읽기 전용'으로 재사용한다(MCP 서버·검색·데이터는 건드리지 않는다). 코퍼스
미가용 시 전량 폴백해 트랙 1 standalone 동작을 보존한다.
"""
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS_DIR = _REPO_ROOT / "corpus"

_REF_RE = re.compile(r"\s*(\S+)\s+제\s*([0-9]+)\s*호\s+문단\s+(.+)")


def _ensure_importable():
    """gaap_standards_mcp가 pip 설치되지 않은 실행(dev·gaap-ifrs cwd 테스트·번들)
    에서도 리포/번들 루트를 sys.path에 얹어 코퍼스 리더를 재사용할 수 있게 한다.
    이미 설치된 환경에선 무해한 no-op. (MCP 서버는 여전히 건드리지 않는다.)"""
    import sys
    p = str(_REPO_ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)


def _expand_range(tok):
    """'4.1.1-4.1.4' -> ['4.1.1','4.1.2','4.1.3','4.1.4']. 공통 접두 + 마지막 점
    세그먼트만 정수 확장. 확장 불가하면 양 끝점만."""
    a, _, b = tok.partition("-")
    a, b = a.strip(), b.strip()
    if not b:
        return [a] if a else []
    pa, pb = a.rsplit(".", 1), b.rsplit(".", 1)
    if len(pa) == 2 and len(pb) == 2 and pa[0] == pb[0] and pa[1].isdigit() and pb[1].isdigit():
        return [f"{pa[0]}.{i}" for i in range(int(pa[1]), int(pb[1]) + 1)]
    return [a, b]


def parse_ifrs_ref(ref):
    """'K-IFRS 제1109호 문단 4.1.1-4.1.4, 5.2.1'
       -> ('K-IFRS', '1109', ['4.1.1','4.1.2','4.1.3','4.1.4','5.2.1']).
    파싱 불가 -> (None, None, [])."""
    if not ref:
        return None, None, []
    m = _REF_RE.match(ref)
    if not m:
        return None, None, []
    gaap, std, paras_str = m.group(1), m.group(2), m.group(3)
    out, seen = [], set()
    for tok in paras_str.split(","):
        tok = tok.strip()
        if not tok:
            continue
        for p in (_expand_range(tok) if "-" in tok else [tok]):
            if p and p not in seen:
                seen.add(p)
                out.append(p)
    return gaap, std, out


_CORPUS_CACHE = {}


def load_corpus_for_grounding(corpus_dir=None):
    """코퍼스 레코드 로드(가드·캐시). gaap_standards_mcp/zstandard 미설치 또는
    corpus/ 부재 시 None -> 사용측 전량 폴백. 트랙 1 standalone 보존."""
    import os
    d = str(corpus_dir) if corpus_dir else str(DEFAULT_CORPUS_DIR)
    if d in _CORPUS_CACHE:
        return _CORPUS_CACHE[d]
    records = None
    try:
        if os.path.exists(os.path.join(d, "manifest.json")):
            _ensure_importable()
            from gaap_standards_mcp.corpus import load_corpus
            records = load_corpus(d)
    except Exception:
        records = None
    _CORPUS_CACHE[d] = records
    return records


def ground_ref(ref, records):
    """ifrs_ref -> (found, missing). found=[{'label','text'}] 정확 조회 문단 verbatim,
    missing=[조회 실패 문단번호]. records=None/파싱실패 -> ([], []).

    코퍼스 로딩은 load_corpus_for_grounding가 gaap_standards_mcp.corpus를 재사용하나,
    문단 정확조회는 4줄 선형 스캔이라 여기서 인라인한다(corpus.get_paragraph와 동일
    로직) — 리졸버를 Track 2 import에서 분리해 어떤 records로도 동작하게 한다."""
    gaap, std, paras = parse_ifrs_ref(ref)
    if records is None or not gaap or not paras:
        return [], []
    found, missing = [], []
    for pn in paras:
        r = next((x for x in records if x.gaap == gaap and x.standard_no == std
                  and x.paragraph_no == pn), None)
        if r:
            found.append({"label": f"{gaap} 제{std}호 문단 {pn}", "text": r.text.strip()})
        else:
            missing.append(pn)
    return found, missing
