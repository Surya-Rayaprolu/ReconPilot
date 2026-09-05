"""
main.py
--------
Orchestrates the full loop the track asks for:

  1. Load (or generate) a 50+ record synthetic batch: bank_statement.csv + ledger.csv
  2. Run the reconciliation agent (reconciler.py)
  3. Report the match rate and the exceptions it could not resolve
  4. Write out report.json (machine-readable) and report.md (human-readable)

Usage:
    python3 generate_data.py --n 60      # one-time: create the synthetic batch
    python3 main.py                      # run the agent end-to-end
    python3 main.py --llm                # also ask Claude to triage each exception
"""
import argparse
import json
import os

from reconciler import Reconciler, load_csv
from llm_exception_analyzer import annotate_exceptions


def build_report(reconciler, annotated_exceptions):
    summary = reconciler.summary()
    report = {
        "summary": summary,
        "matches": [
            {
                "bank_id": m.bank_id,
                "ledger_id": m.ledger_id,
                "tier": m.tier,
                "confidence": m.confidence,
                "reason": m.reason,
            }
            for m in reconciler.matches
        ],
        "exceptions": [
            {
                "side": item["exception"].side,
                "record_id": item["exception"].record_id,
                "amount": item["exception"].amount,
                "date": item["exception"].date,
                "reference": item["exception"].reference,
                "description": item["exception"].description,
                "reason": item["exception"].reason,
                "suggested_action": item["note"],
                "note_source": item["source"],
            }
            for item in annotated_exceptions
        ],
    }
    return report


def render_markdown(report):
    s = report["summary"]
    lines = []
    lines.append("# AI Finance Controller — Reconciliation Report\n")
    lines.append("## Summary\n")
    lines.append(f"- Bank records: **{s['bank_records']}**")
    lines.append(f"- Ledger records: **{s['ledger_records']}**")
    lines.append(f"- Total records: **{s['total_records']}**")
    lines.append(f"- Matched pairs: **{s['matched_pairs']}**")
    lines.append(f"- **Match rate: {s['match_rate_pct']}** ({s['matched_records']}/{s['total_records']} records)")
    lines.append(f"- Matches by tier: {s['matches_by_tier']}")
    lines.append(f"- Unresolved exceptions: **{s['unresolved_exceptions']}**\n")

    lines.append("## Unresolved Exceptions (honest list — not cherry-picked)\n")
    lines.append("| Side | Record ID | Amount | Date | Reference | Reason | Suggested Action |")
    lines.append("|---|---|---|---|---|---|---|")
    for e in report["exceptions"]:
        lines.append(
            f"| {e['side']} | {e['record_id']} | ₹{e['amount']:.2f} | {e['date']} | "
            f"{e['reference'] or '—'} | {e['reason']} | {e['suggested_action']} |"
        )

    lines.append("\n## Sample Matches\n")
    lines.append("| Bank ID | Ledger ID | Tier | Confidence | Reason |")
    lines.append("|---|---|---|---|---|")
    for m in report["matches"][:15]:
        lines.append(f"| {m['bank_id']} | {m['ledger_id']} | {m['tier']} | {m['confidence']} | {m['reason']} |")
    lines.append(f"\n_...and {max(0, len(report['matches']) - 15)} more matches (see report.json for the full list)._\n")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--llm", action="store_true", help="Use Claude to triage exceptions (needs ANTHROPIC_API_KEY)")
    ap.add_argument("--out", default="report")
    args = ap.parse_args()

    bank_path = os.path.join(args.data_dir, "bank_statement.csv")
    ledger_path = os.path.join(args.data_dir, "ledger.csv")

    if not (os.path.exists(bank_path) and os.path.exists(ledger_path)):
        raise SystemExit(
            f"Data not found in '{args.data_dir}/'. Run: python3 generate_data.py --n 60"
        )

    bank_rows = load_csv(bank_path)
    ledger_rows = load_csv(ledger_path)

    reconciler = Reconciler(bank_rows, ledger_rows).run()
    annotated = annotate_exceptions(reconciler.exceptions, use_llm=args.llm)
    report = build_report(reconciler, annotated)

    with open(f"{args.out}.json", "w") as f:
        json.dump(report, f, indent=2)
    with open(f"{args.out}.md", "w") as f:
        f.write(render_markdown(report))

    print(json.dumps(report["summary"], indent=2))
    print(f"\nWrote {args.out}.json and {args.out}.md")


if __name__ == "__main__":
    main()
