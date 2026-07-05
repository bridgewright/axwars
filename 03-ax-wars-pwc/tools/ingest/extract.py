from dataclasses import dataclass

@dataclass
class Page:
    text: str
    page_no: int
    locator: str

def extract(path, fmt):
    path = str(path)
    if fmt == "pdf":
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        return [Page(page.get_text("text"), i + 1, f"page={i+1}") for i, page in enumerate(doc)]
    if fmt == "html":
        import trafilatura
        html = open(path, encoding="utf-8").read()
        txt = trafilatura.extract(html, include_tables=True) or ""
        return [Page(txt, 1, path)]
    if fmt == "docx":
        import docx
        d = docx.Document(path)
        txt = "\n".join(p.text for p in d.paragraphs)
        return [Page(txt, 1, path)]
    if fmt == "hwp":
        import subprocess
        txt = subprocess.run(["hwp5txt", path], capture_output=True, text=True).stdout
        return [Page(txt, 1, path)]
    raise ValueError(f"unknown fmt: {fmt}")
