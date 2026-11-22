#!/usr/bin/env python3
"""Fast daily signals backtest for exact 3x leveraged ETPs only.

Signals are formed at close t, entry is next session open, and exit is close
after 1/2/3/5 sessions. OOS is the final 30% of each instrument's chronology.
No intraday VWAP is inferred from daily bars. Existing Sniper engines untouched.
"""
import json, time, warnings
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import yfinance as yf
from corporate_action_filter import apply_history_cutoff, load_cutoffs

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent
UNIVERSE = ROOT / "data" / "instrument_universe.json"
OUT = ROOT / "data" / "fast_leverage3_results.json"
DETAIL = ROOT / "data" / "fast_leverage3_detail.csv"
PERIOD = "10y"
HORIZONS = (1,  2, 3, 5)
COSTS_BPS = (10, 20, 30)
MIN_BARS = 260
BATCH_SIZE = 20

def rsi(close, period):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - 100/(1+rs)
    out = out.mask((avg_loss == 0) & (avg_gain > 0), 100)
    return out

def make_signals(df):
    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]
    e3 = c.ewm(span=3, adjust=False).mean()
    e8 = c.ewm(span=8, adjust=False).mean()
    r2 = rsi(c, 2)
    roc1 = c.pct_change(1) * 100
    roc3 = c.pct_change(3) * 100
    low5 = l.rolling(5).min()
    high5 = h.rolling(5).max()
    fast_k = 100 * (c-low5) / (high5-low5).replace(0, np.nan)
    fast_d = fast_k.rolling(3).mean()
    slow_k = fast_k.rolling(3).mean()
    slow_d = slow_k.rolling(3).mean()
    relvol = v / v.rolling(20).mean().replace(0, np.nan)
    return {
        "EMA 3/8 trend": (e3 > e8) & (c > e3),
        "RSI 2 pullback": r2 < 10,
        "ROC 1/3 acceleration": (roc1 > 0) & (roc3 > 0),
        "Stochastic 5,3,3": (slow_k > slow_d) & (slow_k < 80),
        "Fast Momentum + RVOL": (e3 > e8) & (r2 > 50) & (relvol > 1.0),
        "Fast Momentum": (e3 > e8) & (r2 > 50),
    }

def trade_returns(signal, df, horizon, test_start, cost_bps):
    # Signal on close t; enter at open t+1; exit at close t+horizon.
    sig = signal.fillna(False).to_numpy(dtype=bool)
    op = df["Open"].to_numpy(dtype=float)
    cl = df["Close"].to_numpy(dtype=float)
    dates = df.index
    trades, last_exit = [], -1
    for t in range(max(1, int(test_start)-1), len(df)-horizon):
        entry, exit_i = t+1, t+horizon
        if entry <= last_exit or not sig[t]:
            continue
        if not np.isfinite(op[entry]) or not np.isfinite(cl[exit_i]) or op[entry] <= 0:
            continue
        gross = (cl[exit_i] / op[entry] - 1) * 100
        net = gross - cost_bps / 100
        trades.append({"signal_date": str(dates[t].date()),
                       "entry_date": str(dates[entry].date()),
                       "exit_date": str(dates[exit_i].date()),
                       "gross_return_pct": gross, "net_return_pct": net})
        last_exit = exit_i
    if not trades:
        return {"trades": 0, "win_rate_pct": None, "avg_net_return_pct": None,
                "median_net_return_pct": None, "profit_factor": None,
                "best_net_pct": None, "worst_net_pct": None}
    x = np.array([z["net_return_pct"] for z in trades], dtype=float)
    gains, losses = x[x > 0].sum(), -x[x < 0].sum()
    return {"trades": len(x), "win_rate_pct": round(float((x > 0).mean()*100), 2),
            "avg_net_return_pct": round(float(x.mean()), 4),
            "median_net_return_pct": round(float(np.median(x)), 4),
            "profit_factor": round(float(gains/losses), 3) if losses > 0 else (99.0 if gains > 0 else None),
            "best_net_pct": round(float(x.max()), 4),
            "worst_net_pct": round(float(x.min()), 4)}

