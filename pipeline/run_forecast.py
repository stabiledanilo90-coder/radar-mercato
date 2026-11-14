"""Esecuzione giornaliera: previsioni Kronos (ore/giorni/settimane), scenario 1 anno, anomalie,
registro e pagella. Con --backtest rifà anche le prove sul passato (una volta a settimana)."""
import argparse

from .common import DATA, STATE, config, log, now_iso, read_json, write_json
from . import forecast as F
from . import prices as P
from . import track


def eventi_in_arrivo(simbolo, giorni=14):
    import pandas as pd
    import yfinance as yf
    try:
        cal = yf.Ticker(simbolo).calendar
        date = cal.get("Earnings Date") if isinstance(cal, dict) else None
        if not date:
            return []
        d = pd.Timestamp(date[0])
        mancano = (d.normalize() - pd.Timestamp.now().normalize()).days
        if 0 <= mancano <= giorni:
            return [{"data": d.date().isoformat(), "testo": "Conti del trimestre: di solito movimenti forti", "giorni": mancano}]
    except Exception:
        pass
    return []


def main(fai_backtest=False, solo=None):
    cfg = config()
    titoli = [t for t in cfg["titoli"] if not solo or t["id"] in solo]
    predictor = F.carica_kronos(cfg.get("modello", "NeoQuasar/Kronos-small"))
    reg = track.carica()
    bt_tutti = read_json(STATE / "backtest.json", default={})
    prezzi_verifica, eventi = {}, {}
    for t in titoli:
        log(f"== {t['nome']} ({t['yahoo']})")
        out = {"id": t["id"], "nome": t["nome"], "tipo": t["tipo"], "aggiornato": now_iso(), "orizzonti": {}, "anomalie": []}
        giornaliero = None
        for o, c in P.ORIZZONTI.items():
            df = P.scarica_orizzonte(t["yahoo"], o)
            if df is None:
                continue
            if o == "giorni":
                giornaliero = df
            if o == "ore":
                prezzi_verifica[t["id"]] = df
            prev = F.previsione_json(predictor, df, c, cfg.get("scenari", 40))
            prev["storia"] = P.candele_json(df, c["mostra"])
            out["orizzonti"][o] = prev
            out["anomalie"] += F.anomalie(df, o)
            track.aggiungi(reg, t["id"], o, prev["riassunto"], prev["scadenza"])
            log(f"   {o}: mediana {prev['riassunto']['var_p50']:+.1f}%  fascia {prev['riassunto']['var_p10']:+.1f}% / {prev['riassunto']['var_p90']:+.1f}%")
        if t["id"] not in prezzi_verifica and giornaliero is not None:
            prezzi_verifica[t["id"]] = giornaliero
        if giornaliero is not None:
            anno = F.scenario_anno(giornaliero)
            if anno:
                out["orizzonti"]["anno"] = {"label": "prossimi 12 mesi", **anno}
        out["backtest"] = bt_tutti.get(t["id"], {})
        out["eventi"] = eventi_in_arrivo(t["yahoo"]) if t["tipo"] == "azione" else []
        eventi[t["id"]] = out["eventi"]
        write_json(DATA / "forecast" / f"{t['id']}.json", out)
    track.verifica(reg, prezzi_verifica)
    track.salva(reg)
    write_json(STATE / "eventi.json", eventi)
    write_json(DATA / "pagella.json", {"aggiornato": now_iso(), **track.pagella(reg, bt_tutti)})
    log("Fatto.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--backtest", action="store_true", help="(non più usato: vedi run_backtest)")
    ap.add_argument("--solo", nargs="*")
    a = ap.parse_args()
    main(a.backtest, a.solo)
