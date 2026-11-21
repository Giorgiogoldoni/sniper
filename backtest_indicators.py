#!/usr/bin/env python3
"""Backtest storico Sniper: segnali tecnici su ETP/ETF leva, short e commodity.

Test esplorativo, long-only sul prezzo dello strumento (anche per ETP inversi).
Segnali calcolati a chiusura t; ingresso al close t; uscita dopo 3/5/10 sedute.
Per evitare trade sovrapposti, dopo un ingresso si attende l'orizzonte prima del
successivo ingresso nella stessa strategia/strumento. I risultati OOS usano il
30% finale della storia di ogni strumento; soglia determinata solo sul calendario.
"""
import json, time, warnings
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent
UNIVERSE = ROOT / "data" / "instrument_universe.json"
OUT = ROOT / "data" / "backtest_results.json"
PERIOD = "10y"
HORIZONS = (3, 5, 10)
MIN_BARS = 260
BATCH_SIZE = 20

def rsi(s, n):
    d=s.diff()
    up=d.clip(lower=0).ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    dn=(-d.clip(upper=0)).ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    return 100 - 100/(1+up/dn.replace(0,np.nan))

def indicators(df):
    c,h,l,v=df["Close"],df["High"],df["Low"],df["Volume"]
    roc5=c.pct_change(5)*100
    roc10=c.pct_change(10)*100
    r7,r14=rsi(c,7),rsi(c,14)
    e20=c.ewm(span=20,adjust=False).mean()
    e50=c.ewm(span=50,adjust=False).mean()
    e8=c.ewm(span=8,adjust=False).mean()
    e21=c.ewm(span=21,adjust=False).mean()
    macd=e8-e21
    macd_sig=macd.ewm(span=5,adjust=False).mean()
    # KAMA 10, fast 2, slow 30
    change=c.diff(10).abs()
    volatility=c.diff().abs().rolling(10).sum()
    er=(change/volatility.replace(0,np.nan)).fillna(0)
    sc=(er*(2/3-2/31)+2/31)**2
    kama=pd.Series(np.nan,index=c.index,dtype=float)
    if len(c)>10:
        kama.iloc[10]=c.iloc[10]
        for i in range(11,len(c)):
            prev=kama.iloc[i-1]
            kama.iloc[i]=prev+sc.iloc[i]*(c.iloc[i]-prev) if pd.notna(prev) else c.iloc[i]
    kama_slope=kama.pct_change(5)*100
    prev_high=h.shift(1).rolling(20).max()
    # Wilder-style ATR% for volatility reporting/filter
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    # Relative volume only as diagnostic; not used to select the winner
    relvol=v/v.rolling(20).mean()
    return {
      "ROC 5/10": (roc5>0)&(roc10>0),
      "RSI 7": r7>52,
      "RSI 14": r14>52,
      "EMA 20/50": e20>e50,
      "MACD 8/21/5": macd>macd_sig,
      "KAMA": (c>kama)&(kama_slope>0),
      "Donchian 20": c>prev_high,
      "Sniper consensus": ((roc5>0).astype(int)+(roc10>0).astype(int)+(r7>52).astype(int)+
          (e20>e50).astype(int)+(macd>macd_sig).astype(int)+
          ((c>kama)&(kama_slope>0)).astype(int)+(c>prev_high).astype(int))>=4,
      "ATR%": atr/c*100,
      "RSI7": r7,
      "RelVolume": relvol
    }

def score_events(signal, close, horizon, test_start):
    sig=signal.fillna(False).to_numpy(dtype=bool)
    prices=close.to_numpy(dtype=float)
    dates=close.index
    start_pos=int(test_start)
    entries=[]
    last_exit=-1
    for i in range(max(start_pos,1),len(prices)-horizon):
        if i<=last_exit or not sig[i]:
            continue
        # enter at close i, exit at close i+horizon
        ret=(prices[i+horizon]/prices[i]-1)*100
        if np.isfinite(ret):
            entries.append((dates[i],ret))
            last_exit=i+horizon
    if not entries:
        return {"trades":0,"win_rate_pct":None,"avg_return_pct":None,"median_return_pct":None,
                "profit_factor":None,"best_pct":None,"worst_pct":None}
    vals=np.array([x[1] for x in entries],dtype=float)
    gains=vals[vals>0].sum()
    losses=-vals[vals<0].sum()
    return {"trades":int(len(vals)),
        "win_rate_pct":round(float((vals>0).mean()*100),2),
        "avg_return_pct":round(float(vals.mean()),3),
        "median_return_pct":round(float(np.median(vals)),3),
        "profit_factor":round(float(gains/losses),3) if losses>0 else (None if gains==0 else 99.0),
        "best_pct":round(float(vals.max()),3),"worst_pct":round(float(vals.min()),3)}

