#!/usr/bin/env python3
"""Independent PAPER engine for inverse/short ETPs. No broker integration."""
import argparse, csv, json, math, time, warnings
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import yfinance as yf

ROOT=Path(__file__).resolve().parent
UNIVERSE=ROOT/"data"/"instrument_universe.json"
STATE=ROOT/"data"/"short_paper_state.json"
LOG=ROOT/"data"/"short_paper_log.csv"
SUMMARY=ROOT/"data"/"short_paper_summary.json"
COSTS_BPS=(20,30,50)
BATCH=20
CATEGORIES=("LEVA_SHORT","MATERIE_PRIME_SHORT")
warnings.filterwarnings("ignore")

def indicators(df):
    c,h,l=df.Close,df.High,df.Low
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    prior_high=h.shift(1).rolling(20).max()
    mid=c.rolling(20).mean()
    upper=mid+2*c.rolling(20).std()
    near=(c>=upper*0.985)&(c>=mid)&(upper>upper.shift(1))
    walking=near.rolling(3,min_periods=3).sum()>=2
    return atr,prior_high,walking.fillna(False)

def blank_state():
    return {"schema_version":1,"last_processed":{},"positions":{},"pending_entries":{},"pending_exits":{},"trades":[],"updated_at":None}

def close_trade(state,ticker,p,date,price,reason):
    gross=(float(price)/p["entry_price"]-1)*100
    state["trades"].append({
        "ticker":ticker,"category":p["category"],"signal_date":p["signal_date"],
        "entry_date":p["entry_date"],"entry_price":round(p["entry_price"],8),
        "exit_date":str(date),"exit_price":round(float(price),8),
        "holding_sessions":p["holding_sessions"],"exit_reason":reason,
        "gross_return_pct":round(gross,4),
        "net_return_pct_by_cost_bps":{str(b):round(gross-b/100,4) for b in COSTS_BPS},
        "spread_observed":False,"spread_note":"Bid/ask non disponibile: costi solo ipotesi round-trip."
    })
    state["positions"].pop(ticker,None)

def process_bar(state,ticker,category,date,row,atr_value,donchian,walking):
    """A long position in an inverse ETP: bullish signal on the inverse instrument."""
    date=str(pd.Timestamp(date).date())
    if ticker in state["pending_exits"] and ticker in state["positions"]:
        p=state["positions"][ticker]
        close_trade(state,ticker,p,date,float(row.Open),state["pending_exits"].pop(ticker))
    if ticker in state["pending_entries"] and ticker not in state["positions"]:
        pending=state["pending_entries"].pop(ticker)
        op=float(row.Open)
        if math.isfinite(op) and op>0 and math.isfinite(pending["atr"]) and pending["atr"]>0:
            state["positions"][ticker]={"category":category,"signal_date":pending["signal_date"],
                "entry_date":date,"entry_price":op,"initial_atr":pending["atr"],
                "stop_price":op-2*pending["atr"],"holding_sessions":0,"walking_false_streak":0}
    p=state["positions"].get(ticker)
    if p:
        p["holding_sessions"]+=1
        stop=p["stop_price"]
        if float(row.Low)<=stop:
            fill=float(row.Open) if float(row.Open)<stop else stop
            close_trade(state,ticker,p,date,fill,"ATR_2_STOP")
            return
        p["walking_false_streak"]=0 if walking else p["walking_false_streak"]+1
        if p["holding_sessions"]>=10:
            reason="WALKING_2_NEGATIVE_CLOSES" if p["walking_false_streak"]>=2 else "TIME_MAX_10_SESSIONS"
            close_trade(state,ticker,p,date,float(row.Close),reason)
            return
        if p["walking_false_streak"]>=2:
            state["pending_exits"][ticker]="WALKING_2_NEGATIVE_CLOSES"
    if ticker not in state["positions"] and ticker not in state["pending_entries"] and ticker not in state["pending_exits"]:
        if bool(donchian) and bool(walking) and math.isfinite(atr_value) and atr_value>0:
            state["pending_entries"][ticker]={"signal_date":date,"atr":float(atr_value)}

