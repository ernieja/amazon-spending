"""
Whole Foods Grocery page: a small, intermittent, convenience-driven slice of
grocery spending - what it covers, what's in the basket, and why it can't
support a personal grocery price index.
"""

import re

import streamlit as st
import plotly.graph_objects as go

from src.data_loader import load_orders
from src.style import (
    apply_layout, category_color, setup_page_style, INK_SECONDARY, GRID,
)

st.set_page_config(page_title="Whole Foods Grocery", page_icon="🛒", layout="wide")
setup_page_style()
st.title("Whole Foods Grocery")

df = load_orders()
g = df[df["is_grocery"] == True].copy()  # noqa: E712  (pandas mask, not identity)
g["year"] = g["Order Date"].dt.year

GREEN, BLUE = category_color(2), category_color(4)

st.write(
    "Every Amazon order fulfilled by Whole Foods (the `panda01` marketplace in "
    "the export), 2021 to 2026. Whole Foods isn't my main grocery store - these "
    "are convenience runs, and they step up after 2023 when a new job put an office "
    "next door to one. So this is a small, uneven sample: **56 orders, ~\\$1,141, "
    "over five years**, with whole months and seasons missing. It says something "
    "about habits, maybe, and nothing about grocery inflation like I was hoping."
)

st.divider()

# ---------------------------------------------------------------------------
# Section 1: coverage
# ---------------------------------------------------------------------------
st.subheader("When I actually used it")

total_spend = g["Total Amount"].sum()
n_orders = g["Order ID"].nunique()
n_items = len(g)
active_months = g["year_month"].nunique()
span_months = (
    (g["Order Date"].max().to_period("M") - g["Order Date"].min().to_period("M")).n + 1
)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Grocery spend", f"${total_spend:,.0f}")
c2.metric("Orders", f"{n_orders}")
c3.metric("Avg order", f"${total_spend / n_orders:,.2f}")
c4.metric("Items per order", f"{n_items / n_orders:.1f}")
c5.metric("Active months", f"{active_months} / {span_months}")

by_year = g.groupby("year").agg(
    spend=("Total Amount", "sum"),
    orders=("Order ID", "nunique"),
    items=("ASIN", "size"),
)
by_year["per_order"] = by_year["spend"] / by_year["orders"]

fig = go.Figure()
fig.add_bar(
    x=by_year.index, y=by_year["spend"], marker_color=GREEN,
    customdata=by_year[["orders", "per_order"]].to_numpy(),
    hovertemplate=(
        "%{x}<br>Spend: $%{y:,.0f}<br>"
        "%{customdata[0]} orders · $%{customdata[1]:,.2f}/order<extra></extra>"
    ),
)
apply_layout(fig, title="Grocery spend by year", y_title="Spend ($)")
fig.update_xaxes(type="category")
st.plotly_chart(fig, width="stretch", theme=None)
st.caption(
    f"Only {active_months} of {span_months} months in the range have a single "
    "order; the longest gap is nine months, and 2025 alone is ~45% of all orders. "
    "2021 and 2026 are partial years. Annual bars paper over gaps "
    "this large - treat year-to-year moves as noise, not trend."
)

st.divider()

# ---------------------------------------------------------------------------
# Section 2: basket mix
# ---------------------------------------------------------------------------
st.subheader("What's in the basket")

sub = (
    g[g["grocery_subcategory"] != "Non-item (fee/refund)"]
    .groupby("grocery_subcategory")
    .agg(spend=("Total Amount", "sum"), items=("ASIN", "size"))
)
sub["avg_item"] = sub["spend"] / sub["items"]
sub_by_spend = sub.sort_values("spend")

fig2 = go.Figure()
fig2.add_bar(
    x=sub_by_spend["spend"], y=sub_by_spend.index, orientation="h",
    marker_color=GREEN,
    customdata=sub_by_spend[["items", "avg_item"]].to_numpy(),
    hovertemplate=(
        "%{y}<br>$%{x:,.0f} · %{customdata[0]} items · "
        "$%{customdata[1]:,.2f}/item<extra></extra>"
    ),
)
apply_layout(fig2, title="Spend by subcategory", y_title=None, x_title="Spend ($)")
fig2.update_layout(hovermode="closest")  # after apply_layout, which forces "x unified"
st.plotly_chart(fig2, width="stretch", theme=None)

