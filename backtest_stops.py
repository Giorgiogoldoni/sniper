#!/usr/bin/env python3
"""Second-stage Sniper backtest: next-open execution, ATR/Chandelier stops and cost sensitivity.
Signals are evaluated at close t; entry is next session open. Long-only on the ETP price,
including inverse ETPs. OOS is the final 30% of each instrument's history.
"""
import json, time, warnings
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import yfinance as yf
from corporate_action_filter import apply_history_cutoff, load_cutoffs

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent
UNIVERSE = ROOT / "data" / "instrument_universe.json"
OUT = ROOT / "data" / "backtest_stops_results.json"
AUDIT = ROOT / "data" / "backtest_exclusion_audit.json"
PERIOD, MIN_BARS, BATCH = "10y", 260, 20
HORIZONS = (3, 5, 10)
COST_BPS = (10, 20, 30)  # round-trip sensitivity, not broker-specific

def rsi(s, n):
    d=s.diff()
    up=d.clip(lower=0).ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    dn=(-d.clip(upper=0)).ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    return 100-100/(1+up/dn.replace(0,np.nan))

def make_signals(df):
    c,h,l,v=df.Close,df.High,df.Low,df.Volume
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    e20=c.ewm(span=20,adjust=False).mean()
    e50=c.ewm(span=50,adjust=False).mean()
    e8=c.ewm(span=8,adjust=False).mean()
    e21=c.ewm(span=21,adjust=False).mean()
    macd=e8-e21
    ms=macd.ewm(span=5,adjust=False).mean()
    change=c.diff(10).abs()
    vol=c.diff().abs().rolling(10).sum()
    er=(change/vol.replace(0,np.nan)).fillna(0)
    sc=(er*(2/3-2/31)+2/31)**2
    kama=pd.Series(np.nan,index=c.index,dtype=float)
    if len(c)>10:
        kama.iloc[10]=c.iloc[10]
        for j in range(11,len(c)):
            prev=kama.iloc[j-1]
            kama.iloc[j]=prev+sc.iloc[j]*(c.iloc[j]-prev) if pd.notna(prev) else c.iloc[j]
    ks=kama.pct_change(5)
    r14=rsi(c,14)
    prev_high=h.shift(1).rolling(20).max()
    bb_mid=c.rolling(20).mean()
    bb_upper=bb_mid+2*c.rolling(20).std()
    near_upper=(c>=bb_upper*0.985)&(c>=bb_mid)&(bb_upper>bb_upper.shift(1))
    walking_upper_band=near_upper.rolling(3,min_periods=3).sum()>=2
    bb=c.rolling(20).mean()+2*c.rolling(20).std()
    up=h.diff(); down=-l.diff()
    pdm=up.where((up>down)&(up>0),0.0)
    mdm=down.where((down>up)&(down>0),0.0)
    pdi=100*pdm.ewm(alpha=1/14,adjust=False,min_periods=14).mean()/atr
    ndi=100*mdm.ewm(alpha=1/14,adjust=False,min_periods=14).mean()/atr
    dx=100*(pdi-ndi).abs()/(pdi+ndi).replace(0,np.nan)
    adx=dx.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    vp=(h-l.shift(1)).abs().rolling(14).sum()
    vm=(l-h.shift(1)).abs().rolling(14).sum()
    ts=tr.rolling(14).sum()
    signals={
      "Bollinger breakout": c>bb,
      "Donchian 20": c>prev_high,
      "Walking upper Bollinger Band": walking_upper_band,
      "Donchian + Walking same-day": (c>prev_high)&walking_upper_band,
      "Donchian breakout then Walking confirm (3d)": walking_upper_band & (c>prev_high).rolling(3,min_periods=1).max().astype(bool),
      "KAMA": (c>kama)&(ks>0),
      "RSI 14": r14>52,
      "Vortex 14": vp>vm,
      "ADX trend": (adx>20)&(pdi>ndi),
      "MACD 8/21/5": macd>ms,
      "ROC 5/10": (c.pct_change(5)>0)&(c.pct_change(10)>0),
    }
    return signals, atr

def extract_frame(raw, ticker):
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
        x=x[(x.Close>0)&(x.Open>0)&(x.High>0)&(x.Low>0)]
        return x
    except Exception:
        return None

