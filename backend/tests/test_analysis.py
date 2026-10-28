from datetime import date

import pandas as pd
import pytest

import analysis
import loader


def ts(text):
    return pd.Timestamp(text, tz="UTC")


def forecast_rows(rows):
    return pd.DataFrame(
        [
            {"publishTime": ts(published), "startTime": ts(target), "generation": value}
            for published, target, value in rows
        ]
    )


def actual_rows(rows):
    return pd.DataFrame(
        [{"startTime": ts(start), "generation": value} for start, value in rows]
    )


def test_cutoff_is_0920_on_the_day_before_delivery():
    assert analysis.cutoff_for(date(2026, 1, 5)) == ts("2026-01-04T09:20:00Z")


def test_cutoff_follows_uk_clocks_not_utc():
    # July is BST, so 09:20 London is 08:20 UTC
    assert analysis.cutoff_for(date(2026, 7, 5)) == ts("2026-07-04T08:20:00Z")


def test_a_delivery_day_has_twenty_four_hours():
    hours = analysis.delivery_hours(date(2026, 1, 5))
    assert len(hours) == 24
    assert hours[0] == ts("2026-01-05T00:00:00Z")
    assert hours[-1] == ts("2026-01-05T23:00:00Z")


def test_clock_change_days_are_not_twenty_four_hours():
    assert len(analysis.delivery_hours(date(2026, 3, 29))) == 23
    assert len(analysis.delivery_hours(date(2026, 10, 25))) == 25


def test_picks_the_0730_run_and_not_the_0930_one():
    forecasts = forecast_rows(
        [
            ("2026-01-04T07:30:00Z", "2026-01-05T12:00:00Z", 5000),
            ("2026-01-04T09:30:00Z", "2026-01-05T12:00:00Z", 9999),
        ]
    )
    chosen = analysis.forecast_as_at(forecasts, analysis.cutoff_for(date(2026, 1, 5)))
    assert chosen["generation"].tolist() == [5000]


def test_nothing_published_after_the_cutoff_can_ever_be_used():
    cutoff = analysis.cutoff_for(date(2026, 1, 5))
    forecasts = forecast_rows(
        [
            ("2026-01-04T02:30:00Z", "2026-01-05T00:00:00Z", 100),
            ("2026-01-04T09:30:00Z", "2026-01-05T00:00:00Z", 200),
            ("2026-01-05T22:30:00Z", "2026-01-05T00:00:00Z", 300),
        ]
    )
    chosen = analysis.forecast_as_at(forecasts, cutoff)
    assert (chosen["publishTime"] <= cutoff).all()


def test_the_newest_eligible_run_wins():
    forecasts = forecast_rows(
        [
            ("2026-01-04T02:30:00Z", "2026-01-05T06:00:00Z", 100),
            ("2026-01-04T07:30:00Z", "2026-01-05T06:00:00Z", 300),
            ("2026-01-04T04:30:00Z", "2026-01-05T06:00:00Z", 200),
        ]
    )
    chosen = analysis.forecast_as_at(forecasts, analysis.cutoff_for(date(2026, 1, 5)))
    assert chosen["generation"].tolist() == [300]


def test_the_chosen_row_keeps_its_own_publish_time():
    forecasts = forecast_rows(
        [
            ("2026-01-04T02:30:00Z", "2026-01-05T06:00:00Z", 100),
            ("2026-01-04T07:30:00Z", "2026-01-05T06:00:00Z", 300),
        ]
    )
    chosen = analysis.forecast_as_at(forecasts, analysis.cutoff_for(date(2026, 1, 5)))
    row = chosen.iloc[0]
    assert row["generation"] == 300
    assert row["publishTime"] == ts("2026-01-04T07:30:00Z")


def test_two_half_hours_average_into_one_hour():
    actuals = actual_rows(
        [("2026-01-05T00:00:00Z", 1000), ("2026-01-05T00:30:00Z", 2000)]
    )
    hourly = analysis.to_hourly(actuals)
    assert hourly["actual"].tolist() == [1500]
    assert hourly["periods"].tolist() == [2]


def test_a_lone_half_hour_is_flagged_by_its_period_count():
    actuals = actual_rows([("2026-01-05T00:00:00Z", 1000)])
    hourly = analysis.to_hourly(actuals)
    assert hourly["periods"].tolist() == [1]


def test_over_forecasting_gives_a_positive_error():
    forecasts = forecast_rows([("2026-01-04T07:30:00Z", "2026-01-05T00:00:00Z", 1200)])
    hourly = analysis.to_hourly(
        actual_rows([("2026-01-05T00:00:00Z", 1000), ("2026-01-05T00:30:00Z", 1000)])
    )
    view = analysis.day_view(hourly, forecasts, date(2026, 1, 5))
    assert view.loc[0, "error"] == 200


def test_a_missing_forecast_leaves_a_gap_rather_than_a_zero():
    forecasts = forecast_rows([("2026-01-04T07:30:00Z", "2026-01-05T00:00:00Z", 1200)])
    hourly = analysis.to_hourly(
        actual_rows([("2026-01-05T05:00:00Z", 900), ("2026-01-05T05:30:00Z", 900)])
    )
    view = analysis.day_view(hourly, forecasts, date(2026, 1, 5))
    assert len(view) == 24
    assert pd.isna(view.loc[5, "forecast"])
    assert pd.isna(view.loc[5, "error"])
    assert view.loc[5, "actual"] == 900


def test_lead_time_spans_the_delivery_day():
    forecasts = forecast_rows([("2026-01-04T07:30:00Z", "2026-01-05T00:00:00Z", 1)])
    hourly = analysis.to_hourly(actual_rows([("2026-01-05T00:00:00Z", 1)]))
    view = analysis.day_view(hourly, forecasts, date(2026, 1, 5))
    assert view["lead_hours"].iloc[0] == pytest.approx(14 + 40 / 60)
    assert view["lead_hours"].iloc[-1] == pytest.approx(37 + 40 / 60)


def test_against_the_real_january_data():
    """The 09:20 cutoff should land on the 07:30 run, which is the whole point."""
    view = analysis.day_view(
        analysis.to_hourly(loader.actuals()), loader.forecasts(), date(2026, 1, 15)
    )
    assert len(view) == 24
    assert view["forecast"].notna().all()
    assert view["actual"].notna().all()
    assert (view["publishTime"] == ts("2026-01-14T07:30:00Z")).all()
