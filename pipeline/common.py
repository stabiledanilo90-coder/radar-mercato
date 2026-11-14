"""Funzioni condivise: configurazione, percorsi, lettura/scrittura JSON."""
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "site" / "data"
STATE = ROOT / "state"


def config():
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clean(o):
    """Rende serializzabili numpy/pandas/NaN."""
    try:
        import numpy as np
        import pandas as pd
        if isinstance(o, (np.floating,)):
            o = float(o)
        elif isinstance(o, (np.integer,)):
            return int(o)
        elif isinstance(o, np.bool_):
            return bool(o)
        elif isinstance(o, (pd.Timestamp, datetime)):
            return o.isoformat()
        elif isinstance(o, np.ndarray):
            return [_clean(x) for x in o.tolist()]
    except ImportError:
        pass
    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else round(o, 6)
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(x) for x in o]
    return o


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(_clean(obj), f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def log(*a):
    print(f"[{datetime.now():%H:%M:%S}]", *a, flush=True)
