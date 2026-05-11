#!/usr/bin/env python3
"""
Calcolo indicatori tecnici da OHLCV daily.
Usato da sniper.py per i top 40 ticker.
"""
import math
try:
    import numpy as np
except ImportError:
    import os; os.system("pip install numpy --break-system-packages -q")
    import numpy as np

def calc_kama(closes, n=10, fast=2, slow=30):
    c = np.array(closes, dtype=float)
    fs, ss = 2/(fast+1), 2/(slow+1)
    kama = np.full(len(c), np.nan)
    if len(c) <= n: return kama.tolist()
    kama[n] = c[n]
    for i in range(n+1, len(c)):
        direction  = abs(c[i]-c[i-n])
        volatility = np.sum(np.abs(np.diff(c[i-n:i+1])))
        er  = direction/volatility if volatility else 0
        sc  = (er*(fs-ss)+ss)**2
        kama[i] = kama[i-1] + sc*(c[i]-kama[i-1])
    return [None if math.isnan(v) else round(float(v),4) for v in kama]

def calc_sar(highs, lows, af_step=0.02, af_max=0.2):
    h = np.array(highs); l = np.array(lows)
    sar = np.full(len(h), np.nan)
    bull = np.zeros(len(h), dtype=bool)
    if len(h) < 2: return sar.tolist(), bull.tolist()
    is_bull = True; af = af_step; ep = h[0]; sar[0] = l[0]; bull[0] = True
    for i in range(1, len(h)):
        prev = sar[i-1]
        if is_bull:
            sar[i] = prev + af*(ep-prev)
            sar[i] = min(sar[i], l[i-1], l[i-2] if i>1 else l[i-1])
            if l[i] < sar[i]:
                is_bull=False; af=af_step; ep=l[i]; sar[i]=ep
            else:
                if h[i]>ep: ep=h[i]; af=min(af+af_step,af_max)
        else:
            sar[i] = prev + af*(ep-prev)
            sar[i] = max(sar[i], h[i-1], h[i-2] if i>1 else h[i-1])
            if h[i] > sar[i]:
                is_bull=True; af=af_step; ep=h[i]; sar[i]=ep
            else:
                if l[i]<ep: ep=l[i]; af=min(af+af_step,af_max)
        bull[i] = is_bull
    return ([None if math.isnan(v) else round(float(v),4) for v in sar],
            [bool(v) for v in bull])

def calc_ao(highs, lows):
    mp = [(h+l)/2 for h,l in zip(highs,lows)]
    mp = np.array(mp)
    ao = np.full(len(mp), np.nan)
    for i in range(33, len(mp)):
        ao[i] = np.mean(mp[i-4:i+1]) - np.mean(mp[i-33:i+1])
    return [None if math.isnan(v) else round(float(v),4) for v in ao]

def calc_rsi(closes, period=14):
    c = np.array(closes, dtype=float)
    rsi = np.full(len(c), np.nan)
    if len(c) < period+1: return rsi.tolist()
    deltas = np.diff(c)
    gains = np.where(deltas>0, deltas, 0)
    losses = np.where(deltas<0, -deltas, 0)
    avg_g = np.mean(gains[:period])
    avg_l = np.mean(losses[:period])
    for i in range(period, len(c)-1):
        avg_g = (avg_g*(period-1)+gains[i])/period
        avg_l = (avg_l*(period-1)+losses[i])/period
        rs = avg_g/avg_l if avg_l else float('inf')
        rsi[i+1] = 100 - 100/(1+rs)
    return [None if math.isnan(v) else round(float(v),2) for v in rsi]

