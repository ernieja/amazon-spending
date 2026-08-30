"""
Categories & Returns page: what spending breaks into by (keyword-tagged)
category, which categories actually come back, and the standout purchases -
priciest per year, priciest per category, and the handful of re-bought items.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.data_loader import load_orders
from src.style import apply_layout, category_color, setup_page_style, INK_MUTED

st.set_page_config(page_title="Categories & Returns", page_icon="🏷️", layout="wide")
setup_page_style()
st.title("Categories & Returns")

df = load_orders()
BUY = category_color(0)   # orange, what I buy
RET = category_color(5)   # vermillion, what comes back

total_spend = df["Total Amount"].sum()
other_spend = df.loc[df["category"] == "Other", "Total Amount"].sum()
other_items = int((df["category"] == "Other").sum())

st.write(
    "Amazon exports no category field, so these are keyword-tagged from product "
    f"names and are approximate. After a matching pass, **\\${other_spend:,.0f} "
    f"({other_spend / total_spend * 100:.0f}%)** still lands in **Other**. "
    "Returns come from a separate export with no line-item key, so each return "
    "is counted against its order's highest-spend category."
)

st.divider()

# ---------------------------------------------------------------------------
# Section 1: category mix
# ---------------------------------------------------------------------------
st.subheader("What I buy, by category")

cat = (
    df.groupby("category")
    .agg(spend=("Total Amount", "sum"), items=("ASIN", "size"))
    .sort_values("spend")
)
cat["pct"] = cat["spend"] / cat["spend"].sum() * 100

# Stacked by year: the 7 biggest categories (~88% of spend) plus a rolled-up
# band for the rest, so the mix shift over 15 years is visible in one chart.
TOP_N = 8
top_cats = cat.sort_values("spend", ascending=False).head(TOP_N).index.tolist()
by_yc = (
    df.assign(cat=df["category"].where(df["category"].isin(top_cats),
                                       "Other categories"))
    .pivot_table("Total Amount", "year", "cat", "sum", fill_value=0)
)

fig = go.Figure()
for i, c in enumerate(top_cats + ["Other categories"]):  # biggest added first = bottom
    if c not in by_yc:
        continue
    fig.add_bar(
        x=by_yc.index, y=by_yc[c], name=c,
        marker_color=category_color(8) if c == "Other categories"
        else category_color(i),
        hovertemplate=f"%{{x}}<br>{c}: $%{{y:,.0f}}<extra></extra>",
    )
fig.update_layout(barmode="stack", legend_traceorder="normal")
apply_layout(fig, title="Spend by category and year", y_title="Spend ($)")
fig.update_xaxes(type="category")
fig.update_layout(hovermode="closest")  # after apply_layout, which forces "x unified"
st.plotly_chart(fig, width="stretch", theme=None)
st.caption(
    "Books carried the early years (college); a Clothing binge in 2018-19; Grocery and "
    "Pet only show up from 2021 (got a cat). Electronics is the one constant. **Other** is "
    f"down to \\${other_spend:,.0f} "
    f"({other_spend / total_spend * 100:.0f}%, {other_items} line items): three "
    "gift cards, a ukulele, two bottles of wine, and a few oddments (lye, fridge "
    "magnets, a bike tube). Print books that were listed by title with no "
    "catchable keyword (\"Yes Please\", \"Eating Animals\") now route to Books & "
    "Media by their ISBN-format ASIN; audiobooks route there by their Audible source."
)

# Price per line item, by category: is a big category big because of volume or
# because the things in it cost more? 
priced = df[df["Total Amount"] > 0]
psize = priced.groupby("category").agg(n=("ASIN", "size"), spend=("Total Amount", "sum"))
order = [c for c in cat.index if c in psize.index]  # ascending by spend -> largest on top
tick_txt = [
    f"{c}<br><span style='font-size:0.90em;color:{INK_MUTED}'>"
    f"{psize.loc[c, 'n']} items &#183; ${psize.loc[c, 'spend']:,.0f}</span>"
    for c in order
]
fig1b = go.Figure()
fig1b.add_box(
    x=priced["Total Amount"], y=priced["category"], orientation="h",
    line_color=BUY, fillcolor="rgba(230,159,0,0.15)", boxpoints="outliers",
    marker=dict(color=BUY, size=4, opacity=0.5),
)
apply_layout(fig1b, title="Price per line item, by category", y_title=None,
             x_title="Line-item price ($, log scale)", height=600)
# "y unified" collapses the seven box stats (min/q1/median/q3/max + fences) into
# one tooltip per row instead of seven rotated, overlapping labels; dollars.
fig1b.update_layout(hovermode="y unified")
fig1b.update_traces(hoveron="boxes")
fig1b.update_xaxes(type="log", tickvals=[1, 3, 10, 30, 100, 300],
                   ticktext=["$1", "$3", "$10", "$30", "$100", "$300"],
                   hoverformat="$,.2f")
fig1b.update_yaxes(categoryorder="array", categoryarray=order,
                   tickmode="array", tickvals=order, ticktext=tick_txt)
st.plotly_chart(fig1b, width="stretch", theme=None)
st.caption(
    "Rows are ordered by total category spend (largest at top); each label's "
    "second line is its line-item count and dollars. Electronics is the biggest spend "
    "from a mix of both: 96 priced items *and* a long right tail. "
    "Its median line item is ~\\$29, about the same as Clothing "
    "or Home, but the mean is ~\\$76 because of the laptop, TVs and turntable "
    "sitting out past \\$300. Pet and Outdoors run a higher median but on far "
    "fewer items."
)

st.divider()

# ---------------------------------------------------------------------------
# Section 2: returns
# ---------------------------------------------------------------------------
st.subheader("Returns: who and why")

# Attribute each order to the category of its highest-spend line item.
dom = (
    df.sort_values("Total Amount", ascending=False)
    .drop_duplicates("Order ID")[["Order ID", "category"]]
)
orders = df.drop_duplicates("Order ID").merge(dom, on="Order ID", suffixes=("", "_dom"))
by_cat = orders.groupby("category_dom").agg(
    orders=("Order ID", "size"),
    returned=("is_returned", "sum"),
    refund=("refund_amount", "sum"),
)
by_cat = by_cat[by_cat["orders"] >= 5]  # drop single-order categories (Office)
by_cat["rate"] = by_cat["returned"] / by_cat["orders"] * 100
by_cat = by_cat.sort_values("rate")

fig2 = go.Figure()
fig2.add_bar(
    x=by_cat["rate"], y=by_cat.index, orientation="h", marker_color=RET,
    customdata=by_cat[["returned", "orders", "refund"]].to_numpy(),
    hovertemplate=(
        "%{y}<br>%{x:.0f}% returned "
        "(%{customdata[0]} of %{customdata[1]} orders) · "
        "$%{customdata[2]:,.0f} refunded<extra></extra>"
    ),
)
apply_layout(fig2, title="Return rate by category", y_title=None,
             x_title="% of orders with a return")
fig2.update_layout(hovermode="closest")  # after apply_layout, which forces "x unified"
st.plotly_chart(fig2, width="stretch", theme=None)

# Fold ~20 raw return reasons into a handful of buckets.
_REASON_BUCKETS = {
    "Changed my mind": [
        "No longer needed/wanted", "Better price available", "Accidental order",
    ],
    "Fit / size": [
        "Too large", "Too small", "Ordered wrong style/size/color",
    ],
    "Not as expected": [
        "Style not as expected", "Didn't like fabric",
        "Different from what was ordered", "Different from website description",
        "Performance or quality not adequate",
        "Incompatible or not useful for intended purpose",
    ],
    "Defective": ["Defective/Does not work properly"],
    "Never arrived / refused": [
        "Item never arrived", "Missed estimated delivery date", "Refused",
    ],
    "Other / unknown": ["Unknown Reason", "Unauthorized purchase"],
}
_reason_to_bucket = {r: b for b, rs in _REASON_BUCKETS.items() for r in rs}

# Break each reason bucket out by the order's dominant (highest-spend) category
# -- same attribution as the return-rate chart. Four categories carry it; the
# rest roll into "Other categories", and colors match the first chart.
RET_TOP = ["Clothing & Shoes", "Electronics & Accessories",
           "Home & Kitchen", "Outdoors & Sporting"]

ret_orders = orders[orders["is_returned"]].copy()
ret_orders["cat"] = ret_orders["category_dom"].where(
    ret_orders["category_dom"].isin(RET_TOP), "Other categories")


def _reason_buckets(reasons):
    if not isinstance(reasons, str):
        return {"Other / unknown"}
    return {_reason_to_bucket.get(r.strip(), "Other / unknown")
            for r in reasons.split("; ")}


rc = pd.DataFrame(
    [(b, c) for reasons, c in zip(ret_orders["return_reasons"], ret_orders["cat"])
     for b in _reason_buckets(reasons)],
    columns=["bucket", "cat"],
)
bucket_pivot = (
    rc.pivot_table(index="bucket", columns="cat", aggfunc="size", fill_value=0)
    .reindex(rc["bucket"].value_counts().sort_values().index)  # small buckets at bottom
)

n_returned = int(orders["is_returned"].sum())
fig3 = go.Figure()
for c in RET_TOP + ["Other categories"]:
    if c not in bucket_pivot:
        continue
    color = category_color(8) if c == "Other categories" else category_color(top_cats.index(c))
    fig3.add_bar(x=bucket_pivot[c], y=bucket_pivot.index, orientation="h",
                 name=c, marker_color=color,
                 hovertemplate=f"%{{y}}<br>{c}: %{{x}} orders<extra></extra>")
fig3.update_layout(barmode="stack", legend_traceorder="normal")
apply_layout(fig3, title=f"Why things came back, by category ({n_returned} returned "
             "orders, some with more than one reason)", y_title=None, x_title="Orders")
fig3.update_layout(hovermode="closest")  # after apply_layout, which forces "x unified"
st.plotly_chart(fig3, width="stretch", theme=None)
st.caption(
    "Fit and size returns are almost all Clothing (20 of 21); *changed my mind* "
    "is the one bucket led by Electronics and Home & Kitchen rather than clothes."
)

cl = by_cat.loc["Clothing & Shoes"]
total_refund = orders["refund_amount"].sum()
cl_refund_share = cl["refund"] / total_refund * 100
cl_spend_share = (
    df.loc[df["category"] == "Clothing & Shoes", "Total Amount"].sum()
    / total_spend * 100
)
n_refunded = int(orders["is_refunded"].sum())
n_not_return = int((orders["is_refunded"] & ~orders["is_return_related_refund"]).sum())

st.caption(
    f"Returns are mostly a clothing-fit problem: **{cl['rate']:.0f}% of clothing "
    f"orders come back** ({cl['returned']:.0f} of {cl['orders']:.0f}), and "
    f"clothing is {cl_refund_share:.0f}% of every refund dollar "
    f"(\\${cl['refund']:,.0f} of \\${total_refund:,.0f}) on {cl_spend_share:.0f}% "
    f"of spend. Separately, {n_not_return} of the {n_refunded} refunds weren't "
    "returns at all (item never arrived, undeliverable, or refused at the "
    "door): money back with nothing sent back."
)

st.divider()

# ---------------------------------------------------------------------------
# Section 3: standout purchases
# ---------------------------------------------------------------------------
st.subheader("Standout purchases")
st.write(
    "All three views below exclude any order that had a return: standouts are "
    "things I kept. Returns are order-level in the data, so a mixed order with "
    "one returned item drops out entirely."
)

kept = df[~df["is_returned"]]

year_total = df.groupby("year")["Total Amount"].sum()
top_year = kept.loc[kept.groupby("year")["Total Amount"].idxmax()].copy()
top_year["share"] = top_year["Total Amount"] / top_year["year"].map(year_total)

fig4 = go.Figure()
fig4.add_bar(
    x=top_year["year"], y=top_year["Total Amount"], marker_color=BUY,
    text=[f"{s:.0%}" for s in top_year["share"]], textposition="outside",
    textfont=dict(size=11),
    customdata=top_year[["Product Name", "category", "share"]].to_numpy(),
    hovertemplate=(
        "%{x}: $%{y:,.0f} · %{customdata[2]:.0%} of that year's spend"
        "<br>%{customdata[0]}<br>%{customdata[1]}<extra></extra>"
    ),
)
apply_layout(fig4, title="Priciest single item each year", y_title="Item price ($)")
fig4.update_xaxes(type="category")
st.plotly_chart(fig4, width="stretch", theme=None)
st.caption(
    "Labels are that item's share of the whole year's spend. Early on, one buy "
    "could be most of the year (the 2011 hard drive, the 2016 laptop); once "
    "spending grew, the biggest item settled into roughly 10-25%. Almost always "
    "electronics; the exceptions are early textbooks and a ukulele."
)

top_cat = (
    kept.loc[kept.groupby("category")["Total Amount"].idxmax()]
    [["category", "Product Name", "Total Amount", "year"]]
    .sort_values("Total Amount", ascending=False)
    .rename(columns={"category": "Category", "Product Name": "Item",
                     "Total Amount": "Price", "year": "Year"})
)
st.markdown("**Priciest in each category**")
st.dataframe(
    top_cat, hide_index=True, width="stretch",
    column_config={
        "Price": st.column_config.NumberColumn(format="$%d"),
        "Year": st.column_config.NumberColumn(format="%d"),
    },
)

ng = kept[(~kept["is_grocery"]) & (kept["ASIN"] != "_ASINLESS_")]
rep = ng.groupby("ASIN").agg(
    Item=("Product Name", lambda s: min(s.dropna(), key=len)),
    Category=("category", "first"),
    Times=("ASIN", "size"),
    Spend=("Total Amount", "sum"),
    first=("year", "min"),
    last=("year", "max"),
)
rep = rep[rep["Times"] >= 3].sort_values("Times", ascending=False)
rep["Years"] = [
    str(a) if a == b else f"{a}-{b}" for a, b in zip(rep["first"], rep["last"])
]
st.markdown("**Bought three or more times**")
st.dataframe(
    rep[["Item", "Category", "Times", "Spend", "Years"]], hide_index=True,
    width="stretch",
    column_config={"Spend": st.column_config.NumberColumn(format="$%d")},
)
st.caption(
    "What gets re-bought is consumables and replacements: air and water "
    "filters, cat food, acne patches. Grocery repeats are on the Whole Foods "
    "page."
)
