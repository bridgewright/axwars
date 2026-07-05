import os
from .server import make_app

if __name__ == "__main__":
    corpus_dir = os.environ.get("GAAP_CORPUS_DIR",
                                os.path.join(os.path.dirname(__file__), "..", "corpus"))
    app, _ = make_app(corpus_dir)
    app.run()  # stdio
