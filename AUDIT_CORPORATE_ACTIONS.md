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


## Verifica GraniteShares — approfondimento 21 novembre 2026

Sono state reperite comunicazioni dell'emittente per ulteriori strumenti che compaiono nell'audit prezzi. La presenza dell'operazione è documentata; il suo collegamento al salto Yahoo è classificato separatamente.

| Ticker | Data salto segnalato | Operazione dell'emittente | Confronto e giudizio |
|---|---:|---|---|
| 3LAA.MI | 01/07/2024 | Consolidamento 250:1; record date 28/06/2024; nuovo ISIN XS2842095320 dal 01/07/2024 | **Corrispondenza forte**: data esatta; rapporto atteso compatibile con il salto circa 248x, da verificare sui prezzi ufficiali di chiusura |
| 3LAM.MI | 02/06/2025 | Consolidamento; cambio ISIN XS2377112110 → XS3075487713; prima negoziazione consolidata 02/06/2025 | **Corrispondenza temporale diretta**. Il rapporto di consolidamento non è riportato nell'estratto consultato; non applicare un fattore finché non si recupera il dettaglio completo |
| 3LFB.MI | 16/08/2023 nell'audit | Consolidamento 30:1; record date 11/08/2023; prima negoziazione 14/08/2023; cambio ISIN XS2193971350 → XS2656469561 | **Corrispondenza molto forte**: il primo giorno consolidato precede di due sedute la data massima segnalata; verificare il calendario della quotazione e il mapping Yahoo |
| 3LSQ.MI | 21/03/2023 | Consolidamento 500:1; record date 17/03/2023; prima negoziazione 20/03/2023; cambio ISIN XS2376992207 → XS2596085972 | **Corrispondenza temporale forte, fattore non perfettamente riconciliato**: il salto Yahoo riportato è circa 655x, diverso da 500x; non correggere automaticamente |
| 3LCO.MI | 31/01/2023 | Avviso di consolidamento 20.000:1 efficace 16/01/2023 per ISIN XS2377112896; la quotazione LSE/nuovo ISIN XS2575914176 risulta emessa il 30/01/2023 | **Non riconciliato**: il salto Yahoo del 31/01 non è spiegato dal solo rapporto 20.000:1 sulla base dei dati attuali; probabile discontinuità di identificativo/serie, da ricostruire con le due catene ISIN e la quotazione Borsa Italiana |

Fonti documentali:
- 3LAA, comunicazione RNS dell'emittente: https://www.investegate.co.uk/index.php/announcement/rns/graniteshares-financial-plc--3laa/granite-3x-long-baba-reverse-split-01jul24/8261673
- 3LAM, comunicazione RNS dell'emittente: https://www.investegate.co.uk/announcement/rns/graniteshares-financial-plc--3lam/granite-3x-long-amd-reverse-split-02june25/8885592
- 3LFB, avviso ufficiale GraniteShares: https://graniteshares.com/media/14fpce1z/3lfb-1st-security-holder-notice-consolidation-lse.pdf
- 3LSQ, avviso ufficiale GraniteShares: https://graniteshares.com/media/v40alc4t/3lsq-1st-security-holder-notice-consolidation.pdf
- 3LCO, avviso RNS 20.000:1: https://www.advfn.com/stock-market/london/LCO3/stock-news/89881034/graniteshares-financial-plc-3lco-reverse-split-1
- 3LCO, dati identificativi e data emissione ISIN XS2575914176: https://www.londonstockexchange.com/stock/3LCO/graniteshares/company-page
- 3LCO, factsheet GraniteShares con listing Borsa Italiana, ticker e ISIN: https://graniteshares.com/media/hyukmzpr/factsheet_graniteshares-3x-long-coinbase-daily-etp_en.pdf

### Controllo di coerenza anagrafica da fare

