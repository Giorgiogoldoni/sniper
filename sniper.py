#!/usr/bin/env python3
"""
RAPTOR SNIPER - Aggregatore segnali multi-repo
Gira 4x/giorno via GitHub Actions.
Legge JSON da Chart, One, Alert, Settoriali, Tematici, Geografia, ScannerV2.
Deduplicazione cross-repo: stesso ticker+segnale → aggregato con lista fonti.
Salva signals.json nel root (ultimi 30 giorni).
"""

import json
import os
import urllib.request
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# CONFIGURAZIONE FONTI
# ---------------------------------------------------------------------------

SOURCES = {
    "chart": {
        "url": "https://giorgiogoldoni.github.io/chart/data/index.json",
        "page_url": "https://giorgiogoldoni.github.io/chart/",
        "parser": "chart",
    },
    "one": {
        "url": "https://giorgiogoldoni.github.io/raptor-one/raptor_data.json",
        "page_url": "https://giorgiogoldoni.github.io/raptor-one/",
        "parser": "one",
    },
    "alert": {
        "url": "https://giorgiogoldoni.github.io/raptor-alert/data/etf.json",
        "page_url": "https://giorgiogoldoni.github.io/raptor-alert/",
        "parser": "alert",
    },
    "settoriali": {
        "url": "https://giorgiogoldoni.github.io/raptor-settoriali/settoriali.json",
        "page_url": "https://giorgiogoldoni.github.io/raptor-settoriali/",
        "parser": "settoriali",
    },
    "tematici": {
        "url": "https://giorgiogoldoni.github.io/raptor-tematici/tematici.json",
        "page_url": "https://giorgiogoldoni.github.io/raptor-tematici/",
        "parser": "tematici",
    },
    "geografia": {
        "url": "https://giorgiogoldoni.github.io/raptor-geografia/geografia.json",
        "page_url": "https://giorgiogoldoni.github.io/raptor-geografia/",
        "parser": "geografia",
    },
    "scannerv2": {
        "url": "https://giorgiogoldoni.github.io/scannerv2/data/signals.json",
        "page_url": "https://giorgiogoldoni.github.io/scannerv2/",
        "parser": "scannerv2",
    },
}

BUY_SIGNALS  = {"BUY1", "BUY2", "BUY3", "LONG_FORTE"}
EXIT_SIGNALS = {"EXIT1", "EXIT2", "EXIT3", "SELL"}
SIGNALS_FILE = "signals.json"
MAX_DAYS = 30

# ---------------------------------------------------------------------------
# NORMALIZZAZIONE
# ---------------------------------------------------------------------------

def normalize_signal(raw: str):
    if not raw:
        return None
    s = raw.upper().strip()
    if s in BUY_SIGNALS:
        return "BUY"
    if s in EXIT_SIGNALS:
        return "EXIT"
    return None

# ---------------------------------------------------------------------------
# FETCH
# ---------------------------------------------------------------------------

def fetch_json(url: str):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RaptorSniper/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [WARN] fetch failed {url}: {e}")
        return None

# ---------------------------------------------------------------------------
# CAMPI EXTRA (motivi)
# ---------------------------------------------------------------------------

def extract_extra(item: dict, fields: list) -> dict:
    """Estrae campi extra da un item, solo se non None."""
    out = {}
    for f in fields:
        v = item.get(f)
        if v is not None:
            out[f] = v
    return out

CHART_EXTRA  = ["sar_bull","ao","rsi","er","er_trend","trendycator","vol_class",
                 "composite_score","structural_downtrend","days_below_ks","momentum_days"]
ONE_EXTRA    = ["categoria","prezzo","entryDate"]
ALERT_EXTRA  = ["trendycator","sar_up","rsi","er","kama_v","kama_s","mm_align",
                 "ao_pos","pk_pct","composite_score","vol_class","categoria"]
