"""
data_prep.py
Loads raw Amazon order/return exports, cleans them, and derives the fields.

Writes data/processed_orders.csv
"""

import re
import pandas as pd

pd.set_option("future.no_silent_downcasting", True)

RAW_ORDERS = "data/Order History.csv"
RAW_RETURNS = "data/Returns Status.csv"
RAW_REFUNDS = "data/Refund Details.csv"
OUT_PATH = "data/processed_orders.csv"

# Reversal reasons that mean an actual product return happened, as opposed to a
# refund for a carrier/billing issue where nothing was sent back.
RETURN_RELATED_REASONS = {"Customer return", "Item not satisfactory"}

PLACEHOLDERS = {"Not Applicable", "Not Available", "Not Provided"}

# Ordered so more specific keywords win before generic ones (e.g. "grill" before "kitchen").
CATEGORY_KEYWORDS = [
    ("Electronics & Accessories", [
        "cable", "charger", "usb", "batter", "bluetooth", "headphone", "earbud",
        "speaker", "camera", "monitor", "laptop", "ssd", "hdmi", "router", "adapter",
        "remote control", "electric", " led ", "led ", "watch", "kindle fire", "echo dot",
        "alexa", "phone holder", "phone case", "screen protector", "magsafe",
        "car mount", "power band", "hard drive", "external drive",
    ]),
    ("Clothing & Shoes", [
        "shirt", "dress", "jacket", "pant", "legging", "sock", "shoe", "sneaker",
        "boot", "sandal", "bra", "underwear", "sweater", "hoodie", "scarf", "glove",
        "hat", "cap ", "jean", "loafer", "flat", "heel", "flip flop", "slipper",
        "vest", "coat", "skirt", "romper", "swimsuit", "bikini",
    ]),
    ("Health & Beauty", [
        "vitamin", "supplement", "shampoo", "lotion", "sunscreen", "toothpaste",
        "skincare", "makeup", "razor", "deodorant", "soap", "serum", "cleanser",
        "cleansing", "moisturizer", "sheet mask", "essence", "toner", "spf",
        "hadalabo", "cosrx", "etude", "innisfree", "beauty", "hair dryer",
        "toothbrush", "nail",
    ]),
    ("Home & Kitchen", [
        "kitchen", "cookware", "pan", "pot ", "knife", "mug", "towel", "bedding",
        "pillow", "sheet set", "furniture", "lamp", "storage", "organizer", "rug",
        "curtain", "grill", "vacuum", "cleaning", "table", "chair", "desk", "shelf",
        "whisk", "baking mat", "zester", "grater", "jar", "cutting board",
        "air purifier", "water filter", "wiper blade", "shower", "faucet",
        "candle", "decor", "planter", "vase",
    ]),
    ("Food & Snacks", [
        "chews", "snack", "sparkling water", "candy", "chocolate", "coffee",
        "tea bag", "protein bar", "granola", "jerky", "spice", "seasoning",
        "sugar", "syrup", "sauce", "chip", "cracker", "pretzel", "nut butter",
    ]),
    ("Books & Media", ["book", "audible", "kindle edition", "novel", "paperback", "hardcover"]),
    ("Pet Supplies", ["dog ", "cat ", "pet ", "puppy", "kitten", "leash", "collar", "litter"]),
    ("Outdoors & Sporting", [
        "camp", "hiking", "backpack", "tent", "sleeping bag", "bike", "cycling",
        "fitness", "yoga", "exercise", "sport", "foliage pro", "fertilizer",
        "plant food", "garden",
    ]),
    ("Toys & Games", ["toy", "game", "puzzle", "lego", "paint by number", "xbox", "playstation"]),
    ("Office & Supplies", ["office", "notebook", "pen ", "pencil", "printer", "paper", "planner"]),
]


def clean_placeholders(df):
    return df.replace(list(PLACEHOLDERS), pd.NA)


def derive_category(product_name, is_grocery):
    if is_grocery:
        return "Grocery"
    if not isinstance(product_name, str):
        return "Other"
    name = product_name.lower()
    for category, keywords in CATEGORY_KEYWORDS:
        if any(kw in name for kw in keywords):
            return category
    return "Other"