L'audit dell'universo Sniper riporta 3LAM come Amazon, mentre la documentazione ufficiale GraniteShares identifica 3LAM come **3x Long AMD** (ISIN XS2377112110). L'Elenco prodotti italiano dell'emittente associa invece Amazon a 3LZN e AMD a 3LAM. Questo è un problema di anagrafica/mapping da correggere dopo controllo del record in `data/instrument_universe.json`; non va confuso con la qualità dei prezzi. La documentazione dell'emittente: https://graniteshares.com/media/p1mcbnhy/italian-product-list.pdf e https://www.investegate.co.uk/announcement/rns/graniteshares-financial-plc--3lam/granite-3x-long-amd-reverse-split-02june25/8885592

### Conclusione di questo approfondimento

- Nuove operazioni societarie documentate: 3LAA, 3LAM, 3LFB, 3LSQ e 3LCO.
- 3LAA e 3LAM hanno una corrispondenza di data diretta con l'anomalia; 3LFB e 3LSQ hanno corrispondenza vicina con differenze da riconciliare; 3LCO resta non riconciliato per il cambio/riemissione ISIN.
- Nessun fattore è stato applicato ai prezzi; non sono state fatte interpolazioni o medie.
- Non è stata ottenuta una serie storica indipendente completa per questi strumenti; i casi restano in audit e i backtest non vengono rigenerati.


### Esito del controllo anagrafico 3LAM

Il controllo diretto di `data/instrument_universe.json` ha confermato che il nome associato a `3LAM.MI` era errato: riportava GraniteShares 3x Amazon. È stato corretto in **GraniteShares 3x Long AMD Daily ETP**, coerentemente con l'ISIN XS2377112110 e con l'avviso dell'emittente. Amazon resta correttamente associato a 3LZN. Modifica anagrafica eseguita nel commit `74eb03899520ae2460e0652730b14c89e24d6c37`. Nessun ticker o prezzo è stato rimosso o alterato.


## Verifica aggiuntiva GraniteShares — 21 novembre 2026 (secondo lotto)

| Ticker | Evento massimo Yahoo | Operazione documentata | Valutazione |
|---|---:|---|---|
| 3SAA.MI | 02/07/2024; 0,2745 → 27,96 (circa 102x) | Consolidamento 100:1; record date 28/06/2024; prima seduta consolidata 01/07/2024; ISIN XS2435550194 → XS2842095759 | **Corrispondenza molto forte**: prezzo circa 100x e data Yahoo un giorno dopo la prima seduta consolidata. Verificare il fixing ufficiale della quotazione italiana prima della ricostruzione. |
| 3SAP.MI | 23/08/2023; 0,1105 → 23,65 (circa 214x) | Consolidamento 250:1; record date 18/08/2023; prima seduta consolidata 21/08/2023; ISIN XS2193970030 → XS2662641195 | **Operazione confermata, salto non perfettamente riconciliato**: evento Yahoo due giorni dopo e rapporto osservato circa 214x anziché 250x. Non applicare il fattore senza verificare prezzi e identificativo della linea EUR. |
| 3SSQ.MI | 19/06/2024; 1,65 → 26,465 (circa 16x) | Consolidamento annunciato per il 17/06/2024; ISIN XS2376991738 → XS2836701123. Una fonte secondaria riporta 1.600:1 | **Non riconciliato**: il rapporto osservato è incompatibile con 1.600:1. La notizia conferma il cambio ISIN, ma non autorizza a correggere questa serie. Recuperare l'avviso completo e i dati ufficiali della linea italiana. |
| 3LTS.MI | 16/08/2023; 3,01 → 12,948 (circa 4,3x) | Una fonte comunitaria riporta consolidamento 5:1 con prima negoziazione 14/08/2023; ISIN nuovo XS2656472193, issue date 14/08/2023 | **Indizio, non prova primaria sufficiente**: data vicina e rapporto approssimativo, ma occorre il notice ufficiale dell'emittente e la verifica del vecchio ISIN. |

