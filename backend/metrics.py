import pandas as pd

HORIZON_EDGES = (12, 18, 24, 30, 42)


def summarise(view):
    paired = view.dropna(subset=["forecast", "actual"])
    if paired.empty:
        return {"hours": 0, "coverage": 0.0}

    error = paired["error"]
    absolute = error.abs()
    mae = absolute.mean()
    rmse = (error**2).mean() ** 0.5

    return {
        "hours": int(len(paired)),
        "coverage": len(paired) / len(view),
        "mean_actual": paired["actual"].mean(),
        "mean_forecast": paired["forecast"].mean(),
        "mae": mae,
        "rmse": rmse,
        # above about 1.25 the errors are fat tailed, and imbalance cost rises faster than the size of the miss
        "rmse_over_mae": rmse / mae if mae else None,
        "bias": error.mean(),
        "wape": absolute.sum() / paired["actual"].sum(),
        "p90_absolute_error": absolute.quantile(0.9),
        "p10_error": error.quantile(0.1),
        "p90_error": error.quantile(0.9),
        "mwh_exposure": absolute.sum(),
    }


def correction_factor(view):
    # energy weighted, so calm hours with a near zero denominator cannot dominate it
    paired = view.dropna(subset=["forecast", "actual"])
    total = paired["forecast"].sum()
    return paired["actual"].sum() / total if total else 1.0


def apply_correction(view, factor):
    corrected = view.copy()
    corrected["forecast"] = corrected["forecast"] * factor
    corrected["error"] = corrected["forecast"] - corrected["actual"]
    return corrected


def by_horizon(view, edges=HORIZON_EDGES):
    frame = view.dropna(subset=["forecast", "actual"]).copy()
    frame["band"] = pd.cut(frame["lead_hours"], bins=list(edges), right=False)

    rows = []
    for band, group in frame.groupby("band", observed=True):
        row = summarise(group)
        row["band"] = f"{int(band.left)} to {int(band.right)} hours ahead"
        rows.append(row)
    return rows


def error_histogram(view, bin_width=500):
    error = view.dropna(subset=["forecast", "actual"])["error"]
    if error.empty:
        return []

    low = (error.min() // bin_width) * bin_width
    high = (error.max() // bin_width + 1) * bin_width
    edges = pd.interval_range(start=low, end=high, freq=bin_width)
    counts = pd.cut(error, bins=edges).value_counts().sort_index()

    return [
        {"from_mw": int(interval.left), "to_mw": int(interval.right), "hours": int(count)}
        for interval, count in counts.items()
    ]
