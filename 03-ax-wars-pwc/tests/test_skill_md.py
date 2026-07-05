def test_skill_md_has_contract():
    t = open("skills/gaap-standards-qa/SKILL.md", encoding="utf-8").read()
    assert t.startswith("---") and "name: gaap-standards-qa" in t
    for kw in ["search_standards", "근거를 찾지 못함", "비공식 번역", "출처"]:
        assert kw in t
