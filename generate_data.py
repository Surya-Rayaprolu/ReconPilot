"""
generate_data.py
-----------------
Creates two synthetic datasets that simulate a real-world reconciliation
scenario between a payment gateway / bank settlement file and an internal
ledger (accounting system):

  data/bank_statement.csv   -> what the bank/PG says was settled
  data/ledger.csv           -> what the internal books recorded

Realistic noise is injected on purpose, because a reconciliation agent
that only ever sees perfectly matching data proves nothing (per the
brief: "One cherry-picked match proves nothing"):

  - exact matches                         (the easy majority)
  - amount rounding / fee-adjustment diffs (off by a few paise/rupees)
  - date drift                            (settlement lags by 1-3 days)
  - missing reference number on one side  (manual entries, POS, etc.)
  - duplicate ledger entries               (double-booked refunds)
  - orphan bank entries                    (bank-side only, e.g. bank fees)
  - orphan ledger entries                  (ledger-side only, e.g. void/cancelled)

Run: python3 generate_data.py [--n 60] [--seed 42]
"""
import argparse
import csv
import os
import random
from datetime import datetime, timedelta

CATEGORIES = ["sales", "refund", "subscription", "payout", "fee_reversal"]
DESCRIPTIONS = [
    "Payment received", "Customer refund", "Subscription renewal",
    "Vendor payout", "Fee reversal", "POS settlement", "UPI collect",
    "Card settlement", "NEFT credit", "Wallet settlement",
]


def rand_ref(i):
    return f"TXN{100000 + i}"


def rand_date(base, spread_days=30):
    return base + timedelta(days=random.randint(0, spread_days))


def generate(n=60, seed=42, out_dir="data"):
    random.seed(seed)
    os.makedirs(out_dir, exist_ok=True)

    base_date = datetime(2026, 8, 1)
    bank_rows = []
    ledger_rows = []

    bank_id = 1
    ledger_id = 1

    # Bucket sizes (sum to n "core" transactions, extra noise added after)
    n_exact = int(n * 0.55)
    n_amount_mismatch = int(n * 0.10)
    n_date_drift = int(n * 0.10)
    n_missing_ref = int(n * 0.08)
    n_duplicate = int(n * 0.07)
    n_bank_orphan = int(n * 0.05)
    n_ledger_orphan = n - (n_exact + n_amount_mismatch + n_date_drift +
                            n_missing_ref + n_duplicate + n_bank_orphan)

    def new_txn():
        amount = round(random.uniform(150, 45000), 2)
        date = rand_date(base_date)
        desc = random.choice(DESCRIPTIONS)
        cat = random.choice(CATEGORIES)
        return amount, date, desc, cat

    # 1. Exact matches
    for _ in range(n_exact):
        amount, date, desc, cat = new_txn()
        ref = rand_ref(bank_id)
        bank_rows.append([f"B{bank_id:04d}", date.strftime("%Y-%m-%d"), amount, ref, desc])
        ledger_rows.append([f"L{ledger_id:04d}", date.strftime("%Y-%m-%d"), amount, ref, desc, cat])
        bank_id += 1
        ledger_id += 1

    # 2. Amount mismatch (fee/rounding adjustment applied on one side)
    for _ in range(n_amount_mismatch):
        amount, date, desc, cat = new_txn()
        ref = rand_ref(bank_id)
        adj = round(random.uniform(1, 25), 2) * random.choice([1, -1])
        bank_rows.append([f"B{bank_id:04d}", date.strftime("%Y-%m-%d"), amount, ref, desc])
        ledger_rows.append([f"L{ledger_id:04d}", date.strftime("%Y-%m-%d"), round(amount + adj, 2), ref, desc, cat])
        bank_id += 1
        ledger_id += 1

    # 3. Date drift (settlement T+1/T+2/T+3)
    for _ in range(n_date_drift):
        amount, date, desc, cat = new_txn()
        ref = rand_ref(bank_id)
        drift = timedelta(days=random.choice([1, 2, 3]))
        bank_rows.append([f"B{bank_id:04d}", date.strftime("%Y-%m-%d"), amount, ref, desc])
        ledger_rows.append([f"L{ledger_id:04d}", (date + drift).strftime("%Y-%m-%d"), amount, ref, desc, cat])
        bank_id += 1
        ledger_id += 1

    # 4. Missing reference on the ledger side (manual/POS entry)
    for _ in range(n_missing_ref):
        amount, date, desc, cat = new_txn()
        ref = rand_ref(bank_id)
        bank_rows.append([f"B{bank_id:04d}", date.strftime("%Y-%m-%d"), amount, ref, desc])
        ledger_rows.append([f"L{ledger_id:04d}", date.strftime("%Y-%m-%d"), amount, "", desc, cat])
        bank_id += 1
        ledger_id += 1

    # 5. Duplicate ledger entry (double booking)
    for _ in range(n_duplicate):
        amount, date, desc, cat = new_txn()
        ref = rand_ref(bank_id)
        bank_rows.append([f"B{bank_id:04d}", date.strftime("%Y-%m-%d"), amount, ref, desc])
        ledger_rows.append([f"L{ledger_id:04d}", date.strftime("%Y-%m-%d"), amount, ref, desc, cat])
        ledger_id += 1
        ledger_rows.append([f"L{ledger_id:04d}", date.strftime("%Y-%m-%d"), amount, ref, desc + " (dup)", cat])
        bank_id += 1
        ledger_id += 1

    # 6. Bank-only orphans (e.g. bank charges never booked)
    for _ in range(n_bank_orphan):
        amount, date, desc, cat = new_txn()
        ref = rand_ref(bank_id)
        bank_rows.append([f"B{bank_id:04d}", date.strftime("%Y-%m-%d"), amount, ref, "Bank fee / charge"])
        bank_id += 1

    # 7. Ledger-only orphans (e.g. void/cancelled entries never hit the bank)
    for _ in range(n_ledger_orphan):
        amount, date, desc, cat = new_txn()
        ref = rand_ref(bank_id)
        ledger_rows.append([f"L{ledger_id:04d}", date.strftime("%Y-%m-%d"), amount, ref, "Voided entry", cat])
        bank_id += 1
        ledger_id += 1

    random.shuffle(bank_rows)
    random.shuffle(ledger_rows)

    with open(os.path.join(out_dir, "bank_statement.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["transaction_id", "date", "amount", "reference", "description"])
        w.writerows(bank_rows)

    with open(os.path.join(out_dir, "ledger.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["entry_id", "date", "amount", "reference", "description", "category"])
        w.writerows(ledger_rows)

    print(f"Generated {len(bank_rows)} bank rows and {len(ledger_rows)} ledger rows into '{out_dir}/'")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60, help="approx number of core transactions")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=str, default="data")
    args = ap.parse_args()
    generate(args.n, args.seed, args.out)
