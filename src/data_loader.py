"""
data_loader.py
Single shared entry point for loading data/processed_orders.csv into the
app, so every page parses dates/builds the monthly series the same way
instead of each page re-implementing it slightly differently.
"""

import streamlit as st
import pandas as pd

PROCESSED_PATH = "data/processed_orders.csv"

# Monthly time-series work (STL decomposition, forecasting) starts in 2018:
# pre-2018 order volume is too sparse (as few as 1-2 orders/month) for
# monthly seasonality to mean anything -- see README for the full note.
TIMESERIES_START = "2018-01-01"


@st.cache_data
def load_orders() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED_PATH)
    df["Order Date"] = pd.to_datetime(df["Order Date"], format="ISO8601").dt.tz_localize(None)
    df["year"] = df["Order Date"].dt.year
    df["year_month"] = df["Order Date"].dt.to_period("M").dt.to_timestamp()
    return df


@st.cache_data
def annual_spend(_df: pd.DataFrame = None) -> pd.DataFrame:
    """Per-year gross spend, refunds, and net (gross - refunds).

    Gross sums line-item ``Total Amount``. ``refund_amount`` is order-level in
    the processed data (repeated across an order's line items), so it's summed
    once per unique Order ID and attributed to the year the order was *placed*.
    Refund timing barely diverges from order date here - only a handful of
    refunds land in a different calendar year - so an order-date basis keeps
    the gross bars and the refund overlay on the same axis.
    """
    df = _df if _df is not None else load_orders()
    gross = df.groupby("year")["Total Amount"].sum()
    refund = df.drop_duplicates("Order ID").groupby("year")["refund_amount"].sum()
    out = pd.DataFrame({"gross": gross, "refund": refund}).fillna(0.0)
    out["net"] = out["gross"] - out["refund"]
    return out.reset_index()


@st.cache_data
def monthly_spend_series(_df: pd.DataFrame = None) -> pd.Series:
    """Continuous monthly total-spend series from TIMESERIES_START through
    the last observed month, zero-filled on months with no orders."""
    df = _df if _df is not None else load_orders()
    monthly = df.groupby("year_month")["Total Amount"].sum()
    full_idx = pd.date_range(TIMESERIES_START, monthly.index.max(), freq="MS")
    s = monthly.reindex(full_idx, fill_value=0.0)
    s.index.freq = "MS"
    return s


def is_partial_year(df: pd.DataFrame, year: int) -> bool:
    """True if `year` doesn't run through December in the data (i.e. the
    current, still-in-progress year) -- used to caveat YoY comparisons."""
    max_date = df["Order Date"].max()
    return year == max_date.year and max_date.month < 12
