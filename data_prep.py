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

GROCERY_SUBCATEGORY_KEYWORDS = [
    ("Produce", [
        "produce", "banana", "grape", "lettuce", "spinach", "onion", "tomato",
        "pepper", "broccoli", "avocado", "lemon", "lime", "melon", "berry",
        "mango", "pineapple", "cucumber", "carrot", "potato", "cilantro",
        "basil", "kale", "nectarine", "pumpkin", "shallot", "garlic", "sage",
        "mushroom", "mandarin", "brussels", "peas",
    ]),
    ("Meat & Seafood", [
        "chicken", "beef", "pork", "turkey breast", "salmon", "shrimp", "sausage",
        "bacon", "steak", "drumstick", "ground beef", "fish", "brisket", "cod",
    ]),
    ("Dairy, Eggs & Alt-Protein", [
        "milk", "cheese", "butter", "yogurt", "egg", "cream", "tofu", "feta",
    ]),
    ("Prepared Foods & Bakery", [
        "kitchens", "soup", "meal", "loaf", "bread", "sandwich", "rotisserie",
        "sushi", "pizza", "quiche", "prepared foods", "macaron", "bakery",
    ]),
    ("Pantry & Dry Goods", [
        "flour", "pasta", "rice", "beans", "salsa", "sauce", "oil", "vinegar",
        "spice", "seasoning", "canned", "tortilla", "okra", "mustard", "mayo",
        "dill", "almond",
    ]),
    ("Beverages & Coffee", [
        "coffee", "espresso", "latte", "juice", "tea", "soda", "kombucha", "nog",
    ]),
    ("Snacks & Sweets", [
        "chip", "cracker", "cookie", "chocolate", "candy", "pretzel",
    ]),
    ("Alcohol", ["wine", "beer", "sauvignon", "valpolicella", "cabernet", "chardonnay", "ipa"]),
]

PLACEHOLDERS = {"Not Applicable", "Not Available", "Not Provided"}

