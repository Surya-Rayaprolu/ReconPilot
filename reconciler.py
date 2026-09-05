"""
reconciler.py
--------------
The reconciliation agent. Closes the finance-ops loop between a bank
statement and an internal ledger:

  Tier 1 - Exact match        : same reference number, same amount, same date
  Tier 2 - Reference match    : same reference number, amount/date differ
                                 (flags the diff as a soft exception, still counted matched)
  Tier 3 - Fuzzy match        : no usable reference on one/both sides ->
                                 match on amount (tolerance) + date window (tolerance)
                                 + description similarity, picking the best-scoring
                                 unclaimed candidate (greedy, highest score first)
  Unresolved                  : nothing clears the fuzzy threshold -> exception

Every match records *why* it matched (confidence + reason) and every
unresolved exception records the closest candidate considered and why it
was rejected, so the report is auditable rather than a black box.
"""
import csv
import difflib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


AMOUNT_TOLERANCE = 5.00      # rupees - treated as a "soft" match, still flagged
DATE_WINDOW_DAYS = 3         # settlement lag tolerance for fuzzy matching
FUZZY_AMOUNT_TOLERANCE = 30.00
DESC_SIM_THRESHOLD = 0.35


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d")


@dataclass
class MatchResult:
    bank_id: str
    ledger_id: str
    tier: str            # "exact" | "reference" | "fuzzy"
    confidence: float
    reason: str
    amount_diff: float = 0.0
    date_diff_days: int = 0


@dataclass
class Exception_:
    side: str             # "bank" | "ledger"
    record_id: str
    amount: float
    date: str
    reference: str
    description: str
    reason: str
    closest_candidate: Optional[str] = None


