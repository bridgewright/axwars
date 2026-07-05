"""Parse a source-GAAP trial balance (.csv/.xlsx) into a canonical TrialBalance."""
import csv
from .schema import Account, TrialBalance

_NAME_HINTS = ("계정", "과목", "name", "account")
_AMT_HINTS = ("금액", "잔액", "amount", "balance")


def _to_amount(s) -> float:
    if s is None:
        return 0.0
    if isinstance(s, (int, float)):
        return float(s)
    t = str(s).strip().replace(",", "").replace(" ", "")
    if t in ("", "-"):
        return 0.0
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    try:
        v = float(t)
    except ValueError:
        return 0.0
    return -v if neg else v


def _pick(header, hints):
    for i, h in enumerate(header):
        hl = str(h).lower()
        if any(k in hl for k in hints):
            return i
    return None


def _rows_from_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.reader(f) if any(str(c).strip() for c in r)]


def _rows_from_xlsx(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    out = []
    for row in ws.iter_rows(values_only=True):
        if any(c is not None and str(c).strip() for c in row):
            out.append(["" if c is None else c for c in row])
    return out


def load_trial_balance(path, source_gaap, currency="KRW", period=""):
    rows = _rows_from_xlsx(path) if str(path).lower().endswith((".xlsx", ".xlsm")) else _rows_from_csv(path)
    if not rows:
        raise ValueError(f"empty trial balance: {path}")
    header = rows[0]
    ni = _pick(header, _NAME_HINTS)
    ai = _pick(header, _AMT_HINTS)
    if ni is None:
        ni = 0
    if ai is None:
        ai = 1
    accounts = []
    for r in rows[1:]:
        if ni >= len(r):
            continue
        name = str(r[ni]).strip()
        if not name:
            continue
        amt = _to_amount(r[ai] if ai < len(r) else 0)
        accounts.append(Account(name_src=name, amount=amt))
    return TrialBalance(source_gaap, currency, period, accounts)
