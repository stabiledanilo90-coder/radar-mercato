"""Registro delle previsioni e pagella: confronta ogni previsione con il prezzo reale alla scadenza."""
import numpy as np
import pandas as pd

from .common import STATE, read_json, write_json

PERCORSO = STATE / "registro.json"


def carica():
    return read_json(PERCORSO, default=[])


def salva(reg):
    # tieni al massimo 2 anni di previsioni
    limite = (pd.Timestamp.now(tz="UTC").tz_localize(None) - pd.Timedelta(days=730)).isoformat()
    write_json(PERCORSO, [r for r in reg if r["creato"] >= limite])


def aggiungi(reg, tid, orizzonte, riass, scadenza, metodo="kronos"):
    oggi = pd.Timestamp.now(tz="UTC").tz_localize(None)
    # una sola previsione per titolo/orizzonte/giorno
    chiave = f"{tid}|{orizzonte}|{oggi:%Y-%m-%d}"
    reg[:] = [r for r in reg if r.get("chiave") != chiave]
    reg.append({"chiave": chiave, "creato": oggi.isoformat(), "titolo": tid, "orizzonte": orizzonte,
                "inizio": riass["prezzo"], "p10": riass["p10"], "p50": riass["p50"], "p90": riass["p90"],
                "scadenza": scadenza, "reale": None, "metodo": metodo})


def verifica(reg, prezzi):
    """prezzi: {titolo: DataFrame con timestamps/close} (orario o giornaliero)."""
    adesso = pd.Timestamp.now(tz="UTC").tz_localize(None)
    for r in reg:
        if r["reale"] is not None or pd.Timestamp(r["scadenza"]) > adesso:
            continue
        df = prezzi.get(r["titolo"])
        if df is None:
            continue
        prima = df[df["timestamps"] <= pd.Timestamp(r["scadenza"])]
        if not len(prima):
            continue
        reale = float(prima["close"].iloc[-1])
        r["reale"] = reale
        r["dir_ok"] = bool(np.sign(r["p50"] - r["inizio"]) == np.sign(reale - r["inizio"]))
        r["in_banda"] = bool(r["p10"] <= reale <= r["p90"])


def pagella(reg, backtest_per):
    out = {}
    fatte = [r for r in reg if r["reale"] is not None]
    for r in reg:
        out.setdefault(r["titolo"], {}).setdefault(r["orizzonte"], {"verificate": 0, "dir_ok": None, "in_banda": None})
    for (t, o) in {(r["titolo"], r["orizzonte"]) for r in fatte}:
        g = [r for r in fatte if r["titolo"] == t and r["orizzonte"] == o]
        gk = [r for r in g if r.get("metodo", "kronos") == "kronos"]  # la direzione conta solo per Kronos
        out[t][o] = {"verificate": len(gk),
                     "dir_ok": round(100 * sum(x["dir_ok"] for x in gk) / len(gk), 1) if gk else None,
                     "in_banda": round(100 * sum(x["in_banda"] for x in g) / len(g), 1)}
    for t, per_o in (backtest_per or {}).items():
        for o, b in per_o.items():
            out.setdefault(t, {}).setdefault(o, {"verificate": 0, "dir_ok": None, "in_banda": None})["backtest"] = b
    primo = min((r["creato"] for r in reg), default=None)
    totale_band = [r["in_banda"] for r in fatte]
    return {"titoli": out, "inizio_prova": primo, "verificate_totali": len(fatte),
            "in_banda_totale": round(100 * sum(totale_band) / len(totale_band), 1) if totale_band else None}
