# Istruzioni per agenti (Claude Code, Claude, Codex, ecc.)

Leggi tutto prima di toccare il progetto.

## Dove si lavora
- **Cartella di lavoro: `~/Desktop/radar` sul Mac di Danilo** (Apple Silicon M4, macOS). È un clone di
  `github.com/stabiledanilo90-coder/radar-mercato`. Si lavora QUI.
- **Python si esegue in locale su questo Mac**, sempre tramite `./radar.sh` (usa l'ambiente `.venv`).
  Kronos gira sull'accelerazione Apple (MPS) quando disponibile.
- **I runner di GitHub Actions NON si usano più**: gli avvii automatici sono disattivati e non vanno
  riattivati senza che Danilo lo chieda. I workflow restano solo come riserva manuale.
- **L'app si apre in locale** con `./radar.sh servi` → http://localhost:8000.
  La versione online su GitHub Pages si aggiorna solo se Danilo lo chiede (`./radar.sh pubblica`).
- Se lavori da una macchina virtuale/sandbox che vede la cartella montata (es. Linux): l'ambiente `.venv`
  è del Mac e lì non funziona. Puoi modificare il codice, ma le esecuzioni vanno fatte sul Mac
  (Terminale) oppure chiedendo a Danilo di lanciare il comando.

## Comandi
| Comando | Cosa fa |
|---|---|
| `./radar.sh setup` | una volta sola: crea `.venv`, installa librerie, clona Kronos in `./Kronos` |
| `./radar.sh notizie` | prezzi, notizie verificate, balene (SEC), campanelli → `site/data/` |
| `./radar.sh occasioni` | come sopra + radar occasioni stile GameStop |
| `./radar.sh previsioni [--solo NVDA BTC]` | previsioni Kronos → `site/data/forecast/*.json`, registro, pagella |
| `./radar.sh backtest` | test sul passato a pezzi, riprende da dove si era fermato (`BUDGET_MIN`) |
| `./radar.sh tutto` | notizie + previsioni |
| `./radar.sh servi` | app su localhost:8000 |
| `./radar.sh test` | test senza rete (`tests/`) — eseguili dopo ogni modifica alla pipeline |
| `./radar.sh pubblica` | commit + push dei dati su GitHub (solo se richiesto) |

I log di ogni esecuzione finiscono in `logs/`.

## Com'è fatto
- `config.yaml` — titoli seguiti, modello Kronos, scenari, lookback, fonti ammesse, soglie del radar.
- `pipeline/` — Python: `prices.py` (Yahoo Finance), `forecast.py` (Kronos + fascia statistica + controllo
  di coerenza + backtest + scenario 1 anno), `news.py` (fonti a 3 livelli), `opportunities.py`
  (radar stile GameStop), `track.py` (registro e pagella), `alerts.py` (Telegram, facoltativo),
  `run_*.py` (punti di ingresso).
- `site/` — app web statica (HTML/CSS/JS senza librerie) che legge i JSON in `site/data/`.
- `state/` — memoria tra un giro e l'altro (registro previsioni, backtest, avvisi inviati).

## Regole che non vanno rotte
1. **Onestà prima di tutto.** Nessuno prevede il mercato con certezza. Non presentare mai una previsione
   come sicura. La pagella e il backtest devono dire chiaramente quando un modello non batte il caso.
2. **Controllo di coerenza su Kronos.** Kronos tende a "tornare alla media" della finestra (visto dal vivo:
   NVIDIA +30% in 24 ore). `forecast.controllo_coerenza` scarta queste previsioni e l'app mostra la fascia
   statistica con un avviso. Non togliere questo controllo.
3. **Fonti notizie solo verificate**: livello 1 ufficiali (SEC, siti ufficiali), livello 2 agenzie in
   `config.yaml` (indiscrezioni con fonti anonime → "da confermare"), livello 3 balene (Form 4, 13D/13G).
   **Mai social, forum, influencer.**
4. **Privacy**: il repository è pubblico. Mai salvare importi, saldo, posizioni o dati del conto eToro di
   Danilo nei file del progetto.
5. **Niente operazioni automatiche**: l'app non compra e non vende. Il radar occasioni dà idee "da studiare".
6. **Lingua**: interfaccia, messaggi e commenti in italiano semplice.

## Chi è l'utente
Danilo, non programmatore: spiegagli le cose in italiano semplice, passo per passo, senza gergo.
Investe con capitale limitato che non può reintegrare: prudenza e niente promesse.
