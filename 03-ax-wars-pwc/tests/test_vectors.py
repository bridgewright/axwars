from gaap_standards_mcp.vectors import VectorIndex

def test_missing_index_is_unavailable(tmp_path):
    vi = VectorIndex(tmp_path / "nope.faiss", tmp_path / "nope.json")
    assert vi.available is False
    assert vi.search("리스") == []
