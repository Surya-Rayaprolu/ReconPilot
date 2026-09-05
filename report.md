# AI Finance Controller — Reconciliation Report

## Summary

- Bank records: **56**
- Ledger records: **61**
- Total records: **117**
- Matched pairs: **53**
- **Match rate: 90.6%** (106/117 records)
- Matches by tier: {'exact': 37, 'reference': 12, 'fuzzy': 4}
- Unresolved exceptions: **11**

## Unresolved Exceptions (honest list — not cherry-picked)

| Side | Record ID | Amount | Date | Reference | Reason | Suggested Action |
|---|---|---|---|---|---|---|
| bank | B0055 | ₹11353.82 | 2026-08-30 | TXN100055 | Reference 'TXN100055' not found on the other side; closest description match was too weak to auto-clear (similarity 0.36). | A reference ('TXN100055') exists but has no counterpart. The closest description match wasn't strong enough to auto-clear. Action: pull up both records side-by-side for a human decision. |
| bank | B0056 | ₹36389.80 | 2026-08-28 | TXN100056 | Reference 'TXN100056' not found on the other side; closest description match was too weak to auto-clear (similarity 0.36). | A reference ('TXN100056') exists but has no counterpart. The closest description match wasn't strong enough to auto-clear. Action: pull up both records side-by-side for a human decision. |
| bank | B0054 | ₹6437.18 | 2026-08-06 | TXN100054 | Reference 'TXN100054' not found on the other side; closest description match was too weak to auto-clear (similarity 0.36). | A reference ('TXN100054') exists but has no counterpart. The closest description match wasn't strong enough to auto-clear. Action: pull up both records side-by-side for a human decision. |
| ledger | L0058 | ₹2418.89 | 2026-08-18 | TXN100057 | Reference 'TXN100057' not found on the other side; closest description match was too weak to auto-clear (similarity 0.21). | A reference ('TXN100057') exists but has no counterpart. The closest description match wasn't strong enough to auto-clear. Action: pull up both records side-by-side for a human decision. |
| ledger | L0050 | ₹8689.88 | 2026-08-04 | TXN100050 | Reference 'TXN100050' not found on the other side; closest description match was too weak to auto-clear (similarity 0.21). | A reference ('TXN100050') exists but has no counterpart. The closest description match wasn't strong enough to auto-clear. Action: pull up both records side-by-side for a human decision. |
| ledger | L0059 | ₹41697.56 | 2026-08-28 | TXN100058 | Reference 'TXN100058' not found on the other side; closest description match was too weak to auto-clear (similarity 0.21). | A reference ('TXN100058') exists but has no counterpart. The closest description match wasn't strong enough to auto-clear. Action: pull up both records side-by-side for a human decision. |
| ledger | L0052 | ₹19147.50 | 2026-08-15 | TXN100051 | Reference 'TXN100051' not found on the other side; closest description match was too weak to auto-clear (similarity 0.30). | A reference ('TXN100051') exists but has no counterpart. The closest description match wasn't strong enough to auto-clear. Action: pull up both records side-by-side for a human decision. |
| ledger | L0055 | ₹2868.48 | 2026-08-24 | TXN100052 | Reference 'TXN100052' not found on the other side; closest description match was too weak to auto-clear (similarity 0.22). | A reference ('TXN100052') exists but has no counterpart. The closest description match wasn't strong enough to auto-clear. Action: pull up both records side-by-side for a human decision. |
| ledger | L0057 | ₹11302.24 | 2026-08-07 | TXN100053 | Reference 'TXN100053' not found on the other side; closest description match was too weak to auto-clear (similarity 0.35). | A reference ('TXN100053') exists but has no counterpart. The closest description match wasn't strong enough to auto-clear. Action: pull up both records side-by-side for a human decision. |
| ledger | L0060 | ₹18377.67 | 2026-08-16 | TXN100059 | Reference 'TXN100059' not found on the other side; closest description match was too weak to auto-clear (similarity 0.21). | A reference ('TXN100059') exists but has no counterpart. The closest description match wasn't strong enough to auto-clear. Action: pull up both records side-by-side for a human decision. |
| ledger | L0061 | ₹40624.56 | 2026-08-06 | TXN100060 | Reference 'TXN100060' not found on the other side; closest description match was too weak to auto-clear (similarity 0.21). | A reference ('TXN100060') exists but has no counterpart. The closest description match wasn't strong enough to auto-clear. Action: pull up both records side-by-side for a human decision. |

## Sample Matches

| Bank ID | Ledger ID | Tier | Confidence | Reason |
|---|---|---|---|---|
| B0005 | L0005 | exact | 1.0 | Reference, amount and date all match exactly. |
| B0044 | L0044 | reference | 0.9 | Matched on reference number; date differs by 1 day(s) (settlement lag). |
| B0026 | L0026 | exact | 1.0 | Reference, amount and date all match exactly. |
| B0020 | L0020 | exact | 1.0 | Reference, amount and date all match exactly. |
| B0002 | L0002 | exact | 1.0 | Reference, amount and date all match exactly. |
| B0053 | L0056 | exact | 1.0 | Reference, amount and date all match exactly. |
| B0018 | L0018 | exact | 1.0 | Reference, amount and date all match exactly. |
| B0012 | L0012 | exact | 1.0 | Reference, amount and date all match exactly. |
| B0009 | L0009 | exact | 1.0 | Reference, amount and date all match exactly. |
| B0015 | L0015 | exact | 1.0 | Reference, amount and date all match exactly. |
| B0008 | L0008 | exact | 1.0 | Reference, amount and date all match exactly. |
| B0013 | L0013 | exact | 1.0 | Reference, amount and date all match exactly. |
| B0039 | L0039 | reference | 0.7 | Matched on reference number; amount differs by ₹16.83. |
| B0040 | L0040 | reference | 0.9 | Matched on reference number; date differs by 1 day(s) (settlement lag). |
| B0004 | L0004 | exact | 1.0 | Reference, amount and date all match exactly. |

_...and 38 more matches (see report.json for the full list)._
