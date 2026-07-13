import os
from .server import make_app
from .vectors import prewarm_model

if __name__ == "__main__":
    corpus_dir = os.environ.get("GAAP_CORPUS_DIR",
                                os.path.join(os.path.dirname(__file__), "..", "corpus"))
    app, ctx = make_app(corpus_dir)
    if ctx.vectors_available:      # 벡터 인덱스가 있으면 임베딩 모델을 백그라운드로 프리워밍
        prewarm_model()
    app.run()  # stdio
