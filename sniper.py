#!/usr/bin/env python3
"""
RAPTOR SNIPER v3.1
══════════════════
- Score composito con momentum reale
- Top 40 → arricchimento yfinance → top 20 definitivi con is_top20=True
- Indicatori tecnici completi (KAMA, SAR, AO, RSI, ADX, Baff, Hurst)
- Storia segnali e grafico per dettaglio.html
- Suffisso borsa per TradingView
- Fonte Raptor Leva (LONG_CONF/LONG_EARLY → BUY, USCITA/STOP → EXIT)
"""

import json, os, sys, time, urllib.request, math
from datetime import datetime, timezone, timedelta
from pathlib import Path

def install(pkg):
    os.system(f"pip install {pkg} --break-system-packages -q")

try:
    import numpy as np
except ImportError:
    install("numpy"); import numpy as np

try:
    import yfinance as yf
except ImportError:
    install("yfinance"); import yfinance as yf

# Import modulo indicatori (stesso folder)
sys.path.insert(0, str(Path(__file__).parent))
try:
    from indicators import compute_all
except ImportError:
    print("  [WARN] indicators.py non trovato — grafici disabilitati")
    compute_all = None

# ── CONFIGURAZIONE ────────────────────────────────────────────────
SOURCES = {
    "chart":      {"url":"https://giorgiogoldoni.github.io/chart/data/index.json",         "page_url":"https://giorgiogoldoni.github.io/chart/",         "parser":"chart"},
    "one":        {"url":"https://giorgiogoldoni.github.io/raptor-one/raptor_data.json",    "page_url":"https://giorgiogoldoni.github.io/raptor-one/",    "parser":"one"},
    "alert":      {"url":"https://giorgiogoldoni.github.io/raptor-alert/data/etf.json",    "page_url":"https://giorgiogoldoni.github.io/raptor-alert/",  "parser":"alert"},
    "settoriali": {"url":"https://giorgiogoldoni.github.io/raptor-settoriali/settoriali.json","page_url":"https://giorgiogoldoni.github.io/raptor-settoriali/","parser":"settoriali"},
    "tematici":   {"url":"https://giorgiogoldoni.github.io/raptor-tematici/tematici.json", "page_url":"https://giorgiogoldoni.github.io/raptor-tematici/","parser":"tematici"},
    "geografia":  {"url":"https://giorgiogoldoni.github.io/raptor-geografia/geografia.json","page_url":"https://giorgiogoldoni.github.io/raptor-geografia/","parser":"geografia"},
    "scannerv2":  {"url":"https://giorgiogoldoni.github.io/scannerv2/data/signals.json",   "page_url":"https://giorgiogoldoni.github.io/scannerv2/",     "parser":"scannerv2"},
    "minfinder":  {"url":"https://giorgiogoldoni.github.io/min-finder/data/min_finder_live.json","page_url":"https://giorgiogoldoni.github.io/min-finder/","parser":"minfinder"},
    "leva":       {"url":"https://giorgiogoldoni.github.io/raptor-leva/raptor_leva.json",  "page_url":"https://giorgiogoldoni.github.io/raptor-leva/",   "parser":"leva"},
}

BUY_SIGNALS  = {"BUY1","BUY2","BUY3","LONG_FORTE"}
EXIT_SIGNALS = {"EXIT1","EXIT2","EXIT3","SELL"}
SIGNALS_FILE = "signals.json"
MAX_DAYS     = 30
TOP_ENRICH   = 40   # ticker da arricchire con yfinance
TOP_FINAL    = 20   # top definitivi marcati is_top20

# Suffissi borsa per TradingView
TV_SUFFIX_MAP = {
    ".MI": "MIL",
    ".DE": "XETR",
    ".PA": "EURONEXT",
    ".L":  "LSE",
    ".AS": "AMS",
    ".BR": "EBR",
}