SETT_EXTRA   = ["current_gain_pct","days_held","target_price","stop_loss",
                 "pre_alert","target_hit","size_pct","trend"]
TEM_EXTRA    = ["current_gain_pct","days_held","target_price","stop_loss",
                 "pre_alert","target_hit","size_pct","trend"]
GEO_EXTRA    = ["current_gain_pct","days_held","target_price","stop_loss",
                 "pre_alert","target_hit","size_pct","trend","er"]
SCAN_EXTRA   = ["categoria","is_leveraged","is_short","kama_trend","baff",
                 "sar_bull","ao","ao_rising","rvi_bull","rsi","er","tv_rating",
                 "tv_buy","tv_sell","vol_ratio","bb_width","mom1m","mom3m","mom6m",
                 "regime","signal_bars","hurst_60","adx"]

# ---------------------------------------------------------------------------
# PARSER
# ---------------------------------------------------------------------------

def parse_chart(data):
    results = []
    items = data if isinstance(data, list) else data.get("tickers", data.get("data", []))
    for item in items:
        sig = normalize_signal(item.get("signal", ""))
        if not sig:
            continue
        results.append({
            "ticker":      item.get("ticker", ""),
            "name":        item.get("name", ""),
            "signal":      sig,
            "raw_signal":  item.get("signal", ""),
            "score":       item.get("score"),
            "signal_date": item.get("signal_date", ""),
            "extra":       extract_extra(item, CHART_EXTRA),
        })
    return results

def parse_one(data):
    results = []
    for item in data.get("data", []):
        sig = normalize_signal(item.get("segnale", ""))
        if not sig:
            continue
        extra = extract_extra(item, ONE_EXTRA)
        extra["categoria"] = item.get("categoria", "")
        results.append({
            "ticker":      item.get("ticker", ""),
            "name":        item.get("nome", ""),
            "signal":      sig,
            "raw_signal":  item.get("segnale", ""),
            "score":       item.get("score"),
            "signal_date": item.get("entryDate", ""),
            "extra":       extra,
        })
    return results

def parse_alert(data):
    results = []
    items = data if isinstance(data, list) else data.get("data", [])
    for item in items:
        sig = normalize_signal(item.get("tipo", item.get("segnale", "")))
        if not sig:
            continue
        results.append({
            "ticker":      item.get("ticker", item.get("display", "")),
            "name":        item.get("nome", item.get("name", "")),
            "signal":      sig,
            "raw_signal":  item.get("tipo", item.get("segnale", "")),
            "score":       item.get("score"),
            "signal_date": item.get("entry_date", item.get("entryDate", "")),
            "extra":       extract_extra(item, ALERT_EXTRA),
        })
    return results

def parse_settoriali(data):
    results = []
    for pname, portfolio in data.get("portfolios", {}).items():
        for item in portfolio.get("positions", []):
            sig = normalize_signal(item.get("signal", ""))
            if not sig:
                continue
            extra = extract_extra(item, SETT_EXTRA)
            extra["portfolio"] = pname
            results.append({
                "ticker":      item.get("ticker", ""),
                "name":        item.get("name", ""),
                "signal":      sig,
                "raw_signal":  item.get("signal", ""),
                "score":       item.get("score"),
                "signal_date": item.get("entry_date", ""),
                "extra":       extra,
            })
        seen = {i.get("ticker") for i in portfolio.get("positions", [])}
        for item in portfolio.get("qualified", []):
            if item.get("ticker") in seen:
                continue
            sig = normalize_signal(item.get("signal", ""))
            if not sig:
                continue
            extra = extract_extra(item, SETT_EXTRA)
            extra["portfolio"] = pname
            results.append({
                "ticker":      item.get("ticker", ""),
                "name":        item.get("name", ""),
                "signal":      sig,
                "raw_signal":  item.get("signal", ""),
                "score":       item.get("score"),
                "signal_date": "",
                "extra":       extra,
            })
    return results

