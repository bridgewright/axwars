import openpyxl
from gaap_ifrs.parse import load_trial_balance


def test_parse_csv():
    tb = load_trial_balance("tests/fixtures/sample_tb_kgaap.csv", "K-GAAP", "KRW", "2025-12-31")
    names = {a.name_src: a.amount for a in tb.accounts}
    assert names["현금및현금성자산"] == 5000000
    assert names["대손충당금"] == -150000          # 음수
    assert names["매입채무"] == 1800000            # 콤마 제거
    assert tb.source_gaap == "K-GAAP"


def test_parse_xlsx(tmp_path):
    p = tmp_path / "tb.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["계정과목", "잔액"])
    ws.append(["현금및현금성자산", 5000000])
    ws.append(["매출채권", 3000000])
    wb.save(p)
    tb = load_trial_balance(str(p), "K-GAAP")
    names = {a.name_src: a.amount for a in tb.accounts}
    assert names["매출채권"] == 3000000
