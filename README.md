# Radar Mercato

App personale per seguire i propri titoli con:

- **Previsioni a scenari** con [Kronos](https://github.com/shiyu-coder/Kronos) su ore, giorni e settimane, più uno scenario statistico a 1 anno.
- **Notizie solo da fonti verificate**, su 3 livelli: fonti ufficiali (SEC, siti delle aziende e dei progetti), grandi agenzie (Reuters, Bloomberg, AP…), balene (acquisti e vendite dei manager, quote sopra il 5%). Social e forum sono esclusi.
- **Campanelli** di salita/discesa quando molte notizie forti vanno nella stessa direzione.
- **Radar occasioni** stile GameStop 2021: idee da studiare, non consigli.
- **Pagella**: ogni previsione viene confrontata con il prezzo reale. Se un titolo non batte il caso, lo dice.

> ⚠️ Non è un consulente finanziario. Nessun modello prevede il mercato con certezza. L'app non compra e non vende nulla.

## Come si usa (in locale sul Mac)

```bash
cd ~/Desktop/radar
./radar.sh setup        # una volta sola
./radar.sh tutto        # notizie + previsioni
./radar.sh servi        # apre l'app su http://localhost:8000
```

Tutti i comandi: `./radar.sh`. Istruzioni per gli agenti AI: `AGENTS.md`.

Gli avvii automatici su GitHub Actions sono disattivati; i workflow restano avviabili a mano come riserva.

## Personalizzare

Tutto si regola in **`config.yaml`**: titoli seguiti, modello Kronos, numero di scenari, fonti ammesse e soglie del radar.

## Avvisi su Telegram (facoltativi)

1. Su Telegram scrivi a **@BotFather** → `/newbot` → copia il *token*.
2. Scrivi un messaggio al tuo nuovo bot, poi apri `https://api.telegram.org/bot<TOKEN>/getUpdates` e copia il numero `chat.id`.
3. In locale: crea il file `.env` nella cartella con `TELEGRAM_TOKEN=...` e `TELEGRAM_CHAT_ID=...` (non viene caricato su GitHub).

## Sviluppo

```bash
pip install -r requirements.txt pytest
python -m pytest -q          # test senza rete
python -m pipeline.run_news  # notizie
./radar.sh previsioni --solo BTC
```
