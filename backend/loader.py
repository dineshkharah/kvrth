from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"

_cache = {}


def read_actuals(path=None):
    frame = pd.read_csv(path or DATA_DIR / "actuals_wind.csv")
    frame["startTime"] = pd.to_datetime(frame["startTime"], utc=True)
    return frame


def read_forecasts(path=None):
    frame = pd.read_csv(path or DATA_DIR / "forecasts_wind.csv")
    frame["startTime"] = pd.to_datetime(frame["startTime"], utc=True)
    frame["publishTime"] = pd.to_datetime(frame["publishTime"], utc=True)
    return frame


def actuals():
    if "actuals" not in _cache:
        _cache["actuals"] = read_actuals()
    return _cache["actuals"].copy()


def forecasts():
    if "forecasts" not in _cache:
        _cache["forecasts"] = read_forecasts()
    return _cache["forecasts"].copy()
