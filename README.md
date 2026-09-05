# ReconPilot — Multi-Source Reconciliation Agent

**Track 04 — Razorpay Buildathon: "Run the books and the cash position"**

An agent that closes one finance-ops loop end-to-end: it reconciles a bank
settlement statement against an internal ledger across a 50+ record
synthetic batch, and reports its match rate alongside the exceptions it
genuinely could not resolve.

## Why this direction

The track brief names reconciliation as the first example direction, and
frames the bar explicitly as **throughput + measured accuracy + an honest
exception list** — not a cherry-picked demo. So the design goal here was:
run the full batch, show the real match rate, and never hide a record that
didn't clear.

## How it works

1. **`generate_data.py`** creates two synthetic CSVs — `bank_statement.csv`
   and `ledger.csv` — with deliberately realistic noise: exact duplicates,
   rounding/fee differences, settlement date drift, missing reference
   numbers, duplicate bookings, and one-sided orphan entries. A reconciler
   that only ever sees clean 1:1 data proves nothing.

2. **`reconciler.py`** is the agent core, and it's fully deterministic —
   no LLM call is required for the match rate or exception detection, so
   the numbers are reproducible and auditable:
   - **Tier 1 (exact):** same reference, same amount, same date.
   - **Tier 2 (reference):** same reference number, but amount and/or date
     differ — still counted as matched, with the diff logged so nothing is
     silently smoothed over.
   - **Tier 3 (fuzzy):** no usable reference on one or both sides. Falls
     back to amount tolerance + date-window + description similarity,
     greedily assigning the highest-confidence candidate pairs first.
   - **Unresolved:** anything left over becomes an exception with a
     specific reason (no reference + no fuzzy candidate; reference exists
     but no counterpart; etc.) and the closest candidate it considered, so
     a human can audit *why* the agent gave up.

3. **`llm_exception_analyzer.py`** is an optional narration layer: it asks
   Claude for a one-line "what to check next" triage note per exception.
   This is intentionally kept separate from the matching logic — the match
   rate must never depend on an LLM call succeeding. If `ANTHROPIC_API_KEY`
   isn't set (or the call fails), it falls back to templated, rule-based
   triage notes automatically.

4. **`main.py`** orchestrates the run and writes both a machine-readable
   `report.json` and a human-readable `report.md`.

## Running it

```bash
pip install -r requirements.txt   # only stdlib + nothing exotic, kept minimal
python3 generate_data.py --n 60   # generates data/bank_statement.csv + data/ledger.csv
python3 main.py                   # deterministic reconciliation -> report.json / report.md
python3 main.py --llm             # optional: adds Claude-written triage notes (needs ANTHROPIC_API_KEY)
```

## Sample result (seed=42, n=60)

- 56 bank records, 61 ledger records (117 total)
- **Match rate: 90.6%** (106/117 records matched, 53 pairs)
- Matches by tier: 37 exact, 12 reference-level, 4 fuzzy
- **11 unresolved exceptions**, each with a specific reason and a
  suggested next action — not silently dropped.

## Design decisions worth calling out

- **Determinism over cleverness.** The core matcher never calls an LLM.
  A finance agent whose accuracy number depends on a nondeterministic API
  call isn't trustworthy for a books-and-cash-position use case.
- **Greedy fuzzy assignment, not "first hit".** Tier 3 scores *all*
  plausible candidate pairs and assigns highest-confidence pairs first,
  so one weak match can't steal a record that had a stronger candidate
  elsewhere.
- **Exceptions are diagnosed, not just listed.** Each one names the
  specific reason it failed (missing reference vs. no fuzzy candidate vs.
  weak description similarity) and shows the closest candidate considered.
- **Synthetic noise is intentional and documented**, not accidental —
  every mismatch category in `generate_data.py` mirrors a real reconciliation
  failure mode (fee adjustments, settlement lag, manual entries, duplicate
  bookings, orphaned transactions).

## Extending this (not built, but the architecture supports it)

- **Settlement Q&A agent:** `report.json` is structured enough to hand
  straight to an LLM as context for natural-language questions
  ("why didn't TXN100055 settle?").
- **Forward cash forecaster:** the matched-pairs time series in
  `report.json` gives a clean base to project expected settlement timing.
- **Tax-line matcher:** the same Tier 1→2→3 matching engine generalizes to
  matching ledger entries against tax filing line items with a different
  reference schema.