def self_test():
    R=lambda o,h,l,c:type("Bar",(),{"Open":o,"High":h,"Low":l,"Close":c})()
    s=blank_state()
    process_bar(s,"S","LEVA_SHORT","2026-01-02",R(50,52,49,51),1,True,False)
    assert "S" not in s["pending_entries"], "Walking filter must reject a Donchian-only breakout"
    process_bar(s,"S","LEVA_SHORT","2026-01-05",R(50,52,49,51),1,True,True)
    assert "S" in s["pending_entries"], "Confirmed breakout should queue next-open entry"
    process_bar(s,"S","LEVA_SHORT","2026-01-06",R(51,53,50,52),1,False,True)
    assert s["positions"]["S"]["entry_price"]==51
    process_bar(s,"S","LEVA_SHORT","2026-01-07",R(52,53,51,52),1,False,False)
    process_bar(s,"S","LEVA_SHORT","2026-01-08",R(51,52,50,51),1,False,False)
    assert "S" in s["pending_exits"]
    process_bar(s,"S","LEVA_SHORT","2026-01-09",R(50,51,49,50),1,False,True)
    assert len(s["trades"])==1 and s["trades"][0]["exit_reason"]=="WALKING_2_NEGATIVE_CLOSES"
    s=blank_state()
    process_bar(s,"G","MATERIE_PRIME_SHORT","2026-01-02",R(50,51,49,50),1,True,True)
    process_bar(s,"G","MATERIE_PRIME_SHORT","2026-01-05",R(50,51,49,50),1,False,True)
    process_bar(s,"G","MATERIE_PRIME_SHORT","2026-01-06",R(50,51,47,48),1,False,True)
    assert len(s["trades"])==1 and s["trades"][0]["exit_reason"]=="ATR_2_STOP"
    print("SHORT_SELF_TEST_OK: Donchian20+Walking filter, next-open entry, ATR14x2 stop, two-close Walking exit")

