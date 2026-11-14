"""Test sul passato, a pezzi: salva dopo ogni titolo/orizzonte e si ferma da solo quando finisce il tempo.
Il giro dopo riparte da dove si era fermato (rifà solo le prove più vecchie di 6 giorni)."""
import os
import time
from datetime import datetime, timedelta, timezone

from .common import DATA, STATE, config, log, now_iso, read_json, write_json
from . import forecast as F
from . import prices as P
from . import track


def main():
    cfg = config()
    budget = float(os.environ.get("BUDGET_MIN", "150")) * 60
    t0 = time.time()
    bt = read_json(STATE / "backtest.json", default={})
    vecchio = (datetime.now(timezone.utc) - timedelta(days=6)).isoformat()
    da_fare = [(t, o) for t in cfg["titoli"] for o in P.ORIZZONTI
               if (bt.get(t["id"], {}).get(o, {}).get("fatto") or "") < vecchio]
    if not da_fare:
        log("Backtest già aggiornato.")
        return
    predictor = F.carica_kronos(cfg.get("modello", "NeoQuasar/Kronos-small"))
    for t, o in da_fare:
        if time.time() - t0 > budget:
            log("Tempo finito: riprendo al prossimo giro.")
            break
        df = P.scarica_orizzonte(t["yahoo"], o)
        if df is None:
            continue
        log(f"backtest {t['id']} {o}…")
        g = F.giudizio(F.backtest(predictor, df, P.ORIZZONTI[o]["pred_len"], n_finestre=cfg.get("finestre_backtest", 30)))
        g["fatto"] = now_iso()
        bt.setdefault(t["id"], {})[o] = g
        write_json(STATE / "backtest.json", bt)
        write_json(DATA / "backtest.json", {"aggiornato": now_iso(), "titoli": bt})
        log(f"   {g['verdetto']} ({g.get('dir_ok')}% su {g['prove']})")
        write_json(DATA / "pagella.json", {"aggiornato": now_iso(), **track.pagella(track.carica(), bt)})


if __name__ == "__main__":
    main()
