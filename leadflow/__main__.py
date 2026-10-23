"""
python -m leadflow run --website_form data/website_form.csv --meta_lead_ads data/meta_lead_ads.csv \
                       --event_signups data/event_signups.csv [--hubspot] [--out runs]
"""
import argparse
import json
from pathlib import Path

from .ledger import Ledger
from .pipeline import run
from .report import render
from .sinks import HubSpot, write_csv
from .sources import load_mappings


def main():
    ap = argparse.ArgumentParser(prog="leadflow")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="clean, merge, score and export leads")
    for source in load_mappings():
        r.add_argument(f"--{source}", type=Path, metavar="CSV")
    r.add_argument("--out", type=Path, default=Path("runs"))
    r.add_argument("--country", default="SA", help="default country for local phone numbers")
    r.add_argument("--hubspot", action="store_true", help="push to HubSpot (needs HUBSPOT_TOKEN, else dry run)")
    r.add_argument("--resync", action="store_true", help="push leads even if they were pushed before")
    args = ap.parse_args()

    files = {s: p for s in load_mappings() if (p := getattr(args, s, None))}
    if not files:
        ap.error("give at least one source file, e.g. --website_form data/website_form.csv")

    args.out.mkdir(parents=True, exist_ok=True)
    result = run(files, default_country=args.country)
    ledger = Ledger(args.out / "ledger.sqlite")
    new, known = (result.leads, []) if args.resync else ledger.split_new(result.leads)

    write_csv(result.leads, args.out / "leads_clean.csv")
    sink = HubSpot(dry_run=not args.hubspot).push(new, args.out) if new else {"mode": "nothing new"}
    ledger.record(new)
    report = render(result, new, known, sink, args.out / "report.html")

    print(json.dumps({
        "rows": sum(result.per_source.values()), "rejected": len(result.rejected), "merged": len(result.merges),
        "unique": len(result.leads), "new": len(new), "grades": dict(result.grades), "crm": sink,
    }, indent=2))
    print(f"report: {report}")


if __name__ == "__main__":
    main()