def tv_symbol(ticker: str) -> str:
    for sfx, exchange in TV_SUFFIX_MAP.items():
        if ticker.upper().endswith(sfx):
            base = ticker[:-(len(sfx))].upper()
            return f"{exchange}:{base}"
    return ticker.upper()

def detect_slot(now: datetime) -> str:
    h = now.hour + 1  # approssimazione CET
    m = now.minute
    total = h*60+m
    if total < 11*60:  return "09:15"
    if total < 14*60:  return "12:00"
    if total < 17*60:  return "16:00"
    return "18:30"

SLOT_RELIABLE = {"12:00","16:00"}

def normalize_signal(raw):
    if not raw: return None
    s = raw.upper().strip()
    if s in BUY_SIGNALS:  return "BUY"
    if s in EXIT_SIGNALS: return "EXIT"
    return None

def buy_level_score(raw) -> int:
    s = (raw or "").upper().strip()
    if s in {"BUY1","LONG_FORTE","LONG_CONF"}: return 100
    if s in {"BUY2","LONG_EARLY"}:             return 66
    if s == "BUY3":                            return 33
    if s in EXIT_SIGNALS:                      return 50
    return 33

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"RaptorSniper/3.1"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  [WARN] {url}: {e}")
        return None

# ── PARSER ────────────────────────────────────────────────────────
def ex(item, fields):
    return {f: item[f] for f in fields if item.get(f) is not None}

CHART_EX  = ["sar_bull","ao","rsi","er","trendycator","vol_class","composite_score","momentum_days"]
ONE_EX    = ["categoria"]
ALERT_EX  = ["trendycator","sar_up","rsi","er","mm_align","ao_pos","composite_score","vol_class","categoria"]
SETT_EX   = ["current_gain_pct","days_held","target_price","stop_loss","size_pct","trend","portfolio"]
TEM_EX    = ["current_gain_pct","days_held","target_price","stop_loss","size_pct","trend"]
GEO_EX    = ["current_gain_pct","days_held","target_price","stop_loss","size_pct","trend","er"]
SCAN_EX   = ["categoria","is_leveraged","kama_trend","baff","sar_bull","ao","ao_rising","rvi_bull",
              "rsi","er","tv_rating","tv_buy","tv_sell","vol_ratio","bb_width","mom1m","mom3m",
              "mom6m","regime","signal_bars","hurst_60","adx","chg_pct","kama","k_pct","signal_date"]
MIN_EX    = ["inversion_score","trigger_count","kama_cross","atr_rising","obv_divergence",
             "sar_bull","ret_1w","ret_3m","dist_52w_low","is_min_storico","is_pullback",
             "is_compressione","is_min_relativo","borsa","categoria","low_52w","high_52w"]

def parse_chart(data):
    out=[]
    for item in (data if isinstance(data,list) else data.get("tickers",data.get("data",[]))):
        sig=normalize_signal(item.get("signal",""))
        if not sig: continue
        out.append({"ticker":item.get("ticker",""),"name":item.get("name",""),"signal":sig,
                    "raw_signal":item.get("signal",""),"score":item.get("score"),
                    "signal_date":item.get("signal_date",""),"price":item.get("close",item.get("price")),"extra":ex(item,CHART_EX)})
    return out

def parse_one(data):
    out=[]
    for item in data.get("data",[]):
        sig=normalize_signal(item.get("segnale",""))
        if not sig: continue
        out.append({"ticker":item.get("ticker",""),"name":item.get("nome",""),"signal":sig,
                    "raw_signal":item.get("segnale",""),"score":item.get("score"),
                    "signal_date":item.get("entryDate",""),"price":item.get("prezzo",item.get("price")),"extra":ex(item,ONE_EX)})
    return out