# Keyword tagging
CATEGORY_KEYWORDS = [
    ("Electronics & Accessories", [
        # phrases
        "remote control", "phone case", "phone holder", "phone mount",
        "phone stand", "car mount", "car charger", "wall charger", "usb charger",
        "fast charger", "gan charger", "screen protector",
        "hard drive", "external drive", "usb c", "type c", "usb hub",
        "power bank", "power strip", "surge protector", "wall tap",
        "travel adapter", "travel adaptor", "power adapter", "aux cable",
        "aux cord", "audio cable", "audio adapter", "headphone adapter",
        "charging cable", "charging cord", "usb cable", "led backlight",
        "led light", "string lights", "light bar", "light kit",
        "tv wall mount", "monitor mount", "monitor arm", "monitor light",
        "laptop stand", "laptop riser", "notebook stand", "memory card",
        "micro sd", "microsd", "sd card", "smart plug", "smart bulb",
        "wifi outlet", "fire tv", "tv stick", "streaming device",
        "instant film", "security camera", "security cam", "indoor cam",
        "sewing machine", "bike light", "kindle 2022", "kindle case",
        "kindle paperwhite", "e reader",
        # words
        "cable", "charger", "usb", "bluetooth", "wifi", "headphone",
        "headphones", "earbud", "earbuds", "earphones", "headset", "speaker",
        "speakers", "soundbar", "amplifier", "preamp", "phono", "tv",
        "television", "camera", "webcam", "gopro", "drone", "monitor",
        "laptop", "macbook", "ssd", "hdd", "hdmi", "router", "modem",
        "adapter", "adaptor", "dongle", "keyboard", "mouse", "trackpad",
        "ipad", "iphone", "ipod", "smartphone", "airpods", "airtag",
        "kindle", "projector", "turntable", "tripod", "gimbal", "battery",
        "batteries", "powerbank", "chromecast", "roku", "trimmer", "shaver",
        "pixel", "ringke", "spigen", "caseology", "otterbox", "polaroid",
        "behringer", "earplug", "earplugs",
        "audio technica", "instant film", "600 film",
    ]),
    ("Clothing & Shoes", [
        # phrases
        "flip flop", "sleep pants", "baseball cap", "sun hat", "dad hat",
        "panel cap", "running shoes", "soccer shoe", "skateboard shoe",
        "ankle bootie", "nipple cover", "breast cover", "sports bra",
        # words
        "shirt", "tee", "blouse", "dress", "gown", "cheongsam", "jacket",
        "coat", "parka", "pants", "leggings", "jeans", "jean", "shorts",
        "trunks", "skirt", "romper", "sock", "socks", "sweater", "hoodie",
        "sweatshirt", "cardigan", "flannel", "scarf", "gloves", "mittens",
        "hat", "cap", "beanie", "shoe", "shoes", "sneaker", "sneakers",
        "boot", "boots", "bootie", "sandal", "sandals", "loafer", "loafers",
        "heels", "flats", "slipper", "slippers", "bra", "underwear",
        "pasties", "swimsuit", "bikini", "bandana", "adidas", "nike",
        "reebok", "puma", "asics", "vans", "keds", "emerica", "birkenstock",
        "nydj", "clarks",
    ]),
    ("Pet Supplies", [
        "cat food", "dog food", "cat treat", "dog treat", "cat feeder",
        "dog feeder", "pet feeder", "cat fountain", "water fountain",
        "pet fountain", "cat litter", "litter box", "litter mat",
        "litter genie", "scratching post", "scratching board", "cat scratcher",
        "cat tree", "cat climber", "cat window", "cat perch", "window perch",
        "for cats", "for dogs", "cats and dogs", "dogs and cats", "dog bed",
        "cat bed", "pet bed", "dog playpen", "dog crate", "dog leash",
        "pet mat", "puppy", "kitten", "cats", "dogs", "nulo",
    ]),
    ("Baby & Kids", [
        "diaper", "diapers", "crib", "playpen", "play yard", "stroller",
        "pacifier", "onesie", "baby bib", "drool bib", "baby bottle",
        "nursing", "baby wipes", "diaper rash", "butt paste",
    ]),
    ("Health & Beauty", [
        "hand sanitizer", "eye cream", "eye serum", "eye ointment", "lip balm",
        "face milk", "hand soap", "insect repellent", "bug spray",
        "acne patch", "pimple patch", "hydrocolloid", "sheet mask",
        "hair dryer", "korean skin care", "korean skincare", "body scrubber",
        "exfoliating shower", "shower towel", "loofah", "sleep mask",
        "eye mask", "eau de", "de toilette", "de parfum",
        "vitamin", "supplement", "shampoo", "conditioner", "lotion",
        "sunscreen", "sunblock", "spf", "toothpaste", "toothbrush",
        "skincare", "makeup", "mascara", "lipstick", "razor", "deodorant",
        "serum", "cleanser", "moisturizer", "essence", "toner", "sebum",
        "hadalabo", "cosrx", "etude", "innisfree", "aestura", "biore",
        "curel", "picaridin", "famotidine", "pepcid", "heartburn",
        "antigen", "whitestrips", "whitestrip", "babyliss", "babylisspro",
        "cologne", "perfume", "fragrance", "vibrator",
    ]),
    ("Home & Kitchen", [
        # phrases
        "cutting board", "baking mat", "baking sheet", "cookie sheet",
        "sheet pan", "cake pan", "loaf pan", "bread pan", "muffin pan",
        "frying pan", "saute pan", "saucepan", "cooling rack", "baking rack",
        "pizza steel", "baking steel", "cast iron", "dutch oven",
        "measuring cup", "measuring spoon", "mixing bowl", "salad bowl",
        "bench scraper", "pastry brush", "basting brush", "icing spatula",
        "honing steel", "can opener", "bottle opener", "kitchen scale",
        "food scale", "coffee scale", "espresso scale", "coffee grinder",
        "spice grinder", "coffee mill", "burr grinder", "hand blender",
        "coffee maker", "espresso maker", "espresso machine", "french press",
        "pour over", "coffee filter", "coffee dripper", "filter basket",
        "puck screen", "dosing funnel", "dosing ring", "gooseneck kettle",
        "moka pot", "descaling", "water filter", "air filter", "air purifier",
        "refrigerator filter", "vacuum cleaner", "wiper blade", "shower head",
        "shower arm", "shower caddy", "shower organizer", "shower shelf",
        "bath mat", "shower mat", "diatomaceous earth", "paper towel",
        "towel holder", "towel bar", "sheet set", "duvet cover",
        "picture frame", "poster frame", "poster hanger", "photo frame",
        "wall decor", "metal sign", "door mat", "entrance mat", "floor mat",
        "draft stopper", "door draft", "water bottle", "coffee table",
        "side table", "end table", "plant stand", "floating shelf",
        "floating shelves", "canning jar", "storage container", "storage bag",
        "blackout curtain", "hand towel", "dish towel", "microfiber cloth",
        "cleaning cloth", "cleaning towel", "spray bottle", "perfume atomizer",
        "command hook", "command clip", "command strip", "command decorating",
        "vent deflector", "air deflector", "heat deflector", "sun shade",
        "windshield sun", "keyboard stand", "pocket scale", "gram scale",
        "digital scale", "nordic ware", "half sheet", "meat thermometer",
        "food thermometer", "instant read", "piping tip", "piping nozzle",
        "cake decorating", "squeeze bottle", "dressing bottle",
        "wood frame", "metal frame", "rain x", "glass treatment",
        "whetstone", "sharpening stone", "kuhn rikon", "pitcher filter",
        "pur filter", "pur water filter",
        # words
        "kitchen", "cookware", "skillet", "wok", "knife", "cleaver", "mug",
        "tumbler", "kettle", "teapot", "whisk", "zester", "grater", "colander",
        "spatula", "ladle", "tongs", "corkscrew", "trivet", "bakeware",
        "ramekin", "banneton", "brotform", "pyrex", "tupperware", "jar",
        "kitchenaid", "crockpot", "toaster", "microwave", "blender", "grinder",
        "tamper", "portafilter", "aeropress", "chemex", "kalita", "hario",
        "airfryer", "bedding", "pillow", "pillowcase", "comforter", "duvet",
        "mattress", "furniture", "sofa", "couch", "dresser", "nightstand",
        "shelf", "shelves", "bookshelf", "bookcase", "lamp", "curtain",
        "curtains", "rug", "vase", "candle", "incense", "planter", "faucet",
        "showerhead", "bidet", "vacuum", "roomba", "swiffer", "dehumidifier",
        "humidifier", "footrest", "turntable", "shaker", "oxo", "kotobuki",
        "command",
    ]),
    ("Crafts & Hobby", [
        "crochet", "knitting", "embroidery", "cross stitch", "cross-stitch",
        "needlepoint", "amigurumi", "safety eyes", "quilting", "sewing kit",
        "yarn", "skein", "model paint", "paint brush set", "acrylic paint",
        "magnetic poetry", "polymer clay", "scrapbook", "cabochon",
        "nail craft", "nail art",
    ]),
    ("Books & Media", [
        "a novel", "the novel", "audible", "audiobook", "kindle edition",
        "paperback", "hardcover", "coloring book", "cookbook",
        "modern library", "broadview", "dover books", "signed edition",
        "anniversary edition", "vinyl", "poetry", "poems", "essays",
        "dramatised", "blackwell readings", "box set",
        "book", "novel", "textbook", "handbook", "edition",
    ]),
    ("Food & Snacks", [
        "sparkling water", "protein bar", "nut butter", "tea bag",
        "hot sauce", "chili sauce", "ginger chews", "snow sugar",
        "chews", "snack", "candy", "granola", "jerky", "popcorn",
        "chips", "crackers", "pretzels", "kombucha", "seltzer",
        "malt powder", "barley malt",
    ]),
    ("Outdoors & Sporting", [
        "sleeping bag", "trekking pole", "hiking pole", "water reservoir",
        "hydration bladder", "hydration pack", "bike pump", "bicycle pump",
        "bike tube", "bicycle tube", "inner tube", "bike helmet",
        "cycling helmet", "bike lock", "u lock", "bike rack", "bike storage",
        "swim goggle", "swim goggles", "ski goggles", "yoga mat",
        "exercise mat", "foam mat", "resistance band", "jump rope",
        "travel pillow", "camping pillow", "hip pack", "waist pack",
        "waist pouch", "foliage pro", "plant food", "plant nutrient",
        "climbing", "camp", "camping", "backpacking", "backpack", "hiking",
        "hammock", "tent", "canteen", "carabiner", "kayak", "paddle",
        "snorkel", "wetsuit", "bonsai", "fertilizer", "exercise", "garden",
        "greenhouse", "camelbak", "hydrapak", "katadyn", "osprey", "flipbelt",
        "helmet", "floor pump", "lezyne", "presta", "schrader",
    ]),
    ("Toys & Games", [
        "paint by number", "board game", "jigsaw puzzle", "building set",
        "building blocks", "action figure", "plush toy", "stuffed animal",
        "rubik", "funko", "amiibo", "trading card",
        "toy", "game", "puzzle", "lego", "playmobil", "xbox", "playstation",
        "nintendo", "amigo",
    ]),
    ("Office & Supplies", [
        "ink cartridge", "toner cartridge", "printer paper", "copy paper",
        "sticky notes", "index cards", "file folder", "binder clips",
        "desk organizer", "label maker", "whiteboard", "stapler",
        "tax software", "software",
        "notebook", "planner", "pencil", "highlighter", "printer",
    ]),
]


