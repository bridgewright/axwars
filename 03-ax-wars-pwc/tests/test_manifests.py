import json
def test_mcp_json_declares_stdio():
    m = json.load(open(".mcp.json", encoding="utf-8"))
    s = m["mcpServers"]["gaap-standards"]
    assert s["command"] == "python" and s["args"] == ["-m", "gaap_standards_mcp"]

def test_plugin_json_valid():
    p = json.load(open(".codex-plugin/plugin.json", encoding="utf-8"))
    assert p["name"] and "keywords" in p
