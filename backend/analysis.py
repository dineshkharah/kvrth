from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

UK = ZoneInfo("Europe/London")

# EPEX SPOT GB day ahead auction, moved here from 11:00 when GB left SDAC in 2020
GATE_CLOSURE = time(9, 20)

# stands in for no cutoff at all, used for the hindsight baseline
NO_CUTOFF = pd.Timestamp("2100-01-01", tz="UTC")

FIRST_DELIVERY_DAY = date(2026, 1, 1)
LAST_DELIVERY_DAY = date(2026, 1, 31)


def to_hourly(actuals):
    frame = actuals.copy()
    frame["hour"] = frame["startTime"].dt.floor("h")
    return frame.groupby("hour", as_index=False).agg(
        actual=("generation", "mean"), periods=("generation", "size")
    )


def cutoff_for(delivery_day, cutoff_time=GATE_CLOSURE):
    if cutoff_time is None:
        return NO_CUTOFF
    decision_day = delivery_day - timedelta(days=1)
    local = datetime.combine(decision_day, cutoff_time, tzinfo=UK)
    return pd.Timestamp(local).tz_convert("UTC")


def delivery_days(first=FIRST_DELIVERY_DAY, last=LAST_DELIVERY_DAY):
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def delivery_hours(delivery_day):
    start = pd.Timestamp(datetime.combine(delivery_day, time(0, 0), tzinfo=UK))
    end = pd.Timestamp(
        datetime.combine(delivery_day + timedelta(days=1), time(0, 0), tzinfo=UK)
    )
    return pd.date_range(
        start.tz_convert("UTC"), end.tz_convert("UTC"), freq="h", inclusive="left"
    )


def forecast_as_at(forecasts, cutoff):
    # drop_duplicates keeps whole rows, a groupby last picks each column separately and can mix two runs
    usable = forecasts[forecasts["publishTime"] <= cutoff]
    return usable.sort_values("publishTime").drop_duplicates("startTime", keep="last")


def day_view(actuals_hourly, forecasts, delivery_day, cutoff_time=GATE_CLOSURE):
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
    frame["delivery_day"] = delivery_day
    return frame


def month_view(actuals_hourly, forecasts, days=None, cutoff_time=GATE_CLOSURE):
    frames = [
        day_view(actuals_hourly, forecasts, day, cutoff_time)
        for day in (days or delivery_days())
    ]
    return pd.concat(frames, ignore_index=True)
