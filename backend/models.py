from datetime import date, datetime

from pydantic import BaseModel


class Summary(BaseModel):
    hours: int
    coverage: float
    mean_actual: float | None = None
    mean_forecast: float | None = None
    mae: float | None = None
    rmse: float | None = None
    rmse_over_mae: float | None = None
    bias: float | None = None
    wape: float | None = None
    p90_absolute_error: float | None = None
    p10_error: float | None = None
    p90_error: float | None = None
    mwh_exposure: float | None = None


class HorizonBand(Summary):
    band: str


class SweepRow(Summary):
    label: str
    cutoff: str


class HistogramBin(BaseModel):
    from_mw: int
    to_mw: int
    hours: int


class DaySummary(BaseModel):
    delivery_day: date
    forecast_mwh: float | None = None
    actual_mwh: float | None = None
    mae: float | None = None
    bias: float | None = None
    coverage: float


class HourRow(BaseModel):
    hour: datetime
    forecast: float | None = None
    actual: float | None = None
    error: float | None = None
    lead_hours: float
    published: datetime | None = None


class Purchase(BaseModel):
    forecast_mwh: float
    expected_mwh: float
    low_mwh: float
    high_mwh: float
    correction_factor: float


class DayDetail(BaseModel):
    delivery_day: date
    cutoff: datetime
    published: datetime | None = None
    hours: list[HourRow]
    summary: Summary
    purchase: Purchase | None = None


class Accuracy(BaseModel):
    cutoff: str
    correction_factor: float
    raw: Summary
    corrected: Summary
    raw_by_horizon: list[HorizonBand]
    corrected_by_horizon: list[HorizonBand]
    histogram: list[HistogramBin]
