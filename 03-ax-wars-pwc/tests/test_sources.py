from tools.ingest.sources import SOURCES, get_source

def test_sources_cover_all_gaaps():
    assert set(SOURCES) == {"K-IFRS","K-GAAP","US-GAAP","CAS","VAS"}
    assert get_source("K-IFRS")["lang"] == "ko"
    assert all("standards" in v for v in SOURCES.values())
