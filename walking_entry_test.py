#!/usr/bin/env python3
"""Out-of-sample-style comparison of Walking as an entry filter for commodity leveraged ETPs.
All variants use identical ATR2 stops and Walking-based/time exits. No live book is modified.
"""
import argparse, csv, json, math, time, warnings
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf

ROOT=Path(__file__).resolve().parent
UNIVERSE=ROOT/"data"/"instrument_universe.json"
START_DEFAULT="2023-01-01"
BATCH=15
warnings.filterwarnings("ignore")

VARIANTS={
    "A_DONCHIAN20": {"period":20,"walking_entry":False},
    "B_DONCHIAN20_WALKING": {"period":20,"walking_entry":True},
    "C_DONCHIAN10_WALKING": {"period":10,"walking_entry":True},
}

def get_frame(raw,ticker):
    try:
        x=raw[ticker].copy() if isinstance(raw.columns,pd.MultiIndex) and ticker in raw.columns.get_level_values(0) else raw.copy()
        if isinstance(x.columns,pd.MultiIndex): x.columns=x.columns.get_level_values(0)
        cols=["Open","High","Low","Close","Volume"]
        if not set(cols).issubset(x.columns): return None
        x=x[cols].dropna(subset=["Open","High","Low","Close"])
        x=x[~x.index.duplicated(keep="last")]
        return x[(x.Close>0)&(x.Open>0)&(x.High>0)&(x.Low>0)]
    except Exception: return None

def indicators(df):
    h,l,c=df.High,df.Low,df.Close
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    mid=c.rolling(20).mean()
    sd=c.rolling(20).std()
    upper=mid+2*sd
    near=(c>=upper*0.985)&(c>=mid)&(upper>upper.shift(1))
    walking=(near.rolling(3,min_periods=3).sum()>=2).fillna(False)
    donch={}
    for n in (10,20):
        prior=h.shift(1).rolling(n).max()
        donch[n]=(c>prior).fillna(False)
    return atr,walking,donch

def run_variant(frames,variant,start_date):
    cfg=VARIANTS[variant]
    trades=[]
    skipped=[]
    for ticker,df in frames.items():
        atr,walking,donch=indicators(df)
        pos=None
        pending=None
        pending_exit=False
        dates=df.index
        for i,dt in enumerate(dates):
            d=str(pd.Timestamp(dt).date())
            row=df.iloc[i]
            # Pending exit executes at today's open.
            if pending_exit and pos is not None:
                px=float(row.Open)
                if math.isfinite(px) and px>0:
                    gross=(px/pos["entry"]-1)*100
                    trades.append({"variant":variant,"ticker":ticker,"signal_date":pos["signal_date"],"entry_date":pos["entry_date"],
                        "entry_price":pos["entry"],"exit_date":d,"exit_price":px,"holding_sessions":pos["held"],
                        "exit_reason":"WALKING_2_NEGATIVE_CLOSES","gross_return_pct":gross})
                pos=None
                pending_exit=False
            # Pending entry executes at today's open.
            if pending is not None and pos is None:
                op=float(row.Open)
                av=pending["atr"]
                if math.isfinite(op) and op>0 and math.isfinite(av) and av>0:
                    pos={"signal_date":pending["signal_date"],"entry_date":d,"entry":op,"stop":op-2*av,"held":0,"false_streak":0}
                pending=None
            if pos is not None:
                pos["held"]+=1
                if float(row.Low)<=pos["stop"]:
                    op=float(row.Open)
                    px=op if op<pos["stop"] else pos["stop"]
                    gross=(px/pos["entry"]-1)*100
                    trades.append({"variant":variant,"ticker":ticker,"signal_date":pos["signal_date"],"entry_date":pos["entry_date"],
                        "entry_price":pos["entry"],"exit_date":d,"exit_price":px,"holding_sessions":pos["held"],
                        "exit_reason":"ATR_2_STOP","gross_return_pct":gross})
                    pos=None
                else:
                    pos["false_streak"]=0 if bool(walking.iloc[i]) else pos["false_streak"]+1
                    if pos["held"]>=10:
                        px=float(row.Close)
                        gross=(px/pos["entry"]-1)*100
                        reason="WALKING_2_NEGATIVE_CLOSES" if pos["false_streak"]>=2 else "TIME_MAX_10_SESSIONS"
                        trades.append({"variant":variant,"ticker":ticker,"signal_date":pos["signal_date"],"entry_date":pos["entry_date"],
                            "entry_price":pos["entry"],"exit_date":d,"exit_price":px,"holding_sessions":pos["held"],
                            "exit_reason":reason,"gross_return_pct":gross})
                        pos=None
                    elif pos["false_streak"]>=2:
                        pending_exit=True
            # Signal only after today's completed close; entry is next session open.
            if d>=start_date and pos is None and pending is None and not pending_exit:
                period=cfg["period"]
                if bool(donch[period].iloc[i]) and (not cfg["walking_entry"] or bool(walking.iloc[i])):
                    av=float(atr.iloc[i]) if pd.notna(atr.iloc[i]) else float("nan")
                    if math.isfinite(av) and av>0:
                        pending={"signal_date":d,"atr":av}
        # Open/pending positions are not marked as closed trades.
        if pos is not None or pending is not None:
            skipped.append({"ticker":ticker,"reason":"posizione o ingresso ancora aperto a fine finestra"})
    return trades,skipped

