#!/usr/bin/env python3
"""
RAPTOR SNIPER - Aggregatore segnali multi-repo
Gira 4x/giorno via GitHub Actions.
Legge JSON da Chart, One, Alert, Settoriali, Tematici.
Confronta con storico, salva nuovi eventi in signals.json (ultimi 30 giorni).
"""

import json
import os
import urllib.request
import urllib.error
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

# Segnali da tracciare
BUY_SIGNALS  = {"BUY1", "BUY2", "BUY3", "LONG_FORTE"}
EXIT_SIGNALS = {"EXIT1", "EXIT2", "EXIT3"}
TRACK_SIGNALS = BUY_SIGNALS | EXIT_SIGNALS

SIGNALS_FILE = "signals.json"
MAX_DAYS = 30

# ---------------------------------------------------------------------------
# NORMALIZZAZIONE SEGNALI
# ---------------------------------------------------------------------------

def normalize_signal(raw: str) -> str | None:
    """Normalizza il segnale grezzo in BUY / EXIT oppure None se da ignorare."""
    if not raw:
        return None
    s = raw.upper().strip()
    if s in BUY_SIGNALS:
        return "BUY"
    if s in EXIT_SIGNALS:
        return "EXIT"
    return None

# ---------------------------------------------------------------------------
# FETCH JSON
# ---------------------------------------------------------------------------

def fetch_json(url: str) -> dict | list | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RaptorSniper/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [WARN] fetch failed {url}: {e}")
        return None

# ---------------------------------------------------------------------------
# PARSER PER FONTE
# ---------------------------------------------------------------------------

def parse_chart(data: dict) -> list[dict]:
    """
    Format: {updated, tickers:[]} con campi ticker, name, signal, score, signal_date
    """
    results = []
    items = data if isinstance(data, list) else data.get("tickers", data.get("data", []))
    for item in items:
        sig = normalize_signal(item.get("signal", ""))
        if not sig:
            continue
        results.append({
            "ticker":    item.get("ticker", ""),
            "name":      item.get("name", ""),
            "signal":    sig,
            "raw_signal": item.get("signal", ""),
            "score":     item.get("score"),
            "signal_date": item.get("signal_date", ""),
        })
    return results


def parse_one(data: dict) -> list[dict]:
    """
    Format: data[] con campi ticker, nome, segnale, score, prezzo, entryDate, categoria
    """
    results = []
    items = data.get("data", [])
    for item in items:
        sig = normalize_signal(item.get("segnale", ""))
        if not sig:
            continue
        results.append({
            "ticker":    item.get("ticker", ""),
            "name":      item.get("nome", ""),
            "signal":    sig,
            "raw_signal": item.get("segnale", ""),
            "score":     item.get("score"),
            "signal_date": item.get("entryDate", ""),
        })
    return results


def parse_alert(data: dict) -> list[dict]:
    """
    Format: {data:[]} con campi ticker, display, tipo (segnale), score, entry_date
    """
    results = []
    items = data if isinstance(data, list) else data.get("data", [])
    for item in items:
        sig = normalize_signal(item.get("tipo", item.get("segnale", "")))
        if not sig:
            continue
        results.append({
            "ticker":    item.get("ticker", item.get("display", "")),
            "name":      item.get("nome", item.get("name", item.get("ticker", ""))),
            "signal":    sig,
            "raw_signal": item.get("tipo", item.get("segnale", "")),
            "score":     item.get("score"),
            "signal_date": item.get("entry_date", item.get("entryDate", "")),
        })
    return results


def parse_settoriali(data: dict) -> list[dict]:
    """
    Format: portfolios.{europa,usa,mondo}.positions[] e .qualified[]
    Campi: ticker, name, signal, score, entry_date
    """
    results = []
    portfolios = data.get("portfolios", {})
    for pname, portfolio in portfolios.items():
        # Posizioni aperte
        for item in portfolio.get("positions", []):
            sig = normalize_signal(item.get("signal", ""))
            if not sig:
                continue
            results.append({
                "ticker":    item.get("ticker", ""),
                "name":      item.get("name", ""),
                "signal":    sig,
                "raw_signal": item.get("signal", ""),
                "score":     item.get("score"),
                "signal_date": item.get("entry_date", ""),
                "portfolio": pname,
            })
        # Qualified (senza posizione aperta)
        tickers_in_positions = {i.get("ticker") for i in portfolio.get("positions", [])}
        for item in portfolio.get("qualified", []):
            if item.get("ticker") in tickers_in_positions:
                continue
            sig = normalize_signal(item.get("signal", ""))
            if not sig:
                continue
            results.append({
                "ticker":    item.get("ticker", ""),
                "name":      item.get("name", ""),
                "signal":    sig,
                "raw_signal": item.get("signal", ""),
                "score":     item.get("score"),
                "signal_date": "",
                "portfolio": pname,
            })
    return results


def parse_tematici(data: dict) -> list[dict]:
    """
    Format: groups.{group_name}.positions[] e .qualified[]
    Campi: ticker, name, signal/buy_level, score, entry_date/entry_ts
    """
    results = []
    groups = data.get("groups", {})
    for gname, group in groups.items():
        # Posizioni aperte
        for item in group.get("positions", []):
            raw = item.get("signal", item.get("current_level", item.get("buy_level", "")))
            sig = normalize_signal(raw)
            if not sig:
                continue
            results.append({
                "ticker":    item.get("ticker", ""),
                "name":      item.get("name", ""),
                "signal":    sig,
                "raw_signal": raw,
                "score":     item.get("score"),
                "signal_date": item.get("entry_date", ""),
                "group":     gname,
            })
        # Qualified
        tickers_in_positions = {i.get("ticker") for i in group.get("positions", [])}
        for item in group.get("qualified", []):
            if item.get("ticker") in tickers_in_positions:
                continue
            raw = item.get("buy_level", item.get("signal", ""))
            sig = normalize_signal(raw)
            if not sig:
                continue
            results.append({
                "ticker":    item.get("ticker", ""),
                "name":      item.get("name", ""),
                "signal":    sig,
                "raw_signal": raw,
                "score":     item.get("score"),
                "signal_date": item.get("level_ts", ""),
                "group":     gname,
            })
    return results