def audit_raw_exclusions(tickers):
    out={}
    for start in range(0,len(tickers),BATCH):
        batch=tickers[start:start+BATCH]
        try:
            raw=yf.download(batch,period=PERIOD,interval="1d",auto_adjust=False,repair=True,
                actions=True,group_by="ticker",threads=False,progress=False,timeout=30)
            for t in batch:
                try:
                    x=raw[t].copy() if isinstance(raw.columns,pd.MultiIndex) else raw.copy()
                    if isinstance(x.columns,pd.MultiIndex): x.columns=x.columns.get_level_values(0)
                    if "Close" not in x: continue
                    close=x.Close.dropna()
                    moves=close.pct_change().abs().dropna()
                    if moves.empty: continue
                    ix=moves.nlargest(3).index
                    events=[]
                    for dt in ix:
                        pos=close.index.get_loc(dt)
                        split=None
                        if "Stock Splits" in x.columns and dt in x.index:
                            z=x.loc[dt,"Stock Splits"]
                            split=float(z) if pd.notna(z) and float(z)!=0 else None
                        events.append({"date":str(pd.Timestamp(dt).date()),
                            "absolute_change_pct":round(float(moves.loc[dt])*100,2),
                            "close_before":round(float(close.iloc[pos-1]),6) if pos>0 else None,
                            "close_after":round(float(close.loc[dt]),6),"stock_split":split})
                    out[t]={"max_absolute_move_pct":round(float(moves.max())*100,2),
                        "largest_events":events,
                        "has_split_action":any(e["stock_split"] for e in events)}
                except Exception as e:
                    out[t]={"audit_error":str(e)[:180]}
        except Exception as e:
            for t in batch: out[t]={"audit_error":str(e)[:180]}
        time.sleep(0.5)
    return out

def run_trades(signal, df, atr, horizon, test_start, stop_mode, cost_bps, exit_signal=None):
    # Each trade: close signal at i, enter open i+1. No overlapping positions.
    rows=[]
    last_exit=-1
    for i in range(max(1,test_start),len(df)-horizon-1):
        if i<=last_exit or not bool(signal.iloc[i]) or not np.isfinite(atr.iloc[i]) or atr.iloc[i]<=0:
            continue
        entry_i=i+1
        entry=float(df.Open.iloc[entry_i])
        if not np.isfinite(entry) or entry<=0: continue
        initial_atr=float(atr.iloc[i])
        stop=(entry-2*initial_atr) if stop_mode=="ATR_2" else ((entry-3*initial_atr) if stop_mode=="CHAND_22_3" else None)
        highest=entry
        exit_i=min(entry_i+horizon-1,len(df)-1)
        exit_price=float(df.Close.iloc[exit_i])
        exit_reason="TIME"
        for j in range(entry_i,exit_i+1):
            # Test today's stop before updating trailing high: avoids intraday look-ahead.
            if stop is not None and float(df.Low.iloc[j])<=stop:
                op=float(df.Open.iloc[j])
                exit_price=op if op<stop else stop  # adverse gap fill
                exit_i=j; exit_reason="STOP"; break
            if exit_signal is not None and bool(exit_signal.iloc[j]) and j<exit_i:
                # Close-based invalidation at session j is executed at next session open.
                exit_i=j+1
                exit_price=float(df.Open.iloc[exit_i])
                exit_reason="WALKING_EXIT"
                break
            if stop_mode=="CHAND_22_3" and j<exit_i:
                prior_atr=float(atr.iloc[j]) if np.isfinite(atr.iloc[j]) else initial_atr
                rolling_high=float(df.High.iloc[max(0,j-21):j+1].max())
                stop=max(stop,rolling_high-3*prior_atr)
        gross=(exit_price/entry-1)*100
        net=gross-cost_bps/100
        rows.append({"return_pct":net,"gross_return_pct":gross,"exit_reason":exit_reason,
                     "entry_date":str(df.index[entry_i].date()),"exit_date":str(df.index[exit_i].date())})
        last_exit=exit_i
    if not rows: return None
    vals=np.array([r["return_pct"] for r in rows],dtype=float)
    eq=np.cumprod(1+vals/100)
    peak=np.maximum.accumulate(np.r_[1.0,eq])[1:]
    dd=(eq/peak-1)*100
    gains=vals[vals>0].sum(); losses=-vals[vals<0].sum()
    return {"trades":len(rows),"avg_net_return_pct":round(float(vals.mean()),3),
        "median_net_return_pct":round(float(np.median(vals)),3),
        "win_rate_pct":round(float((vals>0).mean()*100),2),
        "profit_factor":round(float(gains/losses),3) if losses>0 else (99.0 if gains>0 else None),
        "max_trade_equity_drawdown_pct":round(float(dd.min()),2),
        "stop_exit_pct":round(float(sum(r["exit_reason"]=="STOP" for r in rows)/len(rows)*100),2),
        "avg_gross_return_pct":round(float(np.mean([r["gross_return_pct"] for r in rows])),3)}

