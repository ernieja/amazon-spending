# Amazon Spending Analysis

Fifteen years of my real Amazon order history (2011–2026), coming from Amazon's **Request My Data** export and analyzed end to end as a Streamlit app: what's driving spend growth, how categories and returns break down,
and a closer look at Whole Foods grocery purchases. Built with pandas, statsmodels,
and plotly.

https://amazon-spending-zmypvyzhumnxejehx54tdy.streamlit.app/

~\$22k of gross spend across 489 orders.

## Three views

- **Spending Trends** — total spend rewritten as `orders × items/order × avg item
  price` and split between two years into those three drivers (log decomposition, so
  the pieces sum exactly). Indexed-to-2018 factor lines, a median-item-price series,
  an STL decomposition of monthly spend (trend / seasonal / noise) with a toggle to
  drop one-off large purchases, and a Holt-Winters forecast for the next 12 months.
- **Categories & Returns** — spend by category and year, the
  price-per-item distribution per category, return rate by category, why things
  were returned (stacked by category), and the standout purchases (priciest per year,
  priciest per category, items bought >= 3 times).
- **Whole Foods Grocery** — a small, intermittent grocery slice: spend and cart-size trends since 2021, subcategory mix, and an honest account of why a general grocery price index isn't supportable from this data.

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The repo ships a PII-stripped `data/processed_orders.csv`, so the app runs as-is.

## Methodology and caveats

Data limitations:

- **Categories are keyword-tagged from product names** — Amazon exports no category
  field. About 1% of spend and a handful of line items stay in "Other". Print books
  listed by title with no catchable keyword are recovered via their ISBN-shaped
  ASIN.
- **Returns are order-level.** From what I could tell, the returns export has no line-item key, so a return is attributed to its order's highest-spend category. A mixed order with one returned item is treated as fully returned.
- **Refunds are deduplicated.** The refund export repeats each refund once per
  internal retry; rows are collapsed to one per `(Order ID, amount, date)`. Some
  refunds aren't returns at all (item never arrived, refused at the door) and are
  tracked separately.
- **Grocery is a structural break.** Whole Foods delivery starts mid-2021 and is
  intermittent; it's excluded from the main trends page and gets its own section.
- **Monthly time-series work starts in 2018.** Earlier order volume (1–2 orders some
  months) is too sparse for monthly seasonality to mean anything.
- **Big-ticket purchases can be excluded.** A single item at or above the 99th
  percentile of price would bend the STL trend and widen the forecast, so the
  Spending Trends page drops those by default (toggle to include).
- **STL is descriptive, not causal.** The seasonal component is a local fit that drifts year to year and uses the whole series (future included). The Holt-Winters forecast is the causal view.
- **2026 is a partial year** (data through August) and is marked as such throughout.

## Notes and learnings

Things the data say, and changes I made once I'd looked closely.

### What the data said

- **My spend growth is a frequency story.** Splitting spend growth into
  `orders × items/order × avg price`, almost all of it is *ordering more often*.
  Cart size and item price barely moved - not what I expected going in.
- **Excluding grocery flipped the story.** Whole Foods is ~27% of line items but
  only ~5% of dollars (lots of ~\$5 items per order). Left in, items-per-order
  balloons and average price dips, but in reality the three factors only mean something over a consistent population.
- **March and July, not December, are the biggest seasonal months.** The
  "December = holiday spending" intuition does not apply to me; the STL
  seasonal component shows December as *below* trend in 2018–19 and
  only drifted positive recently.
- **The March spikes are coincidental.** Four of seven Marches sit at or below a normal
  month. The three big ones - 2023, 2025, 2026 - were each carried by a different
  category (Home & Kitchen, then Electronics, then Clothing). 
- **Returns are a clothing-fit problem.** 71% of clothing orders come back, and 20
  of 21 "fit / size" returns are clothing. "Changed my mind" is the one bucket led
  by Electronics and Home & Kitchen instead.

### Changes made after digging in

- Pulled Whole Foods grocery out of the Spending Trends page entirely and gave it its
  own page. Initially left in, the growth decomposition was mostly measuring the 2021 WF inclusion, not actual retail spending.
- Added the large purchase exclusion toggle (99th percentile of item price), with an
  expander listing exactly which purchases are dropped so the exclusion is
  auditable.
- Prototyped a rolling-12-month stacked area for the category mix, then removed it -
  the smoothing hid the monthly spike I was investigating.
- Restacked "why things came back" by category; the
  fit-size-is-clothing / changed-my-mind-is-electronics split only shows once the
  bars are subdivided.
- Learned STL is a two-sided smoother: March 2024's seasonal value nearly *tripled*
  as 2025–26 data arrived. The page now says so and points to the Holt-Winters
  forecast as the "what you'd have known at the time" view.

### Engineering gotchas

- A shared `apply_layout()` helper forced `hovermode="x unified"`, silently
  overriding any chart setting made before it. Six charts had the wrong hover
  behavior. `x unified` suits multi-line time series, not horizontal or stacked bars.
- The refund export repeats each refund once per internal retry; simply summing
  overcounts 2–3×. Deduped to one row per `(Order ID, amount, date)` and cross-checked
  against a separate scrape using a chrome plugin.
