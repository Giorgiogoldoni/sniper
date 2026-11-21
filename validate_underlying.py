#!/usr/bin/env python3
"""Audit diagnostico ETP vs sottostante.

Non corregge prezzi e non esclude strumenti. Il confronto daily close-to-close
è indicativo: per ETP Borsa Italiana e azioni USA le chiusure non coincidono.
Per una verifica definitiva servono NAV/benchmark ufficiali con timestamp allineati.
"""
import argparse, json, time
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent
MAPPING = ROOT / "data" / "underlying_mapping.json"
OUT = ROOT / "data" / "underlying_validation.json"

def download(symbol, period):
    raw = yf.download(symbol, period=period, interval="1d", auto_adjust=True,
                      repair=False, progress=False, threads=False, timeout=30)
    if raw is None or raw.empty:
        return pd.Series(dtype=float)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    col = "Close" if "Close" in raw else ("Adj Close" if "Adj Close" in raw else None)
    if col is None:
        return pd.Series(dtype=float)
    s = pd.to_numeric(raw[col], errors="coerce").dropna()
    s = s[s > 0]
    s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
    return s[~s.index.duplicated(keep="last")].sort_index()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", default="2y")
    args = ap.parse_args()
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    results = []
    cache = {}
    for item in mapping["instruments"]:
        etp, und = item["etp_yahoo"], item["underlying_yahoo"]
        if not und:
            results.append({
                "etp_yahoo": etp, "underlying_yahoo": None,
                "status": item["status"], "benchmark_name": item.get("benchmark_name"),
                "benchmark_ticker": item.get("benchmark_ticker"),
                "identity_only": True,
                "warning": "Benchmark ufficiale identificato; serie storica esatta non ancora collegata."
            })
            print(f"{etp}: benchmark identificato, serie numerica da collegare")
            continue
        try:
            for symbol in (etp, und):
                if symbol not in cache:
                    cache[symbol] = download(symbol, args.period)
                    time.sleep(0.3)
            pair = pd.concat(
                [cache[etp].rename("etp"), cache[und].rename("underlying")],
                axis=1, join="inner"
            ).dropna()
            pair["etp_return_pct"] = pair["etp"].pct_change() * 100
            pair["underlying_return_pct"] = pair["underlying"].pct_change() * 100
            pair["theoretical_return_pct"] = (
                item["direction"] * item["leverage"] * pair["underlying_return_pct"]
            )
            pair["residual_pp"] = pair["etp_return_pct"] - pair["theoretical_return_pct"]
            valid = pair.dropna(subset=["etp_return_pct","underlying_return_pct","residual_pp"])
            # Estremi diagnostici, non soglie automatiche di esclusione.
            suspicious = valid[valid["residual_pp"].abs() > 5]
            results.append({
                "etp_yahoo": etp, "underlying_yahoo": und,
                "status": item["status"], "issuer_source": item["issuer_source"],
                "overlap_days": int(len(valid)),
                "correlation_daily_returns": round(float(valid["etp_return_pct"].corr(
                    valid["theoretical_return_pct"])), 4) if len(valid) > 2 else None,
                "median_residual_pp": round(float(valid["residual_pp"].median()), 3) if len(valid) else None,
                "median_abs_residual_pp": round(float(valid["residual_pp"].abs().median()), 3) if len(valid) else None,
                "days_abs_residual_over_5pp": int(len(suspicious)),
                "largest_residuals": [
                    {"date": str(idx.date()), "etp_return_pct": round(float(row.etp_return_pct), 3),
                     "underlying_return_pct": round(float(row.underlying_return_pct), 3),
                     "theoretical_return_pct": round(float(row.theoretical_return_pct), 3),
                     "residual_pp": round(float(row.residual_pp), 3)}
                    for idx, row in suspicious.reindex(
                        suspicious.residual_pp.abs().sort_values(ascending=False).head(10).index
                    ).iterrows()
                ],
                "warning": "Daily close non sincronizzati; scostamenti non dimostrano un errore dati."
            })
            print(f"{etp}: overlap={len(valid)} corr={results[-1]['correlation_daily_returns']} "
                  f"|residuo mediano|={results[-1]['median_abs_residual_pp']}")
        except Exception as exc:
            results.append({"etp_yahoo": etp, "underlying_yahoo": und, "error": str(exc)})
            print(f"WARNING {etp}: {exc}")
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": args.period,
        "method": "daily close-to-close; expected return = direction * leverage * underlying daily return",
        "warning": "Audit esplorativo con prezzi Yahoo non sincronizzati. Nessuna correzione o esclusione automatica.",
        "results": results
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report scritto: {OUT}")

if __name__ == "__main__":
    main()
