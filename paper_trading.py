#!/usr/bin/env python3
"""Independent Sniper paper book for Donchian/ATR2 + Walking exits.
No broker integration and no real orders. Signals at close; entries/exits next open.
"""
import argparse, csv, json, math, sys, time, warnings
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import yfinance as yf

ROOT=Path(__file__).resolve().parent
UNIVERSE=ROOT/"data"/"instrument_universe.json"
STATE=ROOT/"data"/"paper_trading_state.json"
LOG=ROOT/"data"/"paper_trading_log.csv"
SUMMARY=ROOT/"data"/"paper_trading_summary.json"
COSTS_BPS=(20,30,50)
BATCH=20
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
    return atr, prior_high, walking.fillna(False)

def blank_state():
    return {"schema_version":1,"last_processed":{},"positions":{},"pending_entries":{},"pending_exits":{},"trades":[],"updated_at":None}

def close_trade(state,ticker,position,date,price,reason):
    gross=(float(price)/position["entry_price"]-1)*100
    row={"ticker":ticker,"category":position["category"],"signal_date":position["signal_date"],
         "entry_date":position["entry_date"],"entry_price":round(position["entry_price"],8),
         "exit_date":str(date),"exit_price":round(float(price),8),"holding_sessions":position["holding_sessions"],
         "exit_reason":reason,"gross_return_pct":round(gross,4),
         "net_return_pct_by_cost_bps":{str(b):round(gross-b/100,4) for b in COSTS_BPS},
         "spread_observed":False,"spread_note":"Bid/ask non disponibile: costi solo ipotesi round-trip."}
    state["trades"].append(row)
    state["positions"].pop(ticker,None)

def process_bar(state,ticker,category,date,row,atr_value,donchian,walking):
    """Process one completed daily candle, without using future data."""
    date=str(pd.Timestamp(date).date())
    # Pending exits from a previous completed close execute at today's open.
    if ticker in state["pending_exits"] and ticker in state["positions"]:
        p=state["positions"][ticker]
        close_trade(state,ticker,p,date,float(row.Open),state["pending_exits"].pop(ticker))
    # Pending entry from a previous close executes at today's open.
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
        # Conservative daily-bar assumption: stop checked before close-based exits.
        stop=p["stop_price"]
        if float(row.Low)<=stop:
            fill=float(row.Open) if float(row.Open)<stop else stop
            close_trade(state,ticker,p,date,fill,"ATR_2_STOP")
            return
        if category=="LEVA_LONG":
            if p["holding_sessions"]>=3:
                close_trade(state,ticker,p,date,float(row.Close),"TIME_3_SESSIONS")
                return
        elif category=="MATERIE_PRIME_LEVA":
            p["walking_false_streak"]=0 if walking else p["walking_false_streak"]+1
            if p["holding_sessions"]>=10:
                # Hard cap: never carry a commodity position beyond session 10.
                # If Walking confirms on session 10, exit at that session's close.
                reason="WALKING_2_NEGATIVE_CLOSES" if p["walking_false_streak"]>=2 else "TIME_MAX_10_SESSIONS"
                close_trade(state,ticker,p,date,float(row.Close),reason)
                return
            elif p["walking_false_streak"]>=2:
                state["pending_exits"][ticker]="WALKING_2_NEGATIVE_CLOSES"
    # A breakout at today's close can only enter at the next session open.
    if ticker not in state["positions"] and ticker not in state["pending_entries"] and ticker not in state["pending_exits"]:
        if bool(donchian) and math.isfinite(atr_value) and atr_value>0:
            state["pending_entries"][ticker]={"signal_date":date,"atr":float(atr_value)}