def get_frame(raw,ticker):
    try:
        if isinstance(raw.columns,pd.MultiIndex):
            if ticker not in raw.columns.get_level_values(0): return None
            x=raw[ticker].copy()
        else: x=raw.copy()
        if isinstance(x.columns,pd.MultiIndex): x.columns=x.columns.get_level_values(0)
        cols=["Open","High","Low","Close","Volume"]
        if not set(cols).issubset(x.columns): return None
        x=x[cols].dropna(subset=["Open","High","Low","Close"])
        x=x[~x.index.duplicated(keep="last")]
        return x[(x.Close>0)&(x.Open>0)&(x.High>0)&(x.Low>0)]
    except Exception: return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--backfill-from",help="Isolated historical paper reconstruction from YYYY-MM-DD")
    args=ap.parse_args()
    if args.self_test: self_test(); return
    state_path,log_path,summary_path=STATE,LOG,SUMMARY
    if args.backfill_from:
        try: start_date=str(pd.Timestamp(args.backfill_from).date())
        except Exception: raise SystemExit("--backfill-from must be YYYY-MM-DD")
        suffix=start_date.replace("-","")
        state_path=ROOT/"data"/f"short_paper_backfill_{suffix}_state.json"
        log_path=ROOT/"data"/f"short_paper_backfill_{suffix}_log.csv"
        summary_path=ROOT/"data"/f"short_paper_backfill_{suffix}_summary.json"
    universe=json.loads(UNIVERSE.read_text(encoding="utf-8"))["instruments"]
    selected={x.get("yahoo") or x.get("ticker"):x for x in universe
              if x.get("classification") in CATEGORIES and (x.get("yahoo") or x.get("ticker"))}
    tickers=list(selected)
    state=json.loads(state_path.read_text(encoding="utf-8")) if (not args.backfill_from and state_path.exists()) else blank_state()
    for k in ("last_processed","positions","pending_entries","pending_exits","trades"): state.setdefault(k,{} if k!="trades" else [])
    fetched=0; skipped=[]
    for start in range(0,len(tickers),BATCH):
        batch=tickers[start:start+BATCH]
        try:
            raw=yf.download(batch,period="2y",interval="1d",auto_adjust=False,actions=True,repair=True,
                group_by="ticker",threads=False,progress=False,timeout=35)
        except Exception as e:
            skipped.extend([{"ticker":t,"reason":str(e)[:160]} for t in batch]); continue
        for ticker in batch:
            df=get_frame(raw,ticker)
            if df is None or len(df)<60:
                skipped.append({"ticker":ticker,"reason":"dati assenti o meno di 60 sedute"}); continue
            atr,prior_high,walking=indicators(df)
            last=state["last_processed"].get(ticker)
            if args.backfill_from:
                dates=[d for d in df.index if str(pd.Timestamp(d).date())>=start_date]
            elif last:
                dates=[d for d in df.index if str(pd.Timestamp(d).date())>last]
            else:
                dates=[df.index[-1]]
            for dt in dates:
                ix=df.index.get_loc(dt); row=df.loc[dt]
                av=float(atr.iloc[ix]) if pd.notna(atr.iloc[ix]) else float("nan")
                dc=bool(df.Close.iloc[ix]>prior_high.iloc[ix]) if pd.notna(prior_high.iloc[ix]) else False
                process_bar(state,ticker,selected[ticker].get("classification"),dt,row,av,dc,bool(walking.iloc[ix]))
                state["last_processed"][ticker]=str(pd.Timestamp(dt).date()); fetched+=1
        time.sleep(0.4)
    state["updated_at"]=datetime.now(timezone.utc).isoformat()
    state_path.parent.mkdir(parents=True,exist_ok=True)
    state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")
    fields=["ticker","category","signal_date","entry_date","entry_price","exit_date","exit_price","holding_sessions","exit_reason","gross_return_pct","net_return_pct_by_cost_bps","spread_observed","spread_note"]
    append_mode=not bool(args.backfill_from); existing=log_path.exists() and append_mode
    start_index=int(state.get("logged_trades",0)) if append_mode else 0
    with log_path.open("a" if append_mode else "w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields)
        if not existing: w.writeheader()
        for item in state["trades"][start_index:]:
            row=dict(item); row["net_return_pct_by_cost_bps"]=json.dumps(row["net_return_pct_by_cost_bps"]); w.writerow(row)
    state["logged_trades"]=len(state["trades"])
    state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")
    positions=[{"ticker":t,**p} for t,p in state["positions"].items()]
    summary={"generated_at":state["updated_at"],"mode":"PAPER_ONLY_NO_ORDERS",
        "engine":"SNIPER_SHORT_INVERSE_ETP","universe":{"total_selected":len(tickers),
        "categories":{c:sum(x.get("classification")==c for x in selected.values()) for c in CATEGORIES}},
        "processed_bars":fetched,"open_positions":len(positions),"pending_entries":len(state["pending_entries"]),
        "pending_exits":len(state["pending_exits"]),"closed_trades":len(state["trades"]),
        "open_positions_detail":positions,"pending_entries_detail":state["pending_entries"],
        "pending_exits_detail":state["pending_exits"],"closed_trades_latest":state["trades"][-30:],
        "skipped_count":len(skipped),"skipped_latest":skipped[-30:],
        "cost_sensitivity_bps_round_trip":list(COSTS_BPS),
        "spread_data":"Bid/ask non disponibile da Yahoo OHLC; costi sono sensitività, non spread osservati.",
        "price_basis":"Yahoo OHLC auto_adjust=False, actions=True, repair=True; prezzi storici split-adjusted, non necessariamente prezzi nominali originali as-traded.",
        "rules":{"instrument":"Buy-and-hold PAPER on inverse/short ETPs; this is not broker short-selling.",
        "entry":"Donchian20 breakout on the inverse ETP plus Walking true at completed close; enter next session open.",
        "stop":"Initial stop at entry minus 2 x ATR14 measured at signal close; daily low checked; adverse gap exits at open.",
        "exit":"After two consecutive completed closes with Walking false, exit next open; hard cap at close of session 10.",
        "activation":"First live run establishes a baseline on latest daily candle; no historical trades fabricated."}}
    if args.backfill_from:
        summary["simulation_window_start"]=start_date
        summary["rules"]["activation"]="Isolated historical reconstruction; live short paper state is not modified."
    summary_path.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"mode":summary["mode"],"engine":summary["engine"],"universe":summary["universe"],
        "processed_bars":fetched,"open_positions":len(positions),"pending_entries":len(state["pending_entries"]),
        "pending_exits":len(state["pending_exits"]),"closed_trades":len(state["trades"]),"skipped":len(skipped)}))
    if fetched==0: print("NO_NEW_MARKET_BARS: state preserved; no synthetic trades created.")

if __name__=="__main__": main()
