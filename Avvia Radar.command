#!/usr/bin/env bash
# Doppio clic per aprire Radar Mercato.
# Se l'app è già aperta, apre solo il browser. Altrimenti aggiorna le notizie e la avvia.
cd "$(dirname "$0")"
PORTA=8000
if curl -s -o /dev/null "http://localhost:$PORTA"; then
  open "http://localhost:$PORTA"
  exit 0
fi
echo "Aggiorno prezzi e notizie (circa mezzo minuto)…"
./radar.sh notizie >/dev/null 2>&1 || echo "Aggiornamento non riuscito: apro l'app con i dati che ci sono."
echo ""
echo "Radar Mercato è aperto nel browser. Per chiuderlo: chiudi questa finestra."
./radar.sh servi
