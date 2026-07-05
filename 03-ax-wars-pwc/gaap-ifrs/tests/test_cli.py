from gaap_ifrs.cli import main


def test_cli_end_to_end(tmp_path, capsys):
    rc = main(["convert", "--input", "tests/fixtures/sample_tb_kgaap.csv",
               "--extra", "tests/fixtures/sample_aging.json", "--out", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "생성:" in out


def test_cli_flags_missing_input(tmp_path, capsys):
    # aging 미제공 → ECL flagged 메시지
    rc = main(["convert", "--input", "tests/fixtures/sample_tb_kgaap.csv", "--out", str(tmp_path)])
    assert rc == 0
    assert "판단 필요" in capsys.readouterr().out
