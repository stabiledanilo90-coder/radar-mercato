"""Test senza rete: dati sintetici e un finto Kronos. Esegui: python -m pytest -q"""
import shutil
import numpy as np
import pandas as pd
import pytest

from pipeline import common, prices, forecast as F, track, news as N

rng = np.random.default_rng(1)


def sintetico(n, freq, weekend=True, ore_borsa=False):
    ts = pd.date_range("2016-01-04", periods=n * 3, freq=freq)
    if not weekend:
        ts = ts[ts.weekday < 5]
    if ore_borsa:
        ts = ts[(ts.hour >= 14) & (ts.hour <= 20)]
    ts = ts[:n]
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, len(ts))))
    o = np.r_[c[0], c[:-1]]
    raw = pd.DataFrame({"Open": o, "High": np.maximum(o, c) * 1.01, "Low": np.minimum(o, c) * .99, "Close": c,
                        "Volume": rng.integers(1e5, 1e6, len(ts)).astype(float)}, index=ts)
    raw.index.name = "Date"
    return prices.pulisci(raw)


class FintoKronos:
    def predict_batch(self, df_list, x_timestamp_list, y_timestamp_list, pred_len, T, top_p, sample_count, verbose):
        out = []
        for d, y in zip(df_list, y_timestamp_list):
            assert len(y) == pred_len and len(d) <= 512
            c = d["close"].iloc[-1] * np.exp(np.cumsum(rng.normal(0, 0.02, pred_len)))
            o = np.r_[d["close"].iloc[-1], c[:-1]]
            out.append(pd.DataFrame({"open": o, "high": np.maximum(o, c) * 1.01, "low": np.minimum(o, c) * .99,
                                     "close": c, "volume": 1.0, "amount": 1.0}, index=y))
        return out


def test_timestamp_futuri():
    d = sintetico(800, "D", weekend=False)
    f = prices.timestamp_futuri(d["timestamps"], 20)
    assert (f.dt.weekday < 5).all() and f.iloc[0] > d["timestamps"].iloc[-1]
    h = sintetico(2000, "h", weekend=False, ore_borsa=True)
    fh = prices.timestamp_futuri(h["timestamps"], 24)
    assert set(fh.dt.hour) <= set(h["timestamps"].dt.hour)


def test_previsione_backtest_anno():
    d = sintetico(1500, "D", weekend=False)
    p = F.previsione_json(FintoKronos(), d, prices.ORIZZONTI["giorni"], 30)
    assert len(p["candele"]) == 20 and len(p["fascia"]["p10"]) == 20
    assert p["riassunto"]["p10"] <= p["riassunto"]["p50"] <= p["riassunto"]["p90"]
    g = F.giudizio(F.backtest(FintoKronos(), d, 20, n_finestre=25, n_scenari=8))
    assert g["prove"] == 25
    assert g["livello"] in ("grigio", "arancio")  # un modello casuale non deve risultare "verde"
    a = F.scenario_anno(d)
    assert a["riassunto"]["p10"] < a["riassunto"]["p50"] < a["riassunto"]["p90"]


def test_registro(tmp_path, monkeypatch):
    monkeypatch.setattr(track, "PERCORSO", tmp_path / "r.json")
    reg = []
    r = {"prezzo": 100, "p10": 90, "p50": 105, "p90": 110}
    track.aggiungi(reg, "X", "giorni", r, (pd.Timestamp.now() - pd.Timedelta(days=1)).isoformat())
    df = pd.DataFrame({"timestamps": [pd.Timestamp.now() - pd.Timedelta(days=2)], "close": [104.0]})
    track.verifica(reg, {"X": df})
    track.salva(reg)
    p = track.pagella(track.carica(), {})
    assert p["titoli"]["X"]["giorni"]["dir_ok"] == 100.0 and p["verificate_totali"] == 1


def test_notizie_valutazione_e_campanello():
    now = pd.Timestamp.now(tz="UTC").isoformat()
    items = [
        {"id": "1", "titoli": ["NVDA"], "livello": "uff", "titolo": "Nvidia board opens investigation into CEO", "quando": now, "tono": None, "imp": None},
        {"id": "2", "titoli": ["NVDA"], "livello": "ag", "titolo": "Chip stocks plunge after election, Nvidia sued", "quando": now, "tono": None, "imp": None},
        {"id": "3", "titoli": ["NVDA"], "livello": "ag_dc", "titolo": "SpaceX said to weigh merger, people familiar say", "quando": now, "tono": None, "imp": None},
    ]
    N.valuta(items, None)                          # niente FinBERT: parole chiave
    N.valuta(items, type("T", (), {"punteggi": lambda s, t: [-0.9] * len(t)})())
    assert all(i["imp"] >= 1 for i in items)
    c = N.campanello(items)
    assert c["livello"] in ("rosso", "arancio")
    assert N.DA_CONFERMARE.search(items[2]["titolo"])
    assert N._in_elenco("uk.reuters.com", ["reuters.com"]) and not N._in_elenco("reuters.com.fake.io", ["reuters.com"])


class KronosCheTornaAllaMedia:
    """Simula il difetto visto dal vivo: le previsioni saltano alla media della finestra."""
    def predict_batch(self, df_list, x_timestamp_list, y_timestamp_list, pred_len, T, top_p, sample_count, verbose):
        out = []
        for d, y in zip(df_list, y_timestamp_list):
            m = d["close"].mean()
            c = m * np.exp(rng.normal(0, 0.003, pred_len))
            out.append(pd.DataFrame({"open": c, "high": c * 1.001, "low": c * .999, "close": c, "volume": 1.0, "amount": 1.0}, index=y))
        return out


def test_scarta_previsioni_incoerenti():
    # prezzo che sale molto: la media della finestra è lontana dall'ultimo prezzo
    ts = pd.date_range("2020-01-01", periods=900, freq="D")
    c = 100 * np.exp(np.linspace(0, 1.2, 900) + rng.normal(0, 0.01, 900))
    raw = pd.DataFrame({"Open": c, "High": c * 1.01, "Low": c * .99, "Close": c, "Volume": 1e6}, index=ts)
    d = prices.pulisci(raw)
    p = F.previsione_json(KronosCheTornaAllaMedia(), d, prices.ORIZZONTI["giorni"], 20)
    assert p["metodo"] == "statistica" and p["candele"] is None and "scarto_kronos" in p
    ok = F.previsione_json(FintoKronos(), d, prices.ORIZZONTI["giorni"], 20)
    assert ok["metodo"] == "kronos"
