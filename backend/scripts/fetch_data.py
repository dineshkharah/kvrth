import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

FIRST_DELIVERY_DAY = date(2026, 1, 1)
LAST_DELIVERY_DAY = date(2026, 1, 31)

# forecasts start two days early so the gate closure before 1 January is covered
FORECAST_FROM = "2025-12-30T00:00Z"
FORECAST_TO = "2026-02-01T00:00Z"

ATTEMPTS = 3


def fetch(dataset, params):
    url = f"{BASE}/{dataset}/stream"
    for attempt in range(1, ATTEMPTS + 1):
        try:
            response = requests.get(url, params=params, timeout=120)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as error:
            if attempt == ATTEMPTS:
                raise
            print(f"  attempt {attempt} failed ({error}), retrying")
            time.sleep(attempt * 2)


def fetch_actuals():
    rows = fetch(
        "FUELHH",
        {
            "settlementDateFrom": FIRST_DELIVERY_DAY.isoformat(),
            "settlementDateTo": LAST_DELIVERY_DAY.isoformat(),
            "fuelType": "WIND",
        },
    )
    frame = pd.DataFrame(rows)[
        ["startTime", "settlementDate", "settlementPeriod", "generation"]
    ]
    return frame.sort_values("startTime").reset_index(drop=True)


def fetch_forecasts():
    rows = fetch(
        "WINDFOR",
        {"publishDateTimeFrom": FORECAST_FROM, "publishDateTimeTo": FORECAST_TO},
    )
    frame = pd.DataFrame(rows)[["publishTime", "startTime", "generation"]]
    return frame.sort_values(["publishTime", "startTime"]).reset_index(drop=True)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    days = (LAST_DELIVERY_DAY - FIRST_DELIVERY_DAY).days + 1

    print("fetching actual wind output")
    actuals = fetch_actuals()
    actuals.to_csv(DATA_DIR / "actuals_wind.csv", index=False)
    print(f"  {len(actuals)} half hourly rows, expected {days * 48}")

    print("fetching wind forecasts")
    forecasts = fetch_forecasts()
    forecasts.to_csv(DATA_DIR / "forecasts_wind.csv", index=False)
    runs = forecasts["publishTime"].nunique()
    print(f"  {len(forecasts)} rows across {runs} forecast runs")


if __name__ == "__main__":
    main()