def parse_alert(data):
    out=[]
    for item in (data if isinstance(data,list) else data.get("data",[])):
        sig=normalize_signal(item.get("tipo",item.get("segnale","")))
        if not sig: continue
        out.append({"ticker":item.get("ticker",item.get("display","")),"name":item.get("nome",item.get("name","")),"signal":sig,
                    "raw_signal":item.get("tipo",item.get("segnale","")),"score":item.get("score"),
                    "signal_date":item.get("entry_date",item.get("entryDate","")),"price":item.get("price",item.get("entry_price")),"extra":ex(item,ALERT_EX)})
    return out

def parse_settoriali(data):
    out=[]
    for pname,portfolio in data.get("portfolios",{}).items():
        for item in portfolio.get("positions",[]):
            sig=normalize_signal(item.get("signal",""))
            if not sig: continue
            e=ex(item,SETT_EX); e["portfolio"]=pname
            out.append({"ticker":item.get("ticker",""),"name":item.get("name",""),"signal":sig,
                        "raw_signal":item.get("signal",""),"score":item.get("score"),
                        "signal_date":item.get("entry_date",""),"price":item.get("current_price"),"extra":e})
        seen={i.get("ticker") for i in portfolio.get("positions",[])}
        for item in portfolio.get("qualified",[]):
            if item.get("ticker") in seen: continue
            sig=normalize_signal(item.get("signal",""))
            if not sig: continue
            e=ex(item,SETT_EX); e["portfolio"]=pname
            out.append({"ticker":item.get("ticker",""),"name":item.get("name",""),"signal":sig,
                        "raw_signal":item.get("signal",""),"score":item.get("score"),
                        "signal_date":"","price":None,"extra":e})
    return out

def parse_tematici(data):
    out=[]
    for gname,group in data.get("groups",{}).items():
        for item in group.get("positions",[]):
            raw=item.get("signal",item.get("current_level",item.get("buy_level","")))
            sig=normalize_signal(raw)
            if not sig: continue
            e=ex(item,TEM_EX); e["group"]=gname
            out.append({"ticker":item.get("ticker",""),"name":item.get("name",""),"signal":sig,
                        "raw_signal":raw,"score":item.get("score"),"signal_date":item.get("entry_date",""),
                        "price":item.get("current_price"),"extra":e})
        seen={i.get("ticker") for i in group.get("positions",[])}
        for item in group.get("qualified",[]):
            if item.get("ticker") in seen: continue
            raw=item.get("buy_level",item.get("signal",""))
            sig=normalize_signal(raw)
            if not sig: continue
            e=ex(item,TEM_EX); e["group"]=gname
            out.append({"ticker":item.get("ticker",""),"name":item.get("name",""),"signal":sig,
                        "raw_signal":raw,"score":item.get("score"),"signal_date":item.get("level_ts",""),
                        "price":None,"extra":e})
    return out

def parse_geografia(data):
    out=[]
    # v6: struttura {paesi:{all:[],watchlist:[]}, new_area:{all:[],watchlist:[]}}
    for gname, group in data.items():
        if not isinstance(group, dict): continue
        items_list = group.get("all", group.get("positions", []))
        for item in items_list:
            raw = item.get("buy_level", item.get("signal", item.get("current_level", "")))
            sig = normalize_signal(raw)
            if not sig: continue
            e = ex(item, GEO_EX); e["group"] = gname
            out.append({"ticker":item.get("ticker",""),"name":item.get("name",""),"signal":sig,
                        "raw_signal":raw,"score":item.get("score"),
                        "signal_date":item.get("level_ts",item.get("entry_date","")),
                        "price":item.get("price",item.get("current_price")),"extra":e})
    return out

def parse_scannerv2(data):
    out=[]
    for item in data.get("signals",[]):
        sig=normalize_signal(item.get("signal",""))
        if not sig: continue
        e=ex(item,SCAN_EX)
        if isinstance(e.get("regime"),dict): e["regime"]=e["regime"].get("label","")
        out.append({"ticker":item.get("ticker",""),"name":item.get("nome",item.get("name","")),"signal":sig,
                    "raw_signal":item.get("signal",""),"score":item.get("score"),
                    "signal_date":item.get("signal_date",""),"price":item.get("price"),"extra":e})
    return out