def main():
    universe = json.loads(UNIVERSE.read_text(encoding="utf-8"))["instruments"]
    # Exact 3x only: do not mix 2x/5x products or commodity leverage into this test.
    items = {}
    for item in universe:
        lev = item.get("leverage")
        cls = item.get("classification", "")
        ticker = item.get("yahoo") or item.get("ticker")
        if ticker and cls in ("LEVA_LONG", "LEVA_SHORT") and lev is not None:
            try:
                if float(lev) == 3.0:
                    items[ticker] = item
            except (TypeError, ValueError):
                pass
    tickers = list(items)
    print(f"Exact 3x leveraged universe: {len(tickers)} instruments")
    frames, flagged, cutoff_audit = {}, {}, {}
    cutoffs = load_cutoffs()
    for start in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[start:start+BATCH_SIZE]
        try:
            raw = yf.download(batch, period=PERIOD, interval="1d", auto_adjust=True,
                              repair=True, group_by="ticker", threads=False,
                              progress=False, timeout=30)
            for ticker in batch:
                try:
                    df = raw[ticker].copy() if isinstance(raw.columns, pd.MultiIndex) else raw.copy()
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    cols = ["Open", "High", "Low", "Close", "Volume"]
                    if not set(cols).issubset(df.columns):
                        continue
                    df = df[cols].dropna(subset=["Open", "Close"])
                    df = df[~df.index.duplicated(keep="last")]
                    df = df[(df["Open"] > 0) & (df["Close"] > 0)]
                    df, meta = apply_history_cutoff(df, ticker, cutoffs)
                    if meta.get("cutoff_applied"):
                        cutoff_audit[ticker] = meta
                    if len(df) >= MIN_BARS:
                        move = df["Close"].pct_change().abs().dropna()
                        mx = float(move.max()) if len(move) else 0
                        if mx > 0.60:
                            flagged[ticker] = round(mx*100, 2)
                        frames[ticker] = df
                except Exception as exc:
                    print(f"Ticker warning {ticker}: {exc}")
        except Exception as exc:
            print(f"Batch warning {start}: {exc}")
        time.sleep(1)
        print(f"Downloaded {min(start+BATCH_SIZE,len(tickers))}/{len(tickers)}; usable {len(frames)}")

    rows = []
    coverage = {}
    for ticker, df in frames.items():
        meta = items[ticker]
        cat = meta.get("classification", "UNKNOWN")
        try:
            signals = make_signals(df)
            start_oos = int(len(df)*0.70)
            coverage[cat] = coverage.get(cat, 0) + 1
            for name, signal in signals.items():
                for horizon in HORIZONS:
                    for cost in COSTS_BPS:
                        metrics = trade_returns(signal, df, horizon, start_oos, cost)
                        if metrics["trades"] == 0:
                            continue
                        rows.append({"ticker": ticker, "name": meta.get("name", ""),
                                     "leverage": 3, "category": cat, "strategy": name,
                                     "horizon_days": horizon, "cost_bps_round_trip": cost,
                                     "oos_start": str(df.index[start_oos].date()),
                                     "oos_end": str(df.index[-1].date()), **metrics})
        except Exception as exc:
            print(f"Signal warning {ticker}: {exc}")

    detail = pd.DataFrame(rows)
    summary = []
    detail.to_csv(DETAIL, index=False)
    if not detail.empty:
        for (cat, strategy, horizon, cost), g in detail.groupby(
                ["category", "strategy", "horizon_days", "cost_bps_round_trip"]):
            valid = g[g["avg_net_return_pct"].notna()]
            if valid.empty:
                continue
            summary.append({"category": cat, "strategy": strategy,
                "horizon_days": int(horizon), "cost_bps_round_trip": int(cost),
                "instruments": int(valid["ticker"].nunique()),
                "trades": int(valid["trades"].sum()),
                "mean_instrument_net_return_pct": round(float(valid["avg_net_return_pct"].mean()), 4),
                "median_instrument_net_return_pct": round(float(valid["median_net_return_pct"].median()), 4),
                "median_win_rate_pct": round(float(valid["win_rate_pct"].median()), 2),
                "median_profit_factor": round(float(valid["profit_factor"].dropna().median()), 3)
                    if valid["profit_factor"].notna().any() else None})
        summary.sort(key=lambda x: (x["category"], x["horizon_days"],
                                    x["cost_bps_round_trip"], -(x["median_instrument_net_return_pct"] or -999)))
    result = {"generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "solo ETP con leva esattamente 3x; LEVA_LONG e LEVA_SHORT; leva 2x/5x e commodity escluse",
        "period_requested": PERIOD, "minimum_history_bars": MIN_BARS,
        "universe_3x_count": len(tickers), "usable_instruments": len(frames),
        "coverage_by_category": coverage, "quality_flagged_count": len(flagged),
        "quality_flagged_tickers": flagged, "corporate_action_cutoffs": cutoff_audit,
        "horizons_days": list(HORIZONS), "round_trip_cost_bps": list(COSTS_BPS),
        "method": "Segnale a close t; ingresso open t+1; uscita close t+h; OOS ultimo 30% cronologico per strumento; trade non sovrapposti per strategia/orizzonte; rendimenti netti con costo round-trip sottratto; aggregazione equal-weight per strumento.",
        "limitations": ["Dati daily Yahoo auto_adjust e repair=True; nessuna barra intraday.",
          "Non calcola VWAP intraday: servono barre 5m/15m affidabili.",
          "I segnali sono long sul prezzo dell'ETP, inclusi gli ETP inversi.",
          "Flag di variazioni estreme solo per audit, nessuna esclusione automatica.",
          "Il test non applica leva sintetica: usa i prezzi effettivi degli ETP 3x.",
          "Risultati esplorativi, non validazione di una strategia operativa."],
        "results": summary}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"universe_3x": len(tickers), "usable": len(frames),
                      "coverage": coverage, "detail_rows": len(rows),
                      "summary_rows": len(summary)}, ensure_ascii=False))
    if len(frames) < 5:
        raise SystemExit("Too few usable 3x instruments; refusing to publish an unreliable test.")

if __name__ == "__main__":
    main()
