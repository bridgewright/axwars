import json, sys
from .fallback import fallback_search

def answer_query(corpus_dir, query, gaap=None, top_k=8):
    try:
        from .server import Context
        ctx = Context(corpus_dir)
        hits = ctx.search(query, gaap=gaap, top_k=top_k)
        return {"mode": "full" if ctx.vectors_available else "degraded", "hits": hits}
    except Exception:
        return {"mode": "no-mcp", "hits": fallback_search(corpus_dir, query, gaap=gaap, top_k=top_k)}

if __name__ == "__main__":
    print(json.dumps(answer_query(sys.argv[1], sys.argv[2]), ensure_ascii=False, indent=2))
