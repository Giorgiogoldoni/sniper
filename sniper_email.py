#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAPTOR Sniper — Rassegna Mattutina via Email
Legge signals.json, applica la stessa logica della dashboard:
  - Solo segnali BUY nella finestra (default 48h)
  - Multi-fonte in evidenza (ordinati prima)
  - Dedup per ticker
Invia email HTML via SMTP Gmail.
"""

import json, os, sys
from datetime import datetime, timedelta, timezone

FRESH_HOURS = int(os.environ.get('FRESH_HOURS', '48'))
SIGNALS_FILE = 'signals.json'

def load_signals():
    with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_rassegna(events, hours=48):
    """Stessa logica della dashboard: BUY nella finestra, multi-fonte prima, dedup per ticker."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    candidates = []
    for ev in events:
        if ev.get('signal') != 'BUY':
            continue
        det_at = ev.get('detected_at', '')
        try:
            det_dt = datetime.fromisoformat(det_at.replace('Z', '+00:00'))
            if det_dt.tzinfo is None:
                det_dt = det_dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if det_dt < cutoff:
            continue
        candidates.append(ev)

    # Ordina: prima multi-fonte (decrescente), poi per composite_score
    candidates.sort(key=lambda e: (
        -len(e.get('sources', [])),
        -(e.get('composite_score') or 0)
    ))

    # Dedup per ticker
    seen = set()
    result = []
    for ev in candidates:
        t = ev.get('ticker')
        if t not in seen:
            seen.add(t)
            result.append(ev)
    return result

def build_email_html(rassegna, hours, now):
    multi = [r for r in rassegna if len(r.get('sources', [])) >= 2]
    singoli = [r for r in rassegna if len(r.get('sources', [])) < 2]

    def fmt_row(ev, highlight=False):
        sources = ev.get('sources', [])
        n_src = len(sources)
        src_tags = ' '.join(
            '<span style="background:#eeece7;color:#57606a;font-size:9px;padding:2px 6px;'
            'border-radius:3px;margin-right:3px;text-transform:uppercase">{}</span>'.format(s.get('source',''))
            for s in sources
        )
        multi_badge = ''
        if n_src >= 2:
            multi_badge = ('<span style="background:#fef3c7;color:#92400e;font-size:9px;font-weight:800;'
                            'padding:2px 7px;border-radius:8px;margin-right:6px;border:1px solid #fde68a">'
                            '🎯 {} FONTI</span>').format(n_src)
        bg = '#fffbeb' if highlight else '#ffffff'
        score = ev.get('composite_score', 0) or 0
        price = ev.get('price', '—')
        name = (ev.get('name') or '')[:38]
        det_at = ev.get('detected_at', '')
        try:
            det_label = datetime.fromisoformat(det_at.replace('Z','+00:00')).strftime('%d/%m %H:%M')
        except Exception:
            det_label = det_at[:16]

        return (
            '<tr style="background:{bg};border-bottom:1px solid #e0ddd6">'
            '<td style="padding:8px 10px;font-weight:700;font-family:monospace;font-size:13px">{ticker}</td>'
            '<td style="padding:8px 10px;font-size:10px;color:#7a766e">{name}</td>'
            '<td style="padding:8px 10px">{multi_badge}{src_tags}</td>'
            '<td style="padding:8px 10px;text-align:right;font-weight:700;font-family:monospace">{score}</td>'
            '<td style="padding:8px 10px;text-align:right;font-family:monospace;color:#57606a">{price}</td>'
            '<td style="padding:8px 10px;font-size:10px;color:#7a766e">{det_label}</td>'
            '</tr>'
        ).format(bg=bg, ticker=ev.get('ticker','—'), name=name, multi_badge=multi_badge,
                  src_tags=src_tags, score=score, price=price, det_label=det_label)

    rows_multi = ''.join(fmt_row(r, highlight=True) for r in multi)
    rows_singoli = ''.join(fmt_row(r, highlight=False) for r in singoli[:20])  # cap a 20 per non far esplodere l'email

    multi_section = ''
    if multi:
        multi_section = '''
        <div style="margin-bottom:6px;font-size:13px;font-weight:700;color:#92400e">
          🎯 Segnali multi-fonte — {n} ticker confermati da più sistemi
        </div>
        <table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:18px">
          <thead><tr style="background:#f5f4f0">
            <th style="padding:6px 10px;text-align:left;border-bottom:2px solid #d0d7de">Ticker</th>
            <th style="padding:6px 10px;text-align:left;border-bottom:2px solid #d0d7de">Nome</th>
            <th style="padding:6px 10px;text-align:left;border-bottom:2px solid #d0d7de">Fonti</th>
            <th style="padding:6px 10px;text-align:right;border-bottom:2px solid #d0d7de">Score</th>
            <th style="padding:6px 10px;text-align:right;border-bottom:2px solid #d0d7de">Prezzo</th>
            <th style="padding:6px 10px;text-align:left;border-bottom:2px solid #d0d7de">Rilevato</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>'''.format(n=len(multi), rows=rows_multi)

    singoli_section = ''
    if singoli:
        singoli_section = '''
        <div style="margin-bottom:6px;font-size:13px;font-weight:700;color:#1a1816">
          📋 Altri segnali BUY — top {n} per score (singola fonte)
        </div>
        <table style="width:100%;border-collapse:collapse;font-size:12px">
          <thead><tr style="background:#f5f4f0">
            <th style="padding:6px 10px;text-align:left;border-bottom:2px solid #d0d7de">Ticker</th>
            <th style="padding:6px 10px;text-align:left;border-bottom:2px solid #d0d7de">Nome</th>
            <th style="padding:6px 10px;text-align:left;border-bottom:2px solid #d0d7de">Fonte</th>
            <th style="padding:6px 10px;text-align:right;border-bottom:2px solid #d0d7de">Score</th>
            <th style="padding:6px 10px;text-align:right;border-bottom:2px solid #d0d7de">Prezzo</th>
            <th style="padding:6px 10px;text-align:left;border-bottom:2px solid #d0d7de">Rilevato</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>'''.format(n=min(len(singoli),20), rows=rows_singoli)

    empty_msg = ''
    if not rassegna:
        empty_msg = ('<div style="padding:20px;text-align:center;color:#7a766e;font-size:13px">'
                      'Nessun segnale BUY nelle ultime {}h — giornata di attesa.</div>').format(hours)

    html = '''<!DOCTYPE html><html><body style="font-family:'Segoe UI',sans-serif;background:#f5f4f0;padding:20px;margin:0">
<div style="max-width:760px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.08)">
  <div style="background:#1a1816;color:#fff;padding:16px 22px">
    <h2 style="margin:0;font-size:19px;font-family:Georgia,serif">🌅 RAPTOR Sniper — Rassegna Mattutina</h2>
    <p style="margin:5px 0 0;font-size:11px;opacity:.75">{ts} &middot; Finestra: ultime {hours}h &middot; {n_tot} segnali trovati</p>
  </div>
  <div style="padding:18px 22px">
    {empty_msg}
    {multi_section}
    {singoli_section}
    <p style="margin-top:16px;padding-top:12px;border-top:1px solid #e0ddd6;font-size:11px;color:#7a766e">
      📊 <a href="https://giorgiogoldoni.github.io/sniper/" style="color:#1a6fcf">Apri RAPTOR Sniper</a>
      &nbsp;&middot;&nbsp; ⚠️ Solo uso educativo — verificare sempre i filtri prima di operare
    </p>
  </div>
</div></body></html>'''.format(
        ts=now.strftime('%d/%m/%Y %H:%M'), hours=hours, n_tot=len(rassegna),
        empty_msg=empty_msg, multi_section=multi_section, singoli_section=singoli_section
    )
    return html