def parse_minfinder(data):
    out=[]
    for item in data.get("top20",[]):
        raw=item.get("buy_level","")
        sig=normalize_signal(raw)
        if not sig: continue
        out.append({"ticker":item.get("ticker",""),"name":item.get("name",""),"signal":sig,
                    "raw_signal":raw,"score":item.get("composite_score"),
                    "signal_date":"","price":item.get("price"),"extra":ex(item,MIN_EX)})
    return out

def parse_leva(data):
    """Parser per raptor_leva.json — usa campo 'zona' per determinare BUY/EXIT."""
    out  = []
    ZONE_BUY  = {"LONG_CONF", "LONG_EARLY"}
    ZONE_EXIT = {"USCITA", "STOP"}
    for item in data.get("data", []):
        zona = item.get("zona", "")
        if zona in ZONE_BUY:
            sig = "BUY"
        elif zona in ZONE_EXIT:
            sig = "EXIT"
        else:
            continue  # GRIGIA, WATCH, ATTENZIONE → scarta
        score = item.get("score")
        # Filtro qualità minimo per BUY
        if sig == "BUY" and (score is None or score < 65):
            continue
        yahoo = item.get("yahoo", item.get("ticker", ""))
        if not yahoo:
            continue
        out.append({
            "ticker":      yahoo,
            "name":        item.get("nome", ""),
            "signal":      sig,
            "raw_signal":  zona,
            "score":       score,
            "signal_date": item.get("entryDate", ""),
            "price":       item.get("prezzo"),
            "extra": {
                "er":        item.get("er"),
                "baff":      item.get("baff"),
                "ao":        item.get("ao"),
                "rsi":       item.get("rsi"),
                "sar_bull":  item.get("sarBull"),
                "vol_ratio": item.get("volRatio"),
                "provider":  item.get("provider", ""),
                "zona":      zona,
                "ret_1w":    item.get("perfSett"),
                "ret_4w":    item.get("perfMese"),
                "kama_fast": item.get("kama_fast"),
                "kama_slow": item.get("kama_slow"),
            }
        })
    return out

PARSERS = {
    "chart":      parse_chart,
    "one":        parse_one,
    "alert":      parse_alert,
    "settoriali": parse_settoriali,
    "tematici":   parse_tematici,
    "geografia":  parse_geografia,
    "scannerv2":  parse_scannerv2,
    "minfinder":  parse_minfinder,
    "leva":       parse_leva,
}

# ── SCORE COMPOSITO ───────────────────────────────────────────────
def composite_score(ev, slot="") -> float:
    sources     = ev.get("sources", [])
    n_src       = len(sources)
    score_raw   = ev.get("score") or 50
    primary_raw = sources[0].get("raw_signal","BUY3") if sources else ev.get("raw_signal","BUY3")

    s_fonte  = min(100, float(score_raw))
    s_buy    = buy_level_score(primary_raw)
    s_nfonti = min(100, n_src * 33)

    r1w = ev.get("ret_1w")
    r4w = ev.get("ret_4w")
    # Normalizza momentum: -20%→0, 0%→50, +20%→100
    s_mom1w = min(100, max(0, (r1w + 20) * 2.5))   if r1w is not None else 50
    s_mom4w = min(100, max(0, (r4w + 30) * 100/60)) if r4w is not None else 50

    cs = s_fonte*0.35 + s_buy*0.20 + s_nfonti*0.20 + s_mom1w*0.15 + s_mom4w*0.10
    if slot in SLOT_RELIABLE: cs += 5
    return round(cs, 1)

