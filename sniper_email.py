#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RAPTOR Sniper operational email: dashboard BUY + independent PAPER entries/exits."""
import json, os, sys, smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

FRESH_HOURS = int(os.environ.get("FRESH_HOURS", "48"))
SIGNALS_FILE = "signals.json"
PAPER_STATE_FILE = "data/paper_trading_state.json"
PAPER_SUMMARY_FILE = "data/paper_trading_summary.json"
UNIVERSE_FILE = "data/instrument_universe.json"
SHORT_STATE_FILE = "data/short_paper_state.json"
SHORT_SUMMARY_FILE = "data/short_paper_summary.json"

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as exc:
        print("WARN: impossibile leggere {}: {}".format(path, exc))
        return default

def get_rassegna(events, hours=48):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    candidates = []
    for ev in events:
        if ev.get("signal") != "BUY":
            continue
        try:
            dt = datetime.fromisoformat(ev.get("detected_at", "").replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if dt >= cutoff:
            candidates.append(ev)
    candidates.sort(key=lambda e: (-len(e.get("sources", [])), -(e.get("composite_score") or 0)))
    seen, result = set(), []
    for ev in candidates:
        ticker = ev.get("ticker")
        if ticker and ticker not in seen:
            seen.add(ticker)
            result.append(ev)
    return result

def esc(value):
    return str(value if value is not None else "—").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def fmt_dt(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.astimezone().strftime("%d/%m/%Y %H:%M")
    except Exception:
        return esc(value)

def build_email_html(buys, state, summary, universe, hours, now, short_state=None, short_summary=None):
    short_state = short_state or {}
    short_summary = short_summary or {}
    instruments = {x.get("yahoo") or x.get("ticker"): x for x in universe.get("instruments", [])}
    def name(ticker):
        return esc(instruments.get(ticker, {}).get("name") or ticker)

    # Dashboard BUY are candidate signals; they are not automatically paper fills.
    buy_rows = []
    for ev in buys:
        ticker = ev.get("ticker", "—")
        sources = ", ".join(s.get("source", "") for s in ev.get("sources", []))
        buy_rows.append("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            esc(ticker), name(ticker), esc(ev.get("composite_score", "—")),
            esc(ev.get("price", "—")), esc(sources or "—")))
    buys_html = "".join(buy_rows) or '<tr><td colspan="5">Nessun nuovo BUY nella finestra selezionata.</td></tr>'

    pending_entries = state.get("pending_entries", {})
    pending_exits = state.get("pending_exits", {})
    positions = state.get("positions", {})
    entry_rows = []
    for ticker, item in sorted(pending_entries.items()):
        entry_rows.append("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            esc(ticker), name(ticker), esc(item.get("signal_date")), esc(round(float(item.get("atr", 0)), 4))))
    entries_html = "".join(entry_rows) or '<tr><td colspan="4">Nessun ingresso paper in attesa.</td></tr>'

    exit_rows = []
    for ticker, reason in sorted(pending_exits.items()):
        pos = positions.get(ticker, {})
        exit_rows.append("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            esc(ticker), name(ticker), esc(reason), esc(pos.get("entry_date", "—"))))
    exits_html = "".join(exit_rows) or '<tr><td colspan="4">Nessuna uscita paper da eseguire alla prossima apertura.</td></tr>'

    position_rows = []
    for ticker, pos in sorted(positions.items()):
        position_rows.append("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            esc(ticker), name(ticker), esc(pos.get("entry_date")), esc(pos.get("entry_price")),
            esc(pos.get("stop_price")), esc(pos.get("holding_sessions"))))
    positions_html = "".join(position_rows) or '<tr><td colspan="6">Nessuna posizione paper aperta.</td></tr>'

    latest = sorted(state.get("trades", []), key=lambda x: x.get("exit_date", ""), reverse=True)[:8]
    trade_rows = "".join("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}%</td><td>{}</td></tr>".format(
        esc(t.get("ticker")), name(t.get("ticker")), esc(t.get("exit_date")),
        esc(t.get("gross_return_pct")), esc(t.get("exit_reason"))) for t in latest)
    trades_html = trade_rows or '<tr><td colspan="5">Nessuna operazione paper chiusa registrata.</td></tr>'

    generated = summary.get("generated_at") or state.get("updated_at") or "non disponibile"
    mode = summary.get("mode", "PAPER_STATUS_UNAVAILABLE")
    paper_note = ("Motore paper indipendente: Donchian 20 + Walking per materie prime; stop iniziale ATR(14) x 2. "
                  "Gli ingressi/uscite in attesa sono simulazioni alla prossima apertura, non ordini reali.")
    if mode != "PAPER_ONLY_NO_ORDERS":
        paper_note += " ATTENZIONE: stato paper non verificato."
    skipped = summary.get("skipped_count", "—")
    last_market = max(state.get("last_processed", {}).values(), default="non disponibile")

    def table(headers, rows):
        th = "".join('<th style="text-align:left;padding:7px;border-bottom:2px solid #ccd2d8">{}</th>'.format(h) for h in headers)
        return '<table style="width:100%;border-collapse:collapse;font-size:12px;margin:8px 0 18px"><thead><tr style="background:#f2f4f7">{}</tr></thead><tbody>{}</tbody></table>'.format(
            th, rows.replace("<td>", '<td style="padding:7px;border-bottom:1px solid #e5e7eb">'))


    # Independent bearish sleeve: purchases of inverse ETPs, not broker short sales.
    short_pending = short_state.get("pending_entries", {})
    short_exits = short_state.get("pending_exits", {})
    short_positions = short_state.get("positions", {})
    short_entry_rows = "".join("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
        esc(t), name(t), esc(v.get("signal_date")), esc(round(float(v.get("atr", 0)), 4)))
        for t, v in sorted(short_pending.items())) or '<tr><td colspan="4">Nessuna entrata SHORT paper in attesa.</td></tr>'
    short_position_rows = "".join("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
        esc(t), name(t), esc(v.get("entry_date")), esc(v.get("entry_price")), esc(v.get("stop_price")))
        for t, v in sorted(short_positions.items())) or '<tr><td colspan="5">Nessuna posizione SHORT paper aperta.</td></tr>'
    short_exit_rows = "".join("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
        esc(t), name(t), esc(reason), esc(short_positions.get(t, {}).get("entry_date", "—")))
        for t, reason in sorted(short_exits.items())) or '<tr><td colspan="4">Nessuna uscita SHORT paper in attesa.</td></tr>'
    short_mode = short_summary.get("mode", "SHORT_PAPER_STATUS_UNAVAILABLE")
    short_note = ("Motore indipendente: Donchian 20 + Walking su ETP inversi; stop ATR(14) x 2. "
                  "Sono acquisti paper di strumenti inversi, non vendite allo scoperto reali.")
    if short_mode != "PAPER_ONLY_NO_ORDERS":
        short_note += " ATTENZIONE: stato SHORT non aggiornato o non verificato."
    short_sections = [
        ("🟠 OPPORTUNITÀ RIBASSISTE — ETP inversi, ingresso PAPER alla prossima apertura",
         table(["Ticker ETP inverso","Strumento","Data segnale","ATR14"], short_entry_rows)),
        ("📍 POSIZIONI SHORT PAPER APERTE — controllo stop",
         table(["Ticker","Strumento","Data entrata","Prezzo entrata","Stop ATR"], short_position_rows)),
        ("↘ USCITE SHORT PAPER IN ATTESA",
         table(["Ticker","Strumento","Motivo","Data entrata"], short_exit_rows))
    ]
    short_html = '<div style="background:#fff7ed;padding:10px;border-radius:6px;font-size:12px;margin-top:16px"><b>Motore SHORT:</b> {} · strumenti: {} · posizioni: {} · ingressi in attesa: {} · ticker saltati: {}</div>'.format(
        esc(short_note), esc(short_summary.get("universe", {}).get("total_selected", "—")),
        esc(len(short_positions)), esc(len(short_pending)), esc(short_summary.get("skipped_count", "—")))
    short_html += "".join('<h3 style="font-size:15px;margin:20px 0 6px;color:#202833">{}</h3>{}'.format(title, body)
                          for title, body in short_sections)

    sections = [
        ("🟢 ACQUISTA ORA — ingresso PAPER simulato alla prossima apertura", table(["Ticker","Strumento","Data segnale","ATR14"], entries_html)),
        ("🔴 VENDI ORA — uscita PAPER simulata alla prossima apertura", table(["Ticker","Strumento","Motivo uscita","Data entrata"], exits_html)),
        ("📌 POSIZIONI PAPER APERTE — controllo stop", table(["Ticker","Strumento","Data entrata","Prezzo entrata","Stop ATR","Sedute"], positions_html)),
        ("🔎 BUY DELLA DASHBOARD — segnali da valutare, non ordini", table(["Ticker","Strumento","Score","Prezzo rilevato","Fonti"], buys_html)),
        ("📚 Ultime operazioni PAPER chiuse", table(["Ticker","Strumento","Uscita","Rendimento lordo","Motivo"], trades_html)),
    ]
    section_html = "".join('<h3 style="font-size:15px;margin:20px 0 6px;color:#202833">{}</h3>{}'.format(title, body) for title, body in sections)
    html = """<!doctype html><html><body style="font-family:Arial,sans-serif;background:#f3f5f7;padding:18px">
<div style="max-width:900px;margin:auto;background:white;padding:22px;border-radius:10px">
<h2 style="margin:0;color:#17212b">RAPTOR Sniper — Bollettino operativo</h2>
<p style="color:#667085;font-size:12px">{ts} · BUY dashboard: ultime {hours} ore</p>
<div style="background:#eef4fb;padding:12px;border-radius:6px;font-size:12px">
<b>Stato PAPER:</b> {mode} · aggiornamento: {generated}<br>
<b>Ultima seduta elaborata:</b> {last_market} · strumenti selezionati: {selected} · ticker saltati per dati: {skipped}<br>
{note}
</div>
{sections}
{short_sections}
<p style="font-size:11px;color:#667085;border-top:1px solid #ddd;padding-top:12px">
<a href="https://giorgiogoldoni.github.io/sniper/">Apri dashboard RAPTOR Sniper</a><br>
Solo simulazione e supporto decisionale: nessun ordine viene inviato a un broker. I BUY dashboard non equivalgono a un ingresso paper confermato.
</p></div></body></html>""".format(
        ts=now.strftime("%d/%m/%Y %H:%M"), hours=hours, mode=esc(mode), generated=fmt_dt(generated),
        last_market=esc(last_market), selected=esc(summary.get("universe", {}).get("total_selected", "—")),
        skipped=esc(skipped), note=esc(paper_note), sections=section_html, short_sections=short_html)
    return html

