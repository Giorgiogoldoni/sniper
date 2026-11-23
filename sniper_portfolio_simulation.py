#!/usr/bin/env python3
"""Sniper B portfolio simulation: Donchian20 + Walking, daily mark-to-market."""
import argparse,json,time,warnings
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf
ROOT=Path(__file__).resolve().parent
UNIVERSE=ROOT/"data"/"instrument_universe.json"
warnings.filterwarnings("ignore")
SLOTS=(5,8,12)
CAPITAL=100000.0
def get_frame(raw,t):
    try:
        x=raw[t].copy() if isinstance(raw.columns,pd.MultiIndex) and t in raw.columns.get_level_values(0) else raw.copy()
        if isinstance(x.columns,pd.MultiIndex): x.columns=x.columns.get_level_values(0)
        x=x[["Open","High","Low","Close"]].dropna()
        x=x[~x.index.duplicated(keep="last")]
        return x[(x>0).all(axis=1)]
    except Exception:return None
def indicators(df):
    h,l,c=df.High,df.Low,df.Close
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    mid=c.rolling(20).mean(); sd=c.rolling(20).std(); upper=mid+2*sd
    near=(c>=upper*.985)&(c>=mid)&(upper>upper.shift(1))
    walk=(near.rolling(3,min_periods=3).sum()>=2).fillna(False)
    prior=h.shift(1).rolling(20).max()
    sig=((c>prior)&walk&(atr>0)).fillna(False)
    strength=(c/prior-1).replace([np.inf,-np.inf],np.nan)
    return atr,walk,sig,strength
