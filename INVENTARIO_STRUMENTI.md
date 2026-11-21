# Sniper — inventario strumenti specializzati

Aggiornamento sorgenti: 20 novembre 2026. Inventario generato da archivi GitHub; non equivale a una verifica di negoziabilità o disponibilità presso il broker.

## Totale deduplicato

**310 strumenti**, deduplicati sul simbolo Yahoo Finance completo.

| Classe | Numero |
|---|---:|
| LEVA_LONG | 73 |
| LEVA_SHORT | 86 |
| MATERIE_PRIME_1X | 108 |
| MATERIE_PRIME_LEVA | 26 |
| MATERIE_PRIME_SHORT | 17 |
| **Totale** | **310** |

## Sorgenti e controlli

| Fonte | Record esaminati / candidati |
|---|---:|
| Scanner universe — leva, short e materie prime | 76 |
| Raptor One — categoria Materie | 77 |
| Raptor Leva — record validi | 342 |
| Raptor Leva — candidati leva/short/materie prime | 244 |
| Chart — candidati commodity in attesa di mapping borsa | 43 |

## Regole

- Leva long e short sono mantenute in classi separate.
- Materie prime 1x, a leva e short sono separate.
- Sono conservati ticker e simbolo Yahoo completo per evitare fusioni errate fra borse.
- Il file JSON contiene fonti e metadati per ogni strumento.
- I candidati Chart non sono stati aggiunti al totale perché il simbolo di borsa non è ancora verificato.
- Min Finder resta una fonte di controllo, non primaria, per i numerosi campi mancanti.

## Limiti

Il conteggio è un inventario tecnico dei feed, non una certificazione legale della natura ETF/ETC/ETN né una verifica di quotazione attiva. Prima di automatizzare l'universo operativo vanno controllati ISIN, emittente, leva dichiarata, liquidità e stato del prodotto.
