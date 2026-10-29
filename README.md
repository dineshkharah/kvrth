# Windsight

Wind generation forecasts for a GB day ahead power purchasing desk, scored against what the desk could actually see when it had to buy.

**Live app: https://kvrth.vercel.app**

## The problem

A UK supplier buys tomorrow's electricity in a day ahead auction that closes at 09:20 today. How much thermal generation they need to buy depends on how much wind they expect, so the purchase hangs on a wind forecast. If they overestimate wind they under buy gas, end up short at delivery, and have to cover the gap at the imbalance price, which in a tight hour runs far above the day ahead price.

This app does two things. It shows the wind forecast as it stood at the moment the buying decision had to be made, and it scores how accurate those forecasts turned out to be, so the known error can be priced into the decision.

Scope is GB national level, wind only, Elexon BMRS data only, January 2026 delivery days.

## The thing that makes the numbers mean something

Elexon republishes its wind forecast eight times a day, at 02:30, 04:30, 07:30, 09:30, 11:30, 15:30, 18:30 and 22:30 UTC. A forecast for a given hour therefore exists in many versions, each better than the last, and the final version is published roughly thirteen hours **after** the hour it describes.

Scoring accuracy against that final version measures hindsight. The desk never saw it. Here is the timeline for delivery on Thursday 15 January:

```
WEDNESDAY 14 JAN
  02:30   forecast published
  04:30   forecast published
  07:30   forecast published   (the newest one that exists at the gate)
  09:20   gate closes, the desk buys
  09:30   forecast published   (ten minutes too late)
  ...
THURSDAY 15 JAN
          delivery
  later   revisions continue, final version lands well after the fact
```

Every number in this app is built from forecasts with a `publishTime` at or before the cutoff. The cutoff defaults to 09:20 and is adjustable in the interface, including a "final forecast" setting that deliberately breaks the rule so you can see how much it flatters the result.

It flatters it by about 18 percent. Measured honestly the mean absolute error is 2142 MW. Scored against the final forecast it looks like 1767 MW.

### Why 09:20

The EPEX SPOT GB day ahead auction closes at 09:20 UK time. Nord Pool's N2EX closes at 09:50. Both are selectable.

11:00 is a common wrong answer. It was correct before Brexit, when GB participated in the European Single Day Ahead Coupling, whose gate closes at 12:00 CET. GB decoupled on 31 December 2020 and the auction moved earlier so participants can see interconnector capacity results before bidding.

## What the January 2026 data shows

All figures in MW, error defined as forecast minus delivered, across 744 delivery hours with no gaps.

| Cutoff | MAE | RMSE | Bias | WAPE |
|---|---|---|---|---|
| 07:30, last run before the gate | 2142 | 2612 | +1852 | 18.5% |
| 09:20, EPEX gate closure | 2142 | 2612 | +1852 | 18.5% |
| 09:50, N2EX gate closure | 2123 | 2617 | +1840 | 18.3% |
| 11:30, after the gate | 2018 | 2477 | +1806 | 17.4% |
| Final forecast, hindsight | 1767 | 2263 | +1597 | 15.3% |

The first two rows are identical, which is the point working correctly: at a 09:20 cutoff the newest admissible run is the 07:30 one. Moving the cutoff to 09:50 reaches a run published two hours later and buys under one percent of accuracy, which is a smaller effect than it first appears.

### The forecast runs about 14 percent above delivered wind

The bias is large and one directional. Scaling every forecast by **0.862** takes the bias to zero and cuts MAE from 2142 to **1230**, a 43 percent reduction.

That gap is not weather forecasting error. It is still there in the final revision, published after the weather has happened, when there is nothing left to forecast. Two explanations were tested:

- **A fleet coverage difference**, where WINDFOR forecasts more wind farms than FUELHH meters. This does not fit. The gap roughly doubles overnight, about 2200 MW between midnight and 06:00 against about 1100 MW at midday, whereas a coverage difference would be a constant proportion all day. More decisively, 4 to 6 January have daily ratios of 0.95 and 0.96, and delivered output cannot exceed forecast across a whole day if the forecast simply counts more turbines.
- **Curtailment**, where wind farms are paid to reduce output when the network cannot carry the power or demand is too low. This fits: worst overnight, worst on the windiest days, 1.36 on 11 January and 1.30 on 12 January.

So WINDFOR appears to forecast *available* wind while FUELHH meters *delivered* wind. This is strong circumstantial evidence rather than proof. Confirming it would need Bid Offer Acceptance data to measure curtailment volumes directly, which falls outside the stated scope of wind only and these two datasets.

For the desk the practical consequence is the useful part. Roughly 43 percent of the apparent forecast error is a systematic level difference that can simply be subtracted. The rest is genuine weather uncertainty that has to be hedged.

### The lead time chart is misleading unless you correct the level first

Every delivery day shares the same cutoff, so lead time and hour of day are the same variable. The lead bands are blocks of the clock:

