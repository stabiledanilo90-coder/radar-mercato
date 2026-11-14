"""Notizie solo da fonti verificate, su 3 livelli:
1. Ufficiali: depositi alla SEC (8-K, 10-Q, 6-K...) e siti ufficiali di aziende e progetti crypto.
2. Agenzie: solo le testate nell'elenco di config.yaml. Le indiscrezioni con fonti anonime sono marcate "da confermare".
3. Balene: acquisti/vendite dei manager (SEC Form 4) e quote sopra il 5% (13D/13G).
Social, forum e siti non in elenco vengono scartati.
"""
import hashlib
import os
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests

from .common import STATE, log, read_json, write_json

SEC_UA = os.environ.get("SEC_USER_AGENT") or "RadarMercato/1.0 stabiledanilo90-coder@users.noreply.github.com"  # la SEC chiede un contatto email
HTTP = requests.Session()
HTTP.headers.update({"User-Agent": SEC_UA, "Accept-Encoding": "gzip, deflate"})

# ---------------------------------------------------------------- utilità
def _id(*parti):
    return hashlib.sha1("|".join(parti).encode()).hexdigest()[:16]


def _dominio(url):
    try:
        h = urllib.parse.urlparse(url).hostname or ""
    except ValueError:
        return ""
    return h.lower().removeprefix("www.")


def _in_elenco(dominio, elenco):
    return any(dominio == d or dominio.endswith("." + d) for d in elenco)


DA_CONFERMARE = re.compile(
    r"people familiar|familiar with the matter|sources said|sources say|according to sources|reportedly|"
    r"is said to|are said to|said to be|in talks|weighs|weighing|considering|explores|exploring|rumou?r|"
    r"secondo fonti|indiscrezion|sarebbe in trattativa|valuta(no)? (una|la)", re.I)

PAROLE_FORTI = re.compile(
    r"investigation|probe|subpoena|lawsuit|sued|fraud|sec charges|indict|ban(s|ned)?\b|sanction|tariff|"
    r"recall|bankrupt|default|delist|hack|exploit|merger|acquisition|acquire|takeover|buyout|guidance|"
    r"earnings|results|downgrade|upgrade|resign|steps down|ceo|approval|approved|etf|halt|crash|plunge|soar|surge|"
    r"indagine|fusione|acquisizione|conti|trimestrale|dimission|causa|multa", re.I)

PAROLE_NEG = re.compile(r"investigation|probe|lawsuit|sued|fraud|charges|ban|sanction|tariff|recall|bankrupt|default|"
                        r"delist|hack|exploit|downgrade|resign|steps down|plunge|crash|selloff|sell-off|miss|cut|"
                        r"indagine|crollo|causa|multa|dimission", re.I)
PAROLE_POS = re.compile(r"beat|upgrade|record|approval|approved|partnership|raises|surge|soar|rally|buyback|wins|"
                        r"rialzo|record|accordo", re.I)


# ---------------------------------------------------------------- SEC
def _cik_map():
    cache = STATE / "sec_tickers.json"
    m = read_json(cache)
    if m and time.time() - m.get("_t", 0) < 7 * 86400:
        return m
    try:
        r = HTTP.get("https://www.sec.gov/files/company_tickers.json", timeout=30)
        r.raise_for_status()
        m = {v["ticker"].upper(): int(v["cik_str"]) for v in r.json().values()}
        m["_t"] = time.time()
        write_json(cache, m)
    except Exception as e:
        log(f"  ! elenco SEC non disponibile: {e}")
        m = m or {}
    return m


