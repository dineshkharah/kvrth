from datetime import date, time

import pandas as pd
from fastapi import FastAPI, HTTPException

import analysis
import loader
import metrics
from models import (
    Accuracy,
    DayDetail,
    DaySummary,
    HistogramBin,
    HorizonBand,
    HourRow,
    Purchase,
    Summary,
    SweepRow,
)

# docs live under /api because only that prefix is routed to this service
app = FastAPI(
    title="Windsight API",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

SWEEP = [
    ("07:30 run only", "07:30"),
    ("09:20 EPEX gate closure", "09:20"),
    ("09:50 N2EX gate closure", "09:50"),
    ("11:30, after the gate", "11:30"),
    ("final forecast, hindsight", "final"),
]

_views = {}


def parse_cutoff(value):
    if value.lower() == "final":
        return None
    try:
        hour, minute = value.split(":")
        return time(int(hour), int(minute))
    except ValueError:
        raise HTTPException(400, f"cutoff must look like 09:20 or be final, got {value!r}")


def month(cutoff_time):
    key = cutoff_time.isoformat() if cutoff_time else "final"
    if key not in _views:
        hourly = analysis.to_hourly(loader.actuals())
        _views[key] = analysis.month_view(hourly, loader.forecasts(), cutoff_time=cutoff_time)
    return _views[key]


def blank_nans(record):
    return {key: (None if pd.isna(value) else value) for key, value in record.items()}


@app.get("/api/days", response_model=list[DaySummary])
def days(cutoff: str = "09:20"):
    view = month(parse_cutoff(cutoff))
    rows = []
    for day, group in view.groupby("delivery_day"):
        scored = group.dropna(subset=["forecast", "actual"])
        rows.append(
            DaySummary(
                delivery_day=day,
                forecast_mwh=group["forecast"].sum(),
                actual_mwh=group["actual"].sum(),
                mae=scored["error"].abs().mean() if len(scored) else None,
                bias=scored["error"].mean() if len(scored) else None,
                coverage=len(scored) / len(group),
            )
        )
    return rows


@app.get("/api/days/{delivery_day}", response_model=DayDetail)
def day(delivery_day: date, cutoff: str = "09:20"):
    cutoff_time = parse_cutoff(cutoff)
    view = month(cutoff_time)
    group = view[view["delivery_day"] == delivery_day]
    if group.empty:
        raise HTTPException(404, f"{delivery_day} is outside the pilot window")

    columns = ["hour", "forecast", "actual", "error", "lead_hours", "publishTime"]
    hours = []
    for record in group[columns].to_dict("records"):
        row = blank_nans(record)
        hours.append(
            HourRow(
                hour=row["hour"],
                forecast=row["forecast"],
                actual=row["actual"],
                error=row["error"],
                lead_hours=row["lead_hours"],
                published=row["publishTime"],
            )
        )

    summary = Summary(**blank_nans(metrics.summarise(group)))
    published = group["publishTime"].dropna()

    return DayDetail(
        delivery_day=delivery_day,
        cutoff=group["cutoff"].iloc[0],
        published=published.iloc[0] if len(published) else None,
        hours=hours,
        summary=summary,
        purchase=purchase_for(group, month(cutoff_time)),
    )


def purchase_for(group, whole_month):
    forecast_mwh = group["forecast"].sum()
    if not forecast_mwh:
        return None

    factor = metrics.correction_factor(whole_month)
    corrected_month = metrics.apply_correction(whole_month, factor)
    spread = metrics.summarise(corrected_month)
    scored = len(group.dropna(subset=["forecast"]))

    # errors inside one day share a weather system, so they are added rather than
    # treated as independent, which gives the wider and safer band
    return Purchase(
        forecast_mwh=forecast_mwh,
        expected_mwh=forecast_mwh * factor,
        low_mwh=forecast_mwh * factor - scored * spread["p90_error"],
        high_mwh=forecast_mwh * factor - scored * spread["p10_error"],
        correction_factor=factor,
    )


@app.get("/api/accuracy", response_model=Accuracy)
def accuracy(cutoff: str = "09:20"):
    view = month(parse_cutoff(cutoff))
    factor = metrics.correction_factor(view)
    corrected = metrics.apply_correction(view, factor)

    return Accuracy(
        cutoff=cutoff,
        correction_factor=factor,
        raw=Summary(**blank_nans(metrics.summarise(view))),
        corrected=Summary(**blank_nans(metrics.summarise(corrected))),
        raw_by_horizon=[HorizonBand(**blank_nans(band)) for band in metrics.by_horizon(view)],
        corrected_by_horizon=[
            HorizonBand(**blank_nans(band)) for band in metrics.by_horizon(corrected)
        ],
        histogram=[HistogramBin(**row) for row in metrics.error_histogram(view)],
    )


@app.get("/api/accuracy/cutoff-sweep", response_model=list[SweepRow])
def cutoff_sweep():
    rows = []
    for label, value in SWEEP:
        summary = metrics.summarise(month(parse_cutoff(value)))
        rows.append(SweepRow(label=label, cutoff=value, **blank_nans(summary)))
    return rows
