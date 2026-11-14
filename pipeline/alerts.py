"""Avvisi sul telefono via Telegram (facoltativi).
Servono due segreti nel progetto GitHub: TELEGRAM_TOKEN e TELEGRAM_CHAT_ID.
"""
import os

import requests

from .common import STATE, log, read_json, write_json

PERCORSO = STATE / "avvisi_inviati.json"
ICONE = {"rosso": "🔴", "verde": "🟢", "arancio": "🟠"}


def attivi():
    return bool(os.environ.get("TELEGRAM_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))


def _invia(testo):
    try:
        r = requests.post(f"https://api.telegram.org/bot{os.environ['TELEGRAM_TOKEN']}/sendMessage",
                          json={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": testo,
                                "parse_mode": "HTML", "disable_web_page_preview": True}, timeout=20)
        return r.ok
    except Exception as e:
        log(f"  ! Telegram: {e}")
        return False


def invia_nuovi(items, campanelli, nomi, url_app):
    if not attivi():
        return
    stato = read_json(PERCORSO, default={"notizie": [], "campanelli": {}})
    inviati = set(stato["notizie"])
    for it in items:
        if it["id"] in inviati or it["imp"] < 3 or it["livello"] == "ag_dc":
            continue
        tit = ", ".join(nomi.get(t, t) for t in it["titoli"])
        livello = {"uff": "Fonte ufficiale", "ag": "Agenzia", "bal": "Balene"}.get(it["livello"], "")
        if _invia(f"<b>{tit}</b> · {livello}\n{it['titolo']}\n<i>{it['fonte']}</i>\n{it['link']}"):
            inviati.add(it["id"])
    for t, c in campanelli.items():
        prima = stato["campanelli"].get(t)
        if c["livello"] in ("rosso", "verde") and c["livello"] != prima:
            verso = "discesa" if c["livello"] == "rosso" else "salita"
            _invia(f"{ICONE[c['livello']]} <b>Campanello di {verso} · {nomi.get(t, t)}</b>\n{c.get('principale') or ''}\n{url_app}#/t/{t}")
        stato["campanelli"][t] = c["livello"]
    stato["notizie"] = list(inviati)[-2000:]
    write_json(PERCORSO, stato)
