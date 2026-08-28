"""
Spending Trends page: growth-driver decomposition (indexed to 2018),
STL decomposition of monthly spend, and a Holt-Winters forecast.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.data_loader import load_orders, monthly_spend_series, is_partial_year
from src.spend_decomposition import decompose_growth
from src.timeseries import decompose as stl_decompose, fit_holt_winters, forecast as hw_forecast
from src.style import apply_layout, category_color, setup_page_style, FORECAST_BAND

st.set_page_config(page_title="Spending Trends", page_icon="📈", layout="wide")
setup_page_style()
st.title("📈 Spending Trends")

df = load_orders()
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
    "it did."
)

d = decompose_growth(df, "year", 2018, LAST_FULL_YEAR)
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Total spend growth ({2018}→{LAST_FULL_YEAR})", f"{d['total_growth_pct']:+.0f}%")
c2.metric("From ordering more often", f"{d['orders_growth_pct']:+.0f}%")
c3.metric("From bigger baskets", f"{d['basket_growth_pct']:+.0f}%")
c4.metric("From item price changes", f"{d['price_growth_pct']:+.0f}%")
st.caption(
    "Price changes are *negative*: the average item you buy actually got "
    "cheaper over this period. Growth came entirely from ordering more often "
    "and buying more per order — if prices hadn't dropped, growth would have "
    "been even larger."
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
    fig.add_scatter(
        x=annual["year"], y=annual[name], name=name, mode="lines+markers",
        line=dict(width=3 if name == "Total spend" else 2, color=category_color(i),
                   dash="solid" if name == "Total spend" else "dot"),
        marker=dict(size=7),
        hovertemplate=f"{name}: " + "%{y:.0f} (2018=100)<extra></extra>",
    )
fig.add_hline(y=100, line_dash="dot", line_color="#c8c8c8", annotation_text="2018 baseline")
fig.add_vrect(x0=2025.5, x1=annual["year"].max() + 0.5, fillcolor="#e8e8e8", opacity=0.4,
              line_width=0, annotation_text="partial year", annotation_position="top left")
apply_layout(fig, title="Growth drivers, indexed to 2018 = 100", y_title="Index (2018 = 100)")
fig.update_xaxes(type="category")
st.plotly_chart(fig, use_container_width=True)
st.caption(
    "Each line is that factor's own year vs. 2018, so 'Orders' at 269 in 2025 means "
    "2.7x as many orders as 2018, independent of what price or basket size did. "
    "Total spend is, by construction, the product of the other three (divided by "
    "100²) — you can see it track whichever factor moves most."
)

st.divider()

# ---------------------------------------------------------------------------
# Section 2: STL decomposition
# ---------------------------------------------------------------------------
st.subheader("Trend, seasonality, and noise in monthly spend")
st.write(
    "Monthly spend from 2018 onward (pre-2018 order volume is too sparse, "
    "as low as 1-2 orders/month, for monthly seasonality to mean anything), "
    "decomposed via STL (Seasonal-Trend decomposition using LOESS)."
)

s = monthly_spend_series(df)
decomp = stl_decompose(s, period=12)

fig2 = go.Figure()
fig2.add_scatter(x=decomp.index, y=decomp["observed"], name="Observed", mode="lines",
                  line=dict(color="#c8c8c8", width=1.5))
fig2.add_scatter(x=decomp.index, y=decomp["trend"], name="Trend", mode="lines",
                  line=dict(color=category_color(0), width=3))
apply_layout(fig2, title="Monthly spend: observed vs. trend", y_title="Spend ($)")
st.plotly_chart(fig2, use_container_width=True)

fig3 = go.Figure()
fig3.add_bar(x=decomp.index, y=decomp["seasonal"], marker_color=category_color(1),
             hovertemplate="%{x|%b %Y}: $%{y:.0f}<extra></extra>")
fig3.add_hline(y=0, line_color="#c8c8c8")
apply_layout(fig3, title="Seasonal component", y_title="$ vs. seasonally-typical month")
st.plotly_chart(fig3, use_container_width=True)
st.caption(
    "December consistently runs highest (holiday spending), spring/late-summer "
    "months tend to run below the seasonally-adjusted trend."
)

st.divider()

# ---------------------------------------------------------------------------
# Section 3: forecast
# ---------------------------------------------------------------------------
st.subheader("Next 12 months")
fitted = fit_holt_winters(s, period=12)
fc = hw_forecast(fitted, steps=12)

fig4 = go.Figure()
fig4.add_scatter(x=s.index, y=s.values, name="Actual", mode="lines", line=dict(color="#8c8c8c", width=1.5))
fig4.add_scatter(
    x=pd.concat([pd.Series(fc.index), pd.Series(fc.index[::-1])]),
    y=pd.concat([fc["upper_95"], fc["lower_95"][::-1]]),
    fill="toself", fillcolor=FORECAST_BAND, line=dict(width=0),
    name="95% interval", hoverinfo="skip",
)
fig4.add_scatter(x=fc.index, y=fc["forecast"], name="Forecast", mode="lines+markers",
                  line=dict(color=category_color(0), width=3, dash="dash"))
apply_layout(fig4, title="Holt-Winters forecast (statsmodels)", y_title="Spend ($)")
st.plotly_chart(fig4, use_container_width=True)

next12_sum = fc["forecast"].sum()
last12_sum = s.iloc[-12:].sum()
st.metric("Forecast: next 12 months", f"${next12_sum:,.0f}",
          delta=f"{(next12_sum/last12_sum-1)*100:+.0f}% vs. last 12 months")
st.caption(
    "The interval is intentionally wide — monthly personal spend is genuinely "
    "noisy with only ~100 data points behind this model, so a wide honest "
    "interval beats a falsely precise point estimate. Interval built from Monte "
    "Carlo simulation of the fitted model's error distribution, not a "
    "closed-form Gaussian assumption."
)
