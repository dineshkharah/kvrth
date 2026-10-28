import pandas as pd
import pytest

import metrics


def view(forecasts, actuals, leads=None):
    frame = pd.DataFrame({"forecast": forecasts, "actual": actuals})
    frame["error"] = frame["forecast"] - frame["actual"]
    frame["lead_hours"] = leads if leads is not None else list(range(len(frame)))
    return frame


# forecasts 110, 90, 120 against a flat 100 give errors of 10, -10 and 20
SIMPLE = view([110, 90, 120], [100, 100, 100])


def test_mae_is_the_average_miss_ignoring_direction():
    assert metrics.summarise(SIMPLE)["mae"] == pytest.approx(40 / 3)


def test_rmse_punishes_the_big_miss_harder_than_mae():
    assert metrics.summarise(SIMPLE)["rmse"] == pytest.approx(200**0.5)


def test_bias_keeps_the_direction():
    assert metrics.summarise(SIMPLE)["bias"] == pytest.approx(20 / 3)


def test_wape_is_total_miss_over_total_delivered():
    assert metrics.summarise(SIMPLE)["wape"] == pytest.approx(40 / 300)


def test_rmse_over_mae_flags_fat_tails():
    summary = metrics.summarise(SIMPLE)
    assert summary["rmse_over_mae"] == pytest.approx(summary["rmse"] / summary["mae"])


def test_exposure_sums_the_misses_because_an_hour_of_mw_is_mwh():
    assert metrics.summarise(SIMPLE)["mwh_exposure"] == pytest.approx(40)


def test_hours_with_a_missing_side_are_dropped_and_reported_as_coverage():
    frame = view([110, None, 120], [100, 100, None])
    summary = metrics.summarise(frame)
    assert summary["hours"] == 1
    assert summary["coverage"] == pytest.approx(1 / 3)


def test_nothing_to_score_does_not_explode():
    summary = metrics.summarise(view([None], [None]))
    assert summary["hours"] == 0


def test_the_correction_factor_scales_forecast_onto_delivered():
    assert metrics.correction_factor(SIMPLE) == pytest.approx(300 / 320)


def test_applying_the_correction_removes_the_bias():
    corrected = metrics.apply_correction(SIMPLE, metrics.correction_factor(SIMPLE))
    assert metrics.summarise(corrected)["bias"] == pytest.approx(0)


def test_the_correction_does_not_remove_the_random_part():
    corrected = metrics.apply_correction(SIMPLE, metrics.correction_factor(SIMPLE))
    assert metrics.summarise(corrected)["mae"] > 0


def test_horizon_bands_split_by_lead_time():
    frame = view([110] * 4, [100] * 4, leads=[13, 19, 25, 31])
    bands = metrics.by_horizon(frame)
    assert len(bands) == 4
    assert bands[0]["band"] == "12 to 18 hours ahead"
    assert all(band["hours"] == 1 for band in bands)


def test_the_histogram_counts_every_scored_hour():
    frame = view([1100, 900, 1200], [1000, 1000, 1000])
    assert sum(row["hours"] for row in metrics.error_histogram(frame)) == 3
