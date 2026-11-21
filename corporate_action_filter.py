#!/usr/bin/env python3
"""Conservative post-corporate-action history filter for Sniper backtests.

Raw market data are never rewritten. For affected ETPs, indicator selection tests
start only from the first verified stable post-event date. Instruments remain in
the universe; only their pre-event observations are outside this specific test.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POLICY = ROOT / "data" / "indicator_history_cutoffs.json"

def load_cutoffs():
    data = json.loads(POLICY.read_text(encoding="utf-8"))
    return {x["ticker"]: x for x in data.get("instruments", [])}

def apply_history_cutoff(frame, ticker, cutoffs=None):
    """Return (filtered_frame, audit_metadata); preserves all source values."""
    cutoffs = cutoffs if cutoffs is not None else load_cutoffs()
    rule = cutoffs.get(ticker)
    if not rule or frame is None or frame.empty:
        return frame, {"ticker": ticker, "cutoff_applied": False,
                       "rows_before": 0 if frame is None else int(len(frame)),
                       "rows_after": 0 if frame is None else int(len(frame))}
    valid_from = rule["valid_from"]
    idx = frame.index
    dates = idx
    try:
        dates = idx.tz_localize(None)
    except (TypeError, AttributeError):
        pass
    mask = dates >= valid_from
    filtered = frame.loc[mask].copy()
    return filtered, {
        "ticker": ticker, "cutoff_applied": True,
        "event_date": rule["event_date"], "valid_from": valid_from,
        "old_isin": rule.get("old_isin"), "new_isin": rule.get("new_isin"),
        "reason": rule.get("reason"),
        "rows_before": int(len(frame)), "rows_after": int(len(filtered)),
        "rows_omitted": int(len(frame) - len(filtered))
    }
