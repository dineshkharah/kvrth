"""The point in time join.

A forecast for a given hour is republished eight times a day as the weather
updates. Scoring accuracy against the newest version measures hindsight, not
what the desk knew when it had to buy. Everything here exists to make sure only
forecasts published at or before gate closure can influence the answer.
"""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

UK = ZoneInfo("Europe/London")

# EPEX SPOT GB day ahead auction. Moved here from 11:00 when GB left SDAC in 2020.
GATE_CLOSURE = time(9, 20)


def to_hourly(actuals):
    """Average the two half hour readings into the hourly value the auction trades."""
    frame = actuals.copy()
    frame["hour"] = frame["startTime"].dt.floor("h")
    return frame.groupby("hour", as_index=False).agg(
        actual=("generation", "mean"), periods=("generation", "size")
    )


def cutoff_for(delivery_day, cutoff_time=GATE_CLOSURE):
    decision_day = delivery_day - timedelta(days=1)
    local = datetime.combine(decision_day, cutoff_time, tzinfo=UK)
    return pd.Timestamp(local).tz_convert("UTC")


def delivery_hours(delivery_day):
    """The hours of a UK local delivery day, which is 23 or 25 on clock change days."""
    start = pd.Timestamp(datetime.combine(delivery_day, time(0, 0), tzinfo=UK))
    end = pd.Timestamp(
        datetime.combine(delivery_day + timedelta(days=1), time(0, 0), tzinfo=UK)
    )
    return pd.date_range(
        start.tz_convert("UTC"), end.tz_convert("UTC"), freq="h", inclusive="left"
    )


def forecast_as_at(forecasts, cutoff):
    """The newest forecast for each hour that existed at the cutoff.

    drop_duplicates keeps whole rows, so publishTime always belongs to the same
    record as the generation value. A groupby last would pick each column
    independently and could mix two different forecast runs together.
    """
    usable = forecasts[forecasts["publishTime"] <= cutoff]
    return usable.sort_values("publishTime").drop_duplicates("startTime", keep="last")


def day_view(actuals_hourly, forecasts, delivery_day, cutoff_time=GATE_CLOSURE):
    """Hour by hour forecast, delivered output and error for one delivery day."""
    cutoff = cutoff_for(delivery_day, cutoff_time)
    chosen = forecast_as_at(forecasts, cutoff).rename(
        columns={"startTime": "hour", "generation": "forecast"}
    )

    frame = pd.DataFrame({"hour": delivery_hours(delivery_day)})
    frame = frame.merge(chosen[["hour", "forecast", "publishTime"]], on="hour", how="left")
    frame = frame.merge(actuals_hourly, on="hour", how="left")

    frame["error"] = frame["forecast"] - frame["actual"]
    frame["lead_hours"] = (frame["hour"] - cutoff).dt.total_seconds() / 3600
    frame["cutoff"] = cutoff
    return frame