| Lead band | Delivery hours | Raw MAE | Corrected MAE |
|---|---|---|---|
| 12 to 18 hours | 00:00 to 03:00 | 2345 | 1057 |
| 18 to 24 hours | 04:00 to 09:00 | 2346 | 1160 |
| 24 to 30 hours | 10:00 to 15:00 | 2005 | 1280 |
| 30 to 42 hours | 16:00 to 23:00 | 1991 | 1332 |

On the raw figures the error *falls* the further ahead the forecast reaches, which is backwards for any forecast. It is not a forecasting result at all, it is curtailment being worst overnight. Remove the level difference and the expected shape appears, rising about 26 percent from the nearest band to the furthest. Both versions are shown in the app side by side, because the contrast is the finding.

## Metrics, and one that was rejected

Reported: MAE, RMSE, the RMSE over MAE ratio as a fat tail indicator, bias as mean signed error, WAPE, p90 absolute error, the p10 to p90 band, and total MWh exposure.

**MAPE is deliberately excluded.** GB wind falls to a few hundred MW in calm hours, and dividing by a near zero denominator produces values that swamp the average, so MAPE would be driven almost entirely by a handful of low wind hours. It is also asymmetric, unbounded when the forecast is high and capped at 100 percent when it is low, which quietly rewards forecasting low. WAPE, total absolute error over total delivered output, fixes both.

Sign convention throughout: **error = forecast minus delivered**. Positive means the forecast ran high, so too little thermal generation was bought.

## Running it

### With Docker, which is the shortest path

```
docker compose up
```

Serves the app on `http://localhost:5173` with the API on `http://localhost:8000`. Both containers mount the source from the host, so edits reload without a rebuild.

```
docker compose run --rm test    the test suite, in the container
docker compose run --rm etl     refetches the Elexon data, in the container
```

**Docker is not the deployment artifact here, and it is worth being straight about that.** Vercel builds in its own container runtime and never consumes these images. What Docker does in this project is give those three commands a fixed environment: the same Python 3.14 and Node 24 as the host machine, the same pinned package versions, running on Linux rather than Windows. The test suite passing identically in both places, and the containerised fetch producing byte for byte identical CSVs to the committed ones, is the evidence that it earns its place rather than decorating the repo.

### Without Docker

Requires Python 3.14 and Node 20 or later.

**Backend**

```
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt
cd backend
../.venv/Scripts/python.exe -m uvicorn main:app --reload --port 8000
```

On macOS or Linux the interpreter is at `.venv/bin/python` instead.

Generated API documentation is served at `http://localhost:8000/api/docs`.

**Frontend**

```
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The dev server proxies `/api` to port 8000.

**Tests**

```
cd backend
../.venv/Scripts/python.exe -m pytest -q
```

36 tests. `pytest.ini` sets `filterwarnings = error`, so any new warning fails the run.

**Refreshing the data**

The January 2026 data is committed, so the app needs no network access to run. To pull it again:

```
cd backend
../.venv/Scripts/python.exe scripts/fetch_data.py
```

**The analysis as a terminal report**

```
cd backend
../.venv/Scripts/python.exe -m scripts.report
```

Prints every table in this README from the committed data.

## Files and directories

```
backend/                  the Python service, and the root of the api service on Vercel
  main.py                 FastAPI app and the four endpoints
  models.py               Pydantic response models, which also generate the API docs
  loader.py               reads the CSVs into pandas and caches them
  analysis.py             the point in time join: gate closure, vintage selection, hourly alignment
  metrics.py              MAE, RMSE, bias, WAPE, the level correction, lead time bands, histogram
  data/
    actuals_wind.csv      FUELHH wind output, 1488 half hourly rows for January 2026
    forecasts_wind.csv    WINDFOR forecasts, 19272 rows across 264 publication runs
  scripts/
    fetch_data.py         pulls both datasets from Elexon and writes the CSVs
    report.py             prints the whole analysis to the terminal
  tests/                  36 tests across the join, the metrics and the API
  requirements.txt        runtime dependencies, which is what gets deployed
  requirements-dev.txt    adds uvicorn, pytest, requests and httpx
  pytest.ini              test discovery and the warnings policy
  .python-version         pins Python 3.14

frontend/                 the React app, and the root of the web service on Vercel
  src/
    App.tsx               shell and the two tabs
    DecisionView.tsx      day and cutoff pickers, purchase range, hourly chart and table
    AccuracyView.tsx      cutoff sweep, level correction, lead time bands, error histogram
    api.ts                response types mirrored from the Pydantic models, fetch hook, formatters
    ui.tsx                panel, stat tile, form controls, loading and failure states
    index.css             Tailwind entry point and the colour tokens
  vite.config.ts          React and Tailwind plugins, and the dev proxy to port 8000

docker/
  backend.Dockerfile      python:3.14-slim, installs the dev requirements, runs uvicorn
  frontend.Dockerfile     node:24-alpine, installs from the lockfile, runs the dev server
