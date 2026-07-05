import pytest
from tools.ingest.extract import Page
from tools.ingest.chunk import chunk_pages
from tools.ingest.fidelity import roundtrip_coverage, detect_mojibake, assert_coverage, FidelityError

def test_roundtrip_full_coverage():
    text = "22 사용권자산을 인식한다.\n23 리스부채를 측정한다."
    recs = chunk_pages([Page(text,1,"p")], "K-IFRS","1116","리스","ko","u","2025-01-01")
    assert roundtrip_coverage(text, recs) >= 0.995
    assert_coverage(text, recs)  # no raise

def test_mojibake_and_low_coverage():
    assert detect_mojibake("리스�부채") is True
    with pytest.raises(FidelityError):
        assert_coverage("가"*1000, [])
