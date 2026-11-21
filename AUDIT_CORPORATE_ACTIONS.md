# Audit corporate actions — anomalie prezzi storici

**Data verifica:** 21 novembre 2026  
**Universo:** 60 strumenti segnalati in `data/backtest_exclusion_audit.json`  
**Scopo:** distinguere volatilità reale, consolidamenti/reverse split e discontinuità delle serie Yahoo.

## Esito preliminare

Sono state reperite comunicazioni dell'emittente o avvisi regolamentari che documentano consolidamenti per **13 ticker** tra quelli segnalati. In questi casi il salto storico non va interpretato come rendimento di mercato: il numero di titoli posseduti viene ridotto e il prezzo unitario aumenta proporzionalmente.

Questo non dimostra che l'intera serie Yahoo sia corretta dopo aver individuato l'operazione. In diversi casi il rapporto tra i due prezzi riportati dall'audit non coincide con il rapporto di consolidamento: possono esserci più operazioni, cambi di ISIN/ticker o ulteriori difetti di continuità. **Non applicare una correzione automatica basata soltanto sul rapporto dichiarato.**

## Operazioni documentate

| Ticker Yahoo | Data evento nell'audit | Operazione documentata | Rapporto | Valutazione |
|---|---:|---|---:|---|
| 3SMI.MI | 17/06/2024 | Consolidamento GraniteShares, primo giorno di negoziazione dei titoli consolidati 17/06/2024; esiste anche un precedente consolidamento il 19/06/2023 | 35.000:1 nel 2024; 100.000:1 nel 2023 | Corporate action confermata; ricostruire entrambe le transizioni ISIN |
| 3SPA.MI | 18/06/2024 | Consolidamento GraniteShares, primo giorno di negoziazione 17/06/2024 | 8.500:1 | Corporate action confermata; data audit a un giorno di distanza |
| 3STS.MI | 16/08/2023 | Consolidamento GraniteShares, primo giorno di negoziazione 14/08/2023 | 400:1 | Corporate action confermata; data audit a due sedute di distanza |
| 3SNV.MI | 02/05/2023 | Consolidamento GraniteShares, primo giorno di negoziazione 02/05/2023; ulteriore consolidamento dal 01/07/2024 | 25.000:1 nel 2023; 600:1 nel 2024 | Corporate action confermata; ricostruire entrambe le transizioni |
| 3LMI.MI | 19/05/2023 | Consolidamento GraniteShares, primo giorno di negoziazione 15/05/2023 | 2.000:1 | Corporate action confermata; verificare il disallineamento di data |
| 3LMO.MI | 19/05/2025 | Consolidamento GraniteShares, primo giorno di negoziazione 19/05/2025 | 5.000:1 | Corporate action confermata |
| 3SIS.MI | 20/04/2026 | Consolidamento WisdomTree, efficace e negoziazione dei titoli consolidati dal 20/04/2026 | 3.800:1 | Corporate action confermata |
| 3BRS.MI | 21/04/2026 | Consolidamento WisdomTree, efficace dal 20/04/2026 | 650:1 | Corporate action confermata; data audit a una seduta di distanza |
| 3HCS.MI | 20/04/2026 | Consolidamento WisdomTree, efficace e negoziazione dei titoli consolidati dal 20/04/2026 | 30:1 | Corporate action confermata; il salto Yahoo è circa 30 volte |
| SQQQ.MI | 11/06/2026 | Consolidamento Leverage Shares, primo giorno di negoziazione 11/06/2026 | 681:1 | Corporate action confermata |

| 3EUL.MI | 11/05/2026 | Split WisdomTree, primo giorno di negoziazione 11/05/2026 | 25:1 | Split confermato; il prezzo unitario viene diviso per 25 |
| 3DEL.MI | 11/05/2026 | Split WisdomTree, primo giorno di negoziazione 11/05/2026 | 20:1 | Split confermato; il prezzo unitario viene diviso per 20 |
| 3UKL.L | 11/05/2026 | Split WisdomTree, primo giorno di negoziazione 11/05/2026 | 20:1 | Split confermato; il prezzo unitario viene diviso per 20 |

## Fonti primarie e avvisi regolamentari

