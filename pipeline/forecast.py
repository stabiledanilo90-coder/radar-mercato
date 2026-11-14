"""Previsioni a scenari con Kronos, backtest, scenario a 1 anno e anomalie."""
import math

import numpy as np
import pandas as pd

from .common import log
from .prices import timestamp_futuri

LOOKBACK = 256  # finestra più corta: Kronos tende a tornare alla media della finestra


# ------------------------------------------------------------------ modello
def carica_kronos(nome_modello):
    import sys
    import torch
    import os
    sys.path.insert(0, os.environ.get("KRONOS_DIR", "Kronos"))  # clonato da ./radar.sh setup
    from model import Kronos, KronosTokenizer, KronosPredictor
    if torch.cuda.is_available():
        device = "cuda:0"
    elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        device = "mps"  # Mac con chip Apple (M1–M4): molto più veloce della CPU
    else:
        device = "cpu"
    tok = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
    mod = Kronos.from_pretrained(nome_modello)
    try:
        pred = KronosPredictor(mod, tok, device=device, max_context=512)
    except TypeError:
        pred = KronosPredictor(mod, tok, max_context=512)
    log(f"Modello {nome_modello} caricato su {device}")
    return pred


def _batch(predictor, dfs, xts, yts, pred_len, T=1.0, top_p=0.9):
    if hasattr(predictor, "predict_batch"):
        return predictor.predict_batch(df_list=dfs, x_timestamp_list=xts, y_timestamp_list=yts,
                                       pred_len=pred_len, T=T, top_p=top_p, sample_count=1, verbose=False)
    return [predictor.predict(df=d, x_timestamp=x, y_timestamp=y, pred_len=pred_len,
                              T=T, top_p=top_p, sample_count=1, verbose=False)
            for d, x, y in zip(dfs, xts, yts)]


def scenari(predictor, storico, pred_len, n=40, blocco=10, lookback=LOOKBACK):
    x = storico.tail(lookback).reset_index(drop=True)
    x_df = x[["open", "high", "low", "close", "volume", "amount"]]
    x_ts = x["timestamps"]
    y_ts = timestamp_futuri(x_ts, pred_len)
    percorsi = []
    for i in range(0, n, blocco):
        k = min(blocco, n - i)
        percorsi += _batch(predictor, [x_df] * k, [x_ts] * k, [y_ts] * k, pred_len)
    arr = {c: np.stack([p[c].to_numpy(dtype=float)[:pred_len] for p in percorsi]) for c in ["open", "high", "low", "close"]}
    ch = arr["close"]
    q = {f"p{p}": np.percentile(ch, p, axis=0) for p in (10, 25, 50, 75, 90)}
    med = {c: np.median(arr[c], axis=0) for c in ["open", "high", "low", "close"]}
    med["high"] = np.maximum.reduce([med["open"], med["high"], med["close"]])
    med["low"] = np.minimum.reduce([med["open"], med["low"], med["close"]])
    return y_ts, q, med, ch


def riassunto(ultimo, q, ch):
    fine = ch[:, -1]
    return {
        "prezzo": ultimo,
        "p10": float(q["p10"][-1]), "p50": float(np.median(fine)), "p90": float(q["p90"][-1]),
        "var_p10": 100 * (q["p10"][-1] / ultimo - 1),
        "var_p50": 100 * (np.median(fine) / ultimo - 1),
        "var_p90": 100 * (q["p90"][-1] / ultimo - 1),
        "prob_salita": 100 * float((fine > ultimo).mean()),
        "ampiezza": 100 * (q["p90"][-1] - q["p10"][-1]) / ultimo,
    }


def fascia_statistica(storico, pred_len, n=3000, storia=1500, blocco=5, seed=0):
    """Scenari costruiti ricampionando a blocchi i movimenti reali del titolo (ultimi ~1500 periodi).
    Non dice dove andrà il prezzo: dice quanto si muove di solito in quel tempo."""
    c = storico["close"].to_numpy(dtype=float)[-storia:]
    r = np.diff(np.log(c))
    r = r - r.mean()  # nessuna direzione: solo l'ampiezza tipica dei movimenti
    rng = np.random.default_rng(seed)
    nb = math.ceil(pred_len / blocco)
    inizi = rng.integers(0, max(1, len(r) - blocco), size=(n, nb))
    idx = (inizi[:, :, None] + np.arange(blocco)[None, None, :]).reshape(n, -1)[:, :pred_len]
    perc = c[-1] * np.exp(np.cumsum(r[idx], axis=1))
    return {f"p{p}": np.percentile(perc, p, axis=0) for p in (10, 25, 50, 75, 90)}, perc


