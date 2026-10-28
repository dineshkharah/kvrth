import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_every_delivery_day_in_january_is_listed():
    body = client.get("/api/days").json()
    assert len(body) == 31
    assert body[0]["delivery_day"] == "2026-01-01"
    assert body[-1]["delivery_day"] == "2026-01-31"


def test_a_day_is_served_as_twenty_four_hours():
    body = client.get("/api/days/2026-01-15").json()
    assert len(body["hours"]) == 24
    assert body["cutoff"] == "2026-01-14T09:20:00Z"


def test_the_day_reports_which_forecast_run_it_used():
    body = client.get("/api/days/2026-01-15").json()
    assert body["published"] == "2026-01-14T07:30:00Z"


def test_asking_for_the_n2ex_gate_reaches_a_later_run():
    body = client.get("/api/days/2026-01-15", params={"cutoff": "09:50"}).json()
    assert body["published"] == "2026-01-14T09:30:00Z"


def test_a_day_outside_the_pilot_window_is_not_found():
    assert client.get("/api/days/2025-06-01").status_code == 404


def test_a_cutoff_that_is_not_a_time_is_rejected():
    assert client.get("/api/accuracy", params={"cutoff": "banana"}).status_code == 400


def test_the_correction_removes_the_bias_through_the_api():
    body = client.get("/api/accuracy").json()
    assert body["raw"]["bias"] > 1000
    assert body["corrected"]["bias"] == pytest.approx(0, abs=1)


def test_hindsight_scores_better_than_gate_closure():
    sweep = {row["cutoff"]: row for row in client.get("/api/accuracy/cutoff-sweep").json()}
    assert sweep["final"]["mae"] < sweep["09:20"]["mae"]


def test_the_purchase_range_brackets_the_expected_volume():
    purchase = client.get("/api/days/2026-01-15").json()["purchase"]
    assert purchase["low_mwh"] < purchase["expected_mwh"] < purchase["high_mwh"]
    assert purchase["expected_mwh"] < purchase["forecast_mwh"]