sub_by_price = sub.sort_values("avg_item")
fig3 = go.Figure()
fig3.add_bar(
    x=sub_by_price["avg_item"], y=sub_by_price.index, orientation="h",
    marker_color=BLUE,
    customdata=sub_by_price[["items"]].to_numpy(),
    hovertemplate="%{y}<br>$%{x:,.2f}/item · %{customdata[0]} items<extra></extra>",
)
apply_layout(fig3, title="Average line-item price by subcategory",
             y_title=None, x_title="Price per line item ($)")
fig3.update_layout(hovermode="closest")  # after apply_layout, which forces "x unified"
st.plotly_chart(fig3, width="stretch", theme=None)
st.caption(
    "Subcategories are keyword-tagged from product names (Amazon doesn't export "
    "one), so they're approximate. The price bars are the average *line item* in "
    "each group - not normalized by weight or pack size, and not a time series. "
    "A high number often just means bigger packages (alcohol, prepared meals)."
)

st.divider()

# ---------------------------------------------------------------------------
# Section 3: no personal CPI
# ---------------------------------------------------------------------------
st.subheader("Why this can't be a personal grocery price index")

# "Fixed package" = a name that states a unit size, or is a standard bagged SKU.
_FIXED_UNIT_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:fl oz|fz|oz|ct|count|lb|g|ml)\b|\bbag\b", re.I
)

# Hand-curated groups: product lines I treat as one recurring basket item even
# though Amazon lists each flavor / variant under its own ASIN. (regex on the
# normalised key -> canonical key -> display label)
_MANUAL_GROUPS = [
    (re.compile(r"whole foods.*\bsoup\b", re.I),
     "wf 24 oz soup", "Whole Foods 24 oz soup (flavor rotates)"),
    (re.compile(r"^365 .*chicken broth$", re.I),
     "365 chicken broth 32 fz", "365 Organic Chicken Broth, 32 fl oz"),
]


