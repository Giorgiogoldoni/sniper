#!/usr/bin/env python3
"""
RAPTOR SNIPER v2.0
══════════════════
Aggregatore segnali multi-repo con:
- Score composito: fonte + livello BUY + n_fonti + momentum reale
- Top 20: prezzi daily da yfinance + grafico OHLC 90gg
- Storico 30 giorni con badge orario (09:15/12:00/16:00/18:30)
- Deduplicazione cross-repo
"""

import json, os, time, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

def install(pkg):
    os.system(f"pip install {pkg} --break-system-packages -q")

try:
    import yfinance as yf
except ImportError:
    install("yfinance"); import yfinance as yf

# ── FONTI ─────────────────────────────────────────────────────────
SOURCES = {
    "chart": {
        "url":      "https://giorgiogoldoni.github.io/chart/data/index.json",
        "page_url": "https://giorgiogoldoni.github.io/chart/",
        "parser":   "chart",
    },
    "one": {
        "url":      "https://giorgiogoldoni.github.io/raptor-one/raptor_data.json",
        "page_url": "https://giorgiogoldoni.github.io/raptor-one/",
        "parser":   "one",
    },
    "alert": {
        "url":      "https://giorgiogoldoni.github.io/raptor-alert/data/etf.json",
        "page_url": "https://giorgiogoldoni.github.io/raptor-alert/",
        "parser":   "alert",
    },
    "settoriali": {
        "url":      "https://giorgiogoldoni.github.io/raptor-settoriali/settoriali.json",
        "page_url": "https://giorgiogoldoni.github.io/raptor-settoriali/",
        "parser":   "settoriali",
    },
    "tematici": {
        "url":      "https://giorgiogoldoni.github.io/raptor-tematici/tematici.json",
        "page_url": "https://giorgiogoldoni.github.io/raptor-tematici/",
        "parser":   "tematici",
    },
    "geografia": {
        "url":      "https://giorgiogoldoni.github.io/raptor-geografia/geografia.json",
        "page_url": "https://giorgiogoldoni.github.io/raptor-geografia/",
        "parser":   "geografia",
    },
    "scannerv2": {
        "url":      "https://giorgiogoldoni.github.io/scannerv2/data/signals.json",
        "page_url": "https://giorgiogoldoni.github.io/scannerv2/",
        "parser":   "scannerv2",
    },
    "minfinder": {
        "url":      "https://giorgiogoldoni.github.io/min-finder/data/min_finder_live.json",
        "page_url": "https://giorgiogoldoni.github.io/min-finder/",
        "parser":   "minfinder",
    },
}

BUY_SIGNALS  = {"BUY1","BUY2","BUY3","LONG_FORTE"}
EXIT_SIGNALS = {"EXIT1","EXIT2","EXIT3","SELL"}
SIGNALS_FILE = "signals.json"
MAX_DAYS     = 30
TOP_N        = 20   # top N per cui scaricare prezzi daily

# Orario del giro corrente (viene impostato a runtime)
RUN_SLOT = ""

# ── NORMALIZZAZIONE ───────────────────────────────────────────────
def normalize_signal(raw: str):
    if not raw: return None
    s = raw.upper().strip()
    if s in BUY_SIGNALS:  return "BUY"
    if s in EXIT_SIGNALS: return "EXIT"
    return None

def buy_level_score(raw: str) -> int:
    """BUY1=100, BUY2=66, BUY3=33, EXIT=50"""
    s = raw.upper().strip() if raw else ""
    if s == "BUY1" or s == "LONG_FORTE": return 100
    if s == "BUY2":  return 66
    if s == "BUY3":  return 33
    if s in EXIT_SIGNALS: return 50
    return 33

# ── SLOT ORARIO ───────────────────────────────────────────────────
def detect_slot(now: datetime) -> str:
    """Determina in quale slot orario siamo (ora italiana CET/CEST)."""
    # Stima ora italiana (UTC+1 o UTC+2)
    h = now.hour
    m = now.minute
    total_min = h * 60 + m + 60  # approssimazione CET (UTC+1)
    if total_min < 11 * 60:  return "09:15"
    if total_min < 14 * 60:  return "12:00"
    if total_min < 17 * 60:  return "16:00"
    return "18:30"

SLOT_RELIABLE = {"12:00", "16:00"}  # giri più affidabili

# ── FETCH ─────────────────────────────────────────────────────────
def fetch_json(url: str):
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"RaptorSniper/2.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [WARN] {url}: {e}")
        return None