ITEM_8K = {
    "1.01": ("Firmato un accordo importante", "unc", 3), "1.02": ("Interrotto un accordo importante", "neg", 3),
    "1.03": ("Fallimento o procedura concorsuale", "neg", 3), "2.01": ("Completata un'acquisizione o una cessione", "unc", 3),
    "2.02": ("Pubblicati i risultati del trimestre", "ev", 3), "2.03": ("Nuovo debito importante", "unc", 2),
    "2.05": ("Annunciati tagli o ristrutturazione", "neg", 3), "2.06": ("Svalutazione importante", "neg", 3),
    "3.01": ("Problemi con la quotazione in borsa", "neg", 3), "4.01": ("Cambio del revisore dei conti", "unc", 2),
    "4.02": ("I conti passati non sono più affidabili", "neg", 3), "5.01": ("Cambio di controllo della società", "unc", 3),
    "5.02": ("Cambio ai vertici dell'azienda", "unc", 3), "5.07": ("Esito del voto degli azionisti", "ev", 1),
    "7.01": ("Comunicazione ufficiale al mercato", "ev", 2), "8.01": ("Altro evento importante comunicato", "unc", 2),
}


def notizie_sec(titolo, giorni=14):
    cik = _cik_map().get(titolo["yahoo"].upper())
    if not cik:
        return []
    try:
        r = HTTP.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", timeout=30)
        r.raise_for_status()
        rec = r.json()["filings"]["recent"]
    except Exception as e:
        log(f"  ! SEC {titolo['id']}: {e}")
        return []
    limite = (datetime.now(timezone.utc) - timedelta(days=giorni)).date().isoformat()
    out = []
    for i, form in enumerate(rec["form"]):
        data = rec["filingDate"][i]
        if data < limite:
            break
        acc = rec["accessionNumber"][i]
        doc = rec["primaryDocument"][i]
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{doc}"
        quando = (rec.get("acceptanceDateTime") or [None] * len(rec["form"]))[i] or data
        base = {"titoli": [titolo["id"]], "link": url, "quando": quando, "fonte": "SEC · documento ufficiale"}
        if form in ("8-K", "8-K/A"):
            items = [x.strip() for x in (rec.get("items") or [""] * len(rec["form"]))[i].split(",") if x.strip() and x.strip() != "9.01"]
            for it in items or ["8.01"]:
                testo, tono, imp = ITEM_8K.get(it, ("Comunicazione ufficiale", "unc", 2))
                out.append({**base, "id": _id(acc, it), "livello": "uff", "tono": tono, "imp": imp,
                            "titolo": f"{titolo['nome']}: {testo.lower()}", "dettaglio": f"Modulo 8-K, punto {it}"})
        elif form in ("10-Q", "10-K", "20-F", "40-F"):
            out.append({**base, "id": _id(acc), "livello": "uff", "tono": "ev", "imp": 2,
                        "titolo": f"{titolo['nome']}: depositati i conti {'annuali' if form in ('10-K','20-F','40-F') else 'del trimestre'}",
                        "dettaglio": f"Modulo {form}"})
        elif form == "6-K":
            desc = (rec.get("primaryDocDescription") or [""] * len(rec["form"]))[i] or "comunicazione"
            out.append({**base, "id": _id(acc), "livello": "uff", "tono": "unc", "imp": 2,
                        "titolo": f"{titolo['nome']}: comunicazione ufficiale ({desc.lower()})", "dettaglio": "Modulo 6-K"})
        elif form.startswith("SC 13D") or form.startswith("SC 13G") or form.startswith("SCHEDULE 13"):
            out.append({**base, "id": _id(acc), "livello": "bal", "tono": "unc", "imp": 2 if "G" in form else 3,
                        "titolo": f"{titolo['nome']}: un grande investitore dichiara una quota sopra il 5%",
                        "dettaglio": f"Modulo {form}" + (" · investitore attivo" if "D" in form else " · investitore passivo")})
        elif form == "4":
            f4 = _form4(cik, acc, doc)
            if f4:
                out.append({**base, **f4, "id": _id(acc), "livello": "bal"})
    return out


