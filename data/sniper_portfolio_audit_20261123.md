# Sniper portfolio simulation — audit tecnico
Data audit: 2026-11-23
Run verificato: https://github.com/Giorgiogoldoni/sniper/actions/runs/45086658429
Commit dei risultati: file `data/sniper_portfolio_comparison.json`

## Esito sintetico
Il Run #3 è completato con successo. La correzione del calendario (carry-forward dell'ultimo close per la valorizzazione e mantenimento delle uscite pendenti fino alla prima seduta utile del singolo strumento) è presente nel codice e nei risultati.

L'audit del codice non rileva look-ahead evidente nella sequenza segnale a chiusura / ingresso all'apertura successiva. La formula Walking e il Donchian20 sono coerenti con `indicators.py`: Bollinger 20, deviazione standard campionaria, distanza 1,5% dalla banda superiore, close sopra la media, banda crescente, almeno 2 condizioni su 3; Donchian usa i massimi delle 20 sedute precedenti escludendo la barra corrente.

**Non è però ancora una validazione sufficiente per promuovere il sistema.** Sono emersi limiti metodologici che possono influenzare sensibilmente i risultati.

## Controlli superati
- Workflow: tutti gli step completati con esito success.
- Segnale calcolato sulla chiusura; ordine simulato all'open della successiva seduta dello strumento.
- ATR14 calcolato solo con dati disponibili fino alla chiusura del segnale; stop iniziale = open d'ingresso meno 2 ATR.
- Stop controllato sul minimo giornaliero; in caso di apertura sotto stop, prezzo di uscita all'open.
- Uscita Walking dopo due chiusure false, all'open successivo disponibile; limite temporale alla decima seduta, al close.
- Valorizzazione delle posizioni aperte a fine periodo inclusa nell'equity.
- Nei giorni senza barra di uno strumento, l'ultimo close noto viene mantenuto per la sola valorizzazione; l'uscita pendente viene eseguita alla prima barra successiva disponibile.
- Nessuna modifica alla logica di produzione.

## Limiti e rischi da risolvere
1. **Universo non point-in-time / survivorship bias.** La simulazione parte dall'universo corrente di 26 strumenti classificati MATERIE_PRIME_LEVA, non da un archivio storico di tutti i prodotti esistenti in ciascuna data. Prodotti cessati, delistati o sostituiti potrebbero mancare. Questo può sovrastimare la robustezza storica.
2. **Priorità d'ingresso non validata.** Quando i segnali superano gli slot disponibili, il codice ordina per distanza percentuale sopra il massimo Donchian. È una regola di spareggio introdotta per la simulazione, non ancora confrontata con alternative e non una regola strategica approvata. I rendimenti a 5/8/12 slot dipendono da questa scelta.
3. **Prezzi e operazioni societarie.** La fonte è Yahoo Finance OHLC giornaliero con auto_adjust=False e repair=True. Prima di fidarsi dei risultati va verificato, per ogni ETP, il trattamento di split/reverse split e discontinuità storiche. La simulazione non conserva un audit indipendente delle azioni societarie.
4. **Rischio non normalizzato.** Ogni posizione riceve un controvalore fisso pari a capitale iniziale / numero slot. Non è un dimensionamento a rischio costante: la perdita potenziale allo stop varia molto con ATR e volatilità dello strumento.
5. **Drawdown solo a chiusura.** Il max drawdown è calcolato sull'equity giornaliera a close; non misura il massimo drawdown intraday.
6. **Posizioni finali aperte.** L'equity le valorizza al close finale, ma le statistiche delle operazioni chiuse non le includono. Va mantenuta questa distinzione nei report.
7. **Un dato mancante.** 2GOL.MI non ha fornito una serie sufficiente; 25 ticker su 26 sono stati utilizzati. Non sostituire o inventare il dato.

## Risultati del Run #3 — da considerare preliminari
Capitale iniziale €100.000, periodo 2023-01-02 / 2026-11-20, sizing fisso per slot.

| Slot | Equity finale | Rendimento | CAGR | Max DD close | Trade chiusi | Ingressi rifiutati |
|---:|---:|---:|---:|---:|---:|---:|
| 5 | €165.767,31 | +65,77% | 13,90% | -31,63% | 396 | 174 |
| 8 | €152.268,83 | +52,27% | 11,44% | -24,82% | 446 | 41 |
| 12 | €137.746,68 | +37,75% | 8,60% | -18,04% | 456 | 8 |

Rendimenti annuali:
- 5 slot: 2023 -13,83%; 2024 +35,87%; 2025 +6,29%; 2026 +33,20%.
- 8 slot: 2023 -12,57%; 2024 +21,50%; 2025 +15,50%; 2026 +24,11%.
- 12 slot: 2023 -8,99%; 2024 +16,41%; 2025 +11,05%; 2026 +17,08%.

## Piano di validazione successivo
A. Ricostruire l'universo storico, includendo strumenti cessati e date effettive di quotazione; finché non è disponibile, etichettare ogni risultato come soggetto a survivorship bias.

B. Testare la sensibilità della selezione quando i segnali eccedono gli slot: (i) forza breakout, (ii) ATR% più basso, (iii) ordinamento neutrale/deterministico. Nessuna di queste varianti diventa regola di produzione senza confronto.

C. Testare finestre temporali separate e walk-forward: calibrazione solo su una finestra iniziale, verifica su una finestra successiva mai usata per scegliere i parametri. Non ottimizzare sul periodo intero.

D. Confrontare sizing fisso con rischio per trade basato su distanza stop, mantenendo invariata la strategia di segnale; verificare drawdown e concentrazione.

E. Verificare split/reverse split e prezzi anomali per ogni strumento; non interpolare prezzi OHLC e non cancellare strumenti solo perché volatili.

## Decisione
Nessuna promozione in produzione e nessuna modifica a Donchian/Walking/ATR. I risultati attuali sono una base di ricerca, non una promessa di rendimento. La scelta 5 vs 8 vs 12 resta aperta: 5 massimizza il rendimento storico ma ha drawdown close superiore al 31%; 8 è un compromesso descrittivo, non ancora una scelta validata.