def calc_adx(highs, lows, closes, period=14):
    h=np.array(highs); l=np.array(lows); c=np.array(closes)
    n=len(c)
    adx=np.full(n,np.nan); pdi=np.full(n,np.nan); ndi=np.full(n,np.nan)
    if n<period+2: return adx.tolist(), pdi.tolist(), ndi.tolist()
    tr=np.zeros(n); pdm=np.zeros(n); ndm=np.zeros(n)
    for i in range(1,n):
        hl=h[i]-l[i]; hpc=abs(h[i]-c[i-1]); lpc=abs(l[i]-c[i-1])
        tr[i]=max(hl,hpc,lpc)
        up=h[i]-h[i-1]; dn=l[i-1]-l[i]
        pdm[i]=up if up>dn and up>0 else 0
        ndm[i]=dn if dn>up and dn>0 else 0
    atr=np.zeros(n); apd=np.zeros(n); and_=np.zeros(n)
    atr[period]=np.sum(tr[1:period+1])
    apd[period]=np.sum(pdm[1:period+1])
    and_[period]=np.sum(ndm[1:period+1])
    for i in range(period+1,n):
        atr[i]=atr[i-1]-atr[i-1]/period+tr[i]
        apd[i]=apd[i-1]-apd[i-1]/period+pdm[i]
        and_[i]=and_[i-1]-and_[i-1]/period+ndm[i]
    dx=np.zeros(n)
    for i in range(period,n):
        if atr[i]==0: continue
        p=apd[i]/atr[i]*100; nd=and_[i]/atr[i]*100
        pdi[i]=round(p,1); ndi[i]=round(nd,1)
        denom=p+nd
        if denom: dx[i]=abs(p-nd)/denom*100
    adx_val=np.nanmean(dx[period:2*period])
    adx[2*period]=adx_val
    for i in range(2*period+1,n):
        adx[i]=(adx[i-1]*(period-1)+dx[i])/period
    return ([None if math.isnan(v) else round(float(v),1) for v in adx],
            [None if math.isnan(v) else round(float(v),1) for v in pdi],
            [None if math.isnan(v) else round(float(v),1) for v in ndi])

def calc_er(closes, period=10):
    c=np.array(closes,dtype=float)
    er=np.full(len(c),np.nan)
    for i in range(period,len(c)):
        direction=abs(c[i]-c[i-period])
        volatility=np.sum(np.abs(np.diff(c[i-period:i+1])))
        er[i]=round(direction/volatility*100,1) if volatility else 0
    return [None if math.isnan(v) else float(v) for v in er]

def calc_baff(highs, lows):
    """Conta barre consecutive AO stesso colore (verde/rosso)."""
    ao=calc_ao(highs,lows)
    baff=[]
    count=0
    for i,v in enumerate(ao):
        if v is None or i==0 or ao[i-1] is None:
            baff.append(0); continue
        if v>0 and ao[i-1]>0: count=count+1 if count>0 else 1
        elif v<0 and ao[i-1]<0: count=count-1 if count<0 else -1
        else: count=1 if v>0 else -1
        baff.append(abs(count))
    return baff

def calc_hurst(closes, lag=60):
    """Esponente di Hurst approssimato."""
    c=np.array(closes,dtype=float)
    if len(c)<lag+10: return None
    series=c[-lag:]
    lags=range(2,20)
    tau=[np.std(series[l:]-series[:-l]) for l in lags]
    if any(t==0 for t in tau): return None
    try:
        poly=np.polyfit(np.log(list(lags)),np.log(tau),1)
        return round(float(poly[0]),3)
    except Exception:
        return None

def calc_kama_trend(closes, kama_vals):
    """VERDE/GRIGIO/ROSSO basato su slope KAMA."""
    valid=[(c,k) for c,k in zip(closes,kama_vals) if k is not None]
    if len(valid)<5: return "GRIGIO"
    last_k=[v[1] for v in valid[-5:]]
    slope=(last_k[-1]-last_k[0])/abs(last_k[0]) if last_k[0] else 0
    if slope>0.005: return "VERDE"
    if slope<-0.005: return "ROSSO"
    return "GRIGIO"

