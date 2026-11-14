"""Prezzi da Yahoo Finance, nel formato chiesto da Kronos."""
import numpy as np
import pandas as pd

from .common import log

ORIZZONTI = {
    "ore":       {"interval": "1h",  "period": "730d", "pred_len": 24, "label": "prossime 24 ore",        "mostra": 96},
    "giorni":    {"interval": "1d",  "period": "10y",  "pred_len": 20, "label": "prossime 4 settimane",   "mostra": 90},
    "settimane": {"interval": "1wk", "period": "max",  "pred_len": 12, "label": "prossimi 3 mesi",        "mostra": 78},
}


def pulisci(raw):
    if raw is None or len(raw) == 0:
        return None
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    df = df.reset_index()
    df = df.rename(columns={df.columns[0]: "timestamps"})
    df["timestamps"] = pd.to_datetime(df["timestamps"], utc=True).dt.tz_convert(None)
    need = ["open", "high", "low", "close"]
    if not all(c in df.columns for c in need):
        return None
    if "volume" not in df.columns:
        df["volume"] = 0.0
    df = df[["timestamps", "open", "high", "low", "close", "volume"]].dropna(subset=need)
    df = df[df["close"] > 0].drop_duplicates("timestamps").sort_values("timestamps").reset_index(drop=True)
    df["volume"] = df["volume"].fillna(0).astype(float)
    df["amount"] = df["volume"] * df[["open", "high", "low", "close"]].mean(axis=1)
    return df


def scarica(simbolo, interval, period):
    import yfinance as yf
    try:
        raw = yf.download(simbolo, period=period, interval=interval, progress=False,
                          auto_adjust=True, threads=False, multi_level_index=False)
    except Exception as e:  # rete, simbolo inesistente…
        log(f"  ! {simbolo} {interval}: download fallito ({e})")
        return None
    df = pulisci(raw)
    if df is None or len(df) < 30:
        log(f"  ! {simbolo} {interval}: dati insufficienti")
        return None
    return df


def scarica_orizzonte(simbolo, orizzonte):
    c = ORIZZONTI[orizzonte]
    return scarica(simbolo, c["interval"], c["period"])


def quotazione_rapida(simbolo):
    """Prezzo attuale, variazione 24h e mini-grafico 7 giorni (per l'aggiornamento frequente)."""
    df = scarica(simbolo, "1h", "8d")
    if df is None:
        return None
    last = float(df["close"].iloc[-1])
    t_last = df["timestamps"].iloc[-1]
    prima = df[df["timestamps"] <= t_last - pd.Timedelta(hours=24)]
    ref = float(prima["close"].iloc[-1]) if len(prima) else float(df["close"].iloc[0])
    spark = df.set_index("timestamps")["close"].resample("6h").last().dropna().tail(28).round(6).tolist()
    return {"prezzo": last, "var24": 100 * (last / ref - 1), "spark": spark,
            "agg": t_last.isoformat()}


def candele_json(df, n):
    s = df.tail(n)
    return [[t.isoformat(), round(float(o), 6), round(float(h), 6), round(float(l), 6), round(float(c), 6)]
            for t, o, h, l, c in zip(s["timestamps"], s["open"], s["high"], s["low"], s["close"])]


def timestamp_futuri(storico_ts, n):
    ts = pd.Series(pd.to_datetime(storico_ts)).reset_index(drop=True)
    passo = ts.diff().dropna().tail(50).median()
    weekend = (ts.tail(300).dt.weekday >= 5).any()
    out, cur = [], ts.iloc[-1]
    # orari di borsa: se lo storico orario ha "buchi" notturni, usiamo solo le ore viste di solito
    ore_viste = set(ts.tail(500).dt.hour) if passo <= pd.Timedelta(hours=1) else None
    while len(out) < n:
        cur = cur + passo
        if not weekend and passo <= pd.Timedelta(days=1) and cur.weekday() >= 5:
            continue
        if ore_viste is not None and len(ore_viste) < 20 and cur.hour not in ore_viste:
            continue
        out.append(cur)
    return pd.Series(out)