def parse_tematici(data):
    results = []
    for gname, group in data.get("groups", {}).items():
        for item in group.get("positions", []):
            raw = item.get("signal", item.get("current_level", item.get("buy_level", "")))
            sig = normalize_signal(raw)
            if not sig:
                continue
            extra = extract_extra(item, TEM_EXTRA)
            extra["group"] = gname
            results.append({
                "ticker":      item.get("ticker", ""),
                "name":        item.get("name", ""),
                "signal":      sig,
                "raw_signal":  raw,
                "score":       item.get("score"),
                "signal_date": item.get("entry_date", ""),
                "extra":       extra,
            })
        seen = {i.get("ticker") for i in group.get("positions", [])}
        for item in group.get("qualified", []):
            if item.get("ticker") in seen:
                continue
            raw = item.get("buy_level", item.get("signal", ""))
            sig = normalize_signal(raw)
            if not sig:
                continue
            extra = extract_extra(item, TEM_EXTRA)
            extra["group"] = gname
            results.append({
                "ticker":      item.get("ticker", ""),
                "name":        item.get("name", ""),
                "signal":      sig,
                "raw_signal":  raw,
                "score":       item.get("score"),
                "signal_date": item.get("level_ts", ""),
                "extra":       extra,
            })
    return results

def parse_geografia(data):
    results = []
    for group_name, group in data.items():
        if not isinstance(group, dict):
            continue
        seen = {i.get("ticker") for i in group.get("positions", [])}
        for item in group.get("positions", []):
            raw = item.get("signal", item.get("current_level", ""))
            sig = normalize_signal(raw)
            if not sig:
                continue
            extra = extract_extra(item, GEO_EXTRA)
            extra["group"] = group_name
            results.append({
                "ticker":      item.get("ticker", ""),
                "name":        item.get("name", ""),
                "signal":      sig,
                "raw_signal":  raw,
                "score":       item.get("score"),
                "signal_date": item.get("entry_date", ""),
                "extra":       extra,
            })
        for item in group.get("qualified", []):
            if item.get("ticker") in seen:
                continue
            raw = item.get("signal", item.get("buy_level", ""))
            sig = normalize_signal(raw)
            if not sig:
                continue
            extra = extract_extra(item, GEO_EXTRA)
            extra["group"] = group_name
            results.append({
                "ticker":      item.get("ticker", ""),
                "name":        item.get("name", ""),
                "signal":      sig,
                "raw_signal":  raw,
                "score":       item.get("score"),
                "signal_date": item.get("entry_date", item.get("level_ts", "")),
                "extra":       extra,
            })
    return results

def parse_scannerv2(data):
    results = []
    for item in data.get("signals", []):
        sig = normalize_signal(item.get("signal", ""))
        if not sig:
            continue
        extra = extract_extra(item, SCAN_EXTRA)
        # regime è un dict {code, label, color}
        if isinstance(extra.get("regime"), dict):
            extra["regime"] = extra["regime"].get("label", "")
        results.append({
            "ticker":      item.get("ticker", ""),
            "name":        item.get("nome", item.get("name", "")),
            "signal":      sig,
            "raw_signal":  item.get("signal", ""),
            "score":       item.get("score"),
            "signal_date": item.get("signal_date", ""),
            "extra":       extra,
        })
    return results

PARSERS = {
    "chart":      parse_chart,
    "one":        parse_one,
    "alert":      parse_alert,
    "settoriali": parse_settoriali,
    "tematici":   parse_tematici,
    "geografia":  parse_geografia,
    "scannerv2":  parse_scannerv2,
}

# ---------------------------------------------------------------------------
# STORICO
# ---------------------------------------------------------------------------