# ── PARSER ────────────────────────────────────────────────────────
def extract_extra(item: dict, fields: list) -> dict:
    return {f: item[f] for f in fields if item.get(f) is not None}

CHART_EXTRA  = ["sar_bull","ao","rsi","er","er_trend","trendycator","vol_class",
                 "composite_score","structural_downtrend","days_below_ks","momentum_days"]
ONE_EXTRA    = ["categoria","prezzo","entryDate"]
ALERT_EXTRA  = ["trendycator","sar_up","rsi","er","mm_align","ao_pos",
                 "pk_pct","composite_score","vol_class","categoria"]
SETT_EXTRA   = ["current_gain_pct","days_held","target_price","stop_loss","size_pct","trend"]
TEM_EXTRA    = ["current_gain_pct","days_held","target_price","stop_loss","size_pct","trend"]
GEO_EXTRA    = ["current_gain_pct","days_held","target_price","stop_loss","size_pct","trend","er"]
SCAN_EXTRA   = ["categoria","is_leveraged","is_short","kama_trend","baff","sar_bull","ao",
                 "ao_rising","rvi_bull","rsi","er","tv_rating","tv_buy","tv_sell","vol_ratio",
                 "bb_width","mom1m","mom3m","mom6m","regime","signal_bars","hurst_60","adx",
                 "chg_pct","kama","k_pct","kama_above","signal_date"]
MIN_EXTRA    = ["inversion_score","trigger_count","kama_cross","kama_cross_bars","atr_rising",
                "obv_divergence","sar_bull","price_action_3up","ret_1w","ret_3m",
                "dist_52w_low","is_min_storico","is_pullback","is_compressione",
                "is_min_relativo","borsa","categoria","low_52w","high_52w"]

def parse_chart(data):
    results = []
    items = data if isinstance(data,list) else data.get("tickers",data.get("data",[]))
    for item in items:
        sig = normalize_signal(item.get("signal",""))
        if not sig: continue
        results.append({
            "ticker":      item.get("ticker",""),
            "name":        item.get("name",""),
            "signal":      sig,
            "raw_signal":  item.get("signal",""),
            "score":       item.get("score"),
            "signal_date": item.get("signal_date",""),
            "price":       item.get("close",item.get("price")),
            "extra":       extract_extra(item, CHART_EXTRA),
        })
    return results

def parse_one(data):
    results = []
    for item in data.get("data",[]):
        sig = normalize_signal(item.get("segnale",""))
        if not sig: continue
        results.append({
            "ticker":      item.get("ticker",""),
            "name":        item.get("nome",""),
            "signal":      sig,
            "raw_signal":  item.get("segnale",""),
            "score":       item.get("score"),
            "signal_date": item.get("entryDate",""),
            "price":       item.get("prezzo",item.get("price")),
            "extra":       extract_extra(item, ONE_EXTRA),
        })
    return results

def parse_alert(data):
    results = []
    items = data if isinstance(data,list) else data.get("data",[])
    for item in items:
        sig = normalize_signal(item.get("tipo",item.get("segnale","")))
        if not sig: continue
        results.append({
            "ticker":      item.get("ticker",item.get("display","")),
            "name":        item.get("nome",item.get("name","")),
            "signal":      sig,
            "raw_signal":  item.get("tipo",item.get("segnale","")),
            "score":       item.get("score"),
            "signal_date": item.get("entry_date",item.get("entryDate","")),
            "price":       item.get("price",item.get("entry_price")),
            "extra":       extract_extra(item, ALERT_EXTRA),
        })
    return results

def parse_settoriali(data):
    results = []
    for pname, portfolio in data.get("portfolios",{}).items():
        for item in portfolio.get("positions",[]):
            sig = normalize_signal(item.get("signal",""))
            if not sig: continue
            extra = extract_extra(item, SETT_EXTRA)
            extra["portfolio"] = pname
            results.append({
                "ticker": item.get("ticker",""), "name": item.get("name",""),
                "signal": sig, "raw_signal": item.get("signal",""),
                "score": item.get("score"), "signal_date": item.get("entry_date",""),
                "price": item.get("current_price",item.get("price")), "extra": extra,
            })
        seen = {i.get("ticker") for i in portfolio.get("positions",[])}
        for item in portfolio.get("qualified",[]):
            if item.get("ticker") in seen: continue
            sig = normalize_signal(item.get("signal",""))
            if not sig: continue
            extra = extract_extra(item, SETT_EXTRA)
            extra["portfolio"] = pname
            results.append({
                "ticker": item.get("ticker",""), "name": item.get("name",""),
                "signal": sig, "raw_signal": item.get("signal",""),
                "score": item.get("score"), "signal_date": "",
                "price": item.get("current_price"), "extra": extra,
            })
    return results

