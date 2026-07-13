def test_readme_has_run_and_fallback():
    t = open("README.md", encoding="utf-8").read()
    for kw in ["python -m gaap_standards_mcp", "corpus/", "BM25", "≤100MB", "search_standards"]:
        assert kw in t