def load_history():
    if not os.path.exists(SIGNALS_FILE):
        return []
    try:
        with open(SIGNALS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_history(events):
    with open(SIGNALS_FILE, "w") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

def prune_old(events, now):
    cutoff = now - timedelta(days=MAX_DAYS)
    return [e for e in events if datetime.fromisoformat(e["detected_at"]) >= cutoff]

# ---------------------------------------------------------------------------
# DEDUPLICAZIONE CROSS-REPO
# Chiave: ticker + signal (normalizzato) — stesso segnale da più fonti → aggregato
# ---------------------------------------------------------------------------

def merge_cross_repo(raw_items: list) -> list:
    """
    raw_items: lista di (source, item_dict, page_url)
    Output: lista eventi deduplicati, con campo sources:[{source, raw_signal, page_url, extra}]
    """
    groups = {}  # key: (ticker, signal) → evento aggregato
    for source, item, page_url in raw_items:
        ticker = item["ticker"]
        signal = item["signal"]
        key = (ticker, signal)
        if key not in groups:
            groups[key] = {
                "ticker":      ticker,
                "name":        item.get("name", ""),
                "signal":      signal,
                "score":       item.get("score"),
                "signal_date": item.get("signal_date", ""),
                "sources":     [],
            }
        # Aggiorna nome se mancante
        if not groups[key]["name"] and item.get("name"):
            groups[key]["name"] = item["name"]
        # Aggiorna score con il massimo disponibile
        if item.get("score") is not None:
            existing = groups[key]["score"]
            if existing is None or item["score"] > existing:
                groups[key]["score"] = item["score"]
        # Aggiorna signal_date con la più recente
        if item.get("signal_date") and not groups[key]["signal_date"]:
            groups[key]["signal_date"] = item["signal_date"]

        groups[key]["sources"].append({
            "source":     source,
            "raw_signal": item.get("raw_signal", signal),
            "page_url":   page_url,
            "extra":      item.get("extra", {}),
        })
    return list(groups.values())

# ---------------------------------------------------------------------------
# RUN
# ---------------------------------------------------------------------------

def run():
    now = datetime.now(timezone.utc)
    now_str = now.isoformat()
    print(f"[SNIPER] Run at {now_str}")

    history = load_history()
    history = prune_old(history, now)

    # Chiavi già viste nelle ultime 24h (per fonte — dedup intraday per fonte)
    cutoff_24h = now - timedelta(hours=24)
    recent_src_keys = set()
    for e in history:
        detected = datetime.fromisoformat(e["detected_at"])
        if detected >= cutoff_24h:
            for s in e.get("sources", []):
                recent_src_keys.add(f"{s['source']}|{e['ticker']}|{e['signal']}")

    # Raccoglie tutti i nuovi segnali
    raw_new = []  # (source, item, page_url)
    for src_name, src_cfg in SOURCES.items():
        print(f"  Fetching {src_name}...")
        data = fetch_json(src_cfg["url"])
        if data is None:
            continue
        try:
            items = PARSERS[src_cfg["parser"]](data)
        except Exception as ex:
            print(f"  [ERROR] parse {src_name}: {ex}")
            continue
        print(f"  → {len(items)} segnali trovati")
        for item in items:
            if not item["ticker"]:
                continue
            src_key = f"{src_name}|{item['ticker']}|{item['signal']}"
            if src_key in recent_src_keys:
                continue
            recent_src_keys.add(src_key)
            raw_new.append((src_name, item, src_cfg["page_url"]))
            print(f"    + {item['ticker']} {item['signal']} [{src_name}]")

    # Deduplicazione cross-repo
    merged_new = merge_cross_repo(raw_new)

    # Aggiunge metadata
    new_events = []
    for ev in merged_new:
        ev["detected_at"] = now_str
        ev["id"] = f"{ev['ticker']}|{ev['signal']}|{now_str}"
        new_events.append(ev)

    all_events = new_events + history
    all_events = prune_old(all_events, now)
    all_events.sort(key=lambda e: e["detected_at"], reverse=True)

    save_history(all_events)
    print(f"[SNIPER] Salvati {len(all_events)} eventi totali, {len(new_events)} nuovi.")

if __name__ == "__main__":
    run()
