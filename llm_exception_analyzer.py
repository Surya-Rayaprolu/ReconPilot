"""
llm_exception_analyzer.py
--------------------------
Optional layer: turns the rule-based exception list into a short natural
-language triage note per exception ("what a finance ops person should do
next"), using Claude via the Anthropic API.

Design choice: the reconciliation engine (reconciler.py) is 100% deterministic
and works with zero API calls -- match rate and exception detection must be
reproducible and auditable, not dependent on an LLM's mood. The LLM is used
only as a *narrator/triage assistant* on top of exceptions the deterministic
engine already found, and the whole pipeline degrades gracefully (falls back
to a templated note) if ANTHROPIC_API_KEY is not set or the call fails.

This keeps "the bar" (throughput + measured accuracy + honest exceptions)
fully met by code alone, while still demonstrating the "agent" framing the
track asks for.
"""
import json
import os


def _template_note(exc):
    if not exc.reference:
        return ("Likely a manually keyed or POS entry that never got a reference "
                "number stamped on it. Action: check the settlement batch for this "
                f"amount (₹{exc.amount:.2f}) around {exc.date} and tag it manually.")
    if exc.closest_candidate:
        return (f"A reference ('{exc.reference}') exists but has no counterpart. "
                "The closest description match wasn't strong enough to auto-clear. "
                "Action: pull up both records side-by-side for a human decision.")
    return (f"No counterpart found anywhere for reference '{exc.reference}'. "
            "Action: confirm this transaction actually settled / was booked; "
            "it may be a duplicate, a cancellation, or a data entry error.")


def annotate_exceptions(exceptions, use_llm=True):
    """Returns a list of {exception, note} dicts."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    results = []

    if not use_llm or not api_key:
        for exc in exceptions:
            results.append({"exception": exc, "note": _template_note(exc), "source": "rule-based"})
        return results

    try:
        import urllib.request

        payload_items = [
            {
                "id": i,
                "side": exc.side,
                "amount": exc.amount,
                "date": exc.date,
                "reference": exc.reference,
                "description": exc.description,
                "reason": exc.reason,
            }
            for i, exc in enumerate(exceptions)
        ]
        prompt = (
            "You are a finance-ops triage assistant. For each unresolved "
            "reconciliation exception below, write ONE short sentence (max 25 words) "
            "telling a human what to check next. Respond ONLY as a JSON array of "
            "strings, one per input item, in the same order, no other text.\n\n"
            + json.dumps(payload_items)
        )

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps({
                "model": "claude-sonnet-4-6",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}],
            }).encode(),
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        text = "".join(b.get("text", "") for b in data.get("content", []))
        notes = json.loads(text.strip().strip("`").replace("json\n", "", 1))
        for exc, note in zip(exceptions, notes):
            results.append({"exception": exc, "note": note, "source": "llm"})
        return results
    except Exception:
        # Graceful degrade -- never let the report generation fail because
        # the LLM call did.
        for exc in exceptions:
            results.append({"exception": exc, "note": _template_note(exc), "source": "rule-based (llm unavailable)"})
        return results