docker-compose.yml        four services: backend, frontend, test and etl
vercel.json               declares the two services and routes /api to Python
```

The `test` and `etl` services share the backend image and sit behind a `tools` profile, so `docker compose up` starts only the two long running containers and the other two are reached with `docker compose run`.

The Dockerfiles live in `docker/` rather than in each service root on purpose. Vercel treats a service root as a project and can read a `Dockerfile` there as the entrypoint, which switches that service to the container runtime instead of its detected framework. Keeping them out of the way removes the ambiguity.

## Architecture

One Vercel project running two services. `vercel.json` sends anything under `/api` to the Python service and everything else to the React build, so both sit on one domain with no CORS. FastAPI's `app` object is an ASGI application, which is the interface Vercel drives directly, so the same object runs locally under uvicorn and in production with no adapter.

The January data is fetched once and committed rather than pulled live. The analysis window is a fixed historical month, so there is nothing to refresh between requests; it removes a third party from the request path, makes the results reproducible by anyone who clones the repo, and gives the tests fixed inputs. `scripts/fetch_data.py` is the documented way to regenerate it.

Month views are cached in memory per cutoff, which helps while a serverless container stays warm but is never relied on, since the container can be discarded at any point.

### Endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/days?cutoff=09:20` | every delivery day with forecast MWh, delivered MWh, MAE, bias and coverage |
| `GET /api/days/{date}?cutoff=09:20` | 24 hourly rows, the cutoff, which forecast run was used, the day summary and the purchase range |
| `GET /api/accuracy?cutoff=09:20` | raw and corrected month metrics, both lead time tables, the error histogram |
| `GET /api/accuracy/cutoff-sweep` | every cutoff including the hindsight baseline |

`cutoff` accepts `HH:MM` or the word `final`. Anything else returns 400. A date outside January 2026 returns 404.

### Data handling

Hours missing either a forecast or a delivered value are dropped and reported through a `coverage` figure rather than filled with zeros. January 2026 has complete coverage, so this never triggers, but filling gaps silently would corrupt the metrics on any window that did have them.

WINDFOR is hourly and FUELHH is half hourly. The two half hourly readings are averaged up to the hour rather than the forecast being interpolated down, because the GB day ahead product is a 60 minute contract, so the analysis runs at the resolution of the thing being purchased. Interpolating the forecast downward would invent precision the forecaster never published.

All times are handled as timezone aware UTC. The cutoff is constructed in `Europe/London` and converted, so it is 09:20 UTC in winter and 08:20 UTC in summer. January 2026 contains no clock change, but `delivery_hours` correctly returns 23 hours on 29 March and 25 on 25 October, and both cases are tested.

## Testing

36 tests, weighted towards the logic that would be hardest to notice if it broke.

The load bearing one asserts that a 09:20 cutoff on 15 January resolves every hour to the forecast published at 07:30 on 14 January, using the real committed data. A separate test asserts the invariant directly: no row with a `publishTime` later than the cutoff can ever be selected.

There is also a structural check worth mentioning. The hindsight baseline must score *better* than the gate closure figure. If it ever scored worse, the point in time join would be inverted and every number in the app would be wrong. That is asserted in `test_api.py`.

The metrics are checked against values worked out by hand rather than against the implementation's own output.

## Cut on purpose

With more time, in roughly this order:

- **Curtailment confirmed rather than inferred.** Bid Offer Acceptance data would measure it directly instead of leaving it as the best explanation for the 14 percent gap.
- **Money.** Error is reported in MW and MWh. Converting exposure into pounds needs imbalance price data, which the scope excludes, and it is the number a trading desk actually wants.
- **Out of sample validation of the correction.** The 0.862 factor is fitted on the same month it is scored against, which overstates how well it would do on unseen days. A rolling fit over a longer window would be honest.
- **More than one month.** A single January cannot separate seasonal effects from structural ones.
- **Probabilistic forecasts.** The p10 to p90 band is derived from historical error spread, not from an ensemble.

Also deliberately out of scope, as the brief directed: regional or per power station breakdown, live data for the current day, authentication, the intraday market, demand forecasting, fuel types other than wind, and a database, since two CSV files under 1 MB do not need one.

## AI tools

AI assistance was used extensively throughout this project, including for most of the implementation code across both the Python backend and the React frontend.

What I directed and decided: the domain research and the choice of 09:20 as the cutoff, the decision to measure against delivered rather than available wind, the metric selection and the reasoning for excluding MAPE, the decision to average actuals up to hourly rather than interpolate forecasts down, the investigation into the 14 percent gap, the scope boundaries, and what to cut.

What I verified independently: I re ran the Elexon queries directly against the API to confirm the dataset shapes and publication cadence rather than taking them on trust, checked the 09:20 to 07:30 vintage selection against the raw data by hand, and confirmed the hindsight baseline scores better than the gate closure baseline, which is the check that would have caught an inverted join.

The lead time confound was found by questioning a result that looked wrong rather than accepting it: the raw chart showed error falling with lead time, which cannot be right, and the investigation into why produced the correction described above.

## Time spent

Built across two days, against the 16 hour guideline.

Python as a backend language, Docker and automated testing were all new to me at the start of this project, which shaped the pace. The commit history is genuine and unedited.