Fonti:
- 3SAA, avviso ufficiale GraniteShares: https://graniteshares.com/media/efkhaydy/3saa-1st-security-holder-notice-consolidation-bi.pdf
- 3SAP, avviso RNS: https://www.lse.co.uk/rns/granite-3sap3swp3lae-reverse-split-21aug23-hzyxcz3dnm714z6.html
- 3SSQ, avviso RNS: https://www.investegate.info/announcement/rns/graniteshares-financial-plc--3ssq/granite-3x-short-sq-reverse-split-17jun24/8236968
- 3SSQ, rapporto 1.600:1 riportato da fonte secondaria: https://etfworld.co.uk/graniteshares-etp-consolidation-reverse-split-for-3-etps/
- 3LTS, riferimento secondario al consolidamento 5:1: https://community.trading212.com/t/corporate-events-in-august-2023/63735/10
- 3LTS, pagina London Stock Exchange con ISIN XS2656472193 e issue date 14/08/2023: https://www.londonstockexchange.com/stock/3LTS/graniteshares/company-page

### Regola applicata
Questi casi sono stati aggiunti all'audit documentale, non al motore di rettifica. **Nessun prezzo è stato cambiato**: per una correzione automatica serve la riconciliazione completa tra vecchio e nuovo ISIN, rapporto, linea di negoziazione e prezzi ufficiali pre/post evento. Le differenze fra prezzo osservato e rapporto dichiarato non vengono colmate con medie, interpolazioni o fattori stimati.


## Verifiche aggiuntive — casi ad altissimo salto

| Ticker | Evento Yahoo | Operazione documentata | Rapporto osservato | Esito |
|---|---:|---|---:|---|
| 3NIO.MI | 10/02/2025; 0,076 → 49,875 | Leverage Shares 3x Long NIO: consolidamento 641:1; record date 06/02/2025; prima seduta consolidata 07/02/2025; ISIN XS2663694417 → XS2970736489; la notifica include esplicitamente la linea Borsa Italiana 3NIO IM | circa 656:1 | **Corrispondenza molto forte**: salto Yahoo tre giorni dopo l'efficacia, rapporto osservato vicino a 641:1 e identificazione della linea italiana esplicita. Resta da controllare il prezzo ufficiale di chiusura e il calendario della linea. |
| 3LMO.MI | 19/05/2025; 0,0036 → 20,17 | GraniteShares 3x Long Moderna: consolidamento 5.000:1; record date 16/05/2025; prima seduta consolidata 19/05/2025; ISIN XS2613356620 → XS3069877556 | circa 5.603:1 | **Corrispondenza temporale diretta e rapporto compatibile come ordine di grandezza**, ma scarto del 12% circa da riconciliare con prezzi ufficiali/linea EUR. Non applicare ancora il fattore. |
| 3LMI.MI | 19/05/2023; 0,0133 → 24,305 | Consolidamento 2.000:1 del 15/05/2023 riportato per GraniteShares 3x Long MicroStrategy | circa 1.827:1 | **Operazione documentata, rapporto/data non perfettamente riconciliati**: evento Yahoo quattro giorni dopo; serve catena ISIN e verifica prezzi. |

Fonti:
- Leverage Shares, avviso ufficiale consolidamento 3x Long NIO 641:1, con ISIN e linee di negoziazione: https://leverageshares.com/documents/notices/30.01.2025-notice-of-consolidation-3x-long-nio-etp.pdf
- RNS Leverage Shares 3x NIO: https://www.investegate.co.uk/announcement/rns/leverage-shares-public-limited-company--3nie/3x-nio-consolidation-notice/8714551
- Borsa Italiana, 3NIO Leverage Shares, ISIN XS2970736489: https://www.borsaitaliana.it/borsa/etc-etn/scheda/XS2970736489-ETFP.html?lang=it
- GraniteShares 3LMO, avviso RNS con rapporto 5.000:1 e cambio ISIN: https://shareprices.com/rns/granite-3x-long-mrna-reverse-split-19-may-25-kigbex5kdxnsd7l/
- 3LMI, riferimento al rapporto 2.000:1 del 15/05/2023: https://divvydiary.com/en/graniteshares-3x-long-microstrategy-daily-etp-etf-XS2617255760

### Correzione di classificazione dell'emittente
Il ticker **3NIO.MI è Leverage Shares**, non GraniteShares. Il master data/instrument_universe.json riporta già correttamente il provider Leverage Shares; questa verifica conferma che l'audit deve mantenere distinti emittente, ticker e linea di negoziazione. Non è stata necessaria alcuna modifica all'anagrafica.