def main():
    universe=json.loads(UNIVERSE.read_text(encoding="utf-8"))["instruments"]
    # Keep unique Yahoo symbols and valid categories only.
    items={}
    for x in universe:
        ticker=x.get("yahoo") or x.get("ticker")
        if ticker and x.get("classification"):
            items[ticker]=x
    tickers=list(items)
    print(f"Universe: {len(tickers)} unique Yahoo tickers")
    frames={}
    for start in range(0,len(tickers),BATCH_SIZE):
        batch=tickers[start:start+BATCH_SIZE]
        try:
            raw=yf.download(batch,period=PERIOD,interval="1d",auto_adjust=True,
                group_by="ticker",threads=True,progress=False,timeout=30)
            for ticker in batch:
                try:
                    df=raw[ticker].copy() if isinstance(raw.columns,pd.MultiIndex) else raw.copy()
                    if isinstance(df.columns,pd.MultiIndex):
                        df.columns=df.columns.get_level_values(0)
                    cols=["Open","High","Low","Close","Volume"]
                    if not set(cols).issubset(df.columns): continue
                    df=df[cols].dropna(subset=["Close"])
                    df=df[~df.index.duplicated(keep="last")]
                    if len(df)>=MIN_BARS:
                        frames[ticker]=df
                except Exception:
                    continue
        except Exception as e:
            print(f"Batch warning {start}: {e}")
        time.sleep(1.0)
        print(f"Downloaded {min(start+BATCH_SIZE,len(tickers))}/{len(tickers)}; usable {len(frames)}")
    rows=[]
    coverage={}
    for ticker,df in frames.items():
        meta=items[ticker]
        cat=meta.get("classification","UNKNOWN")
        try:
            sigs=indicators(df)
            n=len(df)
            test_start=int(n*0.70)
            coverage[cat]=coverage.get(cat,0)+1
            for strategy in [k for k in sigs if k not in ("ATR%","RSI7","RelVolume")]:
                for horizon in HORIZONS:
                    metrics=score_events(sigs[strategy],df["Close"],horizon,test_start)
                    if metrics["trades"]==0: continue
                    rows.append({"ticker":ticker,"name":meta.get("name",""),"category":cat,
                        "strategy":strategy,"horizon_days":horizon,
                        "test_start":str(df.index[test_start].date()),"test_end":str(df.index[-1].date()),
                        **metrics})
        except Exception as e:
            print(f"Indicator warning {ticker}: {e}")
    # Aggregate equally by instrument: no large category dominates due to trade count.
    summary=[]
    if rows:
        detail=pd.DataFrame(rows)
        for (cat,strategy,horizon),g in detail.groupby(["category","strategy","horizon_days"]):
            valid=g[g["avg_return_pct"].notna()]
            if valid.empty: continue
            summary.append({"category":cat,"strategy":strategy,"horizon_days":int(horizon),
                "instruments":int(valid["ticker"].nunique()),
                "trades":int(valid["trades"].sum()),
                "avg_instrument_return_pct":round(float(valid["avg_return_pct"].mean()),3),
                "median_instrument_return_pct":round(float(valid["median_return_pct"].median()),3),
                "avg_win_rate_pct":round(float(valid["win_rate_pct"].mean()),2),
                "avg_profit_factor":round(float(valid["profit_factor"].dropna().mean()),3) if valid["profit_factor"].notna().any() else None})
        summary.sort(key=lambda x:(x["category"],x["horizon_days"],-(x["avg_instrument_return_pct"] or -999)))
        detail.to_csv(ROOT/"data"/"backtest_detail.csv",index=False)
    result={"generated_at":datetime.now(timezone.utc).isoformat(),"period_requested":PERIOD,
        "minimum_history_bars":MIN_BARS,"universe_total":len(tickers),"usable_instruments":len(frames),
        "coverage_by_category":coverage,"horizons_days":list(HORIZONS),
        "method":"segnale a close t, rendimento close t -> close t+N; segnali non sovrapposti per strumento/strategia/orizzonte; 70% iniziale warm-up/train cronologico, test OOS sul 30% finale; strumenti pesati in modo uguale nelle medie categoria.",
        "limitations":["prezzi Yahoo auto-adjusted; disponibilita e qualita storica variabili","strumenti con meno di 260 sedute esclusi","non include spread, commissioni, slippage, imposte e costi interni dell'ETP","segnali valutati sul prezzo dello strumento, senza leva sintetica","risultati esplorativi, non garanzia di performance"],
        "category_strategy_results":summary}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"usable":len(frames),"coverage":coverage,"rows":len(rows),"summary_rows":len(summary)},ensure_ascii=False))
    if len(frames)<10:
        raise SystemExit("Too few instruments with sufficient historical data; refusing to publish an unreliable test.")
if __name__=="__main__":
    main()
