"""
spend_decomposition.py
Answers "why did spend change" by splitting the change in total spend
between two periods into three multiplicative drivers: how often I
ordered, how many items landed in each order, and how much each item cost
on average. Uses a log decomposition so the three contributions sum
exactly to the total change (no matter how large the changes are).

    spend = orders * (items / orders) * (spend / items)
          = orders * items_per_order * avg_item_price

    log(spend_1 / spend_0) = log(orders_1/orders_0)
                            + log(items_per_order_1/items_per_order_0)
                            + log(avg_item_price_1/avg_item_price_0)
"""

import numpy as np
import pandas as pd


def _period_stats(df: pd.DataFrame) -> dict:
    orders = df["Order ID"].nunique()
    items = len(df)
    spend = df["Total Amount"].sum()
    return {
        "spend": spend,
        "orders": orders,
        "items": items,
        "items_per_order": items / orders,
        "avg_item_price": spend / items,
    }


def decompose_growth(df: pd.DataFrame, year_col: str, year0: int, year1: int) -> dict:
    """Decompose the change in total spend between year0 and year1 into
    order-frequency, order-size, and price contributions.

    Returns a dict with the raw stats for both years, each factor's growth
    ratio, and each factor's *share* of the total log-growth.
    """
    s0 = _period_stats(df[df[year_col] == year0])
    s1 = _period_stats(df[df[year_col] == year1])

    log_total = np.log(s1["spend"] / s0["spend"])
    log_orders = np.log(s1["orders"] / s0["orders"])
    log_basket = np.log(s1["items_per_order"] / s0["items_per_order"])
    log_price = np.log(s1["avg_item_price"] / s0["avg_item_price"])

    def share(component):
        return component / log_total if log_total != 0 else float("nan")

    return {
        "year0": year0,
        "year1": year1,
        "stats0": s0,
        "stats1": s1,
        "total_growth_pct": (np.exp(log_total) - 1) * 100,
        "orders_growth_pct": (np.exp(log_orders) - 1) * 100,
        "basket_growth_pct": (np.exp(log_basket) - 1) * 100,
        "price_growth_pct": (np.exp(log_price) - 1) * 100,
        "orders_share": share(log_orders),
        "basket_share": share(log_basket),
        "price_share": share(log_price),
    }


def yearly_growth_table(df: pd.DataFrame, year_col: str = "year") -> pd.DataFrame:
    """YoY version: one row per year transition with the same
    three shares, for a waterfall chart across the full history."""
    years = sorted(df[year_col].dropna().unique())
    rows = []
    for y0, y1 in zip(years[:-1], years[1:]):
        d = decompose_growth(df, year_col, int(y0), int(y1))
        rows.append({
            "year": int(y1),
            "spend": d["stats1"]["spend"],
            "total_growth_pct": d["total_growth_pct"],
            "orders_share": d["orders_share"],
            "basket_share": d["basket_share"],
            "price_share": d["price_share"],
        })
    return pd.DataFrame(rows)