def load_orders():
    df = pd.read_csv(RAW_ORDERS)
    df = clean_placeholders(df)
    df["Order Date"] = pd.to_datetime(df["Order Date"], format="ISO8601")
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], format="ISO8601", errors="coerce")
    df["is_grocery"] = df["Website"] == "panda01"
    df["category"] = [
        derive_category(name, grocery)
        for name, grocery in zip(df["Product Name"], df["is_grocery"])
    ]
    df["year"] = df["Order Date"].dt.year
    df["year_month"] = df["Order Date"].dt.tz_localize(None).dt.to_period("M").dt.to_timestamp()
    return df


def load_returns():
    df = pd.read_csv(RAW_RETURNS)
    df = clean_placeholders(df)
    for col in ["Contract Creation Date", "Date of Return", "Return Creation Date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format="ISO8601", errors="coerce")
    df["Return Amount"] = pd.to_numeric(df["Return Amount"], errors="coerce")
    return df


def load_refunds():
    df = pd.read_csv(RAW_REFUNDS)
    df = clean_placeholders(df)
    df["Refund Amount"] = pd.to_numeric(df["Refund Amount"], errors="coerce")
    df["Refund Date"] = pd.to_datetime(df["Refund Date"], format="ISO8601", errors="coerce")
    df["is_return_related_refund"] = df["Reversal Reason"].isin(RETURN_RELATED_REASONS)
    return df


def merge_orders_and_returns(orders, returns, refunds):
    # Returns file has no ASIN/line-item key, only Order ID, so a return can only
    # be attributed to the *order*, not a specific item within a multi-item order.
    # That's a real limitation of this data.
    returns_by_order = (
        returns.groupby("Order ID")
        .agg(
            is_returned=("Order ID", "size"),
            return_reasons=("Return Reason", lambda s: "; ".join(sorted(set(s.dropna())))),
            return_amount=("Return Amount", "sum"),
        )
        .reset_index()
    )
    returns_by_order["is_returned"] = True

    # Refund Details is the authoritative dollar figure.
    refunds_by_order = (
        refunds.groupby("Order ID")
        .agg(
            refund_amount=("Refund Amount", "sum"),
            refund_date=("Refund Date", "max"),
            is_return_related_refund=("is_return_related_refund", "any"),
            reversal_reasons=("Reversal Reason", lambda s: "; ".join(sorted(set(s.dropna())))),
        )
        .reset_index()
    )

    merged = orders.merge(returns_by_order, on="Order ID", how="left")
    merged["is_returned"] = merged["is_returned"].fillna(False).astype(bool)
    merged = merged.merge(refunds_by_order, on="Order ID", how="left")
    merged["refund_amount"] = merged["refund_amount"].fillna(0.0)
    merged["is_return_related_refund"] = (
        merged["is_return_related_refund"].fillna(False).astype(bool)
    )
    # A refund can happen without a return record ever being logged (e.g. an
    # "Item not received" claim) - treat that as refunded-but-not-returned.
    merged["is_refunded"] = merged["refund_amount"] > 0
    return merged


def main():
    orders = load_orders()
    returns = load_returns()
    refunds = load_refunds()
    merged = merge_orders_and_returns(orders, returns, refunds)
    merged.to_csv(OUT_PATH, index=False)

    print(f"Loaded {len(orders)} order line items ({orders['Order ID'].nunique()} unique orders)")
    print(f"Loaded {len(returns)} return records")
    print(f"Loaded {len(refunds)} refund records")
    print(f"Matched {merged['is_returned'].sum()} order line items to a return "
          f"({merged.loc[merged['is_returned'], 'Order ID'].nunique()} unique orders)")
    n_refunded_orders = merged.loc[merged['is_refunded'], 'Order ID'].nunique()
    n_return_refunded = merged.loc[merged['is_return_related_refund'], 'Order ID'].nunique()
    print(f"Matched {n_refunded_orders} unique orders to a completed refund "
          f"(total ${merged.drop_duplicates('Order ID')['refund_amount'].sum():.2f})")
    print(f"  of which {n_return_refunded} orders' refunds were return-related; "
          f"the rest were shipping/billing issues with nothing sent back")
    print()
    print("Category breakdown:")
    print(merged["category"].value_counts())
    print()
    print(f"Wrote cleaned data to {OUT_PATH}")


if __name__ == "__main__":
    main()