def calc_signals_history(closes, dates, kama_vals, sar_bull):
    """Genera storia segnali BUY/SELL/WATCH."""
    history=[]
    prev_sig=None
    for i in range(len(closes)):
        if kama_vals[i] is None: continue
        c=closes[i]; k=kama_vals[i]
        bull=sar_bull[i] if i<len(sar_bull) else False
        if c>k and bull: sig="BUY"
        elif c<k and not bull: sig="SELL"
        else: sig="WATCH"
        if sig!=prev_sig:
            history.append({"date":dates[i],"signal":sig,"price":round(float(c),4)})
            prev_sig=sig
    return list(reversed(history))[:10]

def compute_all(dates, closes, highs, lows, volumes=None):
    """Calcola tutti gli indicatori e ritorna un dict completo."""
    n=len(closes)
    kama=calc_kama(closes)
    sar,sar_bull=calc_sar(highs,lows)
    ao=calc_ao(highs,lows)
    rsi=calc_rsi(closes)
    adx,pdi,ndi=calc_adx(highs,lows,closes)
    er=calc_er(closes)
    baff_arr=calc_baff(highs,lows)
    hurst60=calc_hurst(closes,60)
    hurst1y=calc_hurst(closes,252) if n>=262 else None
    kama_trend=calc_kama_trend(closes,kama)

    # Ultimi valori
    def last(arr):
        for v in reversed(arr):
            if v is not None: return v
        return None

    p=float(closes[-1])
    k_val=last(kama)
    k_pct=round((p-k_val)/k_val*100,2) if k_val else None

    # Momentum
    mom1m=round((closes[-1]/closes[-21]-1)*100,2) if n>21 else None
    mom3m=round((closes[-1]/closes[-63]-1)*100,2) if n>63 else None
    mom6m=round((closes[-1]/closes[-126]-1)*100,2) if n>126 else None

    # Var% oggi
    chg_pct=round((closes[-1]/closes[-2]-1)*100,2) if n>1 else None

    # Storia segnali
    sig_history=calc_signals_history(closes,dates,kama,sar_bull)

    # Determina segnale corrente
    current_sig="WATCH"
    if k_val and p>k_val and sar_bull[-1]: current_sig="BUY"
    elif k_val and p<k_val and not sar_bull[-1]: current_sig="SELL"

    # Segnale dal (primo giorno del segnale corrente)
    sig_dal=""
    if sig_history: sig_dal=sig_history[0]["date"]

    # Rating TV approssimato da indicatori
    bullish_count=sum([
        1 if (last(rsi) or 50)>50 else 0,
        1 if k_val and p>k_val else 0,
        1 if sar_bull[-1] else 0,
        1 if (last(ao) or 0)>0 else 0,
        1 if (last(adx) or 0)>20 else 0,
    ])
    tv_rating=["STRONG_SELL","SELL","NEUTRAL","BUY","STRONG_BUY","STRONG_BUY"][bullish_count]

    return {
        "price":       round(float(closes[-1]),4),
        "chg_pct":     chg_pct,
        "kama":        k_val,
        "k_pct":       k_pct,
        "kama_trend":  kama_trend,
        "sar_bull":    bool(sar_bull[-1]),
        "ao":          last(ao),
        "rsi":         last(rsi),
        "adx":         last(adx),
        "pdi":         last(pdi),
        "ndi":         last(ndi),
        "er":          last(er),
        "baff":        baff_arr[-1] if baff_arr else 0,
        "mom1m":       mom1m,
        "mom3m":       mom3m,
        "mom6m":       mom6m,
        "hurst_60":    hurst60,
        "hurst_1y":    hurst1y,
        "tv_rating":   tv_rating,
        "current_signal": current_sig,
        "signal_dal":  sig_dal,
        "signal_bars": 1,
        "signals_history": sig_history,
        # Serie per grafico
        "chart": {
            "dates":    dates[-90:],
            "closes":   [round(float(v),4) for v in closes[-90:]],
            "highs":    [round(float(v),4) for v in highs[-90:]],
            "lows":     [round(float(v),4) for v in lows[-90:]],
            "kama":     kama[-90:],
            "sar":      sar[-90:],
            "sar_bull": sar_bull[-90:],
            "ao":       ao[-90:],
            "rsi":      rsi[-90:],
            "baff":     baff_arr[-90:],
        }
    }
