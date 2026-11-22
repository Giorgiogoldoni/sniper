# Sniper — analisi del backfill dal 1 ottobre 2026

**Fonte:** `data/paper_backfill_20261001_log.csv` e `data/paper_backfill_20261001_summary.json`  
**Esecuzione:** GitHub Actions run [45051649765](https://github.com/Giorgiogoldoni/sniper/actions/runs/45051649765)  
**Metodo:** paper trading, nessun ordine reale. I rendimenti sono percentuali per singola operazione, non una curva di capitale ponderata.

## Controlli del registro

- 99 strumenti selezionati: 73 `LEVA_LONG`, 26 `MATERIE_PRIME_LEVA`.
- 3.182 barre elaborate; 13 strumenti saltati per dati assenti o meno di 60 sedute.
- 88 operazioni chiuse nel CSV: 88 chiavi ticker/segnale/ingresso univoche, zero righe malformate.
- Alla fine della simulazione: 1 posizione aperta (LNGA.MI) e 1 ingresso in attesa (3TYL.MI).
- Il paper quotidiano è separato dal backfill storico.

## Risultato complessivo

| Metrica | Risultato |
|---|---:|
| Operazioni | 88 |
| Positive / negative / pari | 44 / 43 / 1 |
| Percentuale positive lorda | 50,0% |
| Rendimento medio lordo per operazione | -0,533% |
| Medio netto ipotetico a 20 bps round-trip | -0,733% |
| Medio netto ipotetico a 30 bps round-trip | -0,833% |
| Medio netto ipotetico a 50 bps round-trip | -1,033% |
| Profit factor lordo | 0,835 |
| Profit factor netto ipotetico a 30 bps | 0,754 |

I costi sono sensibilità ipotetiche: Yahoo OHLC non fornisce lo spread bid/ask osservato. Non sono quindi una stima del costo effettivamente pagato.

## Risultati per motore

| Motore | N. | Positive / negative / pari | Media lorda | Media netta 30 bps | Profit factor lordo |
|---|---:|---:|---:|---:|---:|
| LEVA_LONG | 67 | 29 / 37 / 1 | -1,156% | -1,456% | 0,636 |
| MATERIE_PRIME_LEVA | 21 | 15 / 6 / 0 | +1,455% | +1,155% | 1,427 |

Il campione è favorevole al motore materie prime, ma 21 operazioni sono ancora poche per considerarlo validato. Il motore LEVA_LONG è negativo nel campione.

## Uscite: dove si genera il risultato

| Uscita | N. | Positive / negative / pari | Media lorda | Media netta 30 bps | Profit factor lordo |
|---|---:|---:|---:|---:|---:|
| TIME_3_SESSIONS | 53 | 29 / 23 / 1 | +1,624% | +1,324% | 2,737 |
| ATR_2_STOP | 16 | 0 / 16 / 0 | -11,998% | -12,298% | 0 |
| WALKING_2_NEGATIVE_CLOSES | 19 | 15 / 4 / 0 | +3,105% | +2,805% | 2,365 |

Dettaglio per categoria:
- LEVA_LONG: 53 uscite a tre sedute, media +1,624%; 14 stop ATR, media -11,681%.
- MATERIE_PRIME_LEVA: 19 uscite Walking, media +3,105%; 2 stop ATR, media -14,214%.

**Lettura:** gli ingressi long che arrivano all'uscita temporale hanno avuto un risultato medio positivo; il risultato negativo del motore long è spiegato soprattutto dalle perdite molto ampie sulle operazioni fermate dallo stop. Non significa che si debba eliminare lo stop: in caso di gap il prezzo di esecuzione può essere molto peggiore del livello stop.

## Caso 3LMO.MI: verifica del movimento estremo

Il registro riporta:
- ingresso 22/10 a 435,27;
- uscita 23/10 a 189,64;
- rendimento -56,4316%, uscita `ATR_2_STOP`.

3LMO è il GraniteShares 3x Long Moderna Daily. Le quotazioni storiche consultate riportano il 22 ottobre apertura 435,27 e chiusura 345,09; il 23 ottobre apertura 189,64 e chiusura 188,07. Il prezzo di uscita simulato coincide quindi con l'apertura del giorno successivo: è un gap avverso, non un errore evidente del CSV. La stessa fonte riporta volumi contenuti (circa 390 unità il 22 ottobre e 1.300 il 23 ottobre), da considerare nel rischio di esecuzione.

Fonti di controllo:
- [Investing.com — storico 3LMO](https://it.investing.com/etfs/3lmo-historical-data?cid=1180780)
- [Trading 212 — storico 3LMO](https://www.trading212.com/trading-instruments/invest/3LMO.IT)

Escludendo entrambe le operazioni su 3LMO, la media lorda delle altre 86 operazioni resta negativa (-0,326%) e il profit factor lordo resta sotto 1 (0,877): il problema del motore long non dipende da questo solo caso.

## Altri segnali da approfondire

- Ripetizioni negative: 3DEL.MI (3 operazioni, media -4,53%), 3AAP.MI (3, -6,65%), LCFE.MI (2, -10,46%), 3EUL.MI (2, -3,50%).
- Ripetizioni positive: 3BRL.MI (4, +6,62%), LBRT.MI (3, +7,26%), LOIL.MI (3, +2,93%), 3LPP.MI (3, +4,45%).
- Questi numeri per ticker sono descrittivi: con 1–4 operazioni non giustificano esclusioni o selezioni permanenti.

## Decisioni operative consigliate

1. **Non cambiare ancora Donchian 20, ATR 2 o le regole di uscita.** Il campione è utile per individuare problemi, non per ottimizzare parametri.
2. **Mantenere separati i due motori.** Materie prime: continuare il paper con ingresso Donchian e uscita Walking. LEVA_LONG: continuare solo in osservazione, senza promuoverlo a motore validato.
3. **Migliorare la diagnostica degli stop nel registro futuro:** salvare ATR iniziale, livello stop, distanza stop in percentuale, apertura/minimo del giorno di uscita e scostamento tra stop teorico e fill effettivo. Questo separerà il rischio gap dal normale comportamento dello stop.
4. **Verificare liquidità e gap dei prodotti più estremi** con una sensibilità di esecuzione più severa. Non applicare ancora filtri o esclusioni sulla base di poche operazioni.
5. **Ampliare il campione** e valutare risultati per strumento, categoria, leva, tipo di uscita e regime di volatilità prima di qualsiasi modifica.

## Limiti

Il rendimento medio per operazione non equivale al rendimento di un portafoglio: le operazioni possono sovrapporsi e non sono ponderate per capitale o rischio. Le quotazioni Yahoo sono utilizzate per la simulazione; il codice richiede `auto_adjust=False`, `actions=True` e `repair=True`, ma nessun feed OHLC garantisce prezzi realmente eseguibili o spread storici. Il test resta paper e non prova la capacità di eseguire questi prodotti in mercato reale.