class Reconciler:
    def __init__(self, bank_rows, ledger_rows):
        self.bank = {r["transaction_id"]: r for r in bank_rows}
        self.ledger = {r["entry_id"]: r for r in ledger_rows}
        self.matches: list[MatchResult] = []
        self.exceptions: list[Exception_] = []

    def run(self):
        unmatched_bank = set(self.bank.keys())
        unmatched_ledger = set(self.ledger.keys())

        # --- Tier 1 + 2: reference-based matching ---
        ledger_by_ref = {}
        for lid in list(unmatched_ledger):
            ref = self.ledger[lid]["reference"].strip()
            if ref:
                ledger_by_ref.setdefault(ref, []).append(lid)

        for bid in list(unmatched_bank):
            b = self.bank[bid]
            ref = b["reference"].strip()
            if not ref or ref not in ledger_by_ref or not ledger_by_ref[ref]:
                continue
            lid = ledger_by_ref[ref].pop(0)
            l = self.ledger[lid]

            amount_diff = round(abs(float(b["amount"]) - float(l["amount"])), 2)
            date_diff = abs((parse_date(b["date"]) - parse_date(l["date"])).days)

            if amount_diff == 0 and date_diff == 0:
                self.matches.append(MatchResult(
                    bid, lid, "exact", 1.0,
                    "Reference, amount and date all match exactly."
                ))
            else:
                notes = []
                if amount_diff > 0:
                    notes.append(f"amount differs by ₹{amount_diff:.2f}")
                if date_diff > 0:
                    notes.append(f"date differs by {date_diff} day(s) (settlement lag)")
                self.matches.append(MatchResult(
                    bid, lid, "reference", 0.9 if amount_diff <= AMOUNT_TOLERANCE else 0.7,
                    "Matched on reference number; " + ", ".join(notes) + ".",
                    amount_diff=amount_diff, date_diff_days=date_diff
                ))
            unmatched_bank.discard(bid)
            unmatched_ledger.discard(lid)

        # --- Tier 3: fuzzy matching for whatever has no usable reference match ---
        candidates = []
        for bid in unmatched_bank:
            b = self.bank[bid]
            for lid in unmatched_ledger:
                l = self.ledger[lid]
                amount_diff = abs(float(b["amount"]) - float(l["amount"]))
                if amount_diff > FUZZY_AMOUNT_TOLERANCE:
                    continue
                date_diff = abs((parse_date(b["date"]) - parse_date(l["date"])).days)
                if date_diff > DATE_WINDOW_DAYS:
                    continue
                desc_sim = difflib.SequenceMatcher(
                    None, b["description"].lower(), l["description"].lower()
                ).ratio()
                if desc_sim < DESC_SIM_THRESHOLD:
                    continue
                # weighted score: amount closeness + date closeness + description similarity
                amount_score = 1 - (amount_diff / FUZZY_AMOUNT_TOLERANCE)
                date_score = 1 - (date_diff / max(DATE_WINDOW_DAYS, 1))
                score = 0.5 * amount_score + 0.25 * date_score + 0.25 * desc_sim
                candidates.append((score, bid, lid, amount_diff, date_diff))

        candidates.sort(key=lambda c: -c[0])
        claimed_b, claimed_l = set(), set()
        for score, bid, lid, amount_diff, date_diff in candidates:
            if bid in claimed_b or lid in claimed_l:
                continue
            claimed_b.add(bid)
            claimed_l.add(lid)
            self.matches.append(MatchResult(
                bid, lid, "fuzzy", round(score, 2),
                f"No reference match; fuzzy-matched on amount (Δ₹{amount_diff:.2f}), "
                f"date (Δ{date_diff}d) and description similarity.",
                amount_diff=round(amount_diff, 2), date_diff_days=date_diff
            ))

        unmatched_bank -= claimed_b
        unmatched_ledger -= claimed_l

        # --- Remaining = exceptions the agent could not resolve ---
        for bid in unmatched_bank:
            b = self.bank[bid]
            closest = self._closest_ledger_desc(b, unmatched_ledger)
            self.exceptions.append(Exception_(
                "bank", bid, float(b["amount"]), b["date"], b["reference"], b["description"],
                self._exception_reason("bank", b, closest),
                closest[1] if closest else None
            ))

        for lid in unmatched_ledger:
            l = self.ledger[lid]
            closest = self._closest_bank_desc(l, unmatched_bank)
            self.exceptions.append(Exception_(
                "ledger", lid, float(l["amount"]), l["date"], l["reference"], l["description"],
                self._exception_reason("ledger", l, closest),
                closest[1] if closest else None
            ))

        return self

    def _closest_ledger_desc(self, b, pool):
        best = None
        for lid in pool:
            l = self.ledger[lid]
            sim = difflib.SequenceMatcher(None, b["description"].lower(), l["description"].lower()).ratio()
            if best is None or sim > best[0]:
                best = (sim, lid)
        return best

    def _closest_bank_desc(self, l, pool):
        best = None
        for bid in pool:
            b = self.bank[bid]
            sim = difflib.SequenceMatcher(None, l["description"].lower(), b["description"].lower()).ratio()
            if best is None or sim > best[0]:
                best = (sim, bid)
        return best

    def _exception_reason(self, side, rec, closest):
        if not rec["reference"].strip():
            return "No reference number present, and no fuzzy candidate cleared the amount/date/description threshold."
        if closest and closest[0] > 0.2:
            return (f"Reference '{rec['reference']}' not found on the other side; "
                    f"closest description match was too weak to auto-clear (similarity {closest[0]:.2f}).")
        return f"Reference '{rec['reference']}' has no counterpart on the other side and no plausible fuzzy candidate exists."

    def summary(self):
        total_records = len(self.bank) + len(self.ledger)
        matched_records = len(self.matches) * 2
        match_rate = matched_records / total_records if total_records else 0
        tiers = {}
        for m in self.matches:
            tiers[m.tier] = tiers.get(m.tier, 0) + 1
        return {
            "bank_records": len(self.bank),
            "ledger_records": len(self.ledger),
            "total_records": total_records,
            "matched_pairs": len(self.matches),
            "matched_records": matched_records,
            "match_rate": round(match_rate, 4),
            "match_rate_pct": f"{match_rate * 100:.1f}%",
            "matches_by_tier": tiers,
            "unresolved_exceptions": len(self.exceptions),
        }