def simulate(frames,n,start):
    ind={t:indicators(df) for t,df in frames.items()}
    dates=sorted(set(d for df in frames.values() for d in df.index if str(pd.Timestamp(d).date())>=start))
    if not dates:raise RuntimeError("Nessuna data disponibile")
    slot=CAPITAL/n; cash=CAPITAL; pos={}; queued={}; pending_exit=set()
    trades=[]; curve=[]; rejected=0; max_open=0; last_close={}
    date_set={str(pd.Timestamp(x).date()) for x in dates}
    for dt in dates:
        day=str(pd.Timestamp(dt).date())
        for t in list(pending_exit):
            if t in pos and dt in frames[t].index:
                p=pos.pop(t); px=float(frames[t].loc[dt].Open); cash+=p["qty"]*px
                trades.append({"ticker":t,"entry_date":p["entry_date"],"exit_date":day,"entry_price":p["entry"],"exit_price":px,"return_pct":(px/p["entry"]-1)*100,"reason":"WALKING_2_FALSE"})
                pending_exit.discard(t)
            elif t not in pos:
                pending_exit.discard(t)
        candidates=queued.pop(day,[])
        candidates.sort(key=lambda x:(-x["strength"],x["ticker"]))
        for c in candidates:
            t=c["ticker"]
            if t in pos:continue
            if len(pos)>=n or cash<slot:rejected+=1;continue
            if dt not in frames[t].index:continue
            op=float(frames[t].loc[dt].Open);pos[t]={"entry_date":day,"entry":op,"qty":slot/op,"stop":op-2*c["atr"],"held":0,"false":0}
            cash-=slot
        for t in list(pos):
            if dt not in frames[t].index:continue
            row=frames[t].loc[dt];p=pos[t];p["held"]+=1
            if float(row.Low)<=p["stop"]:
                px=float(row.Open) if float(row.Open)<p["stop"] else p["stop"]
                cash+=p["qty"]*px;trades.append({"ticker":t,"entry_date":p["entry_date"],"exit_date":day,"entry_price":p["entry"],"exit_price":px,"return_pct":(px/p["entry"]-1)*100,"reason":"ATR_2_STOP"})
                del pos[t];pending_exit.discard(t);continue
            walk=bool(ind[t][1].loc[dt]);p["false"]=0 if walk else p["false"]+1
            if p["held"]>=10:
                px=float(row.Close);cash+=p["qty"]*px
                trades.append({"ticker":t,"entry_date":p["entry_date"],"exit_date":day,"entry_price":p["entry"],"exit_price":px,"return_pct":(px/p["entry"]-1)*100,"reason":"TIME_MAX_10"})
                del pos[t];pending_exit.discard(t)
            elif p["false"]>=2:pending_exit.add(t)
        # Carry forward last observable close when an instrument has no bar
        # on a union-calendar date; never mark an open position at zero value.
        for t,df in frames.items():
            if dt in df.index:
                last_close[t]=float(df.loc[dt].Close)
        mv=sum(p["qty"]*last_close.get(t,p["entry"]) for t,p in pos.items())
        curve.append({"date":day,"cash":cash,"market_value":mv,"equity":cash+mv,"open_positions":len(pos)})
        max_open=max(max_open,len(pos))
        for t,df in frames.items():
            if dt not in df.index or t in pos:continue
            atr,walk,sig,strength=ind[t]
            if bool(sig.loc[dt]):
                ix=df.index.get_loc(dt)
                if ix+1<len(df.index):
                    nd=str(pd.Timestamp(df.index[ix+1]).date())
                    if nd in date_set:queued.setdefault(nd,[]).append({"ticker":t,"atr":float(atr.loc[dt]),"strength":float(strength.loc[dt])})
    e=pd.DataFrame(curve);e["peak"]=e.equity.cummax();e["dd"]=(e.equity/e.peak-1)*100
    final=float(e.equity.iloc[-1]);yrs=max((pd.Timestamp(e.date.iloc[-1])-pd.Timestamp(e.date.iloc[0])).days/365.25,1/365.25)
    r=np.array([x["return_pct"] for x in trades]);gp=r[r>0].sum() if len(r) else 0;gl=-r[r<0].sum() if len(r) else 0
    annual={};e["year"]=pd.to_datetime(e.date).dt.year
    for y,g in e.groupby("year"):
        prior=e[e.year==y-1]
        base=float(prior.equity.iloc[-1]) if len(prior) else CAPITAL
        annual[str(y)]={"return_pct":round((float(g.equity.iloc[-1])/base-1)*100,2),"end_equity":round(float(g.equity.iloc[-1]),2)}
    summary={"slots":n,"initial_capital":CAPITAL,"fixed_slot_amount":round(slot,2),"start":e.date.iloc[0],"end":e.date.iloc[-1],
      "final_equity":round(final,2),"total_return_pct":round((final/CAPITAL-1)*100,2),
      "cagr_pct":round(((final/CAPITAL)**(1/yrs)-1)*100,2) if final>0 else None,
      "max_drawdown_pct":round(float(e.dd.min()),2),"closed_trades":len(trades),
      "trade_win_rate_pct":round(float((r>0).mean()*100),2) if len(r) else None,
      "trade_mean_pct":round(float(r.mean()),2) if len(r) else None,
      "trade_profit_factor":round(float(gp/gl),2) if gl else None,
      "max_concurrent_positions":max_open,"rejected_entries":rejected,
      "open_at_end":[{"ticker":t,"entry_date":p["entry_date"]} for t,p in pos.items()],"annual":annual}
    return summary,e,trades
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--from-date",default="2023-01-01");a=ap.parse_args()
    start=str(pd.Timestamp(a.from_date).date())
    universe=json.loads(UNIVERSE.read_text())["instruments"]
    tickers=[x.get("yahoo") or x.get("ticker") for x in universe if x.get("classification")=="MATERIE_PRIME_LEVA" and (x.get("yahoo") or x.get("ticker"))]
    frames={};failed=[]
    for j in range(0,len(tickers),15):
        batch=tickers[j:j+15]
        try:raw=yf.download(batch,period="10y",interval="1d",auto_adjust=False,repair=True,group_by="ticker",threads=False,progress=False,timeout=35)
        except Exception as ex:
            failed.extend({"ticker":t,"error":str(ex)[:120]} for t in batch);continue
        for t in batch:
            df=get_frame(raw,t)
            if df is None or len(df)<60:failed.append({"ticker":t,"error":"missing/short history"})
            else:frames[t]=df
        time.sleep(.4)
    if not frames:raise RuntimeError("Nessun dato scaricato")
    results={}
    for n in SLOTS:
        s,e,tr=simulate(frames,n,start);results[str(n)]=s
        e.to_csv(ROOT/"data"/f"sniper_portfolio_{n}_equity.csv",index=False)
        pd.DataFrame(tr).to_csv(ROOT/"data"/f"sniper_portfolio_{n}_trades.csv",index=False)
    out={"strategy":"Donchian20 + Walking; ATR14 x2; Walking exit after 2 false closes at next open; max 10 sessions",
      "assumptions":{"capital_eur":CAPITAL,"sizing":"fixed initial capital / slots, equal notional, no leverage, no compounding slot size",
      "entry_priority":"breakout distance above previous 20-session high descending; ticker alphabetical tie-break",
      "mark_to_market":"daily close; last close carried forward on missing instrument sessions; stops checked on daily low with adverse gap fill at open","costs":"excluded",
      "calendar_handling":"union of instrument sessions; missing ticker bars carry forward last close for valuation and defer scheduled next-open exits until that ticker next trades",
      "open_positions":"valued at final close","fractional_units":True,"production_changes":False,
      "data_source":"Yahoo Finance daily OHLC","universe_count":len(tickers),"tickers_with_data":len(frames),"failed_data":failed},
      "results":results}
    (ROOT/"data"/"sniper_portfolio_comparison.json").write_text(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps(results,indent=2,ensure_ascii=False));print("DATA",len(frames),"/",len(tickers),"FAILED",len(failed))
if __name__=="__main__":main()