def clean_placeholders(df):
    return df.replace(list(PLACEHOLDERS), pd.NA)


def derive_grocery_subcategory(product_name):
    """Finer-grained tagging within Grocery (Whole Foods/panda01) items only.
    Same keyword-matching approach and same caveat as derive_category: a real
    long tail stays in "Other Grocery" rather than being force-fit."""
    if not isinstance(product_name, str):
        return "Other Grocery"
    low = product_name.lower()
    if "refund" in low or "customer services" in low:
        return "Non-item (fee/refund)"
    for subcat, keywords in GROCERY_SUBCATEGORY_KEYWORDS:
        if any(kw in low for kw in keywords):
            return subcat
    return "Other Grocery"


def derive_category(product_name, is_grocery, website=None):
    if is_grocery:
        return "Grocery"
    if website == "Audible":
        return "Books & Media"  # audiobooks, mostly listed by title with no keyword
    if not isinstance(product_name, str):
        return "Other"
    norm = re.sub(r"[^a-z0-9]+", " ", product_name.lower()).strip()
    tokens = set(norm.split())
    for category, keywords in CATEGORY_KEYWORDS:
        for kw in keywords:
            if " " in kw:
                if kw in norm:
                    return category
            elif kw in tokens or (kw + "s") in tokens:
                return category
    return "Other"


