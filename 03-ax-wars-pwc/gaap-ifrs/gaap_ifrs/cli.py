"""CLI entrypoint: gaap-ifrs convert --input tb.xlsx --extra aging.json --out out/"""
import argparse
import json
import sys
from .convert import run_conversion
from .report import write_all


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gaap-ifrs")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert", help="소스 GAAP 시산표를 K-IFRS로 변환")
    c.add_argument("--input", required=True, help="시산표 .csv/.xlsx")
    c.add_argument("--source-gaap", default="K-GAAP")
    c.add_argument("--extra", default=None, help="Layer2 보조자료 JSON(예: aging_schedule)")
    c.add_argument("--currency", default="KRW")
    c.add_argument("--period", default="")
    c.add_argument("--out", default="out")
    args = ap.parse_args(argv)

    extra = json.load(open(args.extra, encoding="utf-8")) if args.extra else None
    result = run_conversion(args.input, args.source_gaap, extra, args.currency, args.period)
    paths = write_all(result, args.out)
    print("생성:", ", ".join(f"{k}={v}" for k, v in paths.items()))
    flagged = [a.title for a in result.adjustments if a.flagged]
    if flagged:
        print("판단 필요(flagged):", ", ".join(flagged))
    return 0


if __name__ == "__main__":
    sys.exit(main())
