from gaap_standards_mcp.fusion import rrf_merge

def test_rrf_rewards_agreement():
    # idx 5는 두 랭킹 모두 상위 → 1위
    bm = [5, 1, 2]
    vec = [5, 9, 1]
    merged = rrf_merge([bm, vec], k=60)
    assert merged[0][0] == 5
    assert [i for i, _ in merged].count(5) == 1  # 중복 없음
