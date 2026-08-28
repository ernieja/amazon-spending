"""
Quick smoke test for src/timeseries.py
"""

import pandas as pd
from src.timeseries import decompose, fit_holt_winters, forecast

df = pd.read_csv("data/processed_orders.csv")
df["Order Date"] = pd.to_datetime(df["Order Date"], format="ISO8601")
df["year_month"] = df["Order Date"].dt.tz_localize(None).dt.to_period("M").dt.to_timestamp()

monthly = df.groupby("year_month")["Total Amount"].sum()
full_idx = pd.date_range("2018-01-01", monthly.index.max(), freq="MS")
s = monthly.reindex(full_idx, fill_value=0.0)
s.index.freq = "MS"

print("=== STL decomposition (last 8 months) ===")
d = decompose(s, period=12)
print(d.tail(8).round(2))
print()

print("=== Holt-Winters forecast (next 12 months) ===")
fitted = fit_holt_winters(s, period=12)
fc = forecast(fitted, steps=12)
print(fc.round(2))
print()
print(f"Sum of next-12mo forecast: {fc['forecast'].sum():.2f}")
print(f"Actual last-12mo sum:      {s.iloc[-12:].sum():.2f}")
print()
print("If this ran without errors and the numbers look reasonable "
      "(forecast in the same ballpark as recent actuals), we're good to "
      "wire this into the Streamlit app.")