def metrics(rows):
    if not rows:
        return {"trades":0,"wins":0,"win_rate_pct":None,"gross_mean_pct":None,
                "gross_profit_factor":None,"gross_median_pct":None,"worst_trade_pct":None}
    gross=np.array([x["gross_return_pct"] for x in rows],dtype=float)
    gp=float(gross[gross>0].sum()); gl=float(-gross[gross<0].sum())
    return {"trades":len(rows),"wins":int((gross>0).sum()),"win_rate_pct":round(float((gross>0).mean()*100),2),
        "gross_mean_pct":round(float(gross.mean()),3),
        "gross_profit_factor":round(gp/gl,3) if gl else None,
        "gross_median_pct":round(float(np.median(gross)),3),"worst_trade_pct":round(float(gross.min()),3)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--from-date",default=START_DEFAULT)
    args=ap.parse_args()
    start=str(pd.Timestamp(args.from_date).date())
    OUT_JSON=ROOT/"data"/f"walking_entry_test_{start.replace('-','')}.json"
    OUT_CSV=ROOT/"data"/f"walking_entry_test_{start.replace('-','')}_trades.csv"
    universe=json.loads(UNIVERSE.read_text(encoding="utf-8"))["instruments"]
    tickers=[x.get("yahoo") or x.get("ticker") for x in universe if x.get("classification")=="MATERIE_PRIME_LEVA" and (x.get("yahoo") or x.get("ticker"))]
    frames={}; failed=[]
    for j in range(0,len(tickers),BATCH):
        batch=tickers[j:j+BATCH]
        try:
            raw=yf.download(batch,period="10y",interval="1d",auto_adjust=False,actions=True,repair=True,
                group_by="ticker",threads=False,progress=False,timeout=35)
        except Exception as e:
            failed.extend({"ticker":t,"reason":str(e)[:180]} for t in batch); continue
        for ticker in batch:
            df=get_frame(raw,ticker)
            if df is None or len(df)<60:
                failed.append({"ticker":ticker,"reason":"dati assenti o meno di 60 sedute"})
            else:
                frames[ticker]=df
        time.sleep(0.4)
    result={"window_start":start,"window_end":str(pd.Timestamp.now(tz="UTC").date()),"universe_count":len(tickers),
        "tickers_with_data":len(frames),"failed_data":failed,"method":{
        "A_DONCHIAN20":"breakout close above previous 20-session high; next open entry",
        "B_DONCHIAN20_WALKING":"same Donchian20 breakout plus Walking true on same completed close; next open entry",
        "C_DONCHIAN10_WALKING":"breakout close above previous 10-session high plus Walking true on same completed close; next open entry",
        "walking_definition":"Close >= 98.5% of upper Bollinger band, Close >= 20-session mean, upper band rising; condition true on at least 2 of last 3 completed sessions",
        "common_exits":"Initial stop = entry open - 2 x ATR(14) measured at signal close; daily low stop check with adverse gap fill at open; exit next open after 2 consecutive completed closes with Walking false; hard exit at close of holding session 10",
        "costs":"Excluded: all reported returns and metrics are gross price returns.",
        "window_handling":"Indicators warmed on prior history; only signals from start date counted; trades still open or pending at end excluded",
        "limitations":"Short window and small number of instruments/trades; not proof of robust future performance."},"variants":{},"trades":[]}
    all_rows=[]
    for v in VARIANTS:
        rows,open_items=run_variant(frames,v,start)
        for row in rows:
        result["variants"][v]={**metrics(rows),"open_or_pending_tickers":open_items}
        all_rows.extend(rows)
        result["trades"].extend(rows)
    OUT_JSON.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    fields=["variant","ticker","signal_date","entry_date","entry_price","exit_date","exit_price","holding_sessions","exit_reason","gross_return_pct"]
    with OUT_CSV.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for x in result["trades"]:
            w.writerow(x)
    print(json.dumps({k:{"trades":v["trades"],"wins":v["wins"],"win_rate_pct":v["win_rate_pct"],"gross_mean_pct":v["gross_mean_pct"],"gross_profit_factor":v["gross_profit_factor"]} for k,v in result["variants"].items()},ensure_ascii=False))
    print("TICKERS_WITH_DATA",len(frames),"OF",len(tickers),"FAILED",len(failed))

if __name__=="__main__": main()