def parse_tematici(data):
    results = []
    for gname, group in data.get("groups",{}).items():
        for item in group.get("positions",[]):
            raw = item.get("signal",item.get("current_level",item.get("buy_level","")))
            sig = normalize_signal(raw)
            if not sig: continue
            extra = extract_extra(item, TEM_EXTRA)
            extra["group"] = gname
            results.append({
                "ticker": item.get("ticker",""), "name": item.get("name",""),
                "signal": sig, "raw_signal": raw, "score": item.get("score"),
                "signal_date": item.get("entry_date",""),
                "price": item.get("current_price"), "extra": extra,
            })
        seen = {i.get("ticker") for i in group.get("positions",[])}
        for item in group.get("qualified",[]):
            if item.get("ticker") in seen: continue
            raw = item.get("buy_level",item.get("signal",""))
            sig = normalize_signal(raw)
            if not sig: continue
            extra = extract_extra(item, TEM_EXTRA)
            extra["group"] = gname
            results.append({
                "ticker": item.get("ticker",""), "name": item.get("name",""),
                "signal": sig, "raw_signal": raw, "score": item.get("score"),
                "signal_date": item.get("level_ts",""), "price": None, "extra": extra,
            })
    return results

def parse_geografia(data):
    results = []
    for group_name, group in data.items():
        if not isinstance(group, dict): continue
        seen = {i.get("ticker") for i in group.get("positions",[])}
        for item in group.get("positions",[]):
            raw = item.get("signal",item.get("current_level",""))
            sig = normalize_signal(raw)
            if not sig: continue
            extra = extract_extra(item, GEO_EXTRA)
            extra["group"] = group_name
            results.append({
                "ticker": item.get("ticker",""), "name": item.get("name",""),
                "signal": sig, "raw_signal": raw, "score": item.get("score"),
                "signal_date": item.get("entry_date",""),
                "price": item.get("current_price"), "extra": extra,
            })
        for item in group.get("qualified",[]):
            if item.get("ticker") in seen: continue
            raw = item.get("signal",item.get("buy_level",""))
            sig = normalize_signal(raw)
            if not sig: continue
            extra = extract_extra(item, GEO_EXTRA)
            extra["group"] = group_name
            results.append({
                "ticker": item.get("ticker",""), "name": item.get("name",""),
                "signal": sig, "raw_signal": raw, "score": item.get("score"),
                "signal_date": item.get("entry_date",item.get("level_ts","")),
                "price": item.get("current_price"), "extra": extra,
            })
    return results

def parse_scannerv2(data):
    results = []
    for item in data.get("signals",[]):
        sig = normalize_signal(item.get("signal",""))
        if not sig: continue
        extra = extract_extra(item, SCAN_EXTRA)
        if isinstance(extra.get("regime"), dict):
            extra["regime"] = extra["regime"].get("label","")
        results.append({
            "ticker": item.get("ticker",""), "name": item.get("nome",item.get("name","")),
            "signal": sig, "raw_signal": item.get("signal",""),
            "score": item.get("score"), "signal_date": item.get("signal_date",""),
            "price": item.get("price"), "extra": extra,
        })
    return results