# ── MERGE CROSS-REPO ─────────────────────────────────────────────
def merge_cross_repo(raw_items):
    groups = {}
    for source, item, page_url in raw_items:
        key = (item["ticker"], item["signal"])
        if key not in groups:
            groups[key] = {"ticker":item["ticker"],"name":item.get("name",""),
                           "signal":item["signal"],"score":item.get("score"),
                           "signal_date":item.get("signal_date",""),"price":item.get("price"),
                           "sources":[]}
        g = groups[key]
        if not g["name"] and item.get("name"):                   g["name"]        = item["name"]
        if item.get("score") is not None and (g["score"] is None or item["score"] > g["score"]):
                                                                  g["score"]       = item["score"]
        if item.get("signal_date") and not g["signal_date"]:     g["signal_date"] = item["signal_date"]
        if item.get("price") is not None and g["price"] is None: g["price"]       = item["price"]
        g["sources"].append({"source":source,"raw_signal":item.get("raw_signal",item["signal"]),
                             "page_url":page_url,"extra":item.get("extra",{}),"price":item.get("price")})
    return list(groups.values())

# ── FETCH + INDICATORI ────────────────────────────────────────────
def enrich_top(events, slot):
    """Scarica OHLCV 6 mesi e calcola indicatori per i top TOP_ENRICH."""
    for ev in events:
        ev["composite_score"] = composite_score(ev, slot)

    sorted_ev = sorted(events, key=lambda e: e["composite_score"], reverse=True)
    top40     = sorted_ev[:TOP_ENRICH]
    tickers   = [e["ticker"] for e in top40]

    print(f"  Arricchimento top {len(tickers)} ticker con yfinance (6 mesi daily)...")

    daily_data = {}
    for tk in tickers:
        suffixes = [tk]
        if "." not in tk:
            suffixes = [tk+".MI", tk+".L", tk+".PA", tk+".DE", tk]
        for suffix in suffixes:
            try:
                hist = yf.Ticker(suffix).history(period="6mo", interval="1d", auto_adjust=True)
                if len(hist) < 20: continue
                closes = hist["Close"].dropna().values.tolist()
                highs  = hist["High"].dropna().values.tolist()
                lows   = hist["Low"].dropna().values.tolist()
                dates  = [str(d.date()) for d in hist["Close"].dropna().index]
                daily_data[tk] = {"closes":closes,"highs":highs,"lows":lows,
                                  "dates":dates,"ticker_used":suffix}
                print(f"    ✓ {tk} ({suffix}) {len(closes)} barre")
                break
            except Exception:
                continue
        if tk not in daily_data:
            print(f"    ⚠ {tk} — non trovato")
        time.sleep(0.15)

    for ev in top40:
        tk = ev["ticker"]
        if tk not in daily_data:
            continue
        d = daily_data[tk]
        closes = d["closes"]; highs = d["highs"]; lows = d["lows"]; dates = d["dates"]
        n = len(closes)
        r1w  = (closes[-1]/closes[-6]  - 1)*100 if n > 6  else None
        r4w  = (closes[-1]/closes[-21] - 1)*100 if n > 21 else None
        r12w = (closes[-1]/closes[-63] - 1)*100 if n > 63 else None
        ev["ret_1w"]  = round(r1w,  2) if r1w  is not None else None
        ev["ret_4w"]  = round(r4w,  2) if r4w  is not None else None
        ev["ret_12w"] = round(r12w, 2) if r12w is not None else None
        if not ev.get("price"): ev["price"] = round(float(closes[-1]), 4)

        ev["composite_score"] = composite_score(ev, slot)

        if compute_all:
            try:
                ind = compute_all(dates, closes, highs, lows)
                ev["indicators"] = {k:v for k,v in ind.items() if k != "chart"}
                ev["chart_data"] = ind.get("chart", {})
            except Exception as ex_err:
                print(f"    [WARN] indicatori {tk}: {ex_err}")

        ev["tv_symbol"] = tv_symbol(tk)

    sorted_final  = sorted(events, key=lambda e: e["composite_score"], reverse=True)
    top20_tickers = {e["ticker"] for e in sorted_final[:TOP_FINAL]}
    for ev in events:
        ev["is_top20"] = ev["ticker"] in top20_tickers

    return events