- 3SMI, consolidamento 35.000:1 del 17/06/2024: https://graniteshares.com/media/vicngzc3/3smi-1st-security-holder-notice-of-consolidation-lse.pdf
- 3SMI, precedente consolidamento 100.000:1 del 19/06/2023: https://www.lse.co.uk/rns/granite-3xs-microstrategy-reverse-split-19-june-wt3tyefv2ia4jxt.html
- 3SPA, consolidamento 8.500:1: https://www.investegate.co.uk/announcement/rns/graniteshares-financial-plc--3spa/granite-3x-short-pltr-reverse-split-17jun24/8236970
- 3STS, consolidamento 400:1: https://www.lse.co.uk/rns/3STE/granite-3sts3stp3ste-reverse-split-14aug23-0dbzmdahwz0z6fo.html
- 3SNV, consolidamento 25.000:1: https://shareprices.com/rns/granite-3x-short-nvidia-reverse-split-02-may-tqpuii9bhmsatfw/
- 3SNV, successivo consolidamento 600:1: https://graniteshares.com/media/f4wpdmlc/3snv-1st-security-holder-notice-consolidation-bi.pdf
- 3LMI, consolidamento 2.000:1: https://www.lse.co.uk/rns/graniteshares-3l-microstrategy-rev-split-15-may-pz3a5o8crfiit9f.html
- 3LMO, consolidamento 5.000:1: https://shareprices.com/rns/granite-3x-long-mrna-reverse-split-19-may-25-kigbex5kdxnsd7l/
- 3SIS e 3BRS, consolidamenti WisdomTree: https://www.wisdomtree.com/it/important-notices/2026/q2/consolidations-of-certain-classes-of-wtma-etp-securities
- Rapporti e ISIN WisdomTree (3SIS 3.800:1; 3BRS 650:1): https://www.globenewswire.com/fr/news-release/2026/04/02/3267139/0/en/Programme-for-the-issuance-of-Collateralised-ETP-Securities.html
- SQQQ, consolidamento 681:1: https://leverageshares.com/documents/notices/Consolidation-Notice_-5x-Nasdaq-04-June-2026.pdf
- 3EUL, 3DEL e 3UKL, split WisdomTree con rapporti 25:1, 20:1 e 20:1: https://www.wisdomtree.com/gb/media/advance-notice-wtmai-plc-announcement-splits-23-april-2026

## Caso da non classificare ancora

- **SOXS.MI:** è stato trovato un avviso Leverage Shares per un consolidamento 104:1 con prima negoziazione dei titoli consolidati il 18/12/2025. L'evento massimo nell'audit Yahoo è invece datato 11/12/2025. La vicinanza temporale non basta a collegare i due fatti: resta da verificare la serie e la transizione ISIN. Fonte: https://www.lse.co.uk/rns/-4x-semiconductors-consolidation-notice-klpf42hta1bykke.html

## Limiti del confronto con Twelve Data gratuito

Il piano Basic ufficiale dichiara 8 crediti/minuto e 800/giorno, ma la copertura EOD globale non è inclusa come copertura generalizzata del piano gratuito. La documentazione EOD segnala inoltre **Borsa Italiana (MIC MTAA)** tra i mercati che richiedono licenza o non sono supportati. Quindi Twelve Data Basic non è, allo stato attuale, una seconda fonte gratuita affidabile per verificare in blocco i ticker italiani `.MI`.

Fonti:
- https://twelvedata.com/pricing
- https://support.twelvedata.com/en/articles/12682324-end-of-day-eod-pricing-market-data

## Regole operative per Sniper

1. Conservare tutti i 310 strumenti nell'universo.
2. Non fare medie tra prezzi di provider discordanti.
3. Non correggere prezzi con un fattore automatico prima di aver ricostruito la catena ISIN e tutte le corporate actions.
4. Conservare separatamente prezzi raw, prezzi aggiustati e serie ricostruite.
5. Per ogni correzione registrare fonte, ISIN vecchio/nuovo, data record, ultima seduta vecchio ISIN, prima seduta nuovo ISIN e rapporto.
6. Fino alla verifica, mettere in quarantena **solo la porzione di serie storica non affidabile** per le statistiche del backtest; non eliminare il prodotto dall'universo operativo.
7. Dopo la ricostruzione, confrontare i rendimenti giornalieri e rigenerare i backtest.

