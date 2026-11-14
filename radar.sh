#!/usr/bin/env bash
# ============================================================
#  RADAR MERCATO — comandi locali (Mac)
#  Uso:  ./radar.sh <comando>
#
#    setup       prepara tutto (una volta sola): Python, librerie, Kronos
#    notizie     aggiorna prezzi, notizie, balene e campanelli   (~1-2 min)
#    occasioni   come "notizie" + radar occasioni stile GameStop  (~5 min)
#    previsioni  previsioni Kronos per tutti i titoli             (~10-30 min)
#    backtest    test sul passato, a pezzi (max BUDGET_MIN minuti, default 150)
#    tutto       notizie + previsioni
#    servi       apre l'app su http://localhost:8000
#    pubblica    salva su GitHub e aggiorna la versione online (facoltativo)
#    test        test automatici senza rete
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"
VENV=".venv"
PY="$VENV/bin/python"
mkdir -p logs
[ -f .env ] && { set -a; . ./.env; set +a; }   # segreti facoltativi (es. Telegram), mai su GitHub
export APP_URL="${APP_URL:-http://localhost:8000/}"

need_setup() {
  if [ ! -x "$PY" ]; then echo "Prima esegui: ./radar.sh setup"; exit 1; fi
}

log_run() {  # esegue e salva il log in logs/
  local nome="$1"; shift
  local f="logs/$(date +%Y%m%d-%H%M)-$nome.log"
  echo "→ $nome (log: $f)"
  "$@" 2>&1 | tee "$f"
}

case "${1:-aiuto}" in
  setup)
    if ! command -v python3 >/dev/null; then
      echo "Serve Python 3.10+: installalo da https://www.python.org/downloads/ e riprova."; exit 1
    fi
    python3 -c 'import sys; assert sys.version_info >= (3,10), "Serve Python 3.10 o più recente"'
    [ -d "$VENV" ] || python3 -m venv "$VENV"
    "$PY" -m pip install -q --upgrade pip
    "$PY" -m pip install -q torch                     # su Mac Apple Silicon include l'accelerazione MPS
    "$PY" -m pip install -q -r requirements.txt transformers pytest
    [ -d Kronos ] || git clone -q --depth 1 https://github.com/shiyu-coder/Kronos.git Kronos
    "$PY" -c 'import torch; print("Accelerazione Apple (MPS):", "sì" if torch.backends.mps.is_available() else "no")'
    echo "✅ Pronto. Prova: ./radar.sh tutto && ./radar.sh servi"
    ;;
  notizie)    need_setup; log_run notizie    "$PY" -m pipeline.run_news ;;
  occasioni)  need_setup; log_run occasioni  "$PY" -m pipeline.run_news --occasioni ;;
  previsioni) need_setup; log_run previsioni "$PY" -m pipeline.run_forecast "${@:2}" ;;
  backtest)   need_setup; log_run backtest   "$PY" -m pipeline.run_backtest ;;
  tutto)      need_setup; "$0" notizie; "$0" previsioni ;;
  test)       need_setup; "$PY" -m pytest -q ;;
  servi)
    PORTA="${PORTA:-8000}"
    echo "App su http://localhost:$PORTA  (Ctrl+C per fermare)"
    (sleep 1; open "http://localhost:$PORTA" 2>/dev/null || true) &
    python3 -m http.server "$PORTA" --directory site --bind 127.0.0.1
    ;;
  pubblica)
    git add site/data state
    git diff --cached --quiet && { echo "Niente di nuovo da pubblicare."; exit 0; }
    git commit -qm "Dati aggiornati in locale"
    git pull -q --rebase origin main && git push -q
    echo "✅ Pubblicato: https://stabiledanilo90-coder.github.io/radar-mercato/"
    ;;
  *)
    sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
    ;;
esac
