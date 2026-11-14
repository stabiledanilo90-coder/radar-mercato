"""Esecuzione frequente (ogni ~10 minuti): prezzi aggiornati, notizie verificate, balene, campanelli, avvisi.
Con --occasioni aggiorna anche il radar stile GameStop (una volta al giorno)."""
import argparse
import os
from datetime import datetime, timedelta, timezone

from .common import DATA, STATE, config, log, now_iso, read_json, write_json
from . import news as N
from . import prices as P
from . import alerts


def main(occasioni=False):
    cfg = config()
    titoli = cfg["titoli"]
    nomi = {t["id"]: t["nome"] for t in titoli}

    # 1) prezzi
    quot = {}
    for t in titoli:
        q = P.quotazione_rapida(t["yahoo"])
        if q:
            quot[t["id"]] = q

    # 2) notizie (nuove + quelle già viste negli ultimi 7 giorni)
    vecchie = {i["id"]: i for i in (read_json(DATA / "news.json", default={}) or {}).get("notizie", [])}
    nuove = []
    for t in titoli:
        log(f"notizie {t['id']}")
        nuove += N.notizie_web(t, cfg)
        if t["tipo"] == "azione":
            nuove += N.notizie_sec(t)
    per_id = {t["id"]: t for t in titoli}
    nuove = [it for it in nuove if any(N.rilevante(it, per_id[x]) for x in it["titoli"] if x in per_id)]
    vecchie = {k: v for k, v in vecchie.items() if any(N.rilevante(v, per_id[x]) for x in v["titoli"] if x in per_id)}
    da_valutare = []
    for it in nuove:
        if it["id"] in vecchie:
            v = vecchie[it["id"]]
            v["titoli"] = sorted(set(v["titoli"]) | set(it["titoli"]))
        else:
            vecchie[it["id"]] = it
            da_valutare.append(it)
    N.valuta(da_valutare, N.Tono() if da_valutare else None)
    limite = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    tutte = sorted((i for i in vecchie.values() if i["quando"] >= limite), key=lambda i: i["quando"], reverse=True)[:400]

    # 3) campanelli per titolo
    camp = {t["id"]: N.campanello([i for i in tutte if t["id"] in i["titoli"]]) for t in titoli}
    eventi = read_json(STATE / "eventi.json", default={})

    write_json(DATA / "news.json", {"aggiornato": now_iso(), "notizie": tutte})
    write_json(DATA / "overview.json", {
        "aggiornato": now_iso(),
        "titoli": [{"id": t["id"], "nome": t["nome"], "tipo": t["tipo"], **(quot.get(t["id"]) or {}),
                    "campanello": camp[t["id"]], "eventi": eventi.get(t["id"], [])} for t in titoli],
    })

    # 4) avvisi
    url = os.environ.get("APP_URL", "https://stabiledanilo90-coder.github.io/radar-mercato/")
    alerts.invia_nuovi([i for i in da_valutare], camp, nomi, url)

    # 5) radar occasioni
    if occasioni:
        from .opportunities import radar
        log("radar occasioni…")
        write_json(DATA / "occasioni.json", {"aggiornato": now_iso(), "candidati": radar(cfg)})
    log(f"Fatto: {len(da_valutare)} notizie nuove, {len(tutte)} in archivio.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--occasioni", action="store_true")
    main(ap.parse_args().occasioni)
