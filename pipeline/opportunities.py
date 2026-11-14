"""Radar occasioni stile GameStop 2021: titoli con molte scommesse al ribasso e segnali che potrebbero
costringere chi ha scommesso a ricomprare. Sono idee DA STUDIARE, non consigli."""
import math

import numpy as np

from .common import log
from .news import notizie_sec


def _f(x):
    try:
        x = float(x)
        return None if math.isnan(x) else x
    except (TypeError, ValueError):
        return None


def candidati_iniziali(n=60):
    import yfinance as yf
    simboli = []
    for q in ("most_shorted_stocks", "small_cap_gainers", "aggressive_small_caps"):
        try:
            res = yf.screen(q, count=n)
            simboli += [x["symbol"] for x in res.get("quotes", []) if x.get("symbol")]
        except Exception as e:
            log(f"  ! screener {q}: {e}")
    return list(dict.fromkeys(simboli))


def analizza(simbolo, soglie):
    import yfinance as yf
    t = yf.Ticker(simbolo)
    try:
        info = t.info or {}
    except Exception:
        return None
    if info.get("quoteType") != "EQUITY" or (info.get("marketCap") or 0) < 150e6:
        return None  # niente titoli microscopici: troppo facili da manipolare
    short = _f(info.get("shortPercentOfFloat"))
    dtc = _f(info.get("shortRatio"))
    try:
        h = t.history(period="3mo", interval="1d")
        vol_x = float(h["Volume"].tail(5).mean() / h["Volume"].iloc[:-5].mean()) if len(h) > 30 else None
        var_1m = float(h["Close"].iloc[-1] / h["Close"].iloc[-22] - 1) * 100 if len(h) > 22 else None
    except Exception:
        vol_x = var_1m = None
    ps = _f(info.get("priceToSalesTrailing12Months"))
    fpe = _f(info.get("forwardPE"))
    crescita = _f(info.get("revenueGrowth"))
    cassa, debito = _f(info.get("totalCash")) or 0, _f(info.get("totalDebt")) or 0
    valore_ok = ((ps is not None and ps < 2) or (fpe is not None and 0 < fpe < 15)) and (crescita or 0) > 0 and cassa >= 0.5 * debito
    insider = 0.0
    try:
        ip = t.insider_purchases
        if ip is not None and len(ip):
            riga = ip[ip.iloc[:, 0].astype(str).str.contains("Net Shares", case=False)]
            if len(riga):
                insider = float(riga.iloc[0, 1])
    except Exception:
        pass
    segnali = {
        "scommesse_ribasso": short is not None and short >= soglie["scommesse_ribasso_min"],
        "difficile_uscire": dtc is not None and dtc >= soglie["giorni_per_ricomprare_min"],
        "volumi_crescita": vol_x is not None and vol_x >= soglie["volume_x_min"],
        "conti_solidi": bool(valore_ok),
        "balene_entrata": insider > 0,
    }
    punti = sum(segnali.values())
    if not segnali["scommesse_ribasso"]:
        return None  # senza tante scommesse al ribasso non è un caso "GameStop"
    motivi = []
    if segnali["scommesse_ribasso"]: motivi.append(f"il {short*100:.0f}% delle azioni disponibili è venduto allo scoperto")
    if segnali["difficile_uscire"]: motivi.append(f"servirebbero {dtc:.1f} giorni di scambi per ricomprarle tutte")
    if segnali["volumi_crescita"]: motivi.append(f"volumi {vol_x:.1f} volte la media")
    if segnali["conti_solidi"]: motivi.append("ricavi in crescita e valutazione bassa")
    if segnali["balene_entrata"]: motivi.append("i manager hanno comprato più azioni di quante ne abbiano vendute negli ultimi 6 mesi")
    rischi = []
    if (crescita or 0) < 0: rischi.append("ricavi in calo")
    if debito > 2 * cassa: rischi.append("debiti alti rispetto alla cassa")
    if var_1m is not None and var_1m > 60: rischi.append(f"già salito del {var_1m:.0f}% in un mese: rischio di arrivare tardi")
    return {
        "simbolo": simbolo, "nome": info.get("shortName") or simbolo, "settore": info.get("sector"),
        "prezzo": _f(info.get("currentPrice") or info.get("regularMarketPrice")),
        "cap_mld": round((info.get("marketCap") or 0) / 1e9, 2),
        "metriche": {"scommesse_ribasso_%": None if short is None else round(short * 100, 1),
                     "giorni_per_ricomprare": None if dtc is None else round(dtc, 1),
                     "volume_x": None if vol_x is None else round(vol_x, 1),
                     "p_s": None if ps is None else round(ps, 2), "var_1m_%": None if var_1m is None else round(var_1m, 1)},
        "segnali": segnali, "punti": punti,
        "perche": "; ".join(motivi).capitalize() + "." if motivi else "",
        "rischi": rischi,
    }


def radar(cfg):
    soglie = cfg["occasioni"]
    out = []
    for s in candidati_iniziali():
        try:
            a = analizza(s, soglie)
        except Exception as e:
            log(f"  ! {s}: {e}")
            continue
        if a and a["punti"] >= 3:
            # notizie ufficiali recenti (SEC)
            a["notizie_ufficiali"] = [{"titolo": n["titolo"], "link": n["link"], "quando": n["quando"]}
                                      for n in notizie_sec({"id": s, "nome": a["nome"], "yahoo": s}, giorni=30)][:4]
            out.append(a)
    out.sort(key=lambda a: (-a["punti"], -(a["metriche"]["scommesse_ribasso_%"] or 0)))
    return out[: soglie["max_candidati"]]
