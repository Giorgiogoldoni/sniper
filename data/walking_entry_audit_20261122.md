# Audit di robustezza — Donchian + Walking
Data analisi: 22 novembre 2026

## Perimetro
- 25 ETP su materie prime con dati sufficienti; 2GOL.MI escluso per dati insufficienti.
- Finestra segnali richiesta: 2023-01-01 → 2026-11-22 (circa 3 anni e 11 mesi, non 10 anni).
- Tutti i rendimenti sono lordi e per singola operazione.
- Nessuna modifica al motore operativo o al paper ledger.

## Verifica del codice e della cronologia
- Il filtro Walking del backtest corrisponde alla definizione in indicators.py: chiusura entro l'1,5% dalla Bollinger superiore, sopra la media a 20 sedute, banda superiore crescente; condizione vera in almeno 2 delle ultime 3 sedute.
- Deviazione standard Bollinger campionaria (ddof=1) coerente tra i due calcoli.
- Donchian usa i massimi delle sedute precedenti, escludendo la barra corrente.
- Il segnale è valutato alla chiusura e l'ingresso avviene all'apertura successiva: nessun look-ahead individuato in questa sequenza.
- Lo stop è definito all'ingresso usando ATR(14) disponibile alla chiusura del segnale; gap avversi sono eseguiti all'apertura.
- Nota: questo test è un modello storico indipendente; non equivale a un ordine o a una modifica del motore live.

## Risultati aggregati
| Variante | Operazioni | Win rate | Media lorda | Profit factor | Mediana | Peggior trade |
|---|---:|---:|---:|---:|---:|---:|
| Donchian 20 | 789 | 42,84% | +0,762% | 1,216 | -1,246% | -43,216% |
| Donchian 20 + Walking | 457 | 44,64% | +1,058% | 1,288 | -1,040% | -25,170% |
| Donchian 10 + Walking | 468 | 44,87% | +1,066% | 1,297 | -0,955% | -25,170% |

Walking riduce le operazioni del 42,1% circa rispetto a Donchian 20 puro e migliora media e profit factor nel campione complessivo. Donchian 10 non mostra un vantaggio abbastanza grande da giustificare il cambio del parametro.

## Stabilità annuale — Donchian 20 + Walking
| Anno | Operazioni | Media lorda | Win rate |
|---|---:|---:|---:|
| 2023 | 93 | -1,29% | 38,7% |
| 2024 | 120 | +1,88% | 52,5% |
| 2025 | 143 | +1,21% | 39,9% |
| 2026 | 101 | +2,01% | 47,5% |

Il filtro non è positivo in tutti i regimi: il 2023 resta negativo. Il risultato aggregato non va quindi interpretato come vantaggio costante.

## Dispersione per strumento — Donchian 20 + Walking
| Strumento | Operazioni | Media lorda | Profit factor |
|---|---:|---:|---:|
| 3OIL.MI | 19 | +8,29% | 3,48 |
| 3CFL.MI | 16 | +8,29% | 2,22 |
| LOIL.MI | 20 | +5,08% | 2,92 |
| LCFE.MI | 18 | +4,93% | 2,10 |
| 3BRL.MI | 20 | +3,87% | 1,98 |
| LBRT.MI | 21 | +3,09% | 2,13 |
| LCOC.MI | 23 | +2,12% | 1,41 |
| 3GOL.MI | 19 | +2,55% | 2,23 |
| LSIL.MI | 18 | +2,58% | 1,92 |
| LBUL.MI | 26 | +1,48% | 1,96 |
| LSUG.MI | 19 | +1,69% | 1,84 |
| 3SUL.MI | 17 | +1,53% | 1,48 |
| LALU.MI | 21 | +0,52% | 1,38 |
| LNIK.MI | 11 | +0,27% | 1,09 |
| LAGR.MI | 21 | +0,01% | 1,00 |
| LCOR.MI | 19 | -0,12% | 0,93 |
| LPLA.MI | 18 | -1,18% | 0,73 |
| 3HCL.MI | 19 | -1,12% | 0,70 |
| LCOP.MI | 23 | -0,94% | 0,64 |
| LNGA.MI | 11 | -3,70% | 0,44 |
| 3NGL.MI | 9 | -4,54% | 0,53 |
| LWEA.MI | 16 | -2,65% | 0,37 |
| 3SIL.MI | 21 | -2,31% | 0,59 |
| 3WHL.MI | 15 | -3,86% | 0,34 |
| 2PAL.MI | 17 | -5,71% | 0,11 |

I cinque ticker con maggior contributo netto positivo non spiegano da soli il risultato: eliminandone uno alla volta, la media lorda aggregata resta positiva (da +0,744% a +0,929% a seconda del ticker rimosso). Restano però diversi strumenti con risultati deboli e campioni individuali limitati: non è giustificata un'esclusione automatica.

## Sovrapposizione delle posizioni
Con Donchian 20 + Walking si osservano fino a 15 operazioni contemporanee (conteggio conservativo includendo il giorno di uscita). Il backtest aggregato precedente non aveva un limite di capitale o di posizioni; quindi i risultati per trade non sono un rendimento di portafoglio. Serve un test dedicato con regole esplicite di allocazione, priorità dei segnali, slot disponibili e valorizzazione giornaliera delle posizioni aperte.

## Decisione
1. Mantenere Donchian 20 + Walking come candidato per ulteriori verifiche.
2. Tenere Donchian 10 + Walking solo come variante di confronto.
3. Non cambiare il motore Sniper operativo e non escludere strumenti sulla sola base di questo campione.
4. Prossimo test: simulazione di portafoglio con capitale e numero massimo di posizioni, mark-to-market giornaliero e analisi drawdown.