def self_test():
    s=blank_state()
    process_bar(s,"TEST","LEVA_LONG","2026-01-02",type("R",(),{"Open":100,"High":101,"Low":99,"Close":100})(),2,True,False)
    assert "TEST" in s["pending_entries"] and "TEST" not in s["positions"]
    process_bar(s,"TEST","LEVA_LONG","2026-01-05",type("R",(),{"Open":101,"High":103,"Low":100,"Close":102})(),2,False,True)
    assert s["positions"]["TEST"]["entry_price"]==101
    process_bar(s,"TEST","LEVA_LONG","2026-01-06",type("R",(),{"Open":102,"High":104,"Low":101,"Close":103})(),2,False,True)
    assert s["positions"]["TEST"]["holding_sessions"]==2
    process_bar(s,"TEST","LEVA_LONG","2026-01-07",type("R",(),{"Open":103,"High":105,"Low":102,"Close":104})(),2,False,True)
    assert len(s["trades"])==1 and s["trades"][0]["exit_reason"]=="TIME_3_SESSIONS"
    s=blank_state()
    process_bar(s,"COM","MATERIE_PRIME_LEVA","2026-01-02",type("R",(),{"Open":50,"High":51,"Low":49,"Close":50})(),1,True,True)
    process_bar(s,"COM","MATERIE_PRIME_LEVA","2026-01-05",type("R",(),{"Open":50,"High":51,"Low":49,"Close":50})(),1,False,False)
    process_bar(s,"COM","MATERIE_PRIME_LEVA","2026-01-06",type("R",(),{"Open":51,"High":52,"Low":50,"Close":51})(),1,False,False)
    assert "COM" in s["pending_exits"]
    process_bar(s,"COM","MATERIE_PRIME_LEVA","2026-01-07",type("R",(),{"Open":49,"High":50,"Low":48,"Close":49})(),1,False,True)
    assert len(s["trades"])==1 and s["trades"][0]["exit_reason"]=="WALKING_2_NEGATIVE_CLOSES"
    s=blank_state()
    process_bar(s,"STOP","LEVA_LONG","2026-01-02",type("R",(),{"Open":100,"High":101,"Low":99,"Close":100})(),2,True,False)
    process_bar(s,"STOP","LEVA_LONG","2026-01-05",type("R",(),{"Open":101,"High":102,"Low":95,"Close":96})(),2,False,False)
    assert len(s["trades"])==1 and s["trades"][0]["exit_reason"]=="ATR_2_STOP"
    # Commodity hard-cap test: second Walking failure on session 10 exits at that close.
    s=blank_state()
    process_bar(s,"CAP","MATERIE_PRIME_LEVA","2026-01-02",type("R",(),{"Open":50,"High":51,"Low":49,"Close":50})(),1,True,True)
    process_bar(s,"CAP","MATERIE_PRIME_LEVA","2026-01-05",type("R",(),{"Open":50,"High":51,"Low":49,"Close":50})(),1,False,True)
    for day in range(2,10):
        process_bar(s,"CAP","MATERIE_PRIME_LEVA",f"2026-01-{day+5:02d}",type("R",(),{"Open":50,"High":51,"Low":49,"Close":50})(),1,False,True)
    assert s["positions"]["CAP"]["holding_sessions"]==9
    process_bar(s,"CAP","MATERIE_PRIME_LEVA","2026-01-15",type("R",(),{"Open":50,"High":51,"Low":49,"Close":48})(),1,False,False)
    assert len(s["trades"])==1 and s["trades"][0]["holding_sessions"]==10
    assert s["trades"][0]["exit_reason"]=="WALKING_2_NEGATIVE_CLOSES" and "CAP" not in s["positions"]
    print("SELF_TEST_OK: next-open entry, 3-session time exit, Walking next-open exit, ATR stop, commodity hard cap session 10")
    
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
    ap.add_argument("--backfill-from", help="Run an isolated historical paper simulation from YYYY-MM-DD")
    args=ap.parse_args()
    if args.self_test: self_test(); return
    # Historical reconstruction is isolated from the live paper book.
    state_path=STATE
    log_path=LOG
    summary_path=SUMMARY
    if args.backfill_from:
        try: start_date=str(pd.Timestamp(args.backfill_from).date())
        except Exception: raise SystemExit("--backfill-from must be YYYY-MM-DD")
        suffix=start_date.replace("-","")
        state_path=ROOT/"data"/f"paper_backfill_{suffix}_state.json"
        log_path=ROOT/"data"/f"paper_backfill_{suffix}_log.csv"
        summary_path=ROOT/"data"/f"paper_backfill_{suffix}_summary.json"
    universe=json.loads(UNIVERSE.read_text(encoding="utf-8"))["instruments"]
    selected={x.get("yahoo") or x.get("ticker"):x for x in universe
              if x.get("classification") in ("LEVA_LONG","MATERIE_PRIME_LEVA") and (x.get("yahoo") or x.get("ticker"))}
    tickers=list(selected)
    state=json.loads(state_path.read_text(encoding="utf-8")) if (not args.backfill_from and state_path.exists()) else blank_state()
    state.setdefault("last_processed",{}); state.setdefault("positions",{})
    state.setdefault("pending_entries",{}); state.setdefault("pending_exits",{}); state.setdefault("trades",[])
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
                # Compute indicators on full history, but simulate only bars from requested date onward.
                dates=[d for d in df.index if str(pd.Timestamp(d).date())>=start_date]
            elif last:
                dates=[d for d in df.index if str(pd.Timestamp(d).date())>last]
            else:
                # First live activation is a clean baseline: no historical trades are invented.
                dates=[df.index[-1]]
            if not dates:
                continue
            for dt in dates:
                ix=df.index.get_loc(dt)
                row=df.loc[dt]
                av=float(atr.iloc[ix]) if pd.notna(atr.iloc[ix]) else float("nan")
                dc=bool(df.Close.iloc[ix]>prior_high.iloc[ix]) if pd.notna(prior_high.iloc[ix]) else False
                process_bar(state,ticker,selected[ticker].get("classification"),dt,row,av,dc,bool(walking.iloc[ix]))
                state["last_processed"][ticker]=str(pd.Timestamp(dt).date())
                fetched+=1
        time.sleep(0.4)
    state["updated_at"]=datetime.now(timezone.utc).isoformat()
    state_path.parent.mkdir(parents=True,exist_ok=True)
    state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")
    fields=["ticker","category","signal_date","entry_date","entry_price","exit_date","exit_price","holding_sessions","exit_reason","gross_return_pct","net_return_pct_by_cost_bps","spread_observed","spread_note"]
    existing=log_path.exists()
    with log_path.open("a",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields)
        if not existing: w.writeheader()
        for row in state["trades"][int(state.get("logged_trades",0)):]:
            r=dict(row); r["net_return_pct_by_cost_bps"]=json.dumps(r["net_return_pct_by_cost_bps"])
            w.writerow(r)
    state["logged_trades"]=len(state["trades"])
    state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")
    open_positions=[]
    for t,p in state["positions"].items():
        open_positions.append({"ticker":t,**p})
    summary={"generated_at":state["updated_at"],"mode":"PAPER_ONLY_NO_ORDERS",
        "universe":{"total_selected":len(tickers),"categories":{"LEVA_LONG":sum(x.get("classification")=="LEVA_LONG" for x in selected.values()),
        "MATERIE_PRIME_LEVA":sum(x.get("classification")=="MATERIE_PRIME_LEVA" for x in selected.values())}},
        "processed_bars":fetched,"open_positions":len(open_positions),"pending_entries":len(state["pending_entries"]),
        "closed_trades":len(state["trades"]),"open_positions_detail":open_positions,
        "pending_entries_detail":state["pending_entries"],"closed_trades_latest":state["trades"][-30:],
        "cost_sensitivity_bps_round_trip":list(COSTS_BPS),
        "spread_data":"Not available from Yahoo OHLC. No observed spread is claimed; net returns are sensitivities only.",
        "price_basis":"Yahoo OHLC downloaded with auto_adjust=False and actions=True: split-adjusted historical OHLC without dividend adjustment. These are not guaranteed to be original as-traded historical nominal quotes; they are used consistently for indicators, ATR, stops and simulated fills. Dividend-adjusted OHLC is deliberately not used for execution.",
        "skipped_count":len(skipped),"skipped_latest":skipped[-30:],
        "rules":{"entry":"Donchian 20 breakout at completed close; enter next session open",
        "stop":"Initial stop at entry minus 2 x ATR(14) from signal close; daily low checked; adverse gap exits at open",
        "LEVA_LONG":"Exit at close of third holding session",
        "MATERIE_PRIME_LEVA":"Exit next open after two consecutive completed closes with Walking upper Bollinger Band false; hard cap at close of session 10 (never held into session 11)",
        "walking":"Not an entry filter","position_limit":"One open position per ticker; no overlapping entries",
        "activation":"First run establishes a baseline on the latest available daily candle; it does not backfill or fabricate historical trades."}}
    if args.backfill_from:
        summary["simulation_window_start"]=start_date
        summary["rules"]["activation"]="Isolated historical reconstruction from requested date; live paper state is not modified."
    summary_path.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"mode":summary["mode"],"universe":summary["universe"],"processed_bars":fetched,
        "open_positions":len(open_positions),"pending_entries":len(state["pending_entries"]),
        "closed_trades":len(state["trades"]),"skipped":len(skipped)},ensure_ascii=False))
    if fetched==0: print("NO_NEW_MARKET_BARS: state preserved; no synthetic trades created.")

if __name__=="__main__": main()
