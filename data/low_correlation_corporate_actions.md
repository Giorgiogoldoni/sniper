# Sniper — Fase 1: riconciliazione dei 12 ETP con correlazione inferiore a 0,20

Data verifica: 21 novembre 2026.

## Conclusione
Tutti i 12 strumenti hanno un consolidamento/cambio ISIN documentato nel periodo del test. Il confronto Yahoo concatenato pre/post ISIN è contaminato da discontinuità. Dieci rapporti sono verificati; due restano da confermare (3SMI e 3SNI). Nessun prezzo è stato corretto e nessun ETP è stato escluso.

| ETP | Consolidamento | Rapporto | ISIN vecchio | ISIN nuovo | Stato |
|---|---|---:|---|---|---|
| SNV3 | 03/12/2024 | 246:1 | XS2706225427 | XS2944874416 | verificato |
| 3SMI | 19/05/2025 | n.d. | XS2836637525 | XS3069873134 | rapporto da confermare |
| 3SNF | 02/06/2025 | 50:1 | XS2675292135 | XS3075487986 | verificato |
| 3SPA | 19/05/2025 | 6.000:1 | XS2836484787 | XS3069876582 | verificato |
| SMCI | 30/12/2024 | 46:1 | XS2779863021 | XS2944889109 | verificato |
| TSLQ | 20/08/2025 | 606:1 | XS2706232803 | XS3135031279 | verificato |
| 3STS | 02/06/2025 | 150:1 | XS2656471039 | XS3075487556 | verificato |
| 3LMO | 19/05/2025 | 5.000:1 | XS2613356620 | XS3069877556 | verificato |
| 3NIO | 07/02/2025 | 641:1 | XS2663694417 | XS2970736489 | verificato |
| 3LAM | 02/06/2025 | 200:1 | XS2377112110 | XS3075487713 | verificato |
| 3SNI | 19/05/2025 | n.d. | XS2626290311 | XS3069879768 | rapporto da confermare |
| SBA3 | 07/04/2025 | 329:1 | XS2472334585 | XS3037640110 | verificato |

## Regole
- Non applicare fattori di rettifica ai prezzi Yahoo.
- Non concatenare segmenti ISIN senza prova della continuità NAV.
- Conservare raw market price, NAV ufficiale e serie ricostruita in campi separati.
- I rapporti mancanti non si stimano dal salto osservato.
- Correlazioni originarie non utilizzabili per ranking o segnali operativi.

## Prossimo lavoro
Acquisire NAV e prezzi ufficiali emittente per i segmenti ISIN, verificare i rapporti 3SMI/3SNI e costruire test distinti: NAV close-to-close allineato e prezzo di mercato close-to-close.