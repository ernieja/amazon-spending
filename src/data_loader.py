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

# Line items at or above this percentile of ``Total Amount`` count as
# "big-ticket" one-off purchases -- a single ~$500 buy in an otherwise
# ~$150 month distorts the STL trend and the Holt-Winters fit, so the
# monthly series can optionally drop them. 99th percentile is ~5 items.
BIG_TICKET_PCT = 0.99


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


def _timeseries_frame(exclude_grocery: bool) -> pd.DataFrame:
    """load_orders() restricted to the monthly-series window (TIMESERIES_START
    onward), with grocery optionally dropped. Shared basis for the monthly
    series and the big-ticket cutoff so both see exactly the same line items."""
    df = load_orders()
    if exclude_grocery:
        df = df[~df["is_grocery"]]
    return df[df["year_month"] >= pd.Timestamp(TIMESERIES_START)]


def big_ticket_threshold(exclude_grocery: bool = False, pct: float = BIG_TICKET_PCT) -> float:
    """Dollar value at percentile ``pct`` of line-item ``Total Amount`` over the
    monthly-series window. Items at or above this are treated as big-ticket."""
    return _timeseries_frame(exclude_grocery)["Total Amount"].quantile(pct)


@st.cache_data
def big_ticket_items(exclude_grocery: bool = False, pct: float = BIG_TICKET_PCT) -> pd.DataFrame:
    """The line items that ``monthly_spend_series(exclude_big_ticket=True)``
    removes, most expensive first, with the columns worth showing in a table."""
    df = _timeseries_frame(exclude_grocery)
    thr = df["Total Amount"].quantile(pct)
    cols = ["Order Date", "Product Name", "category", "Total Amount"]
    return (
        df.loc[df["Total Amount"] >= thr, cols]
        .sort_values("Total Amount", ascending=False)
        .reset_index(drop=True)
    )


@st.cache_data
def monthly_spend_series(
    exclude_grocery: bool = False,
    exclude_big_ticket: bool = False,
    big_ticket_pct: float = BIG_TICKET_PCT,
) -> pd.Series:
    """Continuous monthly total-spend series from TIMESERIES_START through
    the last observed month, zero-filled on months with no orders.

    ``exclude_grocery`` drops Whole Foods (panda01) line items -- grocery only
    starts mid-2021 and is intermittent, so it's a structural break rather than
    part of the retail-spending trend (it has its own page).

    ``exclude_big_ticket`` drops line items at or above the ``big_ticket_pct``
    percentile of ``Total Amount`` (default 99th, ~5 items) so one large one-off
    purchase doesn't bend the STL trend or widen the Holt-Winters interval. The
    removed items are listed by ``big_ticket_items()``."""
    df = load_orders()
    if exclude_grocery:
        df = df[~df["is_grocery"]]
    if exclude_big_ticket:
        thr = big_ticket_threshold(exclude_grocery, big_ticket_pct)
        df = df[df["Total Amount"] < thr]
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