def controllo_coerenza(storico, q_kr, ch_kr, q_st):
    """Scarta le previsioni Kronos fuori scala: salto iniziale enorme o movimento mediano
    ben oltre quello che il titolo fa nel 90% dei casi reali."""
    last = float(storico["close"].iloc[-1])
    r = np.diff(np.log(storico["close"].to_numpy(dtype=float)[-500:]))
    sd = float(np.std(r)) or 1e-9
    salto = abs(np.log(np.median(ch_kr[:, 0]) / last)) / sd
    mov_kr = abs(np.log(np.median(ch_kr[:, -1]) / last))
    mov_st = max(abs(np.log(q_st["p90"][-1] / last)), abs(np.log(q_st["p10"][-1] / last)))
    motivi = []
    if salto > 4:
        motivi.append(f"la prima candela prevista salta di {salto:.0f} volte il movimento tipico")
    if mov_kr > 1.5 * mov_st:
        motivi.append("il movimento previsto è molto più grande di quelli reali del titolo")
    return motivi


def previsione_json(predictor, storico, cfg_or, n_scenari, lookback=LOOKBACK):
    pl = cfg_or["pred_len"]
    ultimo = float(storico["close"].iloc[-1])
    q_st, perc_st = fascia_statistica(storico, pl)
    y_ts, q, med, ch = scenari(predictor, storico, pl, n=n_scenari, lookback=lookback)
    motivi = controllo_coerenza(storico, q, ch, q_st)
    out = {"label": cfg_or["label"], "futuro": [t.isoformat() for t in y_ts], "scadenza": y_ts.iloc[-1].isoformat(),
           "statistica": {"fascia": {k: [round(float(v), 6) for v in a] for k, a in q_st.items()},
                          "riassunto": riassunto(ultimo, q_st, perc_st)}}
    if motivi:
        out.update({"metodo": "statistica", "scarto_kronos": "; ".join(motivi),
                    "fascia": out["statistica"]["fascia"], "candele": None,
                    "riassunto": out["statistica"]["riassunto"],
                    "kronos_scartato": {"var_p50": riassunto(ultimo, q, ch)["var_p50"]}})
    else:
        out.update({"metodo": "kronos",
                    "fascia": {k: [round(float(v), 6) for v in arr] for k, arr in q.items()},
                    "candele": [[round(float(med[c][i]), 6) for c in ("open", "high", "low", "close")] for i in range(pl)],
                    "riassunto": riassunto(ultimo, q, ch)})
    return out


# ------------------------------------------------------------------ backtest
def backtest(predictor, storico, pred_len, n_finestre=20, n_scenari=8, lookback=LOOKBACK):
    righe = []
    n = len(storico)
    for k in range(n_finestre, 0, -1):
        origine = n - pred_len * k
        if origine - 100 < 0:
            continue
        passato = storico.iloc[:origine]
        reale = storico.iloc[origine:origine + pred_len]
        if len(reale) < pred_len:
            continue
        q_st, _ = fascia_statistica(passato, pred_len, n=800)
        _, q, _, ch = scenari(predictor, passato, pred_len, n=n_scenari, lookback=lookback)
        scartata = bool(controllo_coerenza(passato, q, ch, q_st))
        p0 = float(passato["close"].iloc[-1]); rf = float(reale["close"].iloc[-1]); mf = float(np.median(ch[:, -1]))
        righe.append({
            "dir_ok": bool(np.sign(mf - p0) == np.sign(rf - p0)),
            "err_mod": 100 * abs(mf - rf) / rf,
            "err_fermo": 100 * abs(p0 - rf) / rf,
            "in_banda": bool(q["p10"][-1] <= rf <= q["p90"][-1]),
            "in_banda_stat": bool(q_st["p10"][-1] <= rf <= q_st["p90"][-1]),
            "scartata": scartata,
        })
    return righe


