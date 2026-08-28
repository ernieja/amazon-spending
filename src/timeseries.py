"""
timeseries.py
Time-series decomposition and forecasting for the monthly spend series,
built on statsmodels.

  - decompose(): STL (Seasonal-Trend decomposition using LOESS), which is
    more robust to outlier months than a simple moving-average split -
    statsmodels.tsa.seasonal.STL.
  - forecast(): Holt-Winters (triple exponential smoothing) via
    statsmodels.tsa.holtwinters.ExponentialSmoothing, with a 95% prediction
    interval built from Monte Carlo simulation (fit.simulate(...)) rather
    than a closed-form formula, since simulation makes fewer distributional
    assumptions about a noisy, low-volume personal spend series.
"""

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.holtwinters import ExponentialSmoothing


def decompose(series: pd.Series, period: int = 12, robust: bool = True) -> pd.DataFrame:
    """Additive STL decomposition: series = trend + seasonal + resid.
    """
    if len(series) < 2 * period:
        raise ValueError(f"Need at least {2 * period} points for period={period}, got {len(series)}")
    result = STL(series, period=period, robust=robust).fit()
    return pd.DataFrame(
        {
            "observed": series.values,
            "trend": result.trend,
            "seasonal": result.seasonal,
            "resid": result.resid,
        },
        index=series.index,
    )


def fit_holt_winters(series: pd.Series, period: int = 12):
    """Fit additive-trend, additive-seasonality Holt-Winters via statsmodels."""
    model = ExponentialSmoothing(
        series, trend="add", seasonal="add", seasonal_periods=period, initialization_method="estimated"
    )
    return model.fit(optimized=True)


def forecast(fitted, steps: int, n_sims: int = 500, random_state: int = 0) -> pd.DataFrame:
    """Point forecast plus a simulation-based 95% interval.

    Simulates `n_sims` future paths from the fitted model's error
    distribution and takes the 2.5th/97.5th percentiles at each horizon,
    rather than assuming a closed-form Gaussian interval.
    """
    point = fitted.forecast(steps)
    sims = fitted.simulate(nsimulations=steps, repetitions=n_sims, error="add", random_state=random_state)
    lower = sims.quantile(0.025, axis=1)
    upper = sims.quantile(0.975, axis=1)
    return pd.DataFrame(
        {"forecast": point.values, "lower_95": lower.values, "upper_95": upper.values},
        index=point.index,
    )