def _form4(cik, acc, doc):
    raw = doc.split("/", 1)[1] if doc.startswith("xsl") and "/" in doc else doc
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{raw}"
    try:
        time.sleep(0.15)
        r = HTTP.get(url, timeout=30)
        r.raise_for_status()
        x = ET.fromstring(r.content)
    except Exception:
        return None
    nome = (x.findtext(".//reportingOwner/reportingOwnerId/rptOwnerName") or "un dirigente").title()
    ruolo = x.findtext(".//reportingOwnerRelationship/officerTitle") or ("consigliere" if x.findtext(".//reportingOwnerRelationship/isDirector") in ("1", "true") else "dirigente")
    programmata = x.findtext(".//aff10b5One") in ("1", "true")
    acq = ven = 0.0
    for t in x.findall(".//nonDerivativeTable/nonDerivativeTransaction"):
        code = t.findtext("transactionCoding/transactionCode")
        try:
            v = float(t.findtext("transactionAmounts/transactionShares/value") or 0) * float(t.findtext("transactionAmounts/transactionPricePerShare/value") or 0)
        except ValueError:
            v = 0
        if code == "P":
            acq += v
        elif code == "S":
            ven += v
    if acq >= 50_000:
        return {"tono": "pos", "imp": 3 if acq >= 1_000_000 else 2,
                "titolo": f"{nome} ({ruolo}) ha comprato azioni sul mercato per {_soldi(acq)}",
                "dettaglio": "Modulo 4 · acquisto con soldi propri: segnale di fiducia"}
    if ven >= 500_000:
        return {"tono": "neg" if not programmata else "unc", "imp": 2 if not programmata else 1,
                "titolo": f"{nome} ({ruolo}) ha venduto azioni per {_soldi(ven)}",
                "dettaglio": "Modulo 4 · " + ("vendita programmata da mesi: pesa poco" if programmata else "vendita non programmata")}
    return None


def _soldi(v):
    return f"{v/1e9:.1f} mld $".replace(".", ",") if v >= 1e9 else (f"{v/1e6:.1f} mln $".replace(".", ",") if v >= 1e6 else f"{v/1e3:.0f} mila $")