def parse_minfinder(data):
    results = []
    for item in data.get("top20",[]):
        raw = item.get("buy_level","")
        sig = normalize_signal(raw)
        if not sig: continue
        results.append({
            "ticker": item.get("ticker",""), "name": item.get("name",""),
            "signal": sig, "raw_signal": raw,
            "score": item.get("composite_score"),
            "signal_date": "",
            "price": item.get("price"),
            "extra": extract_extra(item, MIN_EXTRA),
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
    "minfinder":  parse_minfinder,
}

# ── SCORE COMPOSITO ───────────────────────────────────────────────
def compute_composite_score(event: dict) -> float:
    """
    Score composito = 
      score_fonte    × 0.35
      livello_buy    × 0.20  (BUY1=100, BUY2=66, BUY3=33)
      n_fonti        × 0.20  (1=33, 2=66, 3+=100)
      momentum_1w    × 0.15  (normalizzato 0-100, se disponibile)
      momentum_4w    × 0.10  (normalizzato 0-100, se disponibile)
      slot_bonus     × bonus (12:00/16:00 → +5 punti)
    """
    sources   = event.get("sources", [])
    n_sources = len(sources)
    score_raw = event.get("score") or 50

    # Score fonte (0-100)
    s_fonte = min(100, score_raw)

    # Livello BUY
    primary_raw = sources[0].get("raw_signal","BUY3") if sources else "BUY3"
    s_buy = buy_level_score(primary_raw)

    # N fonti
    s_nfonti = min(100, n_sources * 33)

    # Momentum (se già disponibile da yfinance enrichment)
    r1w = event.get("ret_1w")
    r4w = event.get("ret_4w")
    s_mom1w = min(100, max(0, (r1w + 10) * 5)) if r1w is not None else 50
    s_mom4w = min(100, max(0, (r4w + 15) * 3.3)) if r4w is not None else 50

    composite = (
        s_fonte  * 0.35 +
        s_buy    * 0.20 +
        s_nfonti * 0.20 +
        s_mom1w  * 0.15 +
        s_mom4w  * 0.10
    )

    # Slot bonus
    slot = event.get("slot","")
    if slot in SLOT_RELIABLE:
        composite += 5

    return round(composite, 1)

# ── FETCH DAILY PRICES ────────────────────────────────────────────
def fetch_daily_prices(tickers: list) -> dict:
    """Scarica prezzi daily (3 mesi) per i top N ticker."""
    result = {}
    if not tickers:
        return result
    print(f"  Scarico prezzi daily per {len(tickers)} ticker...")
    for tk in tickers:
        suffixes = [tk]
        # Prova suffissi alternativi per ticker europei senza estensione
        if "." not in tk:
            suffixes = [tk+".MI", tk+".L", tk+".PA", tk+".DE", tk]
        for suffix in suffixes:
            try:
                hist = yf.Ticker(suffix).history(period="3mo", interval="1d", auto_adjust=True)
                if len(hist) < 5:
                    continue
                closes = hist["Close"].dropna()
                highs  = hist["High"].dropna() if "High" in hist else closes
                lows   = hist["Low"].dropna()  if "Low"  in hist else closes
                p = float(closes.iloc[-1])
                r1w  = (closes.iloc[-1]/closes.iloc[-6]-1)*100  if len(closes)>6  else None
                r4w  = (closes.iloc[-1]/closes.iloc[-21]-1)*100 if len(closes)>21 else None
                r12w = (closes.iloc[-1]/closes.iloc[-63]-1)*100 if len(closes)>63 else None
                # OHLC per grafico (ultimi 90 giorni)
                ohlc = []
                for i in range(len(closes)):
                    try:
                        ohlc.append({
                            "d": str(closes.index[i].date()),
                            "c": round(float(closes.iloc[i]), 4),
                            "h": round(float(highs.iloc[i]),  4),
                            "l": round(float(lows.iloc[i]),   4),
                        })
                    except Exception:
                        pass
                result[tk] = {
                    "price": round(p,4),
                    "ret_1w":  round(r1w,2)  if r1w  is not None else None,
                    "ret_4w":  round(r4w,2)  if r4w  is not None else None,
                    "ret_12w": round(r12w,2) if r12w is not None else None,
                    "ohlc":    ohlc,
                    "ticker_used": suffix,
                }
                print(f"    ✓ {tk} ({suffix}) p={p:.2f}")
                break
            except Exception:
                continue
        if tk not in result:
            print(f"    ⚠ {tk} — non trovato")
        time.sleep(0.15)
    return result

# ── MERGE CROSS-REPO ─────────────────────────────────────────────
def merge_cross_repo(raw_items: list) -> list:
    groups = {}
    for source, item, page_url in raw_items:
        ticker = item["ticker"]
        signal = item["signal"]
        key    = (ticker, signal)
        if key not in groups:
            groups[key] = {
                "ticker":      ticker,
                "name":        item.get("name",""),
                "signal":      signal,
                "score":       item.get("score"),
                "signal_date": item.get("signal_date",""),
                "price":       item.get("price"),
                "sources":     [],
            }
        if not groups[key]["name"] and item.get("name"):
            groups[key]["name"] = item["name"]
        if item.get("score") is not None:
            ex = groups[key]["score"]
            if ex is None or item["score"] > ex:
                groups[key]["score"] = item["score"]
        if item.get("signal_date") and not groups[key]["signal_date"]:
            groups[key]["signal_date"] = item["signal_date"]
        if item.get("price") is not None and groups[key]["price"] is None:
            groups[key]["price"] = item["price"]
        groups[key]["sources"].append({
            "source":     source,
            "raw_signal": item.get("raw_signal", signal),
            "page_url":   page_url,
            "extra":      item.get("extra",{}),
            "price":      item.get("price"),
        })
    return list(groups.values())

# ── STORICO ───────────────────────────────────────────────────────
def load_history() -> list:
    if not os.path.exists(SIGNALS_FILE):
        return []
    try:
        with open(SIGNALS_FILE) as f:
            return json.load(f)
    except Exception:
        return []

def save_history(events: list):
    with open(SIGNALS_FILE, "w") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

def prune_old(events: list, now: datetime) -> list:
    cutoff = now - timedelta(days=MAX_DAYS)
    return [e for e in events if datetime.fromisoformat(e["detected_at"]) >= cutoff]

# ── MAIN ──────────────────────────────────────────────────────────
def run():
    now     = datetime.now(timezone.utc)
    now_str = now.isoformat()
    slot    = detect_slot(now)
    print(f"[SNIPER v2.0] Run at {now_str} — Slot: {slot}")

    history = load_history()
    history = prune_old(history, now)

    # Chiavi già viste nelle ultime 24h
    cutoff_24h   = now - timedelta(hours=24)
    recent_keys  = set()
    for e in history:
        detected = datetime.fromisoformat(e["detected_at"])
        if detected >= cutoff_24h:
            for s in e.get("sources",[]):
                recent_keys.add(f"{s['source']}|{e['ticker']}|{e['signal']}")

    # Raccoglie segnali
    raw_new = []
    for src_name, src_cfg in SOURCES.items():
        print(f"  Fetching {src_name}...")
        data = fetch_json(src_cfg["url"])
        if data is None:
            continue
        try:
            items = PARSERS[src_cfg["parser"]](data)
        except Exception as ex:
            print(f"  [ERROR] {src_name}: {ex}")
            continue
        print(f"  → {len(items)} segnali")
        for item in items:
            if not item["ticker"]: continue
            src_key = f"{src_name}|{item['ticker']}|{item['signal']}"
            if src_key in recent_keys: continue
            recent_keys.add(src_key)
            raw_new.append((src_name, item, src_cfg["page_url"]))
            print(f"    + {item['ticker']} {item['signal']} [{src_name}]")

    # Merge cross-repo
    merged = merge_cross_repo(raw_new)

    # Aggiunge metadata base
    new_events = []
    for ev in merged:
        ev["detected_at"] = now_str
        ev["slot"]        = slot
        ev["id"]          = f"{ev['ticker']}|{ev['signal']}|{now_str}"
        ev["composite_score"] = 0  # calcolato dopo yfinance
        new_events.append(ev)

    # Top N per score provvisorio → scarica prezzi daily
    if new_events:
        # Score provvisorio senza momentum
        for ev in new_events:
            ev["composite_score"] = compute_composite_score(ev)

        sorted_new = sorted(new_events, key=lambda e: e["composite_score"], reverse=True)
        top_tickers = [e["ticker"] for e in sorted_new[:TOP_N]]

        daily = fetch_daily_prices(top_tickers)

        # Arricchisci top N con prezzi reali e ricalcola score
        for ev in new_events:
            tk = ev["ticker"]
            if tk in daily:
                d = daily[tk]
                ev["ret_1w"]   = d.get("ret_1w")
                ev["ret_4w"]   = d.get("ret_4w")
                ev["ret_12w"]  = d.get("ret_12w")
                if d.get("price") and not ev.get("price"):
                    ev["price"] = d["price"]
                ev["ohlc"]     = d.get("ohlc", [])
                ev["composite_score"] = compute_composite_score(ev)

    # Ordina per composite_score
    new_events.sort(key=lambda e: e["composite_score"], reverse=True)

    # Merge con storico
    all_events = new_events + history
    all_events = prune_old(all_events, now)
    all_events.sort(key=lambda e: e["detected_at"], reverse=True)

    save_history(all_events)
    print(f"\n[SNIPER] {len(all_events)} eventi totali, {len(new_events)} nuovi | Slot: {slot}")
    if new_events:
        print(f"  Top 3:")
        for ev in new_events[:3]:
            srcs = "+".join(s["source"] for s in ev.get("sources",[]))
            print(f"    {ev['ticker']} {ev['signal']} [{srcs}] score={ev['composite_score']}")

if __name__ == "__main__":
    run()
