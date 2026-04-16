from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from scipy.stats import norm

from python_solvers.mcp_utils import load_dataframe_from_path


def _normalize_freq(value: str | None) -> str:
    freq = (value or "D").strip().upper()
    alias = {
        "DAY": "D",
        "DAILY": "D",
        "WEEK": "W",
        "WEEKLY": "W",
        "MONTH": "MS",
        "MONTHLY": "MS",
        "HOUR": "H",
        "HOURLY": "H",
    }
    return alias.get(freq, freq)


def _find_ci_columns(df: pd.DataFrame, model_col: str, level: int) -> tuple[str | None, str | None]:
    lower_keys = (
        f"{model_col}-lo-{level}",
        f"{model_col}-lo-{float(level):.1f}",
        f"{model_col}-lower-{level}",
        f"{model_col}-lower-{float(level):.1f}",
    )
    upper_keys = (
        f"{model_col}-hi-{level}",
        f"{model_col}-hi-{float(level):.1f}",
        f"{model_col}-upper-{level}",
        f"{model_col}-upper-{float(level):.1f}",
    )

    lower_col = next((c for c in lower_keys if c in df.columns), None)
    upper_col = next((c for c in upper_keys if c in df.columns), None)
    return lower_col, upper_col


def _prepare_series(
    file_path: str,
    time_col: str,
    target_col: str,
    item_col: str | None = None,
) -> tuple[pd.DataFrame, Path]:
    raw_df, src = load_dataframe_from_path(file_path)
    if time_col not in raw_df.columns:
        raise ValueError(f"time_col not found: {time_col}")
    if target_col not in raw_df.columns:
        raise ValueError(f"target_col not found: {target_col}")

    work = raw_df.copy()
    work[time_col] = pd.to_datetime(work[time_col], errors="coerce")
    work[target_col] = pd.to_numeric(work[target_col], errors="coerce")
    work = work.dropna(subset=[time_col, target_col])
    if work.empty:
        raise ValueError("No valid rows after parsing time/target columns.")

    if item_col and item_col in work.columns:
        work[item_col] = work[item_col].astype(str)
        grouped = (
            work.groupby([item_col, time_col], as_index=False)[target_col]
            .sum()
            .rename(columns={item_col: "unique_id", time_col: "ds", target_col: "y"})
        )
    else:
        grouped = (
            work.groupby([time_col], as_index=False)[target_col]
            .sum()
            .rename(columns={time_col: "ds", target_col: "y"})
        )
        grouped["unique_id"] = "all"

    grouped = grouped[["unique_id", "ds", "y"]].sort_values(["unique_id", "ds"]).reset_index(drop=True)
    return grouped, src


def _fallback_forecast(
    series_df: pd.DataFrame,
    horizon: int,
    level: int,
    freq: str,
) -> List[Dict[str, Any]]:
    z = float(norm.ppf(0.5 + (level / 200.0)))
    freq_value = _normalize_freq(freq)

    rows: List[Dict[str, Any]] = []
    for unique_id, group in series_df.groupby("unique_id"):
        ordered = group.sort_values("ds")
        values = ordered["y"].astype(float).tolist()
        last_ds = pd.Timestamp(ordered["ds"].iloc[-1])
        last_value = float(values[-1])
        mean_value = float(sum(values) / len(values))
        variance = sum((v - mean_value) ** 2 for v in values) / max(1, len(values) - 1)
        sigma = variance ** 0.5

        for step in range(1, horizon + 1):
            point = max(0.0, last_value)
            ci_width = z * sigma * (step ** 0.5)
            lower = max(0.0, point - ci_width)
            upper = max(point, point + ci_width)
            rows.append(
                {
                    "item": str(unique_id),
                    "date": (last_ds + step * pd.tseries.frequencies.to_offset(freq_value)).isoformat(),
                    "point": point,
                    "lower": float(lower),
                    "upper": float(upper),
                    "recommended_demand": float(upper),
                }
            )

    return rows


def forecast_demand(
    file_path: str,
    time_col: str,
    target_col: str,
    item_col: str | None = None,
    horizon: int = 7,
    freq: str = "D",
    level: int = 95,
) -> Dict[str, Any]:
    statsforecast_available = True
    try:
        from statsforecast import StatsForecast
        from statsforecast.models import AutoARIMA
    except Exception:
        statsforecast_available = False

    if horizon <= 0:
        raise ValueError("horizon must be >= 1")
    if level <= 0 or level >= 100:
        raise ValueError("level must be between 1 and 99")

    series_df, src = _prepare_series(
        file_path=file_path,
        time_col=time_col,
        target_col=target_col,
        item_col=item_col,
    )

    rows: List[Dict[str, Any]]
    engine = "statsforecast-autoarima"
    if statsforecast_available:
        sf = StatsForecast(
            models=[AutoARIMA(season_length=7)],
            freq=_normalize_freq(freq),
            n_jobs=-1,
        )
        forecast_df = sf.forecast(df=series_df, h=int(horizon), level=[int(level)])

        model_col = "AutoARIMA"
        lower_col, upper_col = _find_ci_columns(forecast_df, model_col, int(level))

        rows = []
        for _, row in forecast_df.iterrows():
            point = float(row.get(model_col, 0.0) or 0.0)
            lower = float(row.get(lower_col, point) or point) if lower_col else point
            upper = float(row.get(upper_col, point) or point) if upper_col else point
            rows.append(
                {
                    "item": str(row.get("unique_id", "all")),
                    "date": pd.Timestamp(row.get("ds")).isoformat(),
                    "point": point,
                    "lower": lower,
                    "upper": upper,
                    "recommended_demand": upper,
                }
            )
    else:
        engine = "fallback-last-value"
        rows = _fallback_forecast(series_df=series_df, horizon=int(horizon), level=int(level), freq=freq)

    return {
        "ok": True,
        "file_name": src.name,
        "horizon": int(horizon),
        "freq": _normalize_freq(freq),
        "confidence_level": int(level),
        "series_count": int(series_df["unique_id"].nunique()),
        "engine": engine,
        "forecast_rows": rows,
    }