from gaap_standards_mcp.schema import Record, GAAPS, TIERS

def test_record_roundtrip():
    r = Record(id="kifrs:1116:22", gaap="K-IFRS", standard_no="1116",
               standard_title="리스", paragraph_no="22", heading="인식",
               text="리스이용자는 리스개시일에 사용권자산과 리스부채를 인식한다.",
               text_norm="리스이용자는 리스개시일에 사용권자산과 리스부채를 인식한다",
               lang="ko", tier="본문", source_url="https://kasb.or.kr/x",
               as_of="2025-01-01", extract_flag=False)
    assert Record.from_dict(r.to_dict()) == r
    assert r.gaap in GAAPS and r.tier in TIERS