**Stato:** indagine documentale preliminare. Nessun prezzo è stato modificato e nessun backtest è stato rigenerato.


## Integrazione della verifica — 21 novembre 2026

### Ulteriori operazioni documentate e confronto con le date anomale

| Ticker | Data evento nell'audit | Operazione documentata | Esito del collegamento |
|---|---:|---|---|
| 3ITS.MI | 22/07/2024 | WisdomTree: consolidamento; negoziazione dei titoli consolidati iniziata il 22/07/2024 | **Corrispondenza temporale diretta**: il salto dell'audit coincide con la data di efficacia |
| VIXL.MI | 05/08/2024 | WisdomTree: consolidamento efficace 22/07/2024 | **Non corrisponde**: l'evento massimo dell'audit è successivo di circa due settimane; il consolidamento è documentato ma non spiega da solo quel salto |
| SNV3.MI | 07/11/2023 | Leverage Shares: consolidamento 457:1, primo giorno di negoziazione con nuovo ISIN 03/11/2023 | **Corrispondenza non conclusiva**: evento Yahoo quattro giorni dopo; occorre verificare ticker/ISIN e prezzi giornalieri intermedi |
| SOXS.MI | 11/12/2025 | Leverage Shares: consolidamento 104:1, primo giorno di negoziazione 18/12/2025 | **Non corrisponde**: il salto segnalato precede la prima seduta consolidata di una settimana; non va attribuito automaticamente a questa operazione |

Fonti primarie:
- WisdomTree, operazioni efficaci 22/07/2024 (3ITS e VIXL): https://www.wisdomtree.com/it/important-notices/2024/q3/splits-and-consolidations-of-certain-classes-of-wtma-etp-securities-effected
- Leverage Shares, consolidamento 457:1 del -3x Short NVIDIA, efficace 03/11/2023: https://www.investegate.co.uk/announcement/rns/leverage-shares-public-limited-company--sxee/leverage-shares-consolidation-notice-update/7833971
- Leverage Shares, consolidamento SOXS 104:1, prima negoziazione 18/12/2025: https://leverageshares.com/documents/notices/consolidation-notice_-4x-semiconductors-10-december-2025.pdf

### Avvertenza sulla classificazione

La presenza di un'operazione societaria per un ticker non prova che ogni salto anomalo della sua serie sia spiegato da quella sola operazione. In particolare, quando data o rapporto non coincidono, la serie resta non risolta. Anche una corrispondenza esatta della data è una prova forte dell'origine societaria del salto, ma prima di correggere i prezzi occorre controllare ISIN, rapporto, prezzi pre/post e valuta della specifica quotazione italiana.

### Stato aggiornato del lavoro

- 13 ticker già elencati nella prima sezione con corporate action documentata.
- 3ITS aggiunto come corrispondenza temporale diretta; VIXL ha un'operazione documentata ma non coincidente con la data del salto massimo.
- SNV3 e SOXS restano casi con operazione documentata ma collegamento al salto Yahoo non dimostrato.
- Non è stata ottenuta una serie EOD gratuita, indipendente e completa per i ticker .MI; Twelve Data Basic non copre in modo generalizzato Borsa Italiana.
- Nessun prezzo corretto o interpolato; nessun backtest rigenerato. I casi non risolti restano da verificare, non vengono cancellati dall'universo.


### Altra corrispondenza verificata

| Ticker | Data evento nell'audit | Operazione documentata | Esito |
|---|---:|---|---|
| SBA3.MI | 07/04/2025 | Leverage Shares -3x Short Alibaba: consolidamento 329:1; ultima seduta vecchio ISIN 04/04/2025, prima seduta nuovo ISIN 07/04/2025 | **Corrispondenza diretta**: data e quotazione italiana SBA3 IM incluse nell'avviso dell'emittente |

Fonte primaria: https://leverageshares.com/documents/notices/28.03.2025-notice-result-of-adjourned-meeting-3x-short-baba.pdf

Questo porta a due ulteriori corrispondenze temporali dirette emerse nell'integrazione (3ITS e SBA3), oltre ai casi già elencati nella prima versione. I casi con sola coincidenza temporale o con date non allineate non vengono conteggiati come confermati.