def parse_geografia(data: dict) -> list[dict]:
    """
    Format: {paesi: {positions:[], qualified:[]}, ...}
    """
    results = []
    for group_name, group in data.items():
        if not isinstance(group, dict):
            continue
        tickers_in_pos = {i.get("ticker") for i in group.get("positions", [])}
        for item in group.get("positions", []):
            raw = item.get("signal", item.get("current_level", ""))
            sig = normalize_signal(raw)
            if not sig:
                continue
            results.append({
                "ticker":    item.get("ticker", ""),
                "name":      item.get("name", ""),
                "signal":    sig,
                "raw_signal": raw,
                "score":     item.get("score"),
                "signal_date": item.get("entry_date", ""),
                "group":     group_name,
            })
        for item in group.get("qualified", []):
            if item.get("ticker") in tickers_in_pos:
                continue
            raw = item.get("signal", item.get("buy_level", ""))
            sig = normalize_signal(raw)
            if not sig:
                continue
            results.append({
                "ticker":    item.get("ticker", ""),
                "name":      item.get("name", ""),
                "signal":    sig,
                "raw_signal": raw,
                "score":     item.get("score"),
                "signal_date": item.get("entry_date", item.get("level_ts", "")),
                "group":     group_name,
            })
    return results


def parse_scannerv2(data: dict) -> list[dict]:
    """
    Format: {meta:{}, signals:[{ticker, signal, nome, score, signal_date, ...}]}
    """
    results = []
    items = data.get("signals", [])
    if not isinstance(items, list):
        items = []
    for item in items:
        raw = item.get("signal", "")
        sig = normalize_signal(raw)
        if not sig:
            continue
        results.append({
            "ticker":    item.get("ticker", ""),
            "name":      item.get("nome", item.get("name", "")),
            "signal":    sig,
            "raw_signal": raw,
            "score":     item.get("score"),
            "signal_date": item.get("signal_date", ""),
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
# LOGICA PRINCIPALE
# ---------------------------------------------------------------------------

def load_history() -> list[dict]:
    if not os.path.exists(SIGNALS_FILE):
        return []
    try:
        with open(SIGNALS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(events: list[dict]):
    
    with open(SIGNALS_FILE, "w") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)


def prune_old(events: list[dict], now: datetime) -> list[dict]:
    cutoff = now - timedelta(days=MAX_DAYS)
    return [e for e in events if datetime.fromisoformat(e["detected_at"]) >= cutoff]


def make_key(source: str, ticker: str, signal: str) -> str:
    return f"{source}|{ticker}|{signal}"


def run():
    now = datetime.now(timezone.utc)
    now_str = now.isoformat()

    print(f"[SNIPER] Run at {now_str}")

    # Carica storico esistente
    history = load_history()
    history = prune_old(history, now)

    # Costruisce set di chiavi già presenti nelle ultime 24h (deduplicazione intraday)
    cutoff_24h = now - timedelta(hours=24)
    recent_keys = set()
    for e in history:
        detected = datetime.fromisoformat(e["detected_at"])
        if detected >= cutoff_24h:
            recent_keys.add(make_key(e["source"], e["ticker"], e["signal"]))

    new_events = []

    for src_name, src_cfg in SOURCES.items():
        print(f"  Fetching {src_name}...")
        data = fetch_json(src_cfg["url"])
        if data is None:
            continue

        parser = PARSERS[src_cfg["parser"]]
        try:
            items = parser(data)
        except Exception as e:
            print(f"  [ERROR] parse {src_name}: {e}")
            continue

        print(f"  → {len(items)} segnali trovati")

        for item in items:
            ticker = item["ticker"]
            if not ticker:
                continue
            signal = item["signal"]
            key = make_key(src_name, ticker, signal)

            if key in recent_keys:
                continue  # già visto nelle ultime 24h

            recent_keys.add(key)

            # Costruisce la URL della pagina sorgente
            page_url = src_cfg["page_url"]

            event = {
                "id":           key + "|" + now_str,
                "source":       src_name,
                "ticker":       ticker,
                "name":         item.get("name", ""),
                "signal":       signal,
                "raw_signal":   item.get("raw_signal", signal),
                "score":        item.get("score"),
                "signal_date":  item.get("signal_date", ""),
                "detected_at":  now_str,
                "page_url":     page_url,
            }
            # Campi opzionali
            if "portfolio" in item:
                event["portfolio"] = item["portfolio"]
            if "group" in item:
                event["group"] = item["group"]

            new_events.append(event)
            print(f"    + {ticker} {signal} [{src_name}]")

    # Merge: nuovi in testa
    all_events = new_events + history
    all_events = prune_old(all_events, now)

    # Ordina per detected_at DESC
    all_events.sort(key=lambda e: e["detected_at"], reverse=True)

    save_history(all_events)
    print(f"[SNIPER] Salvati {len(all_events)} eventi totali, {len(new_events)} nuovi.")


if __name__ == "__main__":
    run()
