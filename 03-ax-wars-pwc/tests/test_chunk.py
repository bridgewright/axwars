from tools.ingest.extract import Page
from tools.ingest.chunk import chunk_pages

def test_chunk_splits_on_paragraph_numbers():
    text = "22 리스이용자는 사용권자산을 인식한다.\n23 리스부채는 현재가치로 측정한다."
    recs = chunk_pages([Page(text, 1, "p1")], "K-IFRS", "1116", "리스", "ko",
                       "https://x", "2025-01-01")
    assert [r.paragraph_no for r in recs] == ["22", "23"]
    assert recs[0].text.startswith("22") and "사용권자산" in recs[0].text
    assert recs[0].id == "kifrs:1116:22"
