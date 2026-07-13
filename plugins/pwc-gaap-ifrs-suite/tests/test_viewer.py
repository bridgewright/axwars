def test_viewer_selfcontained():
    h = open("viewer/index.html", encoding="utf-8").read()
    assert "<textarea" in h and "http" not in h.split("</head>")[0].replace("https://","")