def main():
    instruments=json.loads(UNIVERSE.read_text(encoding="utf-8"))["instruments"]
    items={}
    for x in instruments:
        t=x.get("yahoo") or x.get("ticker")
        if t and x.get("classification"): items[t]=x
    tickers=list(items)
    frames={}; quality_flagged={}; too_short=[]
    corporate_action_audit={}
    corporate_action_cutoffs=load_cutoffs()
    for start in range(0,len(tickers),BATCH):
        batch=tickers[start:start+BATCH]
        try:
            raw=yf.download(batch,period=PERIOD,interval="1d",auto_adjust=True,repair=True,
                group_by="ticker",threads=False,progress=False,timeout=30)
            for t in batch:
                x=extract_frame(raw,t)
                if x is not None:
                    x, cutoff_meta=apply_history_cutoff(x,t,corporate_action_cutoffs)
                    if cutoff_meta.get("cutoff_applied"):
                        corporate_action_audit[t]=cutoff_meta
                if x is None or len(x)<MIN_BARS:
                    too_short.append(t); continue
                moves=x.Close.pct_change().abs().dropna()
                mx=float(moves.max()) if len(moves) else 0
                if mx>0.60:
                    quality_flagged[t]={"adjusted_max_move_pct":round(mx*100,2)}
                # Non si esclude un ETP per volatilita: si segnala l'evento e si conserva.
                frames[t]=x
        except Exception as e:
            print(f"Download batch {start} warning: {e}")
        time.sleep(0.8)
        print(f"Download {min(start+BATCH,len(tickers))}/{len(tickers)}; usable={len(frames)}; flagged={len(quality_flagged)}")
    audit=audit_raw_exclusions(tickers)
    for t,v in quality_flagged.items(): v.update(audit.get(t,{}))
    AUDIT.write_text(json.dumps({"generated_at":datetime.now(timezone.utc).isoformat(),
        "excluded_count":0,"excluded_instruments":{},
        "quality_flagged_count":len(quality_flagged),"quality_flagged_instruments":quality_flagged,
        "audit_scope":"Tutti gli strumenti dell universo; prezzi Yahoo con repair=True. Gli eventi estremi sono segnalati, non usati per escludere gli ETP.",
        "review_note":"repair=True tenta di correggere alcune anomalie Yahoo, ma non certifica la serie. Verificare gli eventi estremi prima di interpretare i rendimenti."},
        ensure_ascii=False,indent=2),encoding="utf-8")
    detail=[]; coverage={}
    for ticker,df in frames.items():
        try:
            signals,atr=make_signals(df)
            start=int(len(df)*0.70)
            cat=items[ticker].get("classification","UNKNOWN")
            coverage[cat]=coverage.get(cat,0)+1
            # All strategies tested with no stop, fixed ATR stop, and trailing Chandelier.
            for name,sig in signals.items():
                for horizon in HORIZONS:
                    for stop_mode in ("NONE","ATR_2","CHAND_22_3"):
                        for cost in COST_BPS:
                            m=run_trades(sig,df,atr,horizon,start,stop_mode,cost)
                            if m:
                                detail.append({"ticker":ticker,"category":cat,"strategy":name,
                                    "horizon_days":horizon,"stop_mode":stop_mode,"round_trip_cost_bps":cost,**m})
            # Donchian entry with three explicit close-based exit rules.
            donchian_entry=signals["Donchian 20"]
            walking=signals["Walking upper Bollinger Band"].fillna(False)
            bb_mid=df.Close.rolling(20).mean()
            exit_rules={
                "Donchian 20 + Walking exit first negative": ~walking,
                "Donchian 20 + Walking exit 2 negative closes": (~walking).rolling(2,min_periods=2).sum().eq(2),
                "Donchian 20 + Bollinger midline loss exit":
                    (df.Close<bb_mid)&(df.Close.shift(1)>=bb_mid.shift(1)),
            }
            for strategy_name, exit_signal in exit_rules.items():
                for horizon in HORIZONS:
                    for stop_mode in ("NONE","ATR_2","CHAND_22_3"):
                        for cost in COST_BPS:
                            m=run_trades(donchian_entry,df,atr,horizon,start,stop_mode,cost,exit_signal=exit_signal)
                            if m:
                                detail.append({"ticker":ticker,"category":cat,
                                    "strategy":strategy_name,
                                    "horizon_days":horizon,"stop_mode":stop_mode,
                                    "round_trip_cost_bps":cost,**m})
            # Comparable passive entry-next-open/time-exit baseline
            baseline=pd.Series(True,index=df.index)
            for horizon in HORIZONS:
                for cost in COST_BPS:
                    m=run_trades(baseline,df,atr,horizon,start,"NONE",cost)
                    if m:
                        detail.append({"ticker":ticker,"category":cat,"strategy":"BASELINE",
                            "horizon_days":horizon,"stop_mode":"NONE","round_trip_cost_bps":cost,**m})
        except Exception as e:
            print(f"Instrument warning {ticker}: {e}")
    summary=[]
    if detail:
        d=pd.DataFrame(detail)
        for keys,g in d.groupby(["category","strategy","horizon_days","stop_mode","round_trip_cost_bps"]):
            summary.append({"category":keys[0],"strategy":keys[1],"horizon_days":int(keys[2]),
                "stop_mode":keys[3],"round_trip_cost_bps":int(keys[4]),
                "instruments":int(g.ticker.nunique()),"trades":int(g.trades.sum()),
                "mean_instrument_net_return_pct":round(float(g.avg_net_return_pct.mean()),3),
                "median_instrument_net_return_pct":round(float(g.avg_net_return_pct.median()),3),
                "median_instrument_win_rate_pct":round(float(g.win_rate_pct.median()),2),
                "median_instrument_profit_factor":round(float(g.profit_factor.dropna().median()),3) if g.profit_factor.notna().any() else None,
                "median_instrument_max_drawdown_pct":round(float(g.max_trade_equity_drawdown_pct.median()),2),
                "median_stop_exit_pct":round(float(g.stop_exit_pct.median()),2)})
        summary.sort(key=lambda x:(x["category"],x["horizon_days"],x["round_trip_cost_bps"],x["stop_mode"],-x["median_instrument_net_return_pct"]))
        d.to_csv(ROOT/"data"/"backtest_stops_detail.csv",index=False)
    result={"generated_at":datetime.now(timezone.utc).isoformat(),"period_requested":PERIOD,
        "universe_total":len(tickers),"usable_instruments":len(frames),"quality_excluded":0,"quality_flagged":len(quality_flagged),
        "corporate_action_cutoff_count":len(corporate_action_audit),
        "corporate_action_cutoffs":corporate_action_audit,
        "insufficient_or_missing_history":len(too_short),"coverage_by_category":coverage,
        "execution":"signal close t; entry next session open; stop checked using daily low, gap fills at open if worse; Walking invalidation at close exits next session open; time exit at close of final holding session",
        "walking_exit_rules":{
            "first_negative_close":"exit at next open when Walking upper Bollinger Band condition is false at a completed close",
            "two_negative_closes":"exit at next open after two consecutive completed closes with Walking upper Bollinger Band condition false",
            "bollinger_midline_loss":"exit at next open on a close crossing below the 20-session Bollinger middle SMA"
        },
        "stops":{"ATR_2":"initial stop at entry minus 2x ATR(14) measured at signal close",
                 "CHAND_22_3":"initial 3x ATR stop, then rolling 22-session highest high minus 3x ATR; updated only after each completed session"},
        "cost_sensitivity_round_trip_bps":list(COST_BPS),
        "oos":"final 30% of each instrument history; no parameter optimization on OOS",
        "metrics":"returns net of assumed round-trip cost; equal-weighted instrument summaries; drawdown computed on sequential compounded trades per instrument",
        "limitations":["daily OHLC cannot resolve intraday ordering beyond conservative stop-first logic",
          "Yahoo adjusted OHLC and corporate-action history can be incomplete for ETPs; repair=True is best-effort and does not guarantee full recovery",
          "12 ETP con corporate action note sono testati solo dal cutoff post-evento; nessun prezzo viene rettificato e nessun ticker viene eliminato dall universo",
          "cost assumptions are sensitivities, not observed spreads/commissions",
          "no taxes, financing or internal ETP fees beyond embedded price history",
          "not a portfolio-level simulation; equal weighting by instrument"],
        "summary":summary}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"usable":len(frames),"flagged":len(quality_flagged),"coverage":coverage,
        "detail_rows":len(detail),"summary_rows":len(summary)},ensure_ascii=False))
    if len(frames)<10: raise SystemExit("Insufficient usable instruments; refusing to publish a valid test.")

if __name__=="__main__": main()