# ---------------------------------------------------------------- agenzie e siti ufficiali (via Google News, filtrato)
def _google_news(query, giorni):
    import feedparser
    q = urllib.parse.quote(f"{query} when:{giorni}d")
    feed = feedparser.parse(f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en")
    return feed.entries


def notizie_web(titolo, cfg, giorni=2):
    agenzie = list(cfg["agenzie"])
    if titolo["tipo"] != "crypto":
        agenzie = [a for a in agenzie if a not in ("coindesk.com", "theblock.co")]
    ufficiali = titolo.get("sito_ufficiale") or []
    esclusi = cfg.get("esclusi", [])
    out = []
    for gruppo, livello in ((ufficiali, "uff"), (agenzie, "ag")):
        if not gruppo:
            continue
        siti = " OR ".join(f"site:{d}" for d in gruppo)
        try:
            entries = _google_news(f'{titolo["ricerca"]} ({siti})', giorni)
        except Exception as e:
            log(f"  ! notizie {titolo['id']}: {e}")
            continue
        for e in entries[:30]:
            src = getattr(e, "source", None) or {}
            href = src.get("href", "") if isinstance(src, dict) else getattr(src, "href", "")
            dom = _dominio(href)
            if not dom or _in_elenco(dom, esclusi) or not _in_elenco(dom, gruppo):
                continue
            nome_fonte = (src.get("title") if isinstance(src, dict) else getattr(src, "title", "")) or dom
            tit = re.sub(rf"\s+-\s+{re.escape(nome_fonte)}$", "", e.title).strip()
            try:
                quando = datetime(*e.published_parsed[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                quando = datetime.now(timezone.utc).isoformat()
            liv = livello
            if livello == "ag":
                liv = "ag_dc" if DA_CONFERMARE.search(tit) else "ag"
            out.append({"id": _id(tit.lower()[:80]), "titoli": [titolo["id"]], "livello": liv, "titolo": tit,
                        "fonte": nome_fonte, "link": e.link, "quando": quando, "tono": None, "imp": None,
                        "dettaglio": "Indiscrezione con fonti anonime: aspetta la conferma ufficiale" if liv == "ag_dc" else ""})
    return out


RUMORE = re.compile(
    r"\b(intern(ship)?|technician|careers?|job opening|jobs|hiring|vacanc|"
    r"shift|nights|full[- ]time|part[- ]time|apply now|cookie|privacy policy|brand guidelines|newsletter)\b", re.I)


def rilevante(it, titolo_cfg):
    """Scarta annunci di lavoro, pagine generiche e notizie che non citano davvero il titolo."""
    t = it["titolo"]
    if it["livello"] in ("uff", "bal") and it.get("fonte", "").startswith("SEC"):
        return True
    if len(t.split()) < 5 or RUMORE.search(t):
        return False
    parole = titolo_cfg.get("parole")
    return not parole or re.search(parole, t, re.I) is not None


# ---------------------------------------------------------------- tono e importanza
class Tono:
    """FinBERT (modello specializzato in notizie finanziarie). Se non disponibile usa parole chiave."""
    def __init__(self):
        try:
            from transformers import pipeline
            self.pipe = pipeline("text-classification", model="ProsusAI/finbert", top_k=None, truncation=True)
        except Exception as e:
            log(f"  ! FinBERT non disponibile ({e}): uso le parole chiave")
            self.pipe = None

    def punteggi(self, testi):
        if not testi:
            return []
        if self.pipe is None:
            return [(0.6 if PAROLE_POS.search(t) else 0) - (0.6 if PAROLE_NEG.search(t) else 0) for t in testi]
        out = []
        for r in self.pipe(testi, batch_size=16):
            d = {x["label"].lower(): x["score"] for x in r}
            out.append(d.get("positive", 0) - d.get("negative", 0))
        return out


def valuta(items, tono):
    da_fare = [it for it in items if it.get("tono") is None]
    punti = tono.punteggi([it["titolo"] for it in da_fare]) if (da_fare and tono) else []
    for it, s in zip(da_fare, punti):
        s = s - (0.25 if PAROLE_NEG.search(it["titolo"]) else 0) + (0.25 if PAROLE_POS.search(it["titolo"]) else 0)
        it["punteggio"] = round(max(-1, min(1, s)), 2)
        it["tono"] = "neg" if s <= -0.35 else ("pos" if s >= 0.35 else ("unc" if it["livello"] == "ag_dc" else "neu"))
        forte = bool(PAROLE_FORTI.search(it["titolo"]))
        it["imp"] = 3 if (forte and abs(s) >= 0.5) or (forte and it["livello"] == "uff") else (2 if forte or abs(s) >= 0.5 else 1)
    for it in items:
        it.setdefault("punteggio", {"neg": -0.7, "pos": 0.7}.get(it["tono"], 0))
    return items


def campanello(items_titolo):
    """Livello per un titolo dalle notizie delle ultime 48 ore."""
    limite = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    rec = [i for i in items_titolo if i["quando"] >= limite and i["livello"] != "ag_dc"]
    neg = [i for i in rec if i["tono"] == "neg" and i["imp"] >= 2]
    pos = [i for i in rec if i["tono"] == "pos" and i["imp"] >= 2]
    forti_neg = [i for i in neg if i["imp"] == 3]
    forti_pos = [i for i in pos if i["imp"] == 3]
    if len(forti_neg) >= 2 or (forti_neg and len(neg) >= 3 and len(neg) > 2 * len(pos)):
        liv = "rosso"
    elif len(forti_pos) >= 2 or (forti_pos and len(pos) >= 3 and len(pos) > 2 * len(neg)):
        liv = "verde"
    elif neg or pos or any(i["livello"] == "ag_dc" and i["imp"] >= 2 for i in items_titolo if i["quando"] >= limite):
        liv = "arancio"
    else:
        liv = "grigio"
    principale = sorted(rec, key=lambda i: (-i["imp"], -abs(i.get("punteggio") or 0)))[:1]
    return {"livello": liv, "negative": len(neg), "positive": len(pos), "totali": len(rec),
            "principale": principale[0]["titolo"] if principale else None}
