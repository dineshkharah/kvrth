from datetime import time

import analysis
import loader
import metrics

CUTOFFS = [
    ("07:30 run only", time(7, 30)),
    ("09:20 EPEX gate", time(9, 20)),
    ("09:50 N2EX gate", time(9, 50)),
    ("11:30 after the gate", time(11, 30)),
    ("final, hindsight", None),
]


def line(label, summary):
    print(
        f"  {label:22} "
        f"mae {summary['mae']:7.0f}   "
        f"rmse {summary['rmse']:7.0f}   "
        f"bias {summary['bias']:+8.0f}   "
        f"wape {summary['wape']:6.1%}   "
        f"hours {summary['hours']:4d}"
    )


def main():
    hourly = analysis.to_hourly(loader.actuals())
    forecasts = loader.forecasts()

    print("January 2026, GB wind, forecast minus delivered")
    print("positive bias means the forecast was high, so the desk under bought gas")
    print()

    print("what the desk could actually see, by cutoff")
    views = {}
    for label, cutoff_time in CUTOFFS:
        views[label] = analysis.month_view(hourly, forecasts, cutoff_time=cutoff_time)
        line(label, metrics.summarise(views[label]))
    print()

    gate = views["09:20 EPEX gate"]
    raw = metrics.summarise(gate)
    factor = metrics.correction_factor(gate)
    corrected = metrics.summarise(metrics.apply_correction(gate, factor))

    print("splitting the 09:20 error into the part you can fix and the part you cannot")
    line("raw", raw)
    line(f"scaled by {factor:.3f}", corrected)
    print(f"  removing the level difference cuts mae by {1 - corrected['mae'] / raw['mae']:.0%}")
    print()

    # a lead band is also a block of the clock, so raw error only shows curtailment being worst overnight
    print("error by lead time, before and after removing the level difference")
    print("  (12 to 18 hours ahead is midnight to 03:00, 30 to 42 is 16:00 to 23:00)")
    for band in metrics.by_horizon(gate):
        line("raw " + band["band"], band)
    for band in metrics.by_horizon(metrics.apply_correction(gate, factor)):
        line("corrected " + band["band"], band)
    print()

    print("sizing the hedge from the 09:20 error spread")
    print(f"  p10 to p90 signed error : {raw['p10_error']:+.0f} to {raw['p90_error']:+.0f} MW")
    print(f"  p90 absolute error      : {raw['p90_absolute_error']:.0f} MW")
    print(f"  total exposure          : {raw['mwh_exposure']:,.0f} MWh over the month")


if __name__ == "__main__":
    main()
