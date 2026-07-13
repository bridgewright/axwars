from gaap_standards_mcp.normalize import normalize_text, char_ngrams, tokenize

def test_normalize_collapses_ws_and_strips_punct_tail():
    assert normalize_text("리스부채를  인식한다.\n") == "리스부채를 인식한다"

def test_char_ngrams_cjk():
    assert "리스" in char_ngrams("리스부채")
    assert "리스부" in char_ngrams("리스부채")

def test_tokenize_mixes_latin_words_and_cjk_ngrams():
    toks = tokenize("ASC 842 리스")
    assert "asc" in toks and "842" in toks and "리스" in toks
