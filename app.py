"""
app.py
Landing page: headline KPIs across the full 15-year order history, plus
navigation into the three deep-dive pages.
"""

import streamlit as st
import plotly.graph_objects as go

from src.data_loader import load_orders, annual_spend
from src.style import (
    apply_layout, category_color, category_color_rgba, setup_page_style,
    INK_SECONDARY,
)

st.set_page_config(page_title="Amazon Spending Analysis", layout="wide")
setup_page_style()

st.title("Amazon Spending Analysis")
st.write(
    "Fifteen years of my real Amazon order history (2011-2026), analyzed end to end: "
    "what's actually driving spend growth, a deep dive into Whole Foods grocery "
    "purchases, and a look at categories and returns. Built with pandas and statsmodels."
)

df = load_orders()
orders_dedup = df.drop_duplicates("Order ID")

total_spend = df["Total Amount"].sum()
total_refunds = orders_dedup["refund_amount"].sum()
net_spend = total_spend - total_refunds
total_orders = df["Order ID"].nunique()
date_min, date_max = df["Order Date"].min(), df["Order Date"].max()
return_rate = orders_dedup["is_returned"].mean()
top_category = (
    df[df["category"] != "Other"].groupby("category")["Total Amount"].sum().idxmax()
)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric(
    "Total spend", f"${total_spend:,.0f}",
    help=f"Gross. \\${net_spend:,.0f} net of the \\${total_refunds:,.0f} "
         f"refunded over the full history "
         f"({total_refunds / total_spend * 100:.0f}% of gross), de-duplicated "
         "from Amazon's refund export.",
)
col2.metric("Unique orders", f"{total_orders:,}")
col3.metric("Date range", f"{date_min.year}–{date_max.year}")
col4.metric("Return rate", f"{return_rate*100:.1f}%", help="Share of orders with at least one return, by unique Order ID.")
# Category labels are long compound names ("Electronics & Accessories"); st.metric
# renders the value on one line and ellipsis-truncates it in a 5-across row, so
# show the short head and keep the full label in the tooltip.
col5.metric("Top category", top_category.split(" & ")[0], help=f"Full label: {top_category}")

st.caption(
    f"Net of refunds: \\${net_spend:,.0f} — \\${total_refunds:,.0f} came back "
    f"({total_refunds / total_spend * 100:.0f}% of gross). "
    f"Data through {date_max.strftime('%b %Y')} — {date_max.year} is a partial "
    "year, called out explicitly wherever it affects a comparison."
)

st.divider()

# --- Hero chart: annual spend, quick visual orientation before the deep dives ---
# Stacked so bar height stays gross: solid = kept, faded cap = refunded back.
annual = annual_spend(df)
fig = go.Figure()
fig.add_bar(
    x=annual["year"], y=annual["net"], name="Kept",
    marker_color=category_color(0), hoverinfo="skip",
)
fig.add_bar(
    x=annual["year"], y=annual["refund"], name="Refunded",
    marker_color=category_color_rgba(0, 0.3), hoverinfo="skip",
)
# One invisible series carries the whole hover block, so its row order is
# independent of the legend: legend reads Kept -> Refunded (trace order), while
# the hover leads with Refunded to match the faded cap, then Kept, then Spent.
# A single trace only gets one hover swatch, so colour each row inline instead.
def _sw(color):
    return f"<span style='color:{color}'>■</span> "

fig.add_scatter(
    x=annual["year"], y=annual["gross"], mode="markers",
    marker=dict(color="rgba(0,0,0,0)"), showlegend=False,
    customdata=annual[["refund", "net", "gross"]].to_numpy(),
    hovertemplate=(
        f"{_sw(category_color_rgba(0, 0.5))}Refunded: $%{{customdata[0]:,.0f}}<br>"
        f"{_sw(category_color(0))}Kept: $%{{customdata[1]:,.0f}}<br>"
        f"{_sw(INK_SECONDARY)}Spent: $%{{customdata[2]:,.0f}}<extra></extra>"
    ),
)
# barmode="stack" defaults the legend to reversed; force natural order so the
# legend leads with "Kept".
fig.update_layout(barmode="stack", legend_traceorder="normal")
apply_layout(fig, title="Spend by year: kept vs. refunded", y_title="Spend ($)")
fig.update_xaxes(type="category")
st.plotly_chart(fig, use_container_width=True, theme=None)
st.caption(
    "Bar height is gross spend; the solid part is what I kept, the faded cap is "
    "refunded back. Refunds are counted in the year the order was placed. Refund "
    "totals are de-duplicated from Amazon's export (it repeats each refund across "
    "internal retries); 2018–19 and 2023 ran unusually high."
)

st.divider()

st.subheader("Explore the analysis")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("#### Spending Trends")
    st.write(
        "- **Growth decomposition**: is spend growth coming from ordering more "
        "often, bigger baskets, or higher prices? A log-decomposition splits "
        "the answer into exact shares.\n"
        "- **STL decomposition**: trend, seasonality, and residual noise in "
        "monthly spend, via statsmodels.\n"
        "- **Holt-Winters forecast**: next 12 months, with a simulation-based "
        "prediction interval."
    )
    st.page_link("pages/1_Spending_Trends.py", label="Open Spending Trends →")
with c2:
    st.markdown("#### Whole Foods Grocery")
    st.write(
        "- Grocery spend and cart-size trends since 2021.\n"
        "- Category-level price patterns (produce, meat, dairy, and more).\n"
        "- An honest look at why a true 'personal grocery CPI' isn't "
        "supportable from this data, and what I could measure instead."
    )
    st.page_link("pages/2_Whole_Foods_Grocery.py", label="Open Whole Foods Grocery →")
with c3:
    st.markdown("#### Categories & Returns")
    st.write(
        "- What I actually buy, by category (keyword-tagged from product names, "
        "since Amazon doesn't export a category field).\n"
        "- Return rate and return reasons over time.\n"
        "- Refunds vs. returns: not every refund means something was sent back."
    )
    st.page_link("pages/3_Categories_and_Returns.py", label="Open Categories & Returns →")

st.divider()
st.caption(
    "Data: personal Amazon order history, returns, and refund exports (Amazon's "
    "own data-download tool). Category and grocery-subcategory tags are "
    "keyword-derived from product names, not an official Amazon field, and are "
    "imperfect by nature; see the Categories & Returns page for the honest "
    "breakdown of what's tagged 'Other.'"
)