# ── STORICO ───────────────────────────────────────────────────────
def load_history():
    if not os.path.exists(SIGNALS_FILE): return []
    try:
        with open(SIGNALS_FILE) as f: return json.load(f)
    except Exception: return []

def save_history(events):
    with open(SIGNALS_FILE, "w") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

def prune_old(events, now):
    cutoff = now - timedelta(days=MAX_DAYS)
    return [e for e in events if datetime.fromisoformat(e["detected_at"]) >= cutoff]

# ── MAIN ──────────────────────────────────────────────────────────
def run():
    now     = datetime.now(timezone.utc)
    now_str = now.isoformat()
    slot    = detect_slot(now)
    print(f"[SNIPER v3.1] {now_str} — Slot: {slot}")

    history = load_history()
    history = prune_old(history, now)

    cutoff_24h  = now - timedelta(hours=24)
    recent_keys = set()
    for e in history:
        detected = datetime.fromisoformat(e["detected_at"])
        if detected >= cutoff_24h:
            for s in e.get("sources", []):
                recent_keys.add(f"{s['source']}|{e['ticker']}|{e['signal']}")

    # Raccoglie segnali
    raw_new = []
    for src_name, src_cfg in SOURCES.items():
        print(f"  Fetching {src_name}...")
        data = fetch_json(src_cfg["url"])
        if data is None: continue
        try:
            items = PARSERS[src_cfg["parser"]](data)
        except Exception as ex_err:
            print(f"  [ERR] {src_name}: {ex_err}"); continue
        print(f"  → {len(items)} segnali")
        for item in items:
            if not item["ticker"]: continue
            key = f"{src_name}|{item['ticker']}|{item['signal']}"
            if key in recent_keys: continue
            recent_keys.add(key)
            raw_new.append((src_name, item, src_cfg["page_url"]))
            print(f"    + {item['ticker']} {item['signal']} [{src_name}]")

    merged = merge_cross_repo(raw_new)

    for ev in merged:
        ev["detected_at"]     = now_str
        ev["slot"]            = slot
        ev["id"]              = f"{ev['ticker']}|{ev['signal']}|{now_str}"
        ev["is_top20"]        = False
        ev["composite_score"] = 0

    if merged:
        merged = enrich_top(merged, slot)

    # Merge con storico — deduplica stesso ticker+segnale nello stesso giorno CET
    all_events = merged + history
    all_events = prune_old(all_events, now)

    # Deduplica: per stesso ticker+segnale nello stesso giorno CET, tieni solo il più recente
    seen_day = {}
    deduped  = []
    for ev in sorted(all_events, key=lambda e: e["detected_at"], reverse=True):
        try:
            from datetime import timezone as tz
            dt  = datetime.fromisoformat(ev["detected_at"])
            cet = dt.astimezone(__import__('zoneinfo').ZoneInfo("Europe/Rome"))
            day_key = f"{cet.date()}|{ev['ticker']}|{ev['signal']}"
        except Exception:
            day_key = f"{ev['detected_at'][:10]}|{ev['ticker']}|{ev['signal']}"
        if day_key not in seen_day:
            seen_day[day_key] = True
            deduped.append(ev)

    deduped.sort(key=lambda e: e["composite_score"], reverse=True)
    save_history(deduped)

    n_top20 = sum(1 for e in merged if e.get("is_top20"))
    print(f"\n[SNIPER] {len(deduped)} totali (deduplicati), {len(merged)} nuovi, {n_top20} top20")
    if merged:
        print("  Top 5:")
        for ev in sorted(merged, key=lambda e: e["composite_score"], reverse=True)[:5]:
            srcs = "+".join(s["source"] for s in ev.get("sources", []))
            mom  = f" 1W:{ev.get('ret_1w','?')}%" if ev.get("ret_1w") is not None else ""
            print(f"    [{ev['composite_score']}★] {ev['ticker']} {ev['signal']} [{srcs}]{mom}")

if __name__ == "__main__":
    run()