def _norm_product(name):
    """Collapse the name variants Amazon uses for one product ("LACTAID" vs
    "Lactaid", "FZ" vs "Fl Oz", a "PRODUCE " prefix, a stray "Test") so repeat
    purchases of the same item actually group together."""
    if not isinstance(name, str):
        return name
    s = name.lower().strip()
    s = re.sub(r"^produce ", "", s)
    s = re.sub(r"\btest\b", "", s)
    s = re.sub(r",?\s*\d+(\.\d+)?\s*(fl oz|fz|oz|ct|count|lb|g|ml)\b.*$", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    for pat, canon, _ in _MANUAL_GROUPS:
        if pat.search(s):
            return canon
    return s


_MANUAL_LABELS = {canon: label for _, canon, label in _MANUAL_GROUPS}

# Canonicalise names through ASIN first: rows that share a real ASIN take that
# ASIN's shortest observed name, so Amazon's reworded / abbreviated variants
# ("WFM" vs "Whole Foods Market", clause reordering) collapse before grouping.
# Falls back to the raw name for loose items, which have no ASIN.
_asin_name = (
    g.loc[g["ASIN"] != "_ASINLESS_"]
    .groupby("ASIN")["Product Name"]
    .agg(lambda s: min(s.dropna(), key=len))
)
g["canon_name"] = g["ASIN"].map(_asin_name).fillna(g["Product Name"])
g["product_key"] = g["canon_name"].apply(_norm_product)

repeats = g.groupby("product_key").filter(lambda x: len(x) >= 3).copy()
_shortest = repeats.groupby("product_key")["canon_name"].agg(lambda s: min(s, key=len))
repeats["label"] = repeats["product_key"].map(
    lambda k: _MANUAL_LABELS.get(k) or _shortest[k]
)

key_fixed = repeats.groupby("product_key")["canon_name"].transform(
    lambda s: bool(s.str.contains(_FIXED_UNIT_RE).any())
)
loose_names = sorted(repeats.loc[~key_fixed, "label"].unique())

fixed = repeats[key_fixed].copy()
fixed["ym"] = fixed["Order Date"].dt.to_period("M").dt.to_timestamp()
fixed = fixed.sort_values("Order Date").drop_duplicates(
    ["product_key", "ym", "Unit Price"]
)
row_order = (
    fixed.groupby("label")["Order Date"].min().sort_values().index.tolist()
)

st.write(
    "A price index needs a **fixed basket** repriced on a **regular schedule** - "
    "this data has neither. Take the strongest case it can offer: products I "
    "bought three or more times *in a fixed package* (a 5 oz clamshell, a 64 fl "
    "oz carton, a bag of mandarins), where the unit price is genuinely "
    f"comparable across purchases. Pooling soup flavors, that's **{len(row_order)} "
    "items**, and none shows a trend:"
)

fig4 = go.Figure()
for label in row_order:
    r = fixed[fixed["label"] == label].sort_values("Order Date")
    prices = r["Unit Price"].tolist()
    # Label a point only when the price changed from the previous purchase, so
    # flat runs and closely-spaced repeats don't stack unreadable labels.
    text = [
        f"${p:.2f}" if i == 0 or p != prices[i - 1] else ""
        for i, p in enumerate(prices)
    ]
    fig4.add_scatter(
        x=r["Order Date"], y=r["label"], mode="lines+markers+text",
        line=dict(color=GRID, width=2), marker=dict(color=GREEN, size=9),
        text=text, textposition="top center",
        textfont=dict(size=11, color=INK_SECONDARY), showlegend=False,
        customdata=r[["Unit Price"]].to_numpy(),
        hovertemplate="%{y}<br>%{x|%b %Y}: $%{customdata[0]:.2f}<extra></extra>",
    )
apply_layout(fig4, title="Fixed-size repeat items: unit price at each purchase",
             y_title=None, x_title=None, height=360)
fig4.update_yaxes(categoryorder="array", categoryarray=row_order)
fig4.update_layout(hovermode="closest")  # after apply_layout, which forces "x unified"
st.plotly_chart(fig4, width="stretch", theme=None)
st.caption(
    "The two milks moved ~4% in opposite directions; the spinach salad's one dip "
    "reverted; the broth, the mandarin bag, and both juices held flat. The soup "
    "sat at \\$8.49 for three years - the latest \\$9.49 is possibly a price rise, but there's "
    "no additional data since. The juices were only ever bought in a single 2021 "
    "quarter. Still no trend, no schedule."
)

n_products = g["product_key"].nunique()
n_once = (g["product_key"].value_counts() == 1).sum()
n_repeat = int((g["product_key"].value_counts() >= 3).sum())
repeat_spend = g.loc[g["product_key"].isin(repeats["product_key"]), "Total Amount"].sum()
n_asinless = (g["ASIN"] == "_ASINLESS_").sum()
qty1_share = (g["Original Quantity"] == 1).mean()

st.markdown(
    f"- **No basket.** {n_once} of {n_products} distinct products "
    f"({n_once / n_products * 100:.0f}%) were bought exactly once. Only "
    f"{n_repeat} were bought three or more times, \\${repeat_spend:,.0f} of the "
    "\\$1,141.\n"
    f"- **Item identity is shaky.** {n_asinless} of {n_items} line items carry no "
    "ASIN at all (loose produce and deli), and items that do have one still show "
    'up under two or three name strings ("LACTAID" vs "Lactaid", "FZ" vs '
    '"Fl Oz", "WFM" vs "Whole Foods Market") - so matching an item to itself '
    "already takes fuzzy string work.\n"
    f"- **No quantity or weight.** `Original Quantity` is 1 for "
    f"{qty1_share * 100:.0f}% of lines, with no weight recorded, which drops "
    "loose produce: grapes, both onions and banana were each bought 3+ times, "
    "but \\$8.98 vs \\$10.08 for grapes is a heavier bag, not a price move.\n"
    "- **Intermittent coverage.** Thirty of 62 months are empty; you can't "
    "measure month-over-month change across gaps that size.\n"
    "- **Wrong basket anyway.** This is a convenience channel next to my work, "
    "not primary shopping - even a clean version wouldn't represent my grocery "
    "costs."
)
st.write(
    "What this *can* show, and the earlier sections do: how spend splits across "
    "categories, how often I order, how big a typical basket is. None of that supports "
    "an indication of inflation, but it's honest."
)