def send_email(html, n_segnali, n_multi):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    EMAIL_USER = os.environ.get('EMAIL_USER', '')
    EMAIL_PASS = os.environ.get('EMAIL_PASS', '')
    if not EMAIL_USER or not EMAIL_PASS:
        print("EMAIL non configurata — skip invio")
        return

    if n_segnali == 0:
        subj = "🌅 RAPTOR Sniper — Nessun segnale oggi · {}".format(datetime.now().strftime('%d/%m %H:%M'))
    elif n_multi > 0:
        subj = "🎯 RAPTOR Sniper — {} segnali ({} multi-fonte) · {}".format(
            n_segnali, n_multi, datetime.now().strftime('%d/%m %H:%M'))
    else:
        subj = "🌅 RAPTOR Sniper — {} segnali · {}".format(
            n_segnali, datetime.now().strftime('%d/%m %H:%M'))

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subj
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_USER
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as srv:
            srv.login(EMAIL_USER, EMAIL_PASS)
            srv.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())
        print("✅ Email inviata: {} segnali ({} multi-fonte)".format(n_segnali, n_multi))
    except Exception as e:
        print("❌ Errore invio email:", e)
        sys.exit(1)

def main():
    now = datetime.now()
    print("RAPTOR Sniper — Rassegna Mattutina · {}".format(now.strftime('%Y-%m-%d %H:%M')))
    print("Finestra: {}h".format(FRESH_HOURS))

    events = load_signals()
    print("Eventi totali in signals.json: {}".format(len(events)))

    rassegna = get_rassegna(events, FRESH_HOURS)
    multi = [r for r in rassegna if len(r.get('sources', [])) >= 2]
    print("Rassegna: {} segnali ({} multi-fonte)".format(len(rassegna), len(multi)))

    html = build_email_html(rassegna, FRESH_HOURS, now)
    send_email(html, len(rassegna), len(multi))

if __name__ == '__main__':
    main()