def load_orders():
    df = pd.read_csv(RAW_ORDERS)
    df = clean_placeholders(df)
    df["Order Date"] = pd.to_datetime(df["Order Date"], format="ISO8601")
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], format="ISO8601", errors="coerce")
    df["is_grocery"] = df["Website"] == "panda01"
    df["category"] = [
        derive_category(name, grocery, site)
        for name, grocery, site in zip(
            df["Product Name"], df["is_grocery"], df["Website"]
        )
    ]
    df["grocery_subcategory"] = df["Product Name"].where(df["is_grocery"]).apply(
        derive_grocery_subcategory
    )
    df.loc[~df["is_grocery"], "grocery_subcategory"] = pd.NA
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

    # The Refund Details export repeats each refund once per internal retry: the
    # "Creation Date" differs but the amount and refund date do not. Summing the
    # raw rows per order over-counts refunds 2-3x (some orders end up with a
    # "refund" larger than the order itself). Collapse to one row per distinct
    # (Order ID, Refund Amount, Refund Date). Cross-checked against an
    # independent order-history scrape whose own pre-cleaned refund totals match
    # this exactly for 2024 and 2025. Trade-off: two genuinely separate refunds
    # of the same amount on the same day for one order would merge, but that is
    # far rarer than the retry duplication being removed here.
    #
    # Retry rows for one refund sometimes carry different reasons (e.g. an early
    # "Customer return" row and a later "Account adjustment" row). Sort the
    # return-related rows first so drop_duplicates keeps the more specific
    # reason and the return-related flag survives.
    before = len(df)
    df = (
        df.sort_values("is_return_related_refund", ascending=False, kind="stable")
        .drop_duplicates(subset=["Order ID", "Refund Amount", "Refund Date"])
    )
    dropped = before - len(df)
    if dropped:
        print(f"load_refunds: dropped {dropped} duplicate refund rows "
              f"({before} -> {len(df)})")

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
    print(f"Loaded {len(refunds)} refund records (after de-duplication)")
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