def giudizio(righe):
    n = len(righe)
    if n == 0:
        return {"prove": 0, "verdetto": "Storico insufficiente", "livello": "grigio"}
    d = 100 * sum(r["dir_ok"] for r in righe) / n
    em = float(np.mean([r["err_mod"] for r in righe])); ef = float(np.mean([r["err_fermo"] for r in righe]))
    cop = 100 * sum(r["in_banda"] for r in righe) / n
    cop_st = 100 * sum(r.get("in_banda_stat", False) for r in righe) / n
    scart = 100 * sum(r.get("scartata", False) for r in righe) / n
    # intervallo di confidenza 95% sulla percentuale di direzioni giuste
    se = 100 * math.sqrt(max(d / 100 * (1 - d / 100), 1e-9) / n)
    if scart >= 30:
        verdetto, liv = f"Kronos dà risultati incoerenti nel {scart:.0f}% dei casi: uso la fascia statistica", "grigio"
    elif n < 20:
        verdetto, liv = f"Solo {n} prove: troppo poche per giudicare", "grigio"
    elif d - 1.96 * se > 50 and em < ef:
        verdetto, liv = "Meglio del caso, in modo misurabile", "verde"
    elif d >= 55:
        verdetto, liv = "Forse meglio del caso: da confermare", "arancio"
    else:
        verdetto, liv = "Come lanciare una moneta: non usarlo per decidere", "grigio"
    return {"prove": n, "dir_ok": round(d, 1), "margine": round(1.96 * se, 1), "err_modello": round(em, 2),
            "err_prezzo_fermo": round(ef, 2), "in_banda": round(cop, 1), "in_banda_stat": round(cop_st, 1),
            "scartate": round(scart, 1), "verdetto": verdetto, "livello": liv}


# ------------------------------------------------------------------ 1 anno
def scenario_anno(giornaliero, anni=5, sim=5000, blocco=4, seed=0):
    d = giornaliero.set_index("timestamps")["close"]
    d = d[d.index >= d.index.max() - pd.Timedelta(days=365 * anni)]
    sett = d.resample("W").last().dropna()
    r = np.log(sett).diff().dropna().to_numpy()
    if len(r) < 52:
        return None
    rng = np.random.default_rng(seed)
    nb = math.ceil(52 / blocco)
    inizi = rng.integers(0, len(r) - blocco, size=(sim, nb))
    idx = (inizi[:, :, None] + np.arange(blocco)[None, None, :]).reshape(sim, -1)[:, :52]
    perc = np.exp(np.cumsum(r[idx], axis=1))
    p0 = float(d.iloc[-1])
    picco = np.maximum.accumulate(np.concatenate([np.ones((sim, 1)), perc], axis=1), axis=1)[:, 1:]
    dd = (perc / picco - 1).min(axis=1)
    fasce = {f"p{p}": (p0 * np.percentile(perc, p, axis=0)).round(6).tolist() for p in (10, 50, 90)}
    storia = sett.tail(104)
    futuro = pd.date_range(sett.index[-1] + pd.Timedelta(weeks=1), periods=52, freq="W")
    return {
        "storia": [[t.isoformat(), round(float(v), 6)] for t, v in storia.items()],
        "futuro": [t.isoformat() for t in futuro],
        "fascia": fasce,
        "riassunto": {"prezzo": p0, "p10": fasce["p10"][-1], "p50": fasce["p50"][-1], "p90": fasce["p90"][-1],
                      "var_p10": 100 * (fasce["p10"][-1] / p0 - 1), "var_p50": 100 * (fasce["p50"][-1] / p0 - 1),
                      "var_p90": 100 * (fasce["p90"][-1] / p0 - 1),
                      "prob_perdita": 100 * float((perc[:, -1] < 1).mean()),
                      "calo_tipico": 100 * float(np.median(dd)), "calo_brutto": 100 * float(np.percentile(dd, 10)),
                      "anni_usati": round(len(r) / 52, 1)},
    }


# ------------------------------------------------------------------ anomalie
def anomalie(storico, nome_orizzonte, finestra=60, soglia_z=3.0, soglia_vol=3.0):
    df = storico.copy()
    r = np.log(df["close"]).diff()
    z = (r - r.rolling(finestra).mean().shift(1)) / r.rolling(finestra).std().shift(1)
    vm = df["volume"].rolling(20).median().shift(1)
    vx = np.where(vm > 0, df["volume"] / vm, np.nan)
    out = []
    for i in range(max(0, len(df) - 3), len(df)):
        if pd.notna(z.iloc[i]) and abs(z.iloc[i]) >= soglia_z:
            out.append({"quando": df["timestamps"].iloc[i].isoformat(), "orizzonte": nome_orizzonte,
                        "tipo": "salita" if z.iloc[i] > 0 else "discesa",
                        "testo": f"Movimento {'in salita' if z.iloc[i] > 0 else 'in discesa'} fuori dal normale (intensità {z.iloc[i]:+.1f}, normale tra −2 e +2)"})
        if pd.notna(vx[i]) and vx[i] >= soglia_vol:
            out.append({"quando": df["timestamps"].iloc[i].isoformat(), "orizzonte": nome_orizzonte, "tipo": "volume",
                        "testo": f"Volume {vx[i]:.1f} volte il solito"})
    return out
