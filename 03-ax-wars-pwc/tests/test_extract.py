from tools.ingest.extract import extract, Page

def test_extract_html(tmp_path):
    p = tmp_path / "s.html"
    p.write_text("<html><body><p>리스부채를 인식한다</p></body></html>", encoding="utf-8")
    pages = extract(p, "html")
    assert isinstance(pages[0], Page)
    assert "리스부채" in pages[0].text