def send_email(html, buys, state, short_state=None):
    short_state = short_state or {}
    email_user, email_pass = os.environ.get("EMAIL_USER", ""), os.environ.get("EMAIL_PASS", "")
    if not email_user or not email_pass:
        raise RuntimeError("EMAIL_USER o EMAIL_PASS non configurati: invio annullato.")
    entries = len(state.get("pending_entries", {}))
    exits = len(state.get("pending_exits", {}))
    short_entries = len(short_state.get("pending_entries", {}))
    subject = "RAPTOR Sniper — BUY {} · LONG {} · SHORT {}".format(len(buys), entries, short_entries)
    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"] = subject, email_user, email_user
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
        srv.login(email_user, email_pass)
        srv.sendmail(email_user, email_user, msg.as_string())
    print("EMAIL_OK: BUY dashboard={}, ingressi LONG paper={}, uscite LONG paper={}, ingressi SHORT paper={}".format(
        len(buys), entries, exits, short_entries))

def main():
    now = datetime.now()
    events = load_json(SIGNALS_FILE, [])
    state = load_json(PAPER_STATE_FILE, {})
    summary = load_json(PAPER_SUMMARY_FILE, {})
    universe = load_json(UNIVERSE_FILE, {"instruments": []})
    short_state = load_json(SHORT_STATE_FILE, {})
    short_summary = load_json(SHORT_SUMMARY_FILE, {})
    buys = get_rassegna(events, FRESH_HOURS)
    html = build_email_html(buys, state, summary, universe, FRESH_HOURS, now, short_state, short_summary)
    send_email(html, buys, state, short_state)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("EMAIL_ERROR:", exc)
        sys.exit(1)
