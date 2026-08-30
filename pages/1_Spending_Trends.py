"""
Spending Trends page: growth-driver decomposition (indexed to 2018),
STL decomposition of monthly spend, and a Holt-Winters forecast.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.data_loader import (
    load_orders, monthly_spend_series, big_ticket_items, big_ticket_threshold,
    is_partial_year, BIG_TICKET_PCT,
)
from src.spend_decomposition import decompose_growth
from src.timeseries import decompose as stl_decompose, fit_holt_winters, forecast as hw_forecast
from src.style import (
    apply_layout, category_color, setup_page_style,
    FORECAST_BAND, PARTIAL_YEAR_FILL, GRID, INK_MUTED,
)

st.set_page_config(page_title="Spending Trends", page_icon="📈", layout="wide")
setup_page_style()
st.title("Spending Trends")

# Grocery (Whole Foods delivery) is excluded from this whole page: it only
# starts mid-2021, is intermittent, and behaves nothing like the rest (many
# ~$5 items per order). Left in, it dominates the item counts and drags the
# average price down, turning the decomposition into a story about adopting a
# grocery channel rather than about retail-spending growth. It has its own page.
df = load_orders()
df = df[~df["is_grocery"]].copy()
LAST_FULL_YEAR = 2025  # 2026 is partial (through Aug) as of this data pull

# ---------------------------------------------------------------------------
# Section 1: growth-driver decomposition
# ---------------------------------------------------------------------------
st.subheader("What's actually driving spend growth?")
st.write(
    "Total spend can be rewritten as **orders × items per order × average item "
    "price**. Splitting the change in spend between two years into these three "
    "factors (via a log decomposition, so the three pieces sum exactly to the "
    "total, see the code walkthrough) answers *why* spend changed, not just that "
    "it did. Whole Foods grocery is excluded throughout this page and covered "
    "separately."
)

d = decompose_growth(df, "year", 2018, LAST_FULL_YEAR)
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Total spend growth ({2018}→{LAST_FULL_YEAR})", f"{d['total_growth_pct']:+.0f}%")
c2.metric("From ordering more often", f"{d['orders_growth_pct']:+.0f}%")
c3.metric("From bigger baskets", f"{d['basket_growth_pct']:+.0f}%")
c4.metric("From item price changes", f"{d['price_growth_pct']:+.0f}%")
st.caption(
    f"Growth is almost all from **ordering more often** "
    f"({d['orders_growth_pct']:+.0f}%). Basket size barely moved "
    f"({d['basket_growth_pct']:+.0f}%), and the average item got a little "
    f"*more* expensive ({d['price_growth_pct']:+.0f}%). Leaving grocery in "
    "would flip that last figure sharply negative, dozens of ~\\$5 Whole Foods "
    "items a year pulling the average down."
)

# Indexed-to-2018 view across the full history, avoids the shares metric's
# instability when total growth between two adjacent years is near zero.
annual = (
    df.groupby("year")
    .agg(spend=("Total Amount", "sum"), items=("ASIN", "count"), orders=("Order ID", "nunique"))
    .reset_index()
)
annual["items_per_order"] = annual["items"] / annual["orders"]
annual["avg_item_price"] = annual["spend"] / annual["items"]
base = annual.loc[annual["year"] == 2018].iloc[0]
annual["Total spend"] = annual["spend"] / base["spend"] * 100
annual["Orders"] = annual["orders"] / base["orders"] * 100
annual["Items per order"] = annual["items_per_order"] / base["items_per_order"] * 100
annual["Avg item price"] = annual["avg_item_price"] / base["avg_item_price"] * 100

fig = go.Figure()
series = ["Total spend", "Orders", "Items per order", "Avg item price"]
for i, name in enumerate(series):
    is_total = name == "Total spend"
    fig.add_scatter(
        x=annual["year"], y=annual[name], name=name,
        mode="lines+markers" if is_total else "lines",
        line=dict(width=3.5 if is_total else 2, color=category_color(i), dash="solid"),
        marker=dict(size=6),
        opacity=1 if is_total else 0.8,
        hovertemplate=f"{name}: " + "%{y:.0f} (2018=100)<extra></extra>",
    )
fig.add_hline(y=100, line_dash="dot", line_color=GRID,
              annotation_text="2018 baseline", annotation_font_color=INK_MUTED)
fig.add_vrect(x0=2025.5, x1=annual["year"].max() + 0.5, fillcolor=PARTIAL_YEAR_FILL,
              line_width=0, annotation_text="partial year", annotation_position="top left",
              annotation_font_color=INK_MUTED)
apply_layout(fig, title="Growth drivers, indexed to 2018 = 100", y_title="Index (2018 = 100)", x_title="Year")
fig.update_xaxes(dtick=1)
st.plotly_chart(fig, width='stretch', theme=None)
orders_idx = annual.loc[annual["year"] == LAST_FULL_YEAR, "Orders"].iloc[0]
st.caption(
    f"Each line is that factor's own year vs. 2018, so 'Orders' at "
    f"{orders_idx:.0f} in {LAST_FULL_YEAR} means {orders_idx / 100:.1f}x as many "
    "orders as 2018, independent of what price or basket size did. Total spend "
    "is, by construction, the product of the other three (divided by 100²) - you "
    "can see it track whichever factor moves most."
)

st.write(
    "That *average* item price is mean-based, so one laptop or TV swings it. "
    "The **median** shows what a typical line item actually cost:"
)
priced = df[df["Total Amount"] > 0]
med = priced.groupby("year")["Total Amount"].median()

figm = go.Figure()
figm.add_scatter(
    x=med.index, y=med.values, name="Median item price", mode="lines+markers",
    line=dict(color=category_color(0), width=3), marker=dict(size=6),
    hovertemplate="%{x}: $%{y:.2f} median<extra></extra>",
)
figm.add_vrect(x0=2025.5, x1=med.index.max() + 0.5, fillcolor=PARTIAL_YEAR_FILL,
               line_width=0, annotation_text="partial year",
               annotation_position="top left", annotation_font_color=INK_MUTED)
apply_layout(figm, title="Median price per line item, by year",
             y_title="Median item price ($)", x_title="Year")
figm.update_xaxes(dtick=1)
st.plotly_chart(figm, width='stretch', theme=None)
st.caption(
    "The typical line item has held around \\$20-30 for most of the period, "
    "with 2023 the outlier on the high side. It's a much flatter picture than "
    "the mean-based *average item price* above, which the odd big-ticket buy "
    "swings around. Pre-2016 years have just 2-20 items each, so those points "
    "are noisy."
)

st.divider()

# ---------------------------------------------------------------------------
# Section 2: STL decomposition
# ---------------------------------------------------------------------------
st.subheader("Trend, seasonality, and noise in monthly spend")
st.write(
    "Monthly spend from 2018 onward (pre-2018 order volume is too sparse, "
    "as low as 1-2 orders/month, for monthly seasonality to mean anything), "
    "decomposed via STL (Seasonal-Trend decomposition using LOESS). Big-ticket "
    "one-off purchases are excluded by default so a single large buy doesn't "
    "bend the trend line or widen the forecast below."
)

exclude_bt = st.toggle(
    f"Exclude big-ticket purchases (top {(1 - BIG_TICKET_PCT) * 100:g}% by item price)",
    value=True,
    help="Drops line items at or above the "
         f"{BIG_TICKET_PCT * 100:g}th percentile of Total Amount over the "
         "2018-onward window. STL is already run with robust=True, which "
         "down-weights outlier months, but this also keeps them out of the "
         "observed line and the Holt-Winters fit.",
)

s = monthly_spend_series(exclude_grocery=True, exclude_big_ticket=exclude_bt)
decomp = stl_decompose(s, period=12)

if exclude_bt:
    bt = big_ticket_items(exclude_grocery=True)
    thr = big_ticket_threshold(exclude_grocery=True)
    with st.expander(
        f"Which {len(bt)} purchases are excluded? "
        f"(≥ ${thr:,.0f}, ${bt['Total Amount'].sum():,.0f} total)"
    ):
        st.dataframe(
            bt.assign(**{"Order Date": bt["Order Date"].dt.date}),
            hide_index=True,
            width="stretch",
            column_config={
                "Total Amount": st.column_config.NumberColumn("Total Amount", format="$%.2f"),
            },
        )

fig2 = go.Figure()
fig2.add_scatter(x=decomp.index, y=decomp["observed"], name="Observed", mode="lines",
                  line=dict(color=INK_MUTED, width=1.5))
fig2.add_scatter(x=decomp.index, y=decomp["trend"], name="Trend", mode="lines",
                  line=dict(color=category_color(0), width=3))
apply_layout(fig2, title="Monthly spend: observed vs. trend", y_title="Spend ($)")
st.plotly_chart(fig2, width='stretch', theme=None)

fig3 = go.Figure()
fig3.add_bar(x=decomp.index, y=decomp["seasonal"], marker_color=category_color(1),
             hovertemplate="%{x|%b %Y}: $%{y:.0f}<extra></extra>")
fig3.add_hline(y=0, line_color=GRID)
apply_layout(fig3, title="Seasonal component", y_title="$ vs. seasonally-typical month")
st.plotly_chart(fig3, width='stretch', theme=None)
st.caption(
    "March is the biggest month above the seasonally-adjusted trend, with July "
    "second and May the furthest below. December swings from slightly negative "
    "in 2018-19 to well above trend by 2025, since STL lets the seasonal shape "
    "drift year to year rather than fitting one fixed monthly profile."
)

# The tall March bar invites a "what do I always buy in March?" reading, so
# break each year's March spend out by category. Same basis as the
# decomposition: grocery out, big-ticket per the toggle above.
mar = df[df["year_month"].dt.month == 3]
if exclude_bt:
    mar = mar[mar["Total Amount"] < big_ticket_threshold(exclude_grocery=True)]
cat_rank = list(df.groupby("category")["Total Amount"].sum().sort_values(ascending=False).index)
mar_piv = (
    mar.pivot_table("Total Amount", "year", "category", "sum", fill_value=0)
    .reindex(range(2018, int(df["year"].max()) + 1), fill_value=0)
)
fig3b = go.Figure()
for c in [c for c in cat_rank if c in mar_piv.columns and mar_piv[c].sum() > 0]:
    fig3b.add_bar(x=mar_piv.index, y=mar_piv[c], name=c,
                  marker_color=category_color(cat_rank.index(c)),
                  hovertemplate=f"{c}: $%{{y:,.0f}}<extra></extra>")
fig3b.update_layout(barmode="stack", legend_traceorder="normal")
apply_layout(fig3b, title="March spend by category, each year", y_title="March spend ($)")
fig3b.update_xaxes(type="category")
st.plotly_chart(fig3b, width="stretch", theme=None)
st.caption(
    "It isn't a recurring habit. March 2018-19 had no non-grocery orders at "
    "all; 2020, 2021 and 2024 land around a normal month. Only 2023, 2025, and "
    "2026 stand out, and each was carried by a different category (Home & "
    "Kitchen, then Electronics, then Clothing). The seasonal bar is tall "
    "because STL's drifting seasonal picks up those two big recent Marches, "
    "not because March is an annual driver the way December might be because of the holidays."
)

st.divider()

# ---------------------------------------------------------------------------
# Section 3: forecast
# ---------------------------------------------------------------------------
st.subheader("Next 12 months")
fitted = fit_holt_winters(s, period=12)
fc = hw_forecast(fitted, steps=12)

fig4 = go.Figure()
fig4.add_scatter(x=s.index, y=s.values, name="Actual", mode="lines", line=dict(color=INK_MUTED, width=1.5))
fig4.add_scatter(
    x=pd.concat([pd.Series(fc.index), pd.Series(fc.index[::-1])]),
    y=pd.concat([fc["upper_95"], fc["lower_95"][::-1]]),
    fill="toself", fillcolor=FORECAST_BAND, line=dict(width=0),
    name="95% interval", hoverinfo="skip",
)
fig4.add_scatter(x=fc.index, y=fc["forecast"], name="Forecast", mode="lines+markers",
                  line=dict(color=category_color(0), width=3, dash="dash"))
apply_layout(fig4, title="Holt-Winters forecast (statsmodels)", y_title="Spend ($)")
st.plotly_chart(fig4, width='stretch', theme=None)

next12_sum = fc["forecast"].sum()
last12_sum = s.iloc[-12:].sum()
st.metric("Forecast: next 12 months", f"${next12_sum:,.0f}",
          delta=f"{(next12_sum/last12_sum-1)*100:+.0f}% vs. last 12 months")
st.caption(
    "The interval is intentionally wide - monthly personal spend is genuinely "
    "noisy with only ~100 data points behind this model, so a wide honest "
    "interval beats a falsely precise point estimate. Interval built from Monte "
    "Carlo simulation of the fitted model's error distribution, not a "
    "closed-form Gaussian assumption."
)
