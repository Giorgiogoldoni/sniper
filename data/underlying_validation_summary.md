# Sniper — rapporto verifica sottostanti

**Run GitHub Actions:** [44946583919](https://github.com/Giorgiogoldoni/sniper/actions/runs/44946583919)  
**Esito:** success  
**Data:** 21 novembre 2026  
**Periodo:** 2 anni  
**Commit verificato:** `fb583d00e21520f9aa340c535526322324ece2c1`

## Sintesi

- Universo verificato: **60 strumenti**.
- Mappature ufficiali: **35 sottostanti azionari** e **25 benchmark/indici**.
- Confronto quantitativo disponibile: **35 strumenti**, tutti con sovrapposizione di date; **25** restano in modalità identificazione benchmark, perché la serie storica esatta non è ancora collegata.
- Errori di download nel test: **0**.
- Correlazione mediana tra rendimento ETP e rendimento teorico giornaliero: **0,6246**.
- Correlazione inferiore a 0,20: **12 strumenti**.
- Correlazione pari o superiore a 0,70: **11 strumenti**.

## Risultati quantitativi

Il rendimento teorico è calcolato come `direzione × leva × rendimento giornaliero del sottostante`. Il residuo è espresso in punti percentuali. La colonna “giorni residuo >5 pp” è un indicatore diagnostico, non una soglia di esclusione.

| ETP | Giorni | Correlazione | Residuo assoluto mediano (pp) | Giorni residuo >5 pp |
|---|---:|---:|---:|---:|
| SNV3.MI | 487 | -0,0484 | 2,871 | 131 |
| 3SMI.MI | 488 | -0,0089 | 6,481 | 288 |
| 3SNF.MI | 487 | -0,0005 | 2,969 | 142 |
| 3SPA.MI | 487 | 0,0096 | 4,064 | 207 |
| SMCI.MI | 488 | 0,0153 | 4,158 | 211 |
| TSLQ.MI | 487 | 0,0195 | 4,102 | 192 |
| 3STS.MI | 487 | 0,0233 | 3,905 | 193 |
| 3LMO.MI | 487 | 0,0278 | 6,758 | 307 |
| 3NIO.MI | 487 | 0,0294 | 3,802 | 190 |
| 3LAM.MI | 487 | 0,0444 | 4,037 | 195 |
| 3SNI.MI | 487 | 0,0615 | 4,173 | 215 |
| SBA3.MI | 487 | 0,1448 | 3,336 | 165 |
| 3SQ.MI | 487 | 0,2149 | 5,253 | 252 |
| 3SSQ.MI | 488 | 0,4600 | 4,665 | 228 |
| 3SAP.MI | 487 | 0,5175 | 2,294 | 102 |
| 3AAP.MI | 487 | 0,5448 | 2,103 | 87 |
| 3LUB.MI | 487 | 0,5555 | 3,529 | 172 |
| 3LSQ.MI | 488 | 0,6246 | 4,329 | 218 |
| 3LAP.MI | 487 | 0,6302 | 2,115 | 81 |
| 3LMI.MI | 488 | 0,6409 | 5,995 | 276 |
| 3SNV.MI | 487 | 0,6668 | 2,868 | 143 |
| 3LTS.MI | 487 | 0,6724 | 3,834 | 191 |
| 3LNV.MI | 487 | 0,6855 | 2,901 | 132 |
| 3NVD.MI | 487 | 0,6893 | 2,873 | 131 |
| 3FB.MI | 487 | 0,7068 | 2,844 | 121 |
| 3LZN.MI | 487 | 0,7095 | 2,348 | 96 |
| 3LFB.MI | 487 | 0,7353 | 2,738 | 102 |
| 3CON.MI | 487 | 0,7417 | 5,418 | 256 |
| 3LPP.MI | 488 | 0,7422 | 2,467 | 105 |
| 3LCO.MI | 488 | 0,7423 | 5,543 | 257 |
| 3SAA.MI | 488 | 0,7676 | 3,172 | 148 |
| ARM3.MI | 488 | 0,7794 | 4,483 | 223 |
| 3TSL.MI | 232 | 0,8539 | 2,684 | 54 |
| 3LAA.MI | 488 | 0,8583 | 2,181 | 74 |
| 3SCR.MI | 505 | 0,9750 | 0,801 | 4 |

## Priorità emerse

1. **Prima fascia di verifica dati:** SNV3, 3SMI, 3SNF, 3SPA, SMCI, TSLQ, 3STS, 3LMO, 3NIO, 3LAM, 3SNI e SBA3: correlazione inferiore a 0,20. Non significa automaticamente che il sottostante sia errato: la serie ETP presenta salti e disallineamenti da riconciliare.
2. **Risultati migliori:** 3SCR (0,975), 3LAA (0,858), 3TSL (0,854), ARM3 (0,779), 3SAA (0,768).
3. **Correzioni di mappatura che hanno sbloccato il test:** 3SCR usa ora `UCG.MI`; 3LCO usa `COIN`. LQQ è stato riclassificato come Amundi 2x, non Leverage Shares 3x.
4. **Benchmark non ancora confrontati numericamente:** 25 strumenti, tra cui gli indici Solactive, WisdomTree, Bloomberg, FTSE, Nasdaq e VIX. Non sono stati sostituiti con proxy generici.

## Limiti e decisioni

- Le chiusure ETP su Borsa Italiana e quelle delle azioni USA non sono sincronizzate: il confronto close-to-close è esplorativo.
- La correlazione è influenzata da eventi societari, consolidamenti, prezzi non aggiornati e possibili discontinuità tra ISIN.
- I dati sono Yahoo Finance con `auto_adjust=True`, `repair=False`; nessun prezzo è stato corretto, interpolato o mediato.
- Nessuno strumento è stato escluso dall'universo Sniper.
- Il test non autorizza ancora a usare queste correlazioni come filtro operativo o come prova di tracking error.

## Prossimo passo

Riconciliare i 12 casi con correlazione più bassa contro NAV/prezzi ufficiali e ISIN, poi collegare le serie storiche dei 25 benchmark esatti. Solo dopo ripetere il test e decidere quali fonti dati siano utilizzabili.


## Fase 1 — riconciliazione dei 12 casi a bassa correlazione (21 novembre 2026)

La verifica delle comunicazioni degli emittenti ha identificato almeno un consolidamento/cambio ISIN ufficiale per **tutti e 12 i 12 strumenti**. I salti di prezzo evidenziati dall'audit Yahoo coincidono con le date delle operazioni o, in alcuni casi, compaiono con uno scarto di una seduta. Questo rende la correlazione originaria non utilizzabile per giudicare la qualità di replica.

| ETP | Evento ufficiale | Rapporto | ISIN precedente → nuovo | Riscontro rispetto al salto Yahoo |
|---|---|---:|---|---|
| SNV3 | 03/12/2024 | 246:1 | XS2706225427 → XS2944874416 | salto 04/12, +1 seduta |
| 3SMI | 19/05/2025 | da confermare | XS2836637525 → XS3069873134 | salto 20/05, +1 seduta |
| 3SNF | 02/06/2025 | 50:1 | XS2675292135 → XS3075487986 | salto 02/06 |
| 3SPA | 19/05/2025 | 6.000:1 | XS2836484787 → XS3069876582 | salto 20/05, +1 seduta |
| SMCI | 30/12/2024 | 46:1 | XS2779863021 → XS2944889109 | salto 30/12 |
| TSLQ | 20/08/2025 | 606:1 | XS2706232803 → XS3135031279 | salti nella finestra 18–20/08 |
| 3STS | 02/06/2025 | 150:1 | XS2656471039 → XS3075487556 | salto 02/06 |
| 3LMO | 19/05/2025 | 5.000:1 | XS2613356620 → XS3069877556 | salto 19/05 |
| 3NIO | 07/02/2025 | 641:1 | XS2663694417 → XS2970736489 | salto 10/02, dopo il weekend e +1 seduta |
| 3LAM | 02/06/2025 | 200:1 | XS2377112110 → XS3075487713 | salto 02/06 |
| 3SNI | 19/05/2025 | da confermare | XS2626290311 → XS3069879768 | salto 20/05, +1 seduta |
| SBA3 | 07/04/2025 | 329:1 | XS2472334585 → XS3037640110 | salto 07/04 |

**Esito della riconciliazione:** 10 rapporti di consolidamento sono confermati documentalmente; per 3SMI e 3SNI sono verificati data e cambio ISIN, ma il rapporto non è leggibile nelle copie degli avvisi reperite e resta da confermare. Nessun rapporto è stato dedotto dal movimento di prezzo.

**Conseguenza sul test:** la correlazione calcolata sulle serie Yahoo concatenando i periodi pre/post consolidamento è contaminata da discontinuità di capitale e da cambi ISIN. I valori negativi o prossimi a zero dei 12 strumenti non sono una prova di tracking difettoso e non vanno usati per ranking, esclusioni o segnali Sniper.

**Ulteriore limite:** il confronto ETP su Borsa Italiana vs azione USA resta disallineato per orario di chiusura; gli scostamenti concentrati nei giorni di forte volatilità (ad esempio 8–10 aprile 2025) richiedono NAV ufficiali e timestamp coerenti.

**Decisioni operative:**
1. Non rettificare né mediare prezzi Yahoo; conservare la serie grezza.
2. Segmentare le serie per ISIN, con data di ultima seduta vecchio ISIN e prima seduta nuovo ISIN.
3. Acquisire NAV/prezzi ufficiali emittente per ogni segmento e verificare i due rapporti ancora incompleti (3SMI, 3SNI).
4. Ripetere la correlazione solo su rendimenti NAV allineati e, separatamente, riportare l'audit close-to-close di mercato.

Fonti ufficiali e avvisi: Leverage Shares (SNV3, 3NIO, TSLQ, SBA3) e GraniteShares/RNS (3SMI, 3SNF, 3SPA, 3STS, 3LMO, 3LAM, 3SNI). I collegamenti puntuali sono registrati nel campo `known_history_events[].source` di `data/underlying_mapping.json`.
