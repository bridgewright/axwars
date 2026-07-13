"""Load the curated knowledge base (account mappings + adjustment rules).

Knowledge = data (JSON with standard citations). Computation stays in code.
This is the DB-less structured RAG: exact, cited, auditable lookups.

Mappings are source-GAAP pluggable: each source framework has its own file,
so the same engine extends to VAS(베트남), China CAS, etc. by dropping in a corpus.
"""
import json
import os

_DATA = os.path.join(os.path.dirname(__file__), "data")

_MAP_FILES = {
    "K-GAAP": "mapping_kgaap.json",
    "VAS": "mapping_vas.json",
    "CAS": "mapping_cas.json",
    "US-GAAP": "mapping_usgaap.json",
    "USGAAP": "mapping_usgaap.json",
    "US GAAP": "mapping_usgaap.json",
}


def load_mappings(source_gaap="K-GAAP"):
    key = (source_gaap or "K-GAAP").upper()
    fn = _MAP_FILES.get(key, "mapping_kgaap.json")
    with open(os.path.join(_DATA, fn), encoding="utf-8") as f:
        return json.load(f)


def find_mapping(name, mappings):
    name = name.strip()
    for m in mappings:
        if name == m["source"] or name in m.get("aliases", []):
            return m
    return None


def load_adjustment_rules():
    d = os.path.join(_DATA, "adjustments")
    if not os.path.isdir(d):
        return []
    rules = []
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".json"):
            with open(os.path.join(d, fn), encoding="utf-8") as f:
                rules.append(json.load(f))
    return rules
